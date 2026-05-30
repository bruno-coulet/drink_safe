"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Suite de Tests de Non-Régression (PyTest)
Description : Vérification automatique de l'intégrité des performances du 
              catalogue de modèles d'IA par rapport à un seuil critique.
-------------------------------------------------------------------------------
"""

import os
from typing import Any, Dict
import pandas as pd
import pytest
from sklearn.metrics import f1_score

from src.api import ml_models


def test_non_regression_performance_catalogue() -> None:
    """S'assure que les modèles actifs maintiennent un score F1 minimal de 60%."""
    # 1. Vérification de l'existence du dataset de validation standardisé
    filepath_val: str = "data/processed/water_std.csv"
    # Ci Dessous : lante sur github car le dataset n'est pas dans le repo
    # En local, il doit être présent pour que le test soit exécuté.
    # assert os.path.exists(filepath_val), f"Le dataset de validation {filepath_val} est introuvable."
    if not os.path.exists(filepath_val):
        pytest.skip("Dataset de validation introuvable (Ignoré en CI/CD).")

    # 2. Chargement des données de test
    df_val: pd.DataFrame = pd.read_csv(filepath_val)
    
    # Extraction de la variable cible et des features
    X_val: pd.DataFrame = df_val.drop(columns=["Potability"], errors="ignore")
    y_true: pd.Series = df_val["Potability"]

    # Seuil de performance minimal acceptable pour la production (60%)
    seuil_f1_minimal: float = 0.60

    # 3. Vérification qu'au moins un modèle est instancié en mémoire
    modeles_actifs = [k for k, v in ml_models.items() if v is not None]
    if not modeles_actifs:
        pytest.skip("Aucun modèle n'est actuellement chargé dans le registre d'API. Test ignoré.")

    # 4. Évaluation de non-régression sur chaque modèle actif
    for nom_modele in modeles_actifs:
        model = ml_models[nom_modele]
        
        # Calcul des prédictions sur le jeu de validation
        y_pred = model.predict(X_val)
        score_f1: float = float(f1_score(y_true, y_pred, zero_division=0))

        print(f"[Non-Régression] Modèle: {nom_modele} | Score F1: {score_f1:.4f}")

        # Le test échoue si le modèle réagit moins bien que le seuil de garde-fou fixé
        assert score_f1 >= seuil_f1_minimal, (
            f"Régression détectée pour le modèle {nom_modele} ! "
            f"Score F1 actuel: {score_f1:.4f} < Seuil requis: {seuil_f1_minimal:.4f}"
        )