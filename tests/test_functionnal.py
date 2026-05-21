from fastapi.testclient import TestClient
import pytest
from src.api import app

# On initialise le client de test en lui passant ton application FastAPI
client = TestClient(app)

def test_health_endpoint():
    """Vérifie que la route de santé de l'API répond correctement."""
    response = client.get("/health")
    assert response.status_code == 200
    # On s'assure que la réponse contient bien le statut (green ou amber si MLflow est éteint)
    assert "status" in response.json()

def test_predict_validation_error():
    """Vérifie que l'API bloque les requêtes si des données sont manquantes ou mal formées."""
    # On envoie un dictionnaire vide pour forcer une erreur de validation Pydantic
    response = client.post("/predict", json={})
    
    # FastAPI doit renvoyer un code 422 (Unprocessable Entity)
    assert response.status_code == 422