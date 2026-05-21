from pathlib import Path

import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

from models import get_models


# =========================
# CONFIG
# =========================

ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = ROOT / "data" / "processed" / "water_inputed.csv"

TARGET = "Potability"

EXPERIMENT_NAME = "water_quality_classification"

RANDOM_STATE = 42

TEST_SIZE = 0.2


# =========================
# DATA
# =========================

def load_data():
    df = pd.read_csv(DATA_PATH)

    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    return X, y


def split_data(X, y):
    return train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE
    )


# =========================
# EVALUATION
# =========================

def evaluate_model(model, X_val, y_val):
    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision": precision_score(y_val, y_pred),
        "recall": recall_score(y_val, y_pred),
        "f1_score": f1_score(y_val, y_pred),
        "roc_auc": roc_auc_score(y_val, y_proba),
    }

    cm = confusion_matrix(y_val, y_pred)

    return metrics, cm


# =========================
# MLFLOW TRAINING
# =========================

def train_and_log_model(model_name, model, X_train, X_val, y_train, y_val):
    with mlflow.start_run(run_name=model_name):

        mlflow.log_param("model_name", model_name)
        mlflow.log_param("target", TARGET)
        mlflow.log_param("test_size", TEST_SIZE)
        mlflow.log_param("random_state", RANDOM_STATE)

        mlflow.log_params(model.get_params())

        model.fit(X_train, y_train)

        metrics, cm = evaluate_model(model, X_val, y_val)

        mlflow.log_metrics(metrics)

        mlflow.log_metric("true_negative", cm[0][0])
        mlflow.log_metric("false_positive", cm[0][1])
        mlflow.log_metric("false_negative", cm[1][0])
        mlflow.log_metric("true_positive", cm[1][1])

        mlflow.sklearn.log_model(model, artifact_path="model")

        print(f"\nModel: {model_name}")
        print(metrics)
        print("Confusion matrix:")
        print(cm)


# =========================
# MAIN
# =========================

def main():
    # Dis à MLflow d'envoyer les métriques et modèles au serveur Docker, pas en local !
    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    # mlflow.set_tracking_uri("file:./runs")
    # mlflow.set_experiment("water_quality_classification")
    mlflow.set_experiment("water_potability_clean_v1")

    X, y = load_data()

    X_train, X_val, y_train, y_val = split_data(X, y)

    models = get_models()

    for model_name, model in models.items():
        train_and_log_model(
            model_name=model_name,
            model=model,
            X_train=X_train,
            X_val=X_val,
            y_train=y_train,
            y_val=y_val
        )


if __name__ == "__main__":
    main()