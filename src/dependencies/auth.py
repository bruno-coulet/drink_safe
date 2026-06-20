"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Sécurité et Authentification par clé API
Description : Intercepteur et validateur de clés API stockées en base de données
              pour sécuriser les endpoints de l'API unifiée.
-------------------------------------------------------------------------------
"""

from fastapi import Security, HTTPException, status, Request
from fastapi.security.api_key import APIKeyHeader
import psycopg2

from src.config import settings

# Définition de l'emplacement et du nom du Header attendu dans la requête HTTP
API_KEY_NAME: str = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_current_client(request: Request, api_key: str = Security(api_key_header)) -> str:
    """Valide la clé API fournie et retourne l'identifiant du client associé.

    Cette dépendance FastAPI extrait le token du header, vérifie sa correspondance
    exacte en base de données PostgreSQL et remonte une erreur 401 si le jeton est
    invalide ou absent. Le client_id résolu est déposé dans `request.state` pour
    permettre au middleware de journalisation de tracer le client (RGPD).

    Args:
        request (Request): Requête HTTP courante (sert à exposer le client_id au middleware).
        api_key (str): Jeton d'authentification extrait du header HTTP.

    Returns:
        str: Le 'client_id' validé du propriétaire de la clé.

    Raises:
        HTTPException: Erreur 401 (Non autorisé) si l'authentification échoue.
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
                cursor.execute(query_check, (api_key,))
                result = cursor.fetchone()
                
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clé API invalide ou révoquée."
            )
            
        # On expose l'ID technique du client au middleware via request.state (traçabilité RGPD)
        client_id: str = str(result[0])
        request.state.client_id = client_id
        # On retourne l'ID technique du client (ex: LOR_EAU_01) pour filtrer ses données
        return client_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la vérification des droits : {str(e)}"
        )