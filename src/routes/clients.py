"""
-------------------------------------------------------------------------------
Projet : Drink safe
Composant : Endpoints de Gestion des Clients
Description : Routes API pour l'enregistrement, la consultation et la
              suppression des clients, ainsi que la gestion du cycle de vie
              des clés API (révocation et régénération).
              Les clés sont stockées hashées (SHA-256) — la valeur brute
              n'est retournée qu'à la création ou à la régénération.
-------------------------------------------------------------------------------
"""

import secrets
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import settings
from src.dependencies.auth import get_current_client, hacher_cle

# Initialisation du routeur pour les clients
router = APIRouter(prefix="/clients", tags=["Clients & Sécurité"])

# Définition de l'en-tête de sécurité attendu (exigé par la spec technique)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


class ClientCreate(BaseModel):
    """Schéma Pydantic de validation pour la création d'un client."""
    client_id: str = Field(..., max_length=50, description="Identifiant unique du client (ex: LOR_EAU_01)")
    denomination: str = Field(..., max_length=100, description="Nom officiel ou raison sociale de l'entité")
    adresse: str = Field(..., description="Adresse postale complète du client")


@router.post("/", status_code=status.HTTP_201_CREATED)
def inscrire_nouveau_client(payload: ClientCreate) -> Dict[str, Any]:
    """Inscrit un client en base de données et lui génère une clé API unique.

    La clé brute est retournée une seule fois dans la réponse et n'est jamais
    persistée en clair — seul son hash SHA-256 est stocké en BDD.

    Args:
        payload: Données d'inscription validées par Pydantic.

    Returns:
        Confirmation contenant la clé API brute (à conserver, affichée une fois).
    """
    cle_brute: str = f"wf_live_{secrets.token_urlsafe(32)}"

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
                    hacher_cle(cle_brute),
                ))
                conn.commit()

        return {
            "status": "Succès",
            "message": "Client enregistré. Conservez cette clé — elle ne sera plus affichée.",
            "client_id": payload.client_id,
            "api_key": cle_brute,
        }

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'identifiant '{payload.client_id}' existe déjà."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur BDD : {str(e)}"
        )


@router.get("/", status_code=status.HTTP_200_OK)
def lister_clients() -> Dict[str, Any]:
    """Récupère la liste de tous les clients enregistrés (vue administrateur)."""
    query_select: str = "SELECT client_id, denomination, adresse, cree_le FROM clients;"

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_select)
                lignes = cursor.fetchall()

        return {
            "status": "Succès",
            "total_clients": len(lignes),
            "clients": [
                {
                    "client_id": row[0],
                    "denomination": row[1],
                    "adresse": row[2],
                    "cree_le": row[3].isoformat() if row[3] else None,
                }
                for row in lignes
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur BDD : {str(e)}"
        )


@router.delete("/{client_id}", status_code=status.HTTP_200_OK)
def supprimer_client(
    client_id: str,
    _: str = Depends(get_current_client),
) -> Dict[str, Any]:
    """Supprime un client et l'ensemble de ses données associées.

    Les prélèvements liés sont supprimés en cascade (contrainte FK).
    Les journaux d'accès (action_logs) sont conservés pour l'audit RGPD.

    Args:
        client_id: Identifiant du client à supprimer.

    Returns:
        Confirmation de suppression avec le nombre de prélèvements supprimés.

    Raises:
        HTTPException: 404 si le client n'existe pas.
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT client_id FROM clients WHERE client_id = %s;",
                    (client_id,)
                )
                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Client '{client_id}' introuvable."
                    )

                cursor.execute(
                    "SELECT COUNT(*) FROM prelevements WHERE client_id = %s;",
                    (client_id,)
                )
                row = cursor.fetchone()
                nb_prelevements: int = row[0] if row else 0

                cursor.execute(
                    "DELETE FROM prelevements WHERE client_id = %s;",
                    (client_id,)
                )
                cursor.execute(
                    "DELETE FROM clients WHERE client_id = %s;",
                    (client_id,)
                )
                conn.commit()

        return {
            "status": "Succès",
            "client_id": client_id,
            "prelevements_supprimes": nb_prelevements,
            "note": "Les journaux d'accès sont conservés pour l'audit RGPD.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur BDD : {str(e)}"
        )


def _verifier_client_existe(cursor: Any, client_id: str) -> None:  # type: ignore[type-arg]
    """Lève une 404 si le client_id n'existe pas en BDD."""
    cursor.execute("SELECT 1 FROM clients WHERE client_id = %s;", (client_id,))
    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' introuvable."
        )


