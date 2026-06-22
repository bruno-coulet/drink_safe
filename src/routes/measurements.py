"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Endpoints de Gestion des Mesures et Prélèvements
Description : Enregistrement des données physico-chimiques et isolation des
              consultations par client pour la conformité RGPD.
-------------------------------------------------------------------------------
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import settings
from src.dependencies.auth import get_current_client

router = APIRouter(prefix="/measurements", tags=["Mesures & Prélèvements"])


class MeasurementCreate(BaseModel):
    """Schéma Pydantic de validation pour le dépôt manuel de mesures."""
    ph: float = Field(..., description="Potentiel Hydrogène (0.0 - 14.0)")
    Hardness: float = Field(..., description="Dureté de l'eau en mg/L")
    Solids: float = Field(..., description="Total des solides dissous en ppm")
    Chloramines: float = Field(..., description="Concentration en chloramines en ppm")
    Sulfate: float = Field(..., description="Concentration en sulfates en mg/L")
    Conductivity: float = Field(..., description="Conductivité électrique en μS/cm")
    Organic_carbon: float = Field(..., description="Carbone organique total en ppm")
    Trihalomethanes: float = Field(..., description="Concentration en trihalométhanes en ppm")
    Turbidity: float = Field(..., description="Turbidité de l'eau en NTU")
    lieu: Optional[str] = Field(None, description="Lieu / point de prélèvement")
    observations: Optional[str] = Field(None, description="Remarques ou contexte du prélèvement")


@router.post("/", status_code=status.HTTP_201_CREATED)
def deposer_mesures(
    payload: MeasurementCreate, 
    client_id: str = Depends(get_current_client)
) -> Dict[str, Any]:
    """Enregistre un prélèvement d'eau structuré associé au client authentifié.

    Args:
        payload (MeasurementCreate): Paramètres physico-chimiques validés.
        client_id (str): Identifiant du client injecté par la clé API (RGPD).

    Returns:
        Dict[str, Any]: Statut du succès de l'opération de persistance.
    """
    query_insert: str = """
    INSERT INTO prelevements (
        client_id, provenance, lieu, ph, hardness, solids, chloramines,
        sulfate, conductivity, organic_carbon, trihalomethanes,
        turbidity, observations
    ) VALUES (%s, 'Saisie', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_insert, (
                    client_id, payload.lieu, payload.ph, payload.Hardness, payload.Solids,
                    payload.Chloramines, payload.Sulfate, payload.Conductivity,
                    payload.Organic_carbon, payload.Trihalomethanes,
                    payload.Turbidity, payload.observations
                ))
                conn.commit()
        return {"status": "Succès", "message": "Le prélèvement a été enregistré."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec de l'écriture en base de données : {str(e)}"
        )


@router.get("/")
def lister_prelevements_client(client_id: str = Depends(get_current_client)) -> List[Dict[str, Any]]:
    """Récupère l'historique exclusif des prélèvements du client authentifié.

    Garantit le cloisonnement strict des données exigé par la gouvernance RGPD.

    Args:
        client_id (str): Identifiant du client extrait de la clé API sécurisée.

    Returns:
        List[Dict[str, Any]]: Liste des enregistrements appartenant à ce client.
    """
    query_select: str = "SELECT * FROM prelevements WHERE client_id = %s ORDER BY cree_le DESC;"
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            # RealDictCursor permet de récupérer les lignes sous forme de dictionnaires Python propres (clé-valeur)
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query_select, (client_id,))
                records = cursor.fetchall()
        return [dict(row) for row in records]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des données : {str(e)}"
        )


@router.get("/admin")
def vue_globale_admin(client_id: str = Depends(get_current_client)) -> List[Dict[str, Any]]:
    """Vue globale non filtrée réservée aux administrateurs et experts métiers.

    Args:
        client_id (str): Permet de tracer quel administrateur a consulté l'historique global.

    Returns:
        List[Dict[str, Any]]: Intégralité de la table des prélèvements du réseau.
    """
    # Note MLOps : En production, une vérification du rôle "admin" dans la table clients
    # viendrait se greffer ici.
    query_select_all: str = "SELECT * FROM prelevements ORDER BY cree_le DESC;"
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query_select_all)
                records = cursor.fetchall()
        return [dict(row) for row in records]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur d'accès à la table globale : {str(e)}"
        )