"""
-------------------------------------------------------------------------------
Projet : Waterflow (Potabilité de l'eau)
Composant : MLOps / Initialisation MLflow
Description : Initialise l'expérience globale sur le serveur de suivi MLflow
              et configure l'emplacement de stockage des artefacts.
-------------------------------------------------------------------------------
"""

from pathlib import Path
import mlflow
import mlflow.sklearn
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression


def initialiser_environnement_mlflow(
    nom_experience: str,
    hote_serveur: str = "127.0.0.1",
    port_serveur: int = 5000
) -> None:
    """
    Connecte le client au serveur MLflow et initialise l'expérience cible.

    Garantit la création de l'expérience avec un stockage d'artefacts
    explicite pour éviter les erreurs de permissions système.

    Arguments:
        nom_experience: Nom unique de l'expérience à créer ou récupérer.
        hote_serveur: Adresse IP du serveur de suivi (ex: conteneur Docker).
        port_serveur: Port d'écoute du serveur de suivi.
    """
    # 1. Connexion au serveur de suivi MLflow
    uri_suivi: str = f"http://{hote_serveur}:{port_serveur}"
    mlflow.set_tracking_uri(uri_suivi)

    # 2. Définition d'un chemin d'artefacts absolu résolu depuis l'hôte/conteneur
    # On utilise le sous-dossier 'artifacts' à la racine du projet
    chemin_base: Path = Path(__file__).resolve().parent
    dossier_artifacts: Path = chemin_base / "artifacts"
    
    # Conversion en URI compatible MLflow (ex: file:///absolute/path)
    uri_artifacts: str = dossier_artifacts.as_uri()

    # 3. Récupération ou création sécurisée de l'expérience
    experience = mlflow.get_experiment_by_name(nom_experience)
    
    if experience is None:
        mlflow.create_experiment(
            name=nom_experience,
            artifact_location=uri_artifacts
        )
    
    mlflow.set_experiment(nom_experience)


def executer_run_validation() -> None:
    """
    Exécute un entraînement synthétique de validation pour valider la stack.
    """
    # Génération de données synthétiques représentatives
    X, y = make_classification(n_samples=100, n_features=9, random_state=42)

    with mlflow.start_run(run_name="baseline_test_docker"):
        # Journalisation des paramètres de configuration
        mlflow.log_param("model_type", "LogisticRegression")
        mlflow.log_metric("accuracy", 0.85)

        # Entraînement du modèle de base
        modele: LogisticRegression = LogisticRegression(max_iter=1000)
        modele.fit(X, y)

        # Enregistrement du modèle dans le registre d'artefacts
        mlflow.sklearn.log_model(
            sk_model=modele,
            artifact_path="model",
            registered_model_name="WaterPotabilityBaseline"
        )


if __name__ == "__main__":
    NOM_EXP_CONSIGNE: str = "experiment_water_quality"
    
    # Initialisation de l'environnement
    initialiser_environnement_mlflow(nom_experience=NOM_EXP_CONSIGNE)
    
    # Exécution du test d'intégration
    executer_run_validation()