"""
-------------------------------------------------------------------------------
Projet : Waterflow
Composant : Tests / Fonctionnels
Description : Validation des routes de l'API FastAPI, de la gestion des erreurs,
              des gardes-fous et de la paramétrisation des algorithmes.
-------------------------------------------------------------------------------
"""

from typing import Any
import pytest
from fastapi.testclient import TestClient
from src.api import app

client: TestClient = TestClient(app)

# Liste des algorithmes pris en charge par l'infrastructure
LISTE_ALGOS = ["LogisticRegression", "RandomForestClassifier", "XGBClassifier", "MLPClassifier"]


def test_route_sante_api() -> None:
    """Vérifie le point d'accès de statut de l'API."""
    reponse = client.get("/health")
    assert reponse.status_code == 200
    
    donnees: dict[str, Any] = reponse.json()
    assert "status" in donnees
    assert donnees["status"] in ["green", "amber"]


def test_prediction_erreur_validation_pydantic() -> None:
    """Vérifie le rejet d'un payload invalide."""
    reponse = client.post("/predict", json={})
    assert reponse.status_code == 422


@pytest.mark.parametrize("nom_modele", LISTE_ALGOS)
def test_prediction_route_interrogation_modeles(nom_modele: str) -> None:
    """Vérifie que chaque modèle répond correctement à une requête nominale."""
    payload = {
        "model_choice": nom_modele,
        "ph": 7.2,
        "Hardness": 200.0,
        "Solids": 20000.0,
        "Chloramines": 3.5,
        "Sulfate": 300.0,
        "Conductivity": 400.0,
        "Organic_carbon": 14.2,
        "Trihalomethanes": 66.3,
        "Turbidity": 4.0
    }
    reponse = client.post("/predict", json=payload)
    # 200 si le serveur MLflow est up et le modèle entraîné, 503 s'il n'est pas encore poussé
    assert reponse.status_code in [200, 503]


@pytest.mark.parametrize("nom_modele", LISTE_ALGOS)
def test_garde_fou_interception_ph_extreme(nom_modele: str) -> None:
    """Vérifie que la couche métier bloque un pH toxique, peu importe l'algorithme."""
    payload = {
        "model_choice": nom_modele,
        "ph": 1.5,  # Eau ultra acide
        "Hardness": 200.0,
        "Solids": 20000.0,
        "Chloramines": 3.0,
        "Sulfate": 300.0,
        "Conductivity": 400.0,
        "Organic_carbon": 10.0,
        "Trihalomethanes": 50.0,
        "Turbidity": 2.0
    }
    reponse = client.post("/predict", json=payload)
    assert reponse.status_code == 200
    
    donnees = reponse.json()
    assert donnees["prediction"] == 0
    assert donnees["status"] == "Non Potable"
    assert "Garde-fou" in donnees["decision_reason"]