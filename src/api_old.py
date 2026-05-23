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
from typing import Any, AsyncGenerator, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import mlflow
import mlflow.sklearn

# MODEL_NAME: str = "WaterPotabilityBaseline"
# # Utilisation de la version 1 du modèle généré par le run de test initial
# MODEL_VERSION: str = "1"

MODEL_LOGISTIC_REGRESSION = "WaterPotabilityBaseline"  # Modèle 1
MODEL_RANDOM_FOREST = "WaterPotabilityRandomForest"      # Modèle 2 (à enregistrer via train.py)

# Configuration de la connexion à MLflow Dockerisé
MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)



# Dictionnaire global pour encapsuler le modèle de manière isolée
ml_models: dict[str, Any] = {}


# schéma Pydantic
class WaterFeatures(BaseModel):
    """
    Modèle de données Pydantic définissant la structure stricte
    des paramètres physico-chimiques d'un échantillon d'eau.
    Les clés doivent correspondre exactement aux colonnes du jeu d'entraînement.
    """
    model_choice: Literal["logistic_regression", "random_forest"] = Field(..., description="Le modèle à utiliser pour la prédiction")
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
# async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
#     """
#     Gère le cycle de vie de l'application FastAPI pour charger le modèle
#     au démarrage et libérer les ressources à l'extinction.
#     """
#     try:
#         # URI pointant vers la version spécifique enregistrée dans le registre
#         model_uri: str = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
#         ml_models["water_model"] = mlflow.sklearn.load_model(model_uri)
#         print(f"✅ Modèle '{MODEL_NAME}' version {MODEL_VERSION} chargé avec succès depuis MLflow.")
#     except Exception as e:
#         print(f"⚠️ Impossible de charger le modèle depuis MLflow Registry: {e}")
#         print("Mode dégradé : l'API fonctionne mais les prédictions renverront une erreur 503.")
#         ml_models["water_model"] = None
        
#     yield
#     ml_models.clear()
# Liste des suffixes de modèles que vous prévoyez d'utiliser
ALGOS = ["LogisticRegression", "RandomForestClassifier", "MLPClassifier"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge dynamiquement tous les modèles disponibles dans le registre au démarrage."""
    for algo in ALGOS:
        nom_registre = f"WaterModel_{algo}"
        try:
            # Tente de charger la version 1 de chaque modèle existant
            ml_models[algo] = mlflow.sklearn.load_model(f"models:/{nom_registre}/1")
            print(f"✅ {nom_registre} chargé avec succès.")
        except Exception:
            # Si le modèle n'est pas encore entraîné, on l'ignore proprement
            print(f"ℹ️ {nom_registre} non disponible dans le registre (pas encore entraîné).")
            ml_models[algo] = None
            
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


# endpoint de prédiction
@app.post("/predict", tags=["Prediction"])
def predict_potability(data: WaterFeatures) -> dict[str, Any]:
    """
    Récupère les paramètres d'un échantillon, applique le modèle de classification
    et retourne la prédiction binaire associée au statut textuel.
    """

    # 'data.model_choice' contiendra directement la chaîne "RandomForestClassifier" ou "LogisticRegression"
    model = ml_models.get(data.model_choice)
    
    if not model:
        raise HTTPException(
            status_code=503, 
            detail=f"Le modèle {data.model_choice} n'est pas actif ou disponible."
        )
    
    try:
        # Conversion stricte des données Pydantic en DataFrame Pandas
        # input_data: pd.DataFrame = pd.DataFrame([data.model_dump()])
        # Extrait les données en excluant le champ 'model_choice' qui ne sert pas au modèle
        raw_data = data.model_dump()
        choice = raw_data.pop("model_choice")
        
        input_data = pd.DataFrame([raw_data])
        
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