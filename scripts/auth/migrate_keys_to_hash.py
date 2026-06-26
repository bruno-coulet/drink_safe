"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Migration — Hashage des clés API existantes en BDD
Description : Convertit les clés API stockées en clair (avant l'introduction
              du hash SHA-256) vers leur équivalent hashé.
              A exécuter une seule fois après déploiement du patch de sécurité.

Usage :
    uv run python scripts/migrate_keys_to_hash.py
-------------------------------------------------------------------------------
"""

import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://admin_waterflow:{os.getenv('POSTGRES_PASSWORD', '')}@127.0.0.1:5432/waterflow_db",
)

HEX_LENGTH = 64  # longueur d'un hash SHA-256 en hex


def _est_deja_hache(valeur: str) -> bool:
    """Détecte si une clé est déjà un hash SHA-256 (64 caractères hexadécimaux)."""
    return len(valeur) == HEX_LENGTH and all(c in "0123456789abcdef" for c in valeur.lower())


def _hacher(valeur: str) -> str:
    return hashlib.sha256(valeur.encode()).hexdigest()


def migrer() -> None:
    """Lit toutes les clés API en BDD et hashe celles qui sont encore en clair."""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT client_id, api_key FROM clients;")
            clients = cursor.fetchall()

        migrees = 0
        ignorees = 0

        with conn.cursor() as cursor:
            for client_id, api_key in clients:
                if _est_deja_hache(api_key):
                    print(f"[SKIP] {client_id} — clé déjà hashée.")
                    ignorees += 1
                else:
                    hash_cle = _hacher(api_key)
                    cursor.execute(
                        "UPDATE clients SET api_key = %s WHERE client_id = %s;",
                        (hash_cle, client_id),
                    )
                    print(f"[OK]   {client_id} — clé migrée vers SHA-256.")
                    migrees += 1

        conn.commit()

    print(f"\nMigration terminée : {migrees} migrée(s), {ignorees} ignorée(s).")
    if migrees > 0:
        print(
            "\n⚠️  Les clés brutes ne sont plus utilisables. Les clients devront "
            "utiliser les clés fournies avant migration ou en régénérer via POST /api/clients."
        )


if __name__ == "__main__":
    migrer()
