import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import mlflow
import mlflow.sklearn

# 1. Configuration de la connexion à MLflow Dockerisé
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

MODEL_NAME = "WaterPotabilityBaseline"
MODEL_STAGE = "Latest"
# On crée un dictionnaire d'état pour stocker le modèle de manière propre et accessible partout
ml_models = {}

# 2. Gestion du cycle de vie de l'application (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tout ce qui est écrit ici s'exécute AU DÉMARRAGE
    try:
        model_uri = f"models://{MODEL_NAME}/{MODEL_STAGE}"
        ml_models["water_model"] = mlflow.sklearn.load_model(model_uri)
        print(f"✅ Modèle '{MODEL_NAME}' chargé avec succès depuis MLflow.")
    except Exception as e:
        print(f"⚠️ Impossible de charger le modèle depuis MLflow Registry: {e}")
        print("Mode dégradé : l'API fonctionne mais les prédictions renverront une erreur 503.")
        ml_models["water_model"] = None
        
    yield
    # Tout ce qui est écrit après le yield s'exécute À L'EXTINCTION (nettoyage si besoin)
    ml_models.clear()

# On passe le lifespan à l'application
app = FastAPI(
    title="Water Potability Prediction API",
    description="API FastAPI pour prédire la potabilité de l'eau à partir de ses caractéristiques physico-chimiques.",
    version="1.0.0",
    lifespan=lifespan
)

# 3. Définition du schéma des données d'entrée (Features du Dataset)
class WaterFeatures(BaseModel):
    ph: float = Field(..., description="Potentiel Hydrogène (0 à 14)", example=7.2)
    Hardness: float = Field(..., description="Dureté de l'eau en mg/L", example=200.5)
    Solids: float = Field(..., description="Total des solides dissous en ppm", example=20000.0)
    Chloramines: float = Field(..., description="Concentration en chloramines en ppm", example=7.3)
    Sulfate: float = Field(..., description="Concentration en sulfates en mg/L", example=330.0)
    Conductivity: float = Field(..., description="Conductivité électrique en μS/cm", example=420.0)
    Organic_carbon: float = Field(..., description="Carbone organique total en ppm", example=14.2)
    Trihalomethanes: float = Field(..., description="Concentration en trihalométhanes en μg/L", example=66.3)
    Turbidity: float = Field(..., description="Turbidité de l'eau en NTU", example=4.0)

# 4. Endpoint de vérification de l'état (Health Check)
@app.get("/health", tags=["Utility"])
def health_check():
    if ml_models.get("water_model") is None:
        return {"status": "amber", "message": "API active mais modèle non chargé."}
    return {"status": "green", "message": "API et modèle opérationnels."}

# 5. Endpoint de prédiction
@app.post("/predict", tags=["Prediction"])
def predict_potability(data: WaterFeatures):
    model = ml_models.get("water_model")
    if model is None:
        raise HTTPException(
            status_code=503, 
            detail="Le modèle de prédiction n'est pas disponible sur le serveur."
        )
    
    try:
        # Convertir les données pydantic en DataFrame Pandas
        input_data = pd.DataFrame([data.model_dump()])
        
        # Exécuter la prédiction (0 ou 1)
        prediction = model.predict(input_data)
        potability_result = int(prediction[0])
        
        status_label = "Potable" if potability_result == 1 else "Non Potable"
        
        return {
            "prediction": potability_result,
            "status": status_label
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction : {str(e)}")