"""
-------------------------------------------------------------------------------
Projet : Waterflow (Potabilité de l'eau)
Composant : Entraînement / Classification binaire
Description :   Charge le dataset spécifié (brut ou standardisé)
                entraîne le modèle sélectionné
                calcule les métriques de validation
                journalise l'ensemble dans MLflow.
-------------------------------------------------------------------------------
"""

from pathlib import Path
from typing import Any
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import mlflow
import mlflow.sklearn


def executer_pipeline_entrainement(
    chemin_donnees: Path,
    nom_experience: str,
    type_modele: str,
    configuration_modele: dict[str, Any],
    hote_mlflow: str = "127.0.0.1",
    port_mlflow: int = 5000
) -> None:
    """
    Exécute l'entraînement d'un modèle spécifique sur un jeu de données donné
    et enregistre les résultats dans l'interface de suivi MLflow.

    Arguments:
        chemin_donnees: Chemin absolu vers le fichier CSV (imputé ou standardisé).
        nom_experience: Nom de l'expérience MLflow.
        type_modele: Nom abrégé du modèle pour l'identification.
        configuration_modele: Dictionnaire contenant les hyperparamètres du modèle.
        hote_mlflow: Adresse IP du serveur MLflow.
        port_mlflow: Port du serveur MLflow.
    """
    # 1. Connexion au serveur de suivi MLflow
    # uri_suivi: str = f"http://{hote_mlflow}:{port_mlflow}"
    # mlflow.set_tracking_uri(uri_suivi)
    # mlflow.set_experiment(nom_experience)
    

    uri_suivi: str = f"http://{hote_mlflow}:{port_mlflow}"
    mlflow.set_tracking_uri(uri_suivi)
    
    # Résolution du chemin absolu local vers le dossier du volume partagé
    racine_projet: Path = chemin_donnees.resolve().parent.parent.parent
    dossier_runs_local: Path = racine_projet / "runs"
    
    # Conversion en URI de fichier (file://...) pour forcer l'écriture locale directe
    uri_backend_local: str = dossier_runs_local.as_uri()

    # Création explicite de l'expérience avec l'emplacement racine écrasé
    experience = mlflow.get_experiment_by_name(nom_experience)
    if experience is None:
        mlflow.create_experiment(
            name=nom_experience,
            artifact_location=uri_backend_local
        )
    
    mlflow.set_experiment(nom_experience)



    # 2. Préparation des données
    df: pd.DataFrame = pd.read_csv(chemin_donnees)
    X: pd.DataFrame = df.drop(columns=["Potability"])
    y: pd.Series = df["Potability"]

    # Division stricte des ensembles d'entraînement et de validation (80/20)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Identification de la nature du dataset pour le suivi MLflow
    suffixe_dataset: str = "standardise" if "_std" in chemin_donnees.stem else "brut"
    nom_run: str = f"{type_modele}_{suffixe_dataset}"

    # 3. Initialisation du modèle
    if type_modele == "LogisticRegression":
        modele = LogisticRegression(**configuration_modele)
    elif type_modele == "RandomForest":
        modele = RandomForestClassifier(**configuration_modele)
    else:
        raise ValueError(f"Type de modèle non supporté : {type_modele}")

    # 4. Phase d'exécution MLflow
    with mlflow.start_run(run_name=nom_run):
        # Entraînement
        modele.fit(X_train, y_train)

        # Évaluation
        predictions = modele.predict(X_val)

        metriques: dict[str, float] = {
            "accuracy": float(accuracy_score(y_val, predictions)),
            "f1_score": float(f1_score(y_val, predictions, average="binary")),
            "precision": float(precision_score(y_val, predictions, average="binary")),
            "recall": float(recall_score(y_val, predictions, average="binary"))
        }

        # Journalisation des métadonnées et paramètres
        mlflow.log_param("model_name", type_modele)
        mlflow.log_param("dataset_type", suffixe_dataset)
        mlflow.log_params(configuration_modele)
        mlflow.log_metrics(metriques)

        # # Enregistrement de l'artefact
        # mlflow.sklearn.log_model(
        #     sk_model=modele, 
        #     artifact_path="model",
        #     registered_model_name="WaterPotabilityBaseline"
        # )
        

        # Extraction dynamique du nom de la classe du modèle
        # Si Pipeline (ex: avec StandardScaler intégré), utilisez : modele.steps[-1][1].__class__.__name__
        # Sinon : :
        name_class_model: str = modele.__class__.__name__
        
        # Formatage standardisé du nom pour le Model Registry (ex: WaterModel_RandomForestClassifier)
        dynamic_name_register: str = f"WaterModel_{name_class_model}"

        # Enregistrement sans aucune condition 'if' en dur
        mlflow.sklearn.log_model(
            sk_model=modele, 
            artifact_path="model",
            registered_model_name=dynamic_name_register
        )
        print(f"📦 Modèle enregistré dynamiquement sous le nom : {dynamic_name_register}")




if __name__ == "__main__":
    RACINE: Path = Path(__file__).resolve().parent.parent
    NOM_EXP: str = "experiment_water_quality"

    # Définition des chemins vers les deux versions des données
    DATA_IMPUTED: Path = RACINE / "data" / "processed" / "water_imputed.csv"
    DATA_STANDARD: Path = RACINE / "data" / "processed" / "water_std.csv"

    # Scénario 1 : Régression Logistique sur données standardisées
    print("Lancement : Logistic Regression + Données Standardisées...")
    executer_pipeline_entrainement(
        chemin_donnees=DATA_STANDARD,
        nom_experience=NOM_EXP,
        type_modele="LogisticRegression",
        configuration_modele={"max_iter": 1000, "random_state": 42}
    )

    # Scénario 2 : Random Forest sur données imputées brutes (non standardisées)
    print("Lancement : Random Forest + Données Imputées Brutes...")
    executer_pipeline_entrainement(
        chemin_donnees=DATA_IMPUTED,
        nom_experience=NOM_EXP,
        type_modele="RandomForest",
        configuration_modele={"n_estimators": 100, "random_state": 42, "n_jobs": -1}
    )