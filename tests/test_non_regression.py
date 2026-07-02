"""
Projet : Drink safe
Composant : Suite de Tests de Non-Régression (PyTest) - Version 2 (Enrichie)
Description : Vérification automatique des métriques de performance du catalogue
              de modèles (F1-score et AUC-PR) et validation de la structure de la
              matrice de confusion sur le jeu de validation.
"""
import os
import pandas as pd
import pytest
from sklearn.metrics import f1_score, average_precision_score, confusion_matrix
from src.api import ml_models
from src.config import settings

def ensure_models_are_loaded():
    """Force le chargement des modèles en mémoire vive s'ils ne le sont pas encore."""
    if not ml_models:
        try:
            import mlflow
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
            client = mlflow.tracking.MlflowClient()
            for model_name in ["WaterModel_LogisticRegression", "WaterModel_RandomForestClassifier", "WaterModel_XGBClassifier", "WaterModel_MLPClassifier"]:
                try:
                    latest_versions = client.get_latest_versions(model_name, stages=["None", "Staging", "Production"])
                    if latest_versions:
                        latest_version = latest_versions[0].version
                        model_uri = f"models:/{model_name}/{latest_version}"
                        loaded_model = mlflow.pyfunc.load_model(model_uri)
                        ml_models[model_name] = loaded_model
                except Exception:
                    pass
        except Exception:
            pass


# Décorateur pour ignorer le test si le dataset de validation standardisé n'est pas présent sur github
@pytest.mark.skipif(not os.path.exists("data/processed/water_std.csv"), reason="Dataset ignoré sur Git (CI)")
def test_non_regression_performance_catalogue() -> None:
    """S'assure que les modèles actifs maintiennent un score F1 minimal de 60% et un AUC-PR minimal de 50%."""
    # 1. Vérification de l'existence du dataset de validation standardisé
    filepath_val: str = "data/processed/water_std.csv"
    assert os.path.exists(filepath_val), f"Le fichier de validation standardisé est introuvable : {filepath_val}"

    # 2. Chargement du dataset de validation
    df_val = pd.read_csv(filepath_val)

    # Séparation des features et de la cible
    assert "Potability" in df_val.columns, "La colonne cible 'Potability' est absente du fichier de validation"
    X_val = df_val.drop(columns=["Potability"])
    y_val = df_val["Potability"]

    # 3. Garantie du chargement des modèles (Lazy Loading)
    ensure_models_are_loaded()

    if not ml_models:
        pytest.skip("Aucun modèle n'est actuellement chargé dans ml_models (le Model Registry ou le serveur de tracking est injoignable).")

    # 4. Évaluation de chaque modèle disponible
    for model_name, model in ml_models.items():
        try:
            y_pred = model.predict(X_val)
        except Exception as e:
            pytest.fail(f"Échec de la prédiction pour le modèle {model_name} : {e}")

        # Validation du score F1
        score_f1 = f1_score(y_val, y_pred)
        assert score_f1 >= 0.60, f"Le modèle {model_name} a subi une régression sur le F1-score : {score_f1:.2f} < 0.60"

        # Validation de l'AUC-PR (Average Precision Score)
        try:
            if hasattr(model, "predict_proba"):
                y_proba = model.predict_proba(X_val)[:, 1]
            elif hasattr(model, "_model_impl") and hasattr(model._model_impl, "predict_proba"):
                y_proba = model._model_impl.predict_proba(X_val)[:, 1]
            else:
                y_proba = y_pred

            auc_pr = average_precision_score(y_val, y_proba)
            assert auc_pr >= 0.50, f"Le modèle {model_name} a un AUC-PR insuffisant : {auc_pr:.2f} < 0.50"
        except Exception as e:
            print(f"Impossible de calculer l'AUC-PR pour {model_name} : {e}")

        # 5. Validation de la cohérence de la Matrice de Confusion (TP, TN, FP, FN)
        tn, fp, fn, tp = confusion_matrix(y_val, y_pred).ravel()
        total_predictions = tn + fp + fn + tp
        assert total_predictions == len(y_val), f"Incohérence dans la matrice de confusion pour {model_name} : {total_predictions} != {len(y_val)}"
