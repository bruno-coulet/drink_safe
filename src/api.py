"""
-------------------------------------------------------------------------------
Projet : Waterflow (Potabilité de l'eau)
Composant : API Backend de Prédiction
Description : Serveur FastAPI chargeant le modèle de classification depuis 
              le Model Registry de MLflow pour effectuer des prédictions en 
              temps réel.
-------------------------------------------------------------------------------
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import mlflow
import mlflow.sklearn

# Configuration de la connexion à MLflow Dockerisé
MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

MODEL_NAME: str = "WaterPotabilityBaseline"
# Utilisation de la version 1 du modèle généré par le run de test initial
MODEL_VERSION: str = "1"

# Dictionnaire global pour encapsuler le modèle de manière isolée
ml_models: dict[str, Any] = {}


class WaterFeatures(BaseModel):
    """
    Modèle de données Pydantic définissant la structure stricte
    des paramètres physico-chimiques d'un échantillon d'eau.
    Les clés doivent correspondre exactement aux colonnes du jeu d'entraînement.
    """
    ph: float = Field(..., description="Potentiel Hydrogène de l'eau (0-14)", example=7.2)
    Hardness: float = Field(..., description="Dureté de l'eau en mg/L", example=200.0)
    Solids: float = Field(..., description="Total des solides dissous en ppm", example=20000.0)
    Chloramines: float = Field(..., description="Concentration en chloramines en ppm", example=7.0)
    Sulfate: float = Field(..., description="Concentration en sulfates en mg/L", example=300.0)
    Conductivity: float = Field(..., description="Conductivité électrique en μS/cm", example=400.0)
    Organic_carbon: float = Field(..., description="Carbone organique total en ppm", example=14.2)
    Trihalomethanes: float = Field(..., description="Concentration en trihalométhanes en μg/L", example=66.3)
    Turbidity: float = Field(..., description="Turbidité de l'eau en NTU", example=4.0)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gère le cycle de vie de l'application FastAPI pour charger le modèle
    au démarrage et libérer les ressources à l'extinction.
    """
    try:
        # URI pointant vers la version spécifique enregistrée dans le registre
        model_uri: str = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
        ml_models["water_model"] = mlflow.sklearn.load_model(model_uri)
        print(f"✅ Modèle '{MODEL_NAME}' version {MODEL_VERSION} chargé avec succès depuis MLflow.")
    except Exception as e:
        print(f"⚠️ Impossible de charger le modèle depuis MLflow Registry: {e}")
        print("Mode dégradé : l'API fonctionne mais les prédictions renverront une erreur 503.")
        ml_models["water_model"] = None
        
    yield
    ml_models.clear()


app = FastAPI(
    title="Waterflow API - Backend",
    description="Service de prédiction de la potabilité de l'eau pour le projet MLOps.",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", tags=["Utility"])
def health_check() -> dict[str, str]:
    """
    Vérifie l'état de disponibilité de l'API et du modèle prédictif.
    """
    if ml_models.get("water_model") is None:
        return {"status": "amber", "message": "API active mais modèle non chargé."}
    return {"status": "green", "message": "API et modèle opérationnels."}


@app.post("/predict", tags=["Prediction"])
def predict_potability(data: WaterFeatures) -> dict[str, Any]:
    """
    Récupère les paramètres d'un échantillon, applique le modèle de classification
    et retourne la prédiction binaire associée au statut textuel.
    """
    model = ml_models.get("water_model")
    if model is None:
        raise HTTPException(
            status_code=503, 
            detail="Le modèle de prédiction n'est pas disponible sur le serveur."
        )
    
    try:
        # Conversion stricte des données Pydantic en DataFrame Pandas
        input_data: pd.DataFrame = pd.DataFrame([data.model_dump()])
        
        # Exécution de la prédiction via Scikit-Learn
        prediction = model.predict(input_data)
        potability_result: int = int(prediction[0])
        
        status_label: str = "Potable" if potability_result == 1 else "Non Potable"
        
        return {
            "prediction": potability_result,
            "status": status_label
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de l'exécution de la prédiction: {str(e)}"
        )