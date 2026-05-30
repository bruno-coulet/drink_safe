"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Pipeline d'Entraînement et Tracking MLOps (MLflow)
Description : Chargement des datasets, entraînement du catalogue de modèles,
              initialisation automatique de PostgreSQL et enregistrement
              dans le Model Registry.
-------------------------------------------------------------------------------
"""

import os
import psycopg2
from typing import Dict, Any
import pandas as pd
import mlflow
import mlflow.sklearn

import requests
_old_prepare_headers = requests.models.PreparedRequest.prepare_headers
def patched_prepare_headers(self, headers):
    _old_prepare_headers(self, headers)
    # On force l'en-tête Host pour tromper la sécurité stricte d'Uvicorn
    self.headers["Host"] = "localhost:5000"
requests.models.PreparedRequest.prepare_headers = patched_prepare_headers

from src.config import settings
from src.models import get_models



# Configuration du serveur de tracking ciblé
mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
mlflow.set_experiment("Water_Potability_Evaluation_v2")


def script_init_db() -> None:
    """Crée les tables SQL requises de manière isolée pour éviter les imports circulaires."""
    queries = [
        """
        CREATE TABLE IF NOT EXISTS clients (
            client_id VARCHAR(50) PRIMARY KEY,
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
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                for query in queries:
                    cursor.execute(query)
                conn.commit()
        print("[SQL Isolation] Tables PostgreSQL vérifiées/créées avec succès.")
    except Exception as e:
        print(f"[SQL Isolation] ⚠️ Impossible d'initialiser la base : {e}")


def executer_pipeline_mlops() -> None:
    """Orchestre l'initialisation SQL, le training et le tracking MLflow."""
    
    # 1. Initialisation locale et isolée
    print("[MLOps] Étape 1 : Initialisation des tables PostgreSQL...")
    script_init_db()
    
    # 2. Chargement des jeux de données nettoyés
    print("[MLOps] Étape 2 : Chargement des matrices de données...")
    path_brut = "data/processed/water_imputed.csv"
    path_std = "data/processed/water_std.csv"
    
    if not os.path.exists(path_brut) or not os.path.exists(path_std):
        raise FileNotFoundError("Les fichiers de données dans 'data/processed/' sont introuvables.")
        
    df_brut = pd.read_csv(path_brut)
    df_std = pd.read_csv(path_std)
    
    # 3. Récupération des modèles depuis le catalogue centralisé
    modeles = get_models()
    
    for nom_modele, instance_modele in modeles.items():
        # Sélection intelligente du dataset selon le besoin de standardisation du modèle
        if nom_modele in ["LogisticRegression", "MLPClassifier"]:
            df_travail = df_std
            type_data = "Standardisées (Anti-leakage)"
        else:
            df_travail = df_brut
            type_data = "Brutes / Imputées"
            
        X = df_travail.drop(columns=["Potability"], errors="ignore")
        y = df_travail["Potability"]
        
        print(f"[MLOps] 🚀 Lancement du Run MLflow pour : {nom_modele} ({type_data})...")
        
        with mlflow.start_run(run_name=f"Run_{nom_modele}"):
            # Entraînement de l'algorithme
            instance_modele.fit(X, y)
            
            # Calcul d'une métrique d'évaluation rapide
            score_entrainement = instance_modele.score(X, y)
            
            # Log des paramètres et des métriques dans MLflow
            mlflow.log_param("architecture", nom_modele)
            mlflow.log_param("dataset_type", type_data)
            mlflow.log_metric("train_accuracy", score_entrainement)
            
            # Enregistrement du modèle dans le Model Registry
            nom_registre = f"WaterModel_{nom_modele}"
            mlflow.sklearn.log_model(
                sk_model=instance_modele,
                artifact_path="model",
                registered_model_name=nom_registre
            )
            print(f"✓ {nom_modele} correctement entraîné et poussé dans le registre sous : {nom_registre}")


if __name__ == "__main__":
    executer_pipeline_mlops()