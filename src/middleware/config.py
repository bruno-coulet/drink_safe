'''
Centralise la sécurité.
 pour ne pas coder les mots de passe ou les adresses localhost en dur dans ton code
'''

import os
from pathlib import Path
from dotenv import load_dotenv

# Trouver le chemin du fichier .env à la racine (src/middleware/config.py -> monte de 3 niveaux)
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

class Config:
    """Centralisation de la configuration et des secrets du Middleware Flask."""
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-key-pas-securisee")
    
    # Configuration de la base de données PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("❌ Erreur critique : DATABASE_URL n'est pas définie dans le fichier .env")
        
    # Couplage avec le serveur d'inférence FastAPI
    FASTAPI_URL: str = os.getenv("FASTAPI_URL", "http://localhost:8000/predict")
    
    # Tracking MLOps
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
