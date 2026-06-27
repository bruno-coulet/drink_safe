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




def get_current_client(request: Request, api_key: str = Security(api_key_header)) -> str:
    """Valide la clé API fournie et retourne l'identifiant du client associé.

    La clé reçue est hachée (SHA-256) avant comparaison avec la valeur en BDD.
    Le client_id résolu est déposé dans request.state pour la traçabilité RGPD.

    Args:
        request: Requête HTTP courante.
        api_key: Clé API brute extraite du header X-API-Key.

    Returns:
        Le client_id validé du propriétaire de la clé.

    Raises:
        HTTPException: 401 si la clé est absente ou invalide.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Clé d'authentification manquante dans le Header '{API_KEY_NAME}'."
        )

    query_check: str = "SELECT client_id FROM clients WHERE api_key = %s;"

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_check, (hacher_cle(api_key),))
                result = cursor.fetchone()

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clé API invalide ou révoquée."
            )

        client_id: str = str(result[0])
        request.state.client_id = client_id
        return client_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la vérification des droits : {str(e)}"
        )



