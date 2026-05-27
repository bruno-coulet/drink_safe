"""
-------------------------------------------------------------------------------
Projet : Waterflow (Potabilité de l'eau)
Composant : API Backend de Prédiction
Description : Serveur FastAPI chargeant les modèles de classification depuis 
              le Model Registry de MLflow pour effectuer des prédictions.
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
from mlflow.tracking import MlflowClient

# Configuration de la connexion à MLflow Dockerisé
MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Le dictionnaire global qui stocke les instances de modèles chargées
ml_models: dict[str, Any] = {}

# # Liste des classes d'algorithmes supportées (évolutive)
# ALGOS = ["LogisticRegression", "RandomForestClassifier", "MLPClassifier"]


class WaterFeatures(BaseModel):
    """
    Modèle de données Pydantic définissant la structure stricte
    des paramètres physico-chimiques d'un échantillon d'eau.
    """    
    # Accepte n'importe quelle chaîne envoyée par le front
    model_choice: str = Field(..., description="Nom de la classe du modèle à interroger (ex: LogisticRegression)")
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
    Scanne dynamiquement le Model Registry de MLflow pour charger 
    les modèles enregistrés sous la nomenclature 'WaterModel_'
    """
    try:
        client = MlflowClient()
        # On récupère tous les modèles enregistrés sur ton serveur MLflow
        registered_models = client.search_registered_models()
        
        for rm in registered_models:
            nom_modele = rm.name  # ex: "WaterModel_LogisticRegression"
            
            if nom_modele.startswith("WaterModel_"):
                # On extrait le nom de l'algo (ex: "LogisticRegression")
                algo_key = nom_modele.replace("WaterModel_", "")
                
                try:
                    # On charge automatiquement la version 1
                    ml_models[algo_key] = mlflow.sklearn.load_model(f"models:/{nom_modele}/1")
                    print(f"Modèle détecté et chargé dynamiquement : {nom_modele}")
                except Exception as e:
                    print(f"⚠️ Erreur lors du chargement de {nom_modele}: {e}")
                    
    except Exception as e:
        print(f"Impossible de scanner le Model Registry MLflow: {e}")
        print("Mode dégradé enclenché.")
        
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
    """Vérifie l'état de disponibilité globale de l'API backend."""
    modeles_charges = [k for k, v in ml_models.items() if v is not None]
    if not modeles_charges:
        return {"status": "amber", "message": "API active mais aucun modèle n'est chargé."}
    return {"status": "green", "message": f"API opérationnelle. Modèles actifs : {modeles_charges}"}


@app.post("/predict", tags=["Prediction"])
def predict_potability(data: WaterFeatures) -> dict[str, Any]:
    """
    Aiguille la requête vers le modèle choisi et renvoie la prédiction.
    Applique un garde-fou physico-chimique strict avant de solliciter le modèle ML.
    """
    # ---- COUCHE GARDE-FOU METIER (Business Rules) ----
    # 1. Sécurité pH (Selon normes OMS)
    if data.ph < 6.5 or data.ph > 8.5:  # Seuils officiels stricts du document
        return {
            "prediction": 0,
            "status": "Non Potable",
            "decision_reason": "Garde-fou : pH hors des limites permissibles de l'OMS (6.5 - 8.5)."
        }
    
    # 2. Sécurité Turbidité (Seuil critique OMS)
    if data.Turbidity > 5.0:
        return {
            "prediction": 0,
            "status": "Non Potable",
            "decision_reason": "Garde-fou : Turbidité supérieure à la recommandation maximale de l'OMS (5.0 NTU)."
        }

    # 3. Sécurité Chloramines (Toxicité chimique)
    if data.Chloramines > 4.0:
        return {
            "prediction": 0,
            "status": "Non Potable",
            "decision_reason": "Garde-fou : Concentration en chloramines supérieure au seuil de sécurité (4.0 mg/L)."
        }

    # 4. Sécurité Trihalométhanes (Toxicité chimique sous-produits)
    if data.Trihalomethanes > 80.0:
        return {
            "prediction": 0,
            "status": "Non Potable",
            "decision_reason": "Garde-fou : Taux de trihalométhanes supérieur au seuil de sécurité (80.0 ppm)."
        }
    # --------------------------------------------------


    model = ml_models.get(data.model_choice)
    
    if not model:
        raise HTTPException(
            status_code=503, 
            detail=f"Le modèle {data.model_choice} n'est pas actif ou disponible sur le serveur."
        )
    
    try:
        # Extraction du payload et exclusion du paramètre technique de choix
        raw_data = data.model_dump()
        choice = raw_data.pop("model_choice")
        
        input_data = pd.DataFrame([raw_data])
        
        # Inférence Scikit-Learn
        prediction = model.predict(input_data)
        potability_result: int = int(prediction[0])
        status_label: str = "Potable" if potability_result == 1 else "Non Potable"
        
        return {
            "prediction": potability_result,
            "status": status_label,
            "model_used": choice
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de l'exécution de la prédiction: {str(e)}"
        )
    

@app.post("/auth", tags=["Utility"])
def auth_user()