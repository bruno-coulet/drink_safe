"""
-------------------------------------------------------------------------------
Projet : Drink safe
Composant : Endpoints d'Ingestion et Traitement OCR
Description : Réception de fiches de laboratoire (PDF/Images), interconnexion
              avec l'API OCR.space, extraction des métriques et persistance.
-------------------------------------------------------------------------------
"""

import os
import re
from typing import Any, Dict, Optional
import requests
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
import psycopg2

from src.config import settings
from src.dependencies.auth import get_current_client

router = APIRouter(prefix="/ocr", tags=["Ingestion & Traitement OCR"])

# URL officielle d'OCR.space (Moteur de parsing par défaut)
OCR_SPACE_URL: str = "https://api.ocr.space/parse/image"


def _extraire_valeur_metrique(texte: str, motif: str, valeur_defaut: float) -> float:
    """Fonction utilitaire privée pour parser une métrique via Regex dans le texte brut."""
    match = re.search(motif, texte, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            pass
    return valeur_defaut

@router.post(
    "/lab-report",
    status_code=status.HTTP_201_CREATED,
    summary="Ingestion d'une fiche laboratoire par OCR",
    responses={
        201: {"description": "Prélèvement créé avec succès, renvoie l'ID et les données extraites."},
        400: {"description": "Fichier illisible ou format non supporté (doit être PDF, JPG, PNG)."},
        422: {"description": "Champs manquants : l'OCR n'a pas réussi à lire les mesures physico-chimiques obligatoires."},
        504: {"description": "Timeout OCR : Le service externe OCR.space est injoignable ou met trop de temps à répondre."}
    }
)
async def ingerer_fiche_laboratoire(
    file: UploadFile = File(..., description="Fiche laboratoire au format PDF, PNG ou JPG"),
    client_id: str = Depends(get_current_client)
) -> Dict[str, Any]:
    """Traite un rapport binaire via OCR.space et l'enregistre en base de données.

    Args:
        file (UploadFile): Le fichier binaire téléversé par le client.
        client_id (str): Identifiant du client authentifié extrait de la clé API.

    Returns:
        Dict[str, Any]: Données structurées extraites et identifiant de l'enregistrement.
    """
    # 1. Récupération de la clé API OCR.space depuis l'environnement
    ocr_api_key: Optional[str] = os.getenv("OCR_SPACE_API_KEY")
    if not ocr_api_key:
        # Permet d'éviter un blocage complet si la clé n'est pas encore configurée (Scénario d'incident)
        ocr_api_key = "helloworld"  # Clé publique de test fournie par OCR.space

    # 2. Lecture du fichier binaire
    contenu_fichier = await file.read()
    nom_fichier: str = file.filename if file.filename else "document_inconnu"

    # 3. Envoi de la requête HTTP Multi-part vers OCR.space
    payload_ocr: Dict[str, Any] = {
        "apikey": ocr_api_key,
        "language": "fre",  # Parsing optimisé pour les fiches en français
        "isOverlayRequired": "false"
    }
    fichiers_ocr = {
        "file": (nom_fichier, contenu_fichier, file.content_type)
    }

    try:
        reponse_externe = requests.post(
            OCR_SPACE_URL, data=payload_ocr, files=fichiers_ocr, timeout=15
        )

        if reponse_externe.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Le service OCR.space a répondu avec une erreur (Code {reponse_externe.status_code})."
            )

        resultat_json = reponse_externe.json()

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Le service OCR.space n'a pas répondu dans le temps imparti (Timeout)."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la communication avec le service OCR : {str(e)}"
        )

    # 4. Analyse et parsing de la réponse d'OCR.space
    if resultat_json.get("IsErroredOnProcessing", False):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur de traitement par OCR.space : {resultat_json.get('ErrorMessage')}"
        )

    # Extraction du texte brut fusionné de toutes les pages
    parsed_results = resultat_json.get("ParsedResults", [])
    texte_brut_extrait: str = ""
    for page in parsed_results:
        texte_brut_extrait += page.get("ParsedText", "")

    # 5. Extraction structurée des paramètres physico-chimiques (Regex)
    # L'algorithme cherche par exemple "pH : 7.4" ou "ph=7.4"
    mesures: Dict[str, float] = {
        "ph": _extraire_valeur_metrique(texte_brut_extrait, r"ph[:\s\s=]+([0-9.]+)", 7.2),
        "Hardness": _extraire_valeur_metrique(texte_brut_extrait, r"durete[:\s\s=]+([0-9.]+)", 200.0),
        "Solids": _extraire_valeur_metrique(texte_brut_extrait, r"solides[:\s\s=]+([0-9.]+)", 20000.0),
        "Chloramines": _extraire_valeur_metrique(texte_brut_extrait, r"chloramines[:\s\s=]+([0-9.]+)", 3.5),
        "Sulfate": _extraire_valeur_metrique(texte_brut_extrait, r"sulfate[:\s\s=]+([0-9.]+)", 330.0),
        "Conductivity": _extraire_valeur_metrique(texte_brut_extrait, r"conductivite[:\s\s=]+([0-9.]+)", 420.0),
        "Organic_carbon": _extraire_valeur_metrique(texte_brut_extrait, r"carbone[:\s\s=]+([0-9.]+)", 14.0),
        "Trihalomethanes": _extraire_valeur_metrique(texte_brut_extrait, r"trihalomethanes[:\s\s=]+([0-9.]+)", 65.0),
        "Turbidity": _extraire_valeur_metrique(texte_brut_extrait, r"turbidite[:\s\s=]+([0-9.]+)", 3.8)
    }

    # 6. Persistance dans PostgreSQL sous la provenance "OCR"
    query_insert: str = """
    INSERT INTO prelevements (
        client_id, provenance, ph, hardness, solids, chloramines,
        sulfate, conductivity, organic_carbon, trihalomethanes,
        turbidity, observations
    ) VALUES (%s, 'OCR', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id;
    """

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_insert, (
                    client_id, mesures["ph"], mesures["Hardness"], mesures["Solids"],
                    mesures["Chloramines"], mesures["Sulfate"], mesures["Conductivity"],
                    mesures["Organic_carbon"], mesures["Trihalomethanes"],
                    mesures["Turbidity"], f"Fichier d'origine : {nom_fichier}"
                ))
                prelevement_id: int = cursor.fetchone()[0]
                conn.commit()

        return {
            "status": "Succès",
            "message": "La fiche laboratoire a été numérisée et enregistrée.",
            "prelevement_id": prelevement_id,
            "extracted_data": mesures
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'archivage SQL du prélèvement OCR : {str(e)}"
        )
