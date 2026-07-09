"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Script de Seeding — Comptes Techniques Admin
Description : Crée en base de données les deux entrées techniques utilisées
              par le front Flask pour appeler l'API au nom des admins :

                - lis les valeurs  placées dans le fichier .env
                - hache les clés API (Backend) en SHA-256
                - injecte automatiquement les profils adminis

              A exécuter une seule fois après `docker compose up`.
Usage :
    uv run python scripts/seed_admins.py
-------------------------------------------------------------------------------
"""

import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2


def _hacher_cle(cle: str) -> str:
    return hashlib.sha256(cle.encode()).hexdigest()

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://admin_waterflow:{os.getenv('POSTGRES_PASSWORD', '')}@127.0.0.1:5432/waterflow_db",
)

ADMIN_ANALYSTE_API_KEY = os.getenv("ADMIN_ANALYSTE_API_KEY", "")
ADMIN_EXPLOITATION_API_KEY = os.getenv("ADMIN_EXPLOITATION_API_KEY", "")

COMPTES = [
    {
        "client_id": "ADMIN_ANALYSTE",
        "role": "analyste",
        "denomination": "Compte technique — Analyste Qualité",
        "adresse": "Interne plateforme",
        "api_key": ADMIN_ANALYSTE_API_KEY,
    },
    {
        "client_id": "ADMIN_EXPLOITATION",
        "role": "exploitation",
        "denomination": "Compte technique — Responsable Exploitation",
        "adresse": "Interne plateforme",
        "api_key": ADMIN_EXPLOITATION_API_KEY,
    },
]


def seed() -> None:
    """Insère les comptes admin en base si absents."""
    if not ADMIN_ANALYSTE_API_KEY or not ADMIN_EXPLOITATION_API_KEY:
        print(
            "[ERREUR] ADMIN_ANALYSTE_API_KEY et ADMIN_EXPLOITATION_API_KEY "
            "doivent être définis dans .env"
        )
        sys.exit(1)

    query = """
        INSERT INTO clients (client_id, role, denomination, adresse, api_key)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (client_id) DO UPDATE
            SET api_key = EXCLUDED.api_key,
                role = EXCLUDED.role,
                denomination = EXCLUDED.denomination;
    """

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            for compte in COMPTES:
                cursor.execute(
                    query,
                    (
                        compte["client_id"],
                        compte["role"],
                        compte["denomination"],
                        compte["adresse"],
                        _hacher_cle(compte["api_key"]),
                    ),
                )
                print(f"[OK] Compte {compte['client_id']} inséré ou mis à jour.")
        conn.commit()

    print("[OK] Seeding des comptes admin terminé.")


if __name__ == "__main__":
    seed()
