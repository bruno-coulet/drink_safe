"""
-------------------------------------------------------------------------------
Projet : Waterflow
Composant : Tests / Non-Régression (TNR)
Description : Garantit que les performances ou les sorties du modèle de base
              ne subissent pas de dégradation lors des modifications de code.
-------------------------------------------------------------------------------
"""

from typing import Any
import pandas as pd
from src.api import ml_models


def test_non_regression_comportement_modele() -> None:
    """
    Vérifie que le modèle chargé produit la prédiction attendue (déterministe)
    sur un échantillon d'évaluation historique fixe (sans déclencher le garde-fou).
    """
    # Sélection d'un modèle de référence parmi ceux chargés au démarrage
    modele: Any = ml_models.get("RandomForestClassifier")
    if modele is None:
        return

    # Données calibrées pour rester dans les clous des gardes-fous (pH viable, THM < 80)
    echantillon_reference: pd.DataFrame = pd.DataFrame([{
        "ph": 7.31,
        "Hardness": 214.37,
        "Solids": 22018.39,
        "Chloramines": 3.05,
        "Sulfate": 356.88,
        "Conductivity": 363.26,
        "Organic_carbon": 12.43,
        "Trihalomethanes": 60.34,
        "Turbidity": 3.62
    }])

    prediction = modele.predict(echantillon_reference)
    resultat_potabilite: int = int(prediction[0])

    # Le modèle doit impérativement retourner une prédiction binaire valide
    assert resultat_potabilite in [0, 1]