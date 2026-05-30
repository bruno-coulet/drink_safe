"""
-------------------------------------------------------------------------------
Projet : Waterflow (Potabilité de l'eau)
Composant : MLOps / Initialisation MLflow
Description : Initialise l'expérience globale sur le serveur de suivi MLflow
              en exploitant directement les variables d'environnement.
-------------------------------------------------------------------------------
"""

import os
from pathlib import Path
from typing import Dict, Any
import mlflow
import mlflow.sklearn
from dotenv import load_dotenv
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

# Chargement du fichier .env à la racine du projet
CHEMIN_RACINE: Path = Path(__file__).resolve().parents[1]
load_dotenv(CHEMIN_RACINE / ".env")


def initialiser_environnement_mlflow(nom_experience: str) -> None:
    """Connecte le client au serveur MLflow et initialise l'expérience.

    Va chercher l'hôte du serveur via la variable d'environnement 
    MLFLOW_TRACKING_HOST. Si elle n'est pas définie, 'localhost' est utilisé.

    Arguments:
        nom_experience: Nom unique de l'expérience à créer ou récupérer.
    """
    # Récupération directe de la variable d'environnement
    hote_serveur: str = os.getenv("MLFLOW_TRACKING_HOST", "localhost")
    port_serveur: str = "5000"
    
    uri_suivi: str = f"http://{hote_serveur}:{port_serveur}"
    mlflow.set_tracking_uri(uri_suivi)

    # Résolution d'un chemin absolu local sur l'hôte pour les artefacts
    dossier_artifacts: Path = CHEMIN_RACINE / "artifacts"
    dossier_artifacts.mkdir(exist_ok=True)
    uri_artifacts: str = dossier_artifacts.as_uri()

    experience = mlflow.get_experiment_by_name(nom_experience)
    
    if experience is None:
        mlflow.create_experiment(
            name=nom_experience,
            artifact_location=uri_artifacts
        )
    
    mlflow.set_experiment(nom_experience)


def executer_run_validation() -> None:
    """Exécute un entraînement synthétique de validation pour valider la stack."""
    X, y = make_classification(n_samples=100, n_features=9, random_state=42)

    with mlflow.start_run(run_name="baseline_test_docker"):
        params: Dict[str, Any] = {"model_type": "LogisticRegression", "max_iter": 1000}
        mlflow.log_params(params)
        mlflow.log_metric("accuracy", 0.85)

        modele: LogisticRegression = LogisticRegression(max_iter=1000)
        modele.fit(X, y)

        mlflow.sklearn.log_model(
            sk_model=modele,
            artifact_path="model",
            registered_model_name="WaterPotabilityBaseline"
        )


def main() -> None:
    """Point d'entrée principal pour l'initialisation MLOps."""
    nom_exp_consigne: str = "experiment_water_quality"
    
    initialiser_environnement_mlflow(nom_experience=nom_exp_consigne)
    executer_run_validation()


if __name__ == "__main__":
    main()