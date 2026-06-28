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
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import settings
from src.dependencies.auth import get_current_client, hacher_cle, get_admin_user


# Initialisation du routeur pour les clients
router = APIRouter(prefix="/clients", tags=["Clients & Sécurité"])

# Définition de l'en-tête de sécurité attendu (exigé par la spec technique)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


class ClientCreate(BaseModel):
    """Schéma Pydantic de validation pour la création d'un client."""
    client_id: str = Field(..., max_length=50, description="Identifiant unique du client (ex: LOR_EAU_01)")
    denomination: str = Field(..., max_length=100, description="Nom officiel ou raison sociale de l'entité")
    adresse: str = Field(..., description="Adresse postale complète du client")
    role: Optional[str] = "client" # Par défaut, on crée un client normal


@router.post("/", status_code=status.HTTP_201_CREATED)
def creer_client(
    payload: ClientCreate,             # données du profil (JSON)
    _: str = Depends(get_admin_user)   # cadenas de sécurité administrateur
    ) -> Dict[str, Any]:

    """Inscrit un profil (Client, Analyste, Exploitation) et génère sa clé API unique.

    La clé brute est retournée une seule fois dans la réponse.
    Seul son hash SHA-256 est stocké en BDD.
    """
    # Génération avec le préfixe de l'ancien code (très bonne pratique)
    cle_brute: str = f"wf_live_{secrets.token_urlsafe(32)}"
    # Hashage de la clé
    cle_hachee = hacher_cle(cle_brute)

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO clients (client_id, denomination, adresse, role, api_key)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (payload.client_id, payload.denomination, payload.adresse, payload.role, cle_hachee)
                )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur d'insertion : {str(e)}")

    # 4. Retourne la clé en clair à Flask pour l'affichage à l'écran
    return {
        "message": "Compte client créé avec succès.",
        "client_id": payload.client_id,
        "api_key": cle_brute
    }

    # try:
    #     with psycopg2.connect(settings.DATABASE_URL) as conn:
    #         with conn.cursor() as cursor:
    #             cursor.execute(query_insert, (
    #                 payload.client_id,
    #                 payload.role,           # <== Le fameux rôle !
    #                 payload.denomination,
    #                 payload.adresse,
    #                 hacher_cle(cle_brute),  # <== L'appel à la fonction centralisée
    #             ))
    #             conn.commit()
    # except Exception as e:
    #     # Pensez à gérer l'erreur (ex: doublon d'ID)
    #     raise HTTPException(status_code=400, detail=f"Erreur d'insertion : {str(e)}")

    # return {
    #     "message": f"Compte {payload.role} créé avec succès.",
    #     "client_id": payload.client_id,
    #     "api_key": cle_brute  # La clé en clair, affichée une seule fois
    # }

@router.get("/", status_code=status.HTTP_200_OK)
def lister_clients(_: str = Depends(get_admin_user)) -> Dict[str, Any]:
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


# article 17 du RGPD (Droit à l'effacement des données personnelles
# Conservation des features pour l'apprentissage
@router.delete("/{client_id}", status_code=status.HTTP_200_OK)
def supprimer_client(
    client_id: str,
    _: str = Depends(get_admin_user),  # Sécurisation de la route
) -> Dict[str, Any]:
    """Supprime un client et anonymise ses prélèvements (Conformité RGPD).

    Les DCP (Données à Caractère Personnel) du client sont supprimées.
    Les prélèvements liés sont anonymisés (client_id = NULL) pour continuer d'entrainer l'IA.
    Les journaux d'accès (action_logs) sont conservés pour l'audit.
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # 1. Vérifier si le client existe
                cursor.execute(
                    "SELECT client_id FROM clients WHERE client_id = %s;",
                    (client_id,)
                )
                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Client '{client_id}' introuvable."
                    )

                # 2. Compter les prélèvements pour le rapport
                cursor.execute(
                    "SELECT COUNT(*) FROM prelevements WHERE client_id = %s;",
                    (client_id,)
                )
                row = cursor.fetchone()
                nb_prelevements: int = row if row else 0

                # 3. CORRECTION 2 : Anonymisation des prélèvements au lieu de la suppression !
                cursor.execute(
                    "UPDATE prelevements SET client_id = NULL WHERE client_id = %s;",
                    (client_id,)
                )

                # 4. Suppression du compte client (Effacement des DCP)
                cursor.execute(
                    "DELETE FROM clients WHERE client_id = %s;",
                    (client_id,)
                )
                conn.commit()

        return {
            "status": "Succès",
            "client_id": client_id,
            "prelevements_anonymises": nb_prelevements,
            "note": "Les données personnelles sont supprimées. Prélèvements anonymisés pour l'IA (RGPD).",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur BDD : {str(e)}"
        )


@router.post("/{client_id}/regenerate-key", status_code=status.HTTP_200_OK)
def regenerer_cle_api(
    client_id: str,
    _: str = Depends(get_admin_user),  # <== Sécurisé pour l'admin
) -> Dict[str, Any]:
    """Régénère la clé API d'un client (révoque automatiquement l'ancienne).

    En cas de compromission, l'administrateur génère une nouvelle clé.
    L'ancienne clé est instantanément écrasée en BDD.
    La nouvelle clé brute est retournée une seule fois.
    """
    # 1. Génération de la nouvelle clé avec notre standard
    nouvelle_cle_brute: str = f"wf_live_{secrets.token_urlsafe(32)}"

    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # 2. Vérification de l'existence du profil
                cursor.execute(
                    "SELECT client_id FROM clients WHERE client_id = %s;",
                    (client_id,)
                )
                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Client '{client_id}' introuvable."
                    )

                # 3. Écrasement (Révocation de fait) par le nouveau Hash
                cursor.execute(
                    "UPDATE clients SET api_key = %s WHERE client_id = %s;",
                    (hacher_cle(nouvelle_cle_brute), client_id),
                )
                conn.commit()

        return {
            "status": "Succès",
            "message": "Clé API régénérée. L'ancienne clé est révoquée et ne fonctionnera plus.",
            "client_id": client_id,
            "nouvelle_api_key": nouvelle_cle_brute
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
