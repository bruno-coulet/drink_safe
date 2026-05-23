"""
-------------------------------------------------------------------------------
Projet : Waterflow
Composant : Tests / Unitaires
Description : Validation isolée des fonctions de nettoyage et de transformation
              des données (imputation et standardisation).
-------------------------------------------------------------------------------
"""

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


def test_imputation_mediane_valeurs_manquantes() -> None:
    """
    Vérifie que l'imputation par la médiane remplace correctement les valeurs
    manquantes (NaN) par la valeur statistique exacte calculée.
    """
    # Données de test : la médiane des valeurs valides (6.8, 7.0, 7.2, 7.4) est 7.1
    df_test: pd.DataFrame = pd.DataFrame({"ph": [7.2, np.nan, 6.8, 7.4, 7.0]})
    
    imputer: SimpleImputer = SimpleImputer(strategy="median")
    df_test["ph"] = imputer.fit_transform(df_test[["ph"]])
    
    assert df_test["ph"].isnull().sum() == 0
    assert float(df_test["ph"].iloc[1]) == 7.1


def test_standardisation_distribution() -> None:
    """
    Vérifie que l'application du StandardScaler produit une distribution
    centrée sur 0 avec une variance égale à 1.
    """
    df_test: pd.DataFrame = pd.DataFrame({"Hardness": [100.0, 200.0, 300.0]})
    
    scaler: StandardScaler = StandardScaler()
    donnees_transformees = scaler.fit_transform(df_test[["Hardness"]])
    
    # Après standardisation, la moyenne doit être de 0 et l'écart-type de 1
    assert np.isclose(donnees_transformees.mean(), 0.0)
    assert np.isclose(donnees_transformees.std(), 1.0)