@router.delete("/{client_id}/api-key", status_code=status.HTTP_200_OK)
def revoquer_cle_api(
    client_id: str,
    _: str = Depends(get_current_client),
) -> Dict[str, Any]:
    """Révoque immédiatement la clé API d'un client compromis.

    La clé est remplacée par un marqueur non fonctionnel unique — le client
    ne peut plus s'authentifier jusqu'à régénération via POST /{client_id}/api-key.
    Les données et journaux sont intégralement conservés.

    Args:
        client_id: Identifiant du client dont la clé doit être révoquée.

    Returns:
        Confirmation de révocation.

    Raises:
        HTTPException: 404 si le client n'existe pas.
    """
    marqueur_revocation: str = f"REVOQUE_{client_id}"

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                _verifier_client_existe(cursor, client_id)
                cursor.execute(
                    "UPDATE clients SET api_key = %s WHERE client_id = %s;",
                    (marqueur_revocation, client_id),
                )
                conn.commit()

        return {
            "status": "Révoquée",
            "client_id": client_id,
            "message": "Clé API révoquée. Le client ne peut plus s'authentifier.",
            "action_suivante": f"POST /api/clients/{client_id}/api-key pour régénérer.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur BDD : {str(e)}"
        )


@router.post("/{client_id}/api-key", status_code=status.HTTP_201_CREATED)
def regenerer_cle_api(
    client_id: str,
    _: str = Depends(get_current_client),
) -> Dict[str, Any]:
    """Génère une nouvelle clé API pour un client existant.

    Invalide automatiquement l'ancienne clé (révoquée ou active) en la
    remplaçant par le hash de la nouvelle. La clé brute est retournée
    une seule fois — elle ne sera plus récupérable ensuite.

    Args:
        client_id: Identifiant du client pour lequel régénérer la clé.

    Returns:
        Nouvelle clé API brute (à transmettre au client, affichée une fois).

    Raises:
        HTTPException: 404 si le client n'existe pas.
    """
    nouvelle_cle: str = f"wf_live_{secrets.token_urlsafe(32)}"

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                _verifier_client_existe(cursor, client_id)
                cursor.execute(
                    "UPDATE clients SET api_key = %s WHERE client_id = %s;",
                    (hacher_cle(nouvelle_cle), client_id),
                )
                conn.commit()

        return {
            "status": "Régénérée",
            "client_id": client_id,
            "api_key": nouvelle_cle,
            "message": "Nouvelle clé générée. L'ancienne est immédiatement invalide. Conservez cette clé.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur BDD : {str(e)}"
        )


@router.get("/me")
def get_mon_profil(api_key: str = Security(api_key_header)) -> Dict[str, Any]:
    """Retourne les informations de profil du client authentifié (RGPD — User Story #5).

    Args:
        api_key: Clé API brute extraite du header X-API-Key.

    Returns:
        Dictionnaire avec client_id et nom_structure.

    Raises:
        HTTPException: 401 si la clé est absente ou invalide, 500 sur erreur BDD.
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT client_id, denomination AS nom_structure FROM clients WHERE api_key = %s;",
                    (hacher_cle(api_key),),
                )
                client = cursor.fetchone()

        if not client:
            raise HTTPException(status_code=401, detail="Clé API invalide ou introuvable.")

        return dict(client)

    except HTTPException:
        raise
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne de la base de données : {e}")
