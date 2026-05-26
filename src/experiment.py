"""
-------------------------------------------------------------------------------
Projet : Waterflow (Potabilité de l'eau)
Composant : Entraînement Automatisé / MLOps
Description : Découvre, entraîne et versionne à la volée tous les modèles 
              déclarés dans 'src/models.py' sur leur dataset idéal.
              Vérifie la disponibilité du serveur MLflow avant le lancement.
-------------------------------------------------------------------------------
"""

from pathlib import Path
from typing import Any
import pandas as pd
import requests
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import mlflow
import mlflow.sklearn

# Importation dynamique du catalogue de modèles
from src.models import get_models

def executer_pipeline_entrainement(
    chemin_donnees: Path,
    nom_experience: str,
    inst_modele: Any,
    hote_mlflow: str = "127.0.0.1",
    port_mlflow: int = 5000
) -> None:
    """
    Entraîne une instance de modèle donnée et pousse les métriques/artifacts sur MLflow.
    """
    # 1. Configuration MLflow
    uri_suivi: str = f"http://{hote_mlflow}:{port_mlflow}"
    mlflow.set_tracking_uri(uri_suivi)
    
    racine_projet: Path = chemin_donnees.resolve().parent.parent.parent
    uri_backend_local: str = (racine_projet / "runs").as_uri()

    if mlflow.get_experiment_by_name(nom_experience) is None:
        mlflow.create_experiment(name=nom_experience, artifact_location=uri_backend_local)
    mlflow.set_experiment(nom_experience)

    # 2. Chargement et découpage des données (80/20)
    df: pd.DataFrame = pd.read_csv(chemin_donnees)
    X: pd.DataFrame = df.drop(columns=["Potability"])
    y: pd.Series = df["Potability"]
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 3. Extraction de l'identité du modèle
    type_modele: str = inst_modele.__class__.__name__
    suffixe_dataset: str = "standardise" if "_std" in chemin_donnees.stem else "brut"
    nom_run: str = f"{type_modele}_{suffixe_dataset}"

    # 4. Cycle de run MLflow
    with mlflow.start_run(run_name=nom_run):
        inst_modele.fit(X_train, y_train)
        predictions = inst_modele.predict(X_val)

        metriques = {
            "accuracy": float(accuracy_score(y_val, predictions)),
            "f1_score": float(f1_score(y_val, predictions, average="binary")),
            "precision": float(precision_score(y_val, predictions, average="binary")),
            "recall": float(recall_score(y_val, predictions, average="binary"))
        }

        mlflow.log_param("model_name", type_modele)
        mlflow.log_param("dataset_type", suffixe_dataset)
        mlflow.log_params(inst_modele.get_params(deep=False))
        mlflow.log_metrics(metriques)

        dynamic_name_register: str = f"WaterModel_{type_modele}"
        mlflow.sklearn.log_model(sk_model=inst_modele, artifact_path="model", registered_model_name=dynamic_name_register)
        print(f"✅ Version poussee avec succes pour : {dynamic_name_register} ({suffixe_dataset})")


if __name__ == "__main__":
    HOTE = "127.0.0.1"
    PORT = 5000
    URI_SERVEUR = f"http://{HOTE}:{PORT}"

    print("🔍 Verification de la disponibilite du serveur MLflow...")
    
    # ---- SÉCURITÉ : VERIFICATION DU SERVEUR DE TRACKING ----
    try:
        # On tente d'appeler rapidement l'API de santé native de MLflow
        reponse = requests.get(f"{URI_SERVEUR}/health", timeout=3)
        if reponse.status_code == 200:
            print(f"✅ Serveur MLflow detecte et joignable sur {URI_SERVEUR}")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        print("\n" + "!" * 80)
        print(f"ERREUR CRITIQUE : Le serveur de tracking MLflow est INJOIGNABLE sur {URI_SERVEUR}")
        print("Veuillez demarrer le serveur dans un autre terminal avant de lancer ce script :")
        print(f"uv run mlflow server --backend-store-uri ./runs --host {HOTE} --port {PORT}")
        print("!" * 80 + "\n")
        # On arrête proprement le script ici pour éviter le crash en cascade
        exit(1)
    # --------------------------------------------------------

    RACINE: Path = Path(__file__).resolve().parent.parent
    NOM_EXP: str = "experiment_water_quality"

    DATA_IMPUTED: Path = RACINE / "data" / "processed" / "water_imputed.csv"
    DATA_STANDARD: Path = RACINE / "data" / "processed" / "water_std.csv"

    # Découverte automatique des modèles
    dictionnaire_modeles = get_models()
    print(f"🔍 {len(dictionnaire_modeles)} modeles decouverts dans src/models.py. Alignement des pipelines...")

    for cle, instance in dictionnaire_modeles.items():
        nom_classe = instance.__class__.__name__
        
        # Attribution du bon dataset
        if "Logistic" in nom_classe or "MLP" in nom_classe or "SVC" in nom_classe:
            dataset_cible = DATA_STANDARD
        else:
            dataset_cible = DATA_IMPUTED
            
        print(f"⏳ Entrainement en cours pour {nom_classe}...")
        executer_pipeline_entrainement(
            chemin_donnees=dataset_cible,
            nom_experience=NOM_EXP,
            inst_modele=instance,
            hote_mlflow=HOTE,
            port_mlflow=PORT
        )