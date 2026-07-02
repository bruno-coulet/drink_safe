"""
-------------------------------------------------------------------------------
Projet : Drink safe
Composant : Configuration Centralisée de l'API Unique
Description : Gestion dynamique des configurations selon le contexte d'exécution
              (Local vs Docker) pour PostgreSQL et le tracking MLflow.
-------------------------------------------------------------------------------
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

ROOT_DIR: Path = Path(__file__).resolve().parents[1]

# 2. Chargement du fichier .env
load_dotenv(ROOT_DIR / ".env")

DATA_DIR: Path = ROOT_DIR / "data"
DATA_RAW_DIR: Path = DATA_DIR / "raw"
DATA_PROCESSED_DIR: Path = DATA_DIR / "processed"

PATH_WATER_IMPUTED: Path = DATA_PROCESSED_DIR / "water_imputed.csv"
PATH_WATER_STD: Path = DATA_PROCESSED_DIR / "water_std.csv"
PATH_WATER_RAW: Path = DATA_RAW_DIR / "water_potability.csv"

ARTIFACTS_DIR: Path = ROOT_DIR / "artifacts"
FRONT_DIR: Path = ROOT_DIR / "front"


class Settings:
    """Configuration globale s'adaptant dynamiquement à l'environnement."""

    PROJECT_NAME: str = "Drink safe API"
    VERSION: str = "2  .0.0"

    # Sécurité et Authentification (Clés API)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-key-super-secrete")

    # Détection du contexte : Sommes-nous dans un conteneur Docker ?
    IS_DOCKER: bool = os.path.exists("/.dockerenv")

    # --- Configuration Dynamique PostgreSQL ---
    DB_HOST: str = "postgres" if IS_DOCKER else " 127.0.0.1"
    DB_USER: str = "admin_waterflow"
    DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "MonMotDePasseSecurise123!")
    DB_NAME: str = "waterflow_db"



    # Assemblage propre et sécurisé de la chaîne de connexion
    # DATABASE_URL: str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    # nettoyer chaque composant individuellement
    DATABASE_URL: str = f"postgresql://{DB_USER.strip()}:{DB_PASSWORD.strip()}@{DB_HOST.strip()}:5432/{DB_NAME.strip()}"

    # --- Configuration Dynamique MLflow ---
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000" if IS_DOCKER else "http://127.0.0.1:5000"

# Instanciation unique (Pattern Singleton)
settings = Settings()

def init_db() -> None:
    """Crée les tables SQL requises si elles n'existent pas encore en BDD."""
    queries = [
        """
        CREATE TABLE IF NOT EXISTS clients (
            client_id VARCHAR(50) PRIMARY KEY,
            role VARCHAR(20) DEFAULT 'client',
            denomination VARCHAR(100) NOT NULL,
            adresse TEXT,
            api_key VARCHAR(100) UNIQUE NOT NULL,
            cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS prelevements (
            id SERIAL PRIMARY KEY,
            client_id VARCHAR(50) REFERENCES clients(client_id),
            provenance VARCHAR(20) NOT NULL,
            lieu VARCHAR(255),
            ph FLOAT,
            hardness FLOAT,
            solids FLOAT,
            chloramines FLOAT,
            sulfate FLOAT,
            conductivity FLOAT,
            organic_carbon FLOAT,
            trihalomethanes FLOAT,
            turbidity FLOAT,
            observations TEXT,
            prediction_potability INT,
            model_version VARCHAR(100),
            cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS action_logs (
            id SERIAL PRIMARY KEY,
            client_id VARCHAR(50),
            api_key_used VARCHAR(100),
            endpoint TEXT,
            method VARCHAR(10),
            status_code INT,
            execution_duration_ms INT,
            execute_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]

    try:
        # Ouvre la connexion et le curseur
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:

                # COMMANDES PYTHON DE NETTOYAGE EN CAS DE BESOIN
                # cursor.execute("DROP TABLE IF EXISTS action_logs CASCADE;")
                # cursor.execute("DROP TABLE IF EXISTS prelevements CASCADE;")
                # cursor.execute("DROP TABLE IF EXISTS clients CASCADE;")

                # Boucle sur la liste pour exécuter chaque création de table
                for query in queries:
                    cursor.execute(query)

                conn.commit()
        print("[SQL] Tables de l'API Unique initialisées avec succès.")

    except Exception as e:
        print(f"Erreur lors de l'initialisation de la BDD : {e}")
