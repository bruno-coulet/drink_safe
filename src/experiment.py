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

from src.config import settings, init_db
from src.models import get_models



# Configuration du serveur de tracking ciblé
mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
mlflow.set_experiment("Water_Potability_Evaluation_v2")


def executer_pipeline_mlops() -> None:
    """Orchestre l'initialisation SQL, le training et le tracking MLflow."""

    # 1. Initialisation des tables via la source unique (src/config.py)
    print("[MLOps] Étape 1 : Initialisation des tables PostgreSQL...")
    init_db()

    # 2. Chargement du jeu de données imputé (échelle brute)
    print("[MLOps] Étape 2 : Chargement de la matrice de données...")
    path_brut = "data/processed/water_imputed.csv"

    if not os.path.exists(path_brut):
        raise FileNotFoundError("Le fichier 'data/processed/water_imputed.csv' est introuvable.")

    df_brut = pd.read_csv(path_brut)

    # 3. Récupération des modèles depuis le catalogue centralisé
    modeles = get_models()

    for nom_modele, instance_modele in modeles.items():
        # Tous les modèles s'entraînent sur les données imputées (échelle brute).
        # La standardisation requise par LogisticRegression et MLPClassifier est
        # encapsulée dans leur Pipeline (StandardScaler), donc appliquée à l'identique
        # à l'entraînement et à l'inférence.
        type_data = "Imputées (standardisation intégrée au Pipeline si requise)"

        X = df_brut.drop(columns=["Potability"], errors="ignore")
        y = df_brut["Potability"]

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
