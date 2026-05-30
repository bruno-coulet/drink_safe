"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Endpoints de Gestion des Clients
Description : Routes API pour l'enregistrement des entreprises clientes et la
              génération/attribution de clés API sécurisées.
-------------------------------------------------------------------------------
"""

import secrets
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import psycopg2

from src.config import settings

# Initialisation du routeur FastAPI pour le sous-module clients
router = APIRouter(prefix="/clients", tags=["Clients & Sécurité"])


class ClientCreate(BaseModel):
    """Schéma Pydantic de validation pour la création d'un client."""
    client_id: str = Field(..., max_length=50, description="Identifiant unique du client (ex: LOR_EAU_01)")
    denomination: str = Field(..., max_length=100, description="Nom officiel ou raison sociale de l'entité")
    adresse: str = Field(..., description="Adresse postale complète du client")


@router.post("/", status_code=status.HTTP_201_CREATED)
def inscrire_nouveau_client(payload: ClientCreate) -> Dict[str, Any]:
    """Inscrit un client en base de données et lui génère une clé API unique.

    Args:
        payload (ClientCreate): Données d'inscription validées par Pydantic.

    Returns:
        Dict[str, Any]: Confirmation contenant la clé API générée (à ne fournir qu'une fois).
    """
    # Génération d'une clé API hautement sécurisée et cryptographique
    generated_api_key: str = f"wf_live_{secrets.token_urlsafe(32)}"

    query_insert: str = """
    INSERT INTO clients (client_id, denomination, adresse, api_key)
    VALUES (%s, %s, %s, %s);
    """

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_insert, (
                    payload.client_id,
                    payload.denomination,
                    payload.adresse,
                    generated_api_key
                ))
                conn.commit()
                
        return {
            "status": "Succès",
            "message": "Le client a été enregistré avec succès.",
            "client_id": payload.client_id,
            "api_key": generated_api_key,
            "instruction": "Conservez cette clé précieusement, elle ne sera plus affichée."
        }

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'identifiant client '{payload.client_id}' ou une clé API similaire existe déjà."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'accès à la base de données : {str(e)}"
        )
    

@router.get("/", status_code=status.HTTP_200_OK)
def lister_clients() -> Dict[str, Any]:
    """Récupère la liste de tous les clients enregistrés (Vue Administrateur)."""
    query_select: str = "SELECT client_id, denomination, adresse, cree_le FROM clients;"
    
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_select)
                lignes = cursor.fetchall()
                
        # Formatage des résultats pour le JSON
        liste_clients = [
            {
                "client_id": row[0],
                "denomination": row[1],
                "adresse": row[2],
                "cree_le": row[3].isoformat() if row[3] else None
            }
            for row in lignes
        ]
        
        return {
            "status": "Succès",
            "total_clients": len(liste_clients),
            "clients": liste_clients
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la lecture de la base de données : {str(e)}"
        )