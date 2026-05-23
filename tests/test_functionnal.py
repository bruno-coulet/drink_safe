"""
-------------------------------------------------------------------------------
Projet : Waterflow
Composant : Tests / Fonctionnels
Description : Validation des routes de l'API FastAPI, de la gestion des erreurs
              et du respect du schéma des payloads d'entrée.
-------------------------------------------------------------------------------
"""

from typing import Any
from fastapi.testclient import TestClient
from src.api import app

client: TestClient = TestClient(app)


def test_route_sante_api() -> None:
    """
    Vérifie que le point d'accès de vérification de santé répond avec un code
    200 et un format JSON correct.
    """
    reponse = client.get("/health")
    assert reponse.status_code == 200
    
    donnees: dict[str, Any] = reponse.json()
    assert "status" in donnees
    assert donnees["status"] in ["green", "amber"]


def test_prediction_erreur_validation_pydantic() -> None:
    """
    Vérifie que l'API rejette explicitement (code 422) une requête dont
    le payload JSON ne respecte pas le modèle de données obligatoire.
    """
    # Envoi d'un payload vide pour forcer l'échec de la validation Pydantic
    reponse = client.post("/predict", json={})
    assert reponse.status_code == 422