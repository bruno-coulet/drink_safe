"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Pipeline d'Entraînement et Tracking MLOps (MLflow)
Description : Chargement des datasets, entraînement du catalogue de modèles,
              initialisation automatique de PostgreSQL et enregistrement
              dans le Model Registry.
              Split stratifié 80/20 + CV 5 folds pour estimer la variance
              des métriques. AUC-PR tracké (métrique adaptée aux classes
              déséquilibrées). Matrice de confusion loggée par modèle.
-------------------------------------------------------------------------------
"""

import os
from collections import defaultdict
from typing import Any
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, average_precision_score, confusion_matrix,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight
import mlflow
import mlflow.sklearn
from pathlib import Path


import mlflow

import requests
_old_prepare_headers = requests.models.PreparedRequest.prepare_headers
def patched_prepare_headers(self, headers):
    _old_prepare_headers(self, headers)
    self.headers["Host"] = "localhost:5000"
requests.models.PreparedRequest.prepare_headers = patched_prepare_headers

from src.config import settings, init_db
from src.models import get_models


mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
# mlflow.set_experiment("Water_Potability_Evaluation_v2")
mlflow.set_experiment("Drink_safe")


# def _extraire_params(modele: Any) -> dict:
#     """
#     Extrait les hyperparamètres en gérant les Pipeline sklearn.
#     Pour un Pipeline, remonte les params du dernier estimateur (step 'model').
#     """
#     if isinstance(modele, Pipeline):
#         etape = modele.named_steps.get("model", list(modele.named_steps.values())[-1])
#         return etape.get_params(deep=False)
#     return modele.get_params(deep=False)

def _extraire_params(modele: Any, nom_dataset: str) -> dict:
    """
    Extrait les hyperparamètres en gérant les Pipeline sklearn,
    et ajoute manuellement le nom du dataset
    """
    # Extrait les paramètres algorithmiques
    if isinstance(modele, Pipeline):
        etape = modele.named_steps.get("model", list(modele.named_steps.values())[-1])
        params = etape.get_params(deep=False)
    else:
        params = modele.get_params(deep=False)

    # Injecte le paramètre personnalisé dans le dictionnaire
    params["dataset_type"] = nom_dataset

    # Retourne le dictionnaire complet
    return params





def _fit_kwargs(modele: Any, y: pd.Series) -> dict:
    """
    Retourne les kwargs de fit pour compenser le déséquilibre des classes sur MLP.
    MLPClassifier n'a pas de class_weight natif : sample_weight calculé par fold.
    Pour un Pipeline le kwarg est préfixé 'model__'.
    """
    if isinstance(modele, Pipeline):
        etape = modele.named_steps.get("model", list(modele.named_steps.values())[-1])
        if isinstance(etape, MLPClassifier):
            return {"model__sample_weight": compute_sample_weight("balanced", y)}
    return {}


def _scores_cv(
    modele: Any,
    X: pd.DataFrame,
    y: pd.Series,
    cv: StratifiedKFold,
) -> dict[str, list[float]]:
    """
    Validation croisée manuelle sur folds stratifiés.
    Le sample_weight est recalculé à chaque fold pour éviter toute fuite de données.
    Retourne les listes de scores bruts (mean/std calculés par l'appelant).
    """
    scores: dict[str, list[float]] = defaultdict(list)

    for train_idx, val_idx in cv.split(X, y):
        X_fold_train, X_fold_val = X.iloc[train_idx], X.iloc[val_idx]
        y_fold_train, y_fold_val = y.iloc[train_idx], y.iloc[val_idx]

        modele.fit(X_fold_train, y_fold_train, **_fit_kwargs(modele, y_fold_train))
        y_pred  = modele.predict(X_fold_val)
        y_proba = (
            modele.predict_proba(X_fold_val)[:, 1]
            if hasattr(modele, "predict_proba") else None
        )

        scores["accuracy"].append(float(accuracy_score(y_fold_val, y_pred)))
        scores["f1"].append(float(f1_score(y_fold_val, y_pred, average="binary", zero_division=0)))
        scores["precision"].append(float(precision_score(y_fold_val, y_pred, average="binary", zero_division=0)))
        scores["recall"].append(float(recall_score(y_fold_val, y_pred, average="binary", zero_division=0)))
        if y_proba is not None:
            scores["roc_auc"].append(float(roc_auc_score(y_fold_val, y_proba)))
            scores["pr_auc"].append(float(average_precision_score(y_fold_val, y_proba)))

    return scores


def executer_pipeline_mlops() -> None:
    """Orchestre l'initialisation SQL, le training et le tracking MLflow."""

    print("[MLOps] Etape 1 : Initialisation des tables PostgreSQL...")
    init_db()

    print("[MLOps] Etape 2 : Chargement de la matrice de données...")

    data_dir = Path("data/processed/")

    # Charge et split les DEUX datasets en mémoire
    df_imputed = pd.read_csv(Path( data_dir / "water_imputed.csv"))
    X_train_imp, X_test_imp, y_train_imp, y_test_imp = train_test_split(
        df_imputed.drop(columns=["Potability"], errors="ignore"), df_imputed["Potability"], test_size=0.2, random_state=42, stratify=df_imputed["Potability"]
    )

    df_std = pd.read_csv(Path(data_dir / "water_std.csv"))
    X_train_std, X_test_std, y_train_std, y_test_std = train_test_split(
        df_std.drop(columns=["Potability"], errors="ignore"), df_std["Potability"], test_size=0.2, random_state=42, stratify=df_std["Potability"]
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    modeles = get_models()

    for nom_modele, model_instance in modeles.items():
        print(f"[MLOps] Lancement du run MLflow : {nom_modele}...")

        # 2. SELECTION DYNAMIQUE DU DATASET SELON LE MODELE
        if "LogisticRegression" in nom_modele or "MLP" in nom_modele:
            X_train, X_test, y_train, y_test = X_train_std, X_test_std, y_train_std, y_test_std
            file_name = Path("data/processed/water_std.csv").name
        else: # RandomForest, XGBoost...
            X_train, X_test, y_train, y_test = X_train_imp, X_test_imp, y_train_imp, y_test_imp
            file_name = Path("data/processed/water_imputed.csv").name


        # (Optionnel) Affiche la stratification
        print(
            f"        Split stratifié — "
            f"Train: {len(y_train)} ({y_train.mean():.1%} potable) | "
            f"Test: {len(y_test)} ({y_test.mean():.1%} potable)"
        )

        # 3. Bloc d'exécution mlflow
        with mlflow.start_run(run_name=nom_modele):

            mlflow.log_param("architecture", nom_modele)
            mlflow.log_param("n_train", len(y_train))
            mlflow.log_param("n_test", len(y_test))
            mlflow.log_param("ratio_potable_train", round(float(y_train.mean()), 4))
            mlflow.log_param("ratio_potable_test", round(float(y_test.mean()), 4))
            mlflow.log_params(_extraire_params(model_instance, file_name))

            # --- Validation croisée 5 folds stratifiés ---
            print(f"  CV 5 folds...")
            scores_cv = _scores_cv(model_instance, X_train, y_train, cv)
            for metrique, valeurs in scores_cv.items():
                mlflow.log_metric(f"cv_mean_{metrique}", round(float(np.mean(valeurs)), 4))
                mlflow.log_metric(f"cv_std_{metrique}", round(float(np.std(valeurs)), 4))

            # --- Entraînement final sur l'ensemble du train ---
            print(f"  Entrainement final...")
            model_instance.fit(X_train, y_train, **_fit_kwargs(model_instance, y_train))

            y_pred_test  = model_instance.predict(X_test)
            y_pred_train = model_instance.predict(X_train)
            y_proba_test = (
                model_instance.predict_proba(X_test)[:, 1]
                if hasattr(model_instance, "predict_proba") else None
            )

            # --- Métriques test (généralisation) ---
            metriques_test: dict[str, float] = {
                "test_accuracy":  round(float(accuracy_score(y_test, y_pred_test)), 4),
                "test_f1":        round(float(f1_score(y_test, y_pred_test, average="binary", zero_division=0)), 4),
                "test_precision": round(float(precision_score(y_test, y_pred_test, average="binary", zero_division=0)), 4),
                "test_recall":    round(float(recall_score(y_test, y_pred_test, average="binary", zero_division=0)), 4),
            }
            if y_proba_test is not None:
                metriques_test["test_roc_auc"] = round(float(roc_auc_score(y_test, y_proba_test)), 4)
                metriques_test["test_pr_auc"]  = round(float(average_precision_score(y_test, y_proba_test)), 4)
            mlflow.log_metrics(metriques_test)

            # --- Métriques train (détection de surapprentissage) ---
            mlflow.log_metrics({
                "train_accuracy": round(float(accuracy_score(y_train, y_pred_train)), 4),
                "train_f1":       round(float(f1_score(y_train, y_pred_train, average="binary", zero_division=0)), 4),
            })

            # --- Matrice de confusion (test set) ---
            tn, fp, fn, tp = confusion_matrix(y_test, y_pred_test).ravel()
            mlflow.log_metrics({
                "vrais_negatifs": int(tn),  # non-potable correct
                "faux_positifs":  int(fp),  # non-potable déclaré potable (risque sanitaire)
                "faux_negatifs":  int(fn),  # potable déclaré non-potable (gaspillage)
                "vrais_positifs": int(tp),  # potable correct
                "test_recall_non_potable": round(float(recall_score(y_test, y_pred_test, pos_label=0, zero_division=0)), 4),
            })

            nom_registre = f"{nom_modele}"
            mlflow.sklearn.log_model(
                sk_model=model_instance,
                artifact_path="model",
                registered_model_name=nom_registre
            )
            print(f"[MLOps] OK — {nom_registre} enregistre dans le Model Registry.")


if __name__ == "__main__":
    executer_pipeline_mlops()
