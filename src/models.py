"""
-------------------------------------------------------------------------------
Projet : Waterflow (Potabilité de l'eau)
Composant : Catalogue des Modèles
Description : Centralise les instances et hyperparamètres des algorithmes
              de classification du projet.
-------------------------------------------------------------------------------
"""

from typing import Any
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

RANDOM_STATE = 42


def get_models() -> dict[str, Any]:
    """
    Retourne le dictionnaire complet des modèles configurés pour le projet.
    L'ajout d'un modèle ici l'intègre automatiquement au pipeline d'entraînement.
    """
    models = {
        "LogisticRegression": LogisticRegression(
            max_iter=1000,
            random_state=RANDOM_STATE
        ),

        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            random_state=RANDOM_STATE,
            n_jobs=-1
        ),

        "XGBClassifier": XGBClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=RANDOM_STATE
        ),

        "MLPClassifier": MLPClassifier(
            hidden_layer_sizes=(100, 50),
            max_iter=500,
            activation="relu",
            solver="adam",
            random_state=RANDOM_STATE
        )
    }

    return models