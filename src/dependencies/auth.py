"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Sécurité et Authentification par clé API
Description : Intercepteur et validateur de clés API stockées en base de données
              pour sécuriser les endpoints de l'API unifiée.
              Les clés API sont stockées sous forme de hash SHA-256 en BDD :
              la clé brute n'est jamais persistée.
-------------------------------------------------------------------------------
"""

import hashlib
from fastapi import Security, HTTPException, status, Request
from fastapi.security.api_key import APIKeyHeader
import psycopg2

from src.config import settings

API_KEY_NAME: str = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def hacher_cle(api_key: str) -> str:
    """Retourne le hash SHA-256 hexadécimal d'une clé API brute.

    SHA-256 est approprié ici car les clés sont des tokens à haute entropie
    (secrets.token_urlsafe(32)) — aucun sel supplémentaire n'est nécessaire.

    Args:
        api_key: Clé API brute transmise par le client.

    Returns:
        Hash SHA-256 en hexadécimal (64 caractères).
    """
    return hashlib.sha256(api_key.encode()).hexdigest()

# def get_current_client(request: Request, api_key: str = Security(api_key_header)) -> str:
#     """Valide la clé API fournie et retourne l'identifiant du client associé.

#     La clé reçue est hachée (SHA-256) avant comparaison avec la valeur en BDD.
#     Le client_id résolu est déposé dans request.state pour la traçabilité RGPD.

#     Args:
#         request: Requête HTTP courante.
#         api_key: Clé API brute extraite du header X-API-Key.

#     Returns:
#         Le client_id validé du propriétaire de la clé.

#     Raises:
#         HTTPException: 401 si la clé est absente ou invalide.
#     """
#     if not api_key:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Clé d'authentification manquante dans le Header '{API_KEY_NAME}'."
#         )

#     cle_hachee = hacher_cle(api_key)

#     query_check: str = "SELECT client_id FROM clients WHERE api_key = %s;"

#     try:
#         with psycopg2.connect(settings.DATABASE_URL) as conn:
#             with conn.cursor() as cursor:
#                 # cursor.execute(query_check, (hacher_cle(api_key),))
#                 ("SELECT client_id FROM clients WHERE api_key = %s;", (cle_hachee,))
#                 result = cursor.fetchone()

#         if result is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Clé API invalide ou révoquée."
#             )

#         return user # Retourne le client_id


#         client_id: str = str(result[0])
#         request.state.client_id = client_id
#         return client_id

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erreur interne lors de la vérification des droits : {str(e)}"
#         )

def get_current_client(request: Request, api_key: str = Security(api_key_header)) -> str:
    """Valide la clé API fournie et retourne l'identifiant du client associé."""

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'authentification manquante dans le Header."
        )

    # 1. Hachage de la clé reçue
    cle_hachee = hacher_cle(api_key)

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # 2. On EXÉCUTE la requête avec la clé hachée
                cursor.execute(
                    "SELECT client_id FROM clients WHERE api_key = %s;",
                    (cle_hachee,)
                )
                result = cursor.fetchone()

         # 3. Si on ne trouve rien (clé invalide ou révoquée)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clé API invalide ou révoquée."
            )

        # 4. On extrait l'ID PROPREMENT en ciblant l'index  du tuple
        client_id: str = result[0]
        request.state.client_id = client_id

        return client_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la vérification des droits : {str(e)}"
        )


def get_admin_user(api_key: str = Security(api_key_header)) -> str:
    """
    Verrou de sécurité : Autorise uniquement les analystes et responsables.
     - prend la clé API
     - hache la clé
     - interroger la table clients (champ role)
     - bloque l'accès avec une erreur 403 Forbidden si la personne n'est qu'un simple "client".
    """
    # "Verrou de sécurité : Autorise uniquement les analystes et responsables.
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante dans l'en-tête."
        )
    # On hache la clé reçue pour la comparer avec la BDD
    cle_hachee = hacher_cle(api_key)

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # On récupère l'ID et surtout le RÔLE !
                cursor.execute(
                    "SELECT client_id, role FROM clients WHERE api_key = %s;",
                    (cle_hachee,)
                )
                user = cursor.fetchone()

                # 1. Si la clé n'existe pas
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Clé API invalide ou compte supprimé."
                    )

                client_id, role = user

                # 2. Si la clé est valide, mais que le rôle n'est pas admin (matrice des droits)
                if role not in ["analyste", "exploitation"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Privilèges insuffisants. Cette action est réservée aux administrateurs."
                    )

                return client_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur d'authentification : {str(e)}"
        )

