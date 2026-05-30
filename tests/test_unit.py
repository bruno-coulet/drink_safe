"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Suite de Tests Unitaires (PyTest)
Description : Validation isolée des schémas de données Pydantic, de la sécurité 
              des en-têtes (Clés API) et de l'intégrité des règles métiers OMS.
-------------------------------------------------------------------------------
"""

from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from src.api import app

# Instanciation du client de test FastAPI
client = TestClient(app)


def test_schema_validation_clients_manquant() -> None:
    """Vérifie que l'API lève une erreur 422 si le corps de la requête clients est incomplet."""
    # Payload invalide : il manque le champ obligatoire 'denomination'
    payload_incomplet: Dict[str, Any] = {
        "client_id": "TEST_LAB_01",
        "adresse": "123 Rue de la Pureté, Marseille"
    }
    
    response = client.post("/api/clients/", json=payload_incomplet)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_securite_cle_api_manquante_mesures() -> None:
    """Vérifie le rejet (HTTP 401) du dépôt de mesures si le Header X-API-Key est absent."""
    payload_mesures: Dict[str, Any] = {
        "ph": 7.2, "Hardness": 200.0, "Solids": 15000.0, "Chloramines": 3.0,
        "Sulfate": 300.0, "Conductivity": 400.0, "Organic_carbon": 12.0,
        "Trihalomethanes": 50.0, "Turbidity": 2.5, "observations": "Test unitaire"
    }
    
    # Appel sans injecter de headers HTTP
    response = client.post("/api/measurements/", json=payload_mesures)
    assert response.status_code == 401
    assert "manquante" in response.json()["detail"]


def test_garde_fou_oms_ph_acide() -> None:
    """Vérifie que la barrière sanitaire OMS rejette instantanément un pH trop acide."""
    # Simulation d'un client valide pour contourner la dépendance d'authentification lors du test unitaire
    # Un pH de 4.5 est critique et doit déclencher le code 'Non Potable' sans interroger le modèle ML
    payload_critique: Dict[str, Any] = {
        "model_choice": "XGBClassifier",
        "ph": 4.5,
        "Hardness": 210.0,
        "Solids": 18000.0,
        "Chloramines": 2.5,
        "Sulfate": 320.0,
        "Conductivity": 410.0,
        "Organic_carbon": 10.5,
        "Trihalomethanes": 45.0,
        "Turbidity": 1.2,
        "observations": "Test barrière OMS pH"
    }
    
    # Note MLOps : On passe une clé fictive car la vérification BDD lèvera une 401. 
    # Pour tester purement la fonction logique du garde-fou, on simule l'en-tête, 
    # mais l'idéal en isolation complète est de mocker la fonction 'get_current_client'.
    # Ici, nous testons la réponse de la couche business rules.
    
    from src.dependencies.auth import get_current_client
    # Mocking de la dépendance de sécurité pour forcer la validation du client sans toucher à PostgreSQL
    app.dependency_overrides[get_current_client] = lambda: "CLIENT_TEST_OK"
    
    response = client.post("/api/predict/", json=payload_critique)
    
    # Nettoyage des mocks après exécution
    app.dependency_overrides.clear()
    
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == 0
    assert data["status"] == "Non Potable"
    assert "Garde-fou" in data["decision_reason"] or "OMS" in data["decision_reason"]


def test_garde_fou_oms_turbidite_elevee() -> None:
    """Vérifie le rejet automatique par l'OMS si la turbidité dépasse le seuil de 5.0 NTU."""
    payload_trouble: Dict[str, Any] = {
        "model_choice": "RandomForestClassifier",
        "ph": 7.4, "Hardness": 195.0, "Solids": 21000.0, "Chloramines": 3.1,
        "Sulfate": 340.0, "Conductivity": 430.0, "Organic_carbon": 13.2,
        "Trihalomethanes": 60.0,
        "Turbidity": 6.8,  # Seuil OMS max fixé à 5.0 NTU
        "observations": "Test barrière OMS Turbidité"
    }
    
    from src.dependencies.auth import get_current_client
    app.dependency_overrides[get_current_client] = lambda: "CLIENT_TEST_OK"
    
    response = client.post("/api/predict/", json=payload_trouble)
    app.dependency_overrides.clear()
    
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == 0
    assert data["status"] == "Non Potable"
    assert "Turbidité" in data["decision_reason"]