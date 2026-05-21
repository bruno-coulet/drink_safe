import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
# Imaginons que tu as isolé ton imputer dans une fonction
# de ton cleaning_utils

def test_imputation_median():
    # 1. Données de test (un pH manquant)
    data = pd.DataFrame({"ph": [7.2, np.nan, 6.8, 7.4, 7.0]})
    
    # 2. Logique à tester (Imputation par la médiane)
    imputer = SimpleImputer(strategy="median")
    data["ph"] = imputer.fit_transform(data[["ph"]])
    
    # 3. Vérification (La médiane de 6.8, 7.0, 7.2, 7.4 est 7.1)
    assert data["ph"].isnull().sum() == 0
    assert data["ph"].iloc[1] == 7.1