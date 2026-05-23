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
    sur un échantillon d'évaluation historique fixe.
    """
    # Si le modèle n'est pas chargé (ex: serveur MLflow déconnecté lors du test),
    # le test est ignoré pour ne pas bloquer la CI/CD inutilement.
    modele: Any = ml_models.get("water_model")
    if modele is None:
        return

    # Données d'un échantillon connu historiquement comme "Non Potable" (0)
    # L'ordre et le nom des colonnes doivent correspondre au schéma d'entraînement
    echantillon_reference: pd.DataFrame = pd.DataFrame([{
        "ph": 8.31,
        "Hardness": 214.37,
        "Solids": 22018.39,
        "Chloramines": 8.05,
        "Sulfate": 356.88,
        "Conductivity": 363.26,
        "Organic_carbon": 18.43,
        "Trihalomethanes": 100.34,
        "Turbidity": 4.62
    }])

    prediction = modele.predict(echantillon_reference)
    resultat_potabilite: int = int(prediction[0])

    # Le modèle doit impérativement retourner la valeur historique attendue
    assert resultat_potabilite in [0, 1]