"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Suite de Tests Fonctionnels et d'Intégration (PyTest)
Description : Validation du scénario complet de bout en bout : enregistrement 
              client, ingestion OCR, persistance PostgreSQL et inférence.
-------------------------------------------------------------------------------
"""

from typing import Any, Dict
import unittest.mock as mock
from fastapi.testclient import TestClient
import pytest

from src.api import app

# Instanciation du client de test FastAPI
client = TestClient(app)


def test_scenario_complet_bout_en_bout() -> None:
    """Valide le cycle de vie applicatif complet exigé par les spécifications."""
    
    # =========================================================================
    # ÉTAPPE 1 : Enregistrement d'un nouveau client industriel
    # =========================================================================
    payload_client: Dict[str, Any] = {
        "client_id": "INTEGRATION_TEST_CORP",
        "denomination": "Société d'Analyse des Eaux de Marseille",
        "adresse": "45 Rue de la République, 13002 Marseille"
    }
    
    response_client = client.post("/api/clients/", json=payload_client)
    assert response_client.status_code == 201
    data_client = response_client.json()
    
    assert data_client["status"] == "Succès"
    assert data_client["client_id"] == "INTEGRATION_TEST_CORP"
    
    # Récupération de la clé API dynamique générée nativement par le système
    cle_api_generee: str = data_client["api_key"]
    assert cle_api_generee.startswith("wf_live_")

    # Préparation des en-têtes de sécurité requis pour les appels clients suivants
    headers_authentifies: Dict[str, str] = {"X-API-Key": cle_api_generee}

    # =========================================================================
    # ÉTAPE 2 : Téléversé de fiche laboratoire et Ingestion OCR (Mocké)
    # =========================================================================
    # Simulation du fichier binaire transmis par formulaire Multi-part form-data
    fichier_simulation = (
        "fiche_aquatest.pdf", 
        b"%PDF-1.4 ... contenu binaire simule ...", 
        "application/pdf"
    )
    payload_fichiers = {"file": fichier_simulation}

    # Structure attendue en retour simulé de l'API externe OCR.space
    reponse_mockee_ocr_space: Dict[str, Any] = {
        "IsErroredOnProcessing": False,
        "ParsedResults": [
            {
                "ParsedText": "RAPPORT LABORATOIRE AQUATEST\npH : 7.6\nDurete : 205.0\nSolides : 19500.0\nChloramines : 3.2\nSulfate : 310.0\nConductivite : 415.0\nCarbone : 11.5\nTrihalomethanes : 55.0\nTurbidite : 0.7\n"
            }
        ]
    }

    # Interception de l'appel requests.post vers OCR.space pour injecter notre réponse simulée
    with mock.patch("src.routes.ocr.requests.post") as mock_post:
        # Configuration du mock pour renvoyer un code HTTP 200 et notre dictionnaire JSON
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = reponse_mockee_ocr_space
        mock_post.return_value = mock_response

        # Exécution de la requête sur notre endpoint unifié
        response_ocr = client.post(
            "/api/ocr/lab-report", 
            files=payload_fichiers, 
            headers=headers_authentifies
        )

    # Validations des résultats de la brique OCR
    assert response_ocr.status_code == 201
    data_ocr = response_ocr.json()
    assert data_ocr["status"] == "Succès"
    assert "prelevement_id" in data_ocr
    
    # Validation du bon fonctionnement du parser par expressions régulières (Regex)
    mesures_extraites = data_ocr["extracted_data"]
    assert mesures_extraites["ph"] == 7.6
    assert mesures_extraites["Turbidity"] == 0.7
    assert mesures_extraites["Chloramines"] == 3.2

    # =========================================================================
    # ÉTAPE 3 : Inférence du modèle d'Intelligence Artificielle (API Model)
    # =========================================================================
    # Payload d'inférence basé sur les métriques extraites de l'OCR
    payload_prediction: Dict[str, Any] = {
        "model_choice": "LogisticRegression",
        "ph": mesures_extraites["ph"],
        "Hardness": mesures_extraites["Hardness"],
        "Solids": mesures_extraites["Solids"],
        "Chloramines": mesures_extraites["Chloramines"],
        "Sulfate": mesures_extraites["Sulfate"],
        "Conductivity": mesures_extraites["Conductivity"],
        "Organic_carbon": mesures_extraites["Organic_carbon"],
        "Trihalomethanes": "%s" % mesures_extraites["Trihalomethanes"],
        "Turbidity": mesures_extraites["Turbidity"],
        "observations": "Validation finale du flux d'intégration"
    }

    # Pour s'assurer du passage du modèle ML en environnement de test sans charger 
    # de lourds fichiers .pkl depuis le Model Registry, on mocke l'inférence
    # de Scikit-Learn / XGBoost en forçant un retour potable (1)
    with mock.patch("src.api.ml_models") as mock_models:
        mock_instance_model = mock.MagicMock()
        # Simulation de la méthode native .predict() de Scikit-Learn
        mock_instance_model.predict.return_value = [1]
        
        # Injection du faux modèle dans notre dictionnaire global d'API
        mock_models.get.return_value = mock_instance_model

        response_pred = client.post(
            "/api/predict/", 
            json=payload_prediction, 
            headers=headers_authentifies
        )

    # Validations finales du succès du pipeline complet
    assert response_pred.status_code == 200
    data_pred = response_pred.json()
    assert data_pred["prediction"] == 1
    assert data_pred["status"] == "Potable"
    assert data_pred["model_used"] == "LogisticRegression"