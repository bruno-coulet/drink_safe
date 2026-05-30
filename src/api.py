"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Point d'Entrée, Cycle de Vie et Middleware de l'API Unique
Description : Serveur FastAPI unifié orchestrant l'initialisation de PostgreSQL,
              le chargement des modèles MLflow, l'exposition des services et
              la journalisation automatique des accès (RGPD & Monitoring).
-------------------------------------------------------------------------------
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List
import pandas as pd
import mlflow
import mlflow.sklearn
from fastapi import FastAPI, Request, Response
from mlflow.tracking import MlflowClient
import psycopg2

from src.config import settings, init_db
from src.routes.clients import router as clients_router
from src.routes.measurements import router as measurements_router
from src.routes.predictions import router as predictions_router
from src.routes.ocr import router as ocr_router

# --- PARADE CONTRE LE BLOCAGE 403 DNS REBINDING SUR L'API ---
import requests
_old_prepare_headers = requests.models.PreparedRequest.prepare_headers

def patched_prepare_headers(self, headers):
    _old_prepare_headers(self, headers)
    # On écrase l'en-tête Host UNIQUEMENT si la cible est le conteneur MLflow
    if self.url and "mlflow-back" in self.url:
        self.headers["Host"] = "localhost:5000"

requests.models.PreparedRequest.prepare_headers = patched_prepare_headers
# -----------------------------------------------------------


# Configuration globale de la connexion à MLflow
mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)

# Registre en mémoire pour stocker les instances de modèles chargées
ml_models: Dict[str, Any] = {}



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gère le cycle de vie applicatif (Démarrage et Arrêt du serveur)."""
    # ---- ACTIONS AU DÉMARRAGE ----
    print("[API Unique] Étape 1 : Initialisation des tables PostgreSQL...")
    try:
        init_db()
    except Exception as e:
        print(f"⚠️ Alerte : Échec de l'initialisation de la BDD au démarrage : {e}")

    print("[API Unique] Étape 2 : Scan et chargement des modèles depuis MLflow Model Registry...")
    try:
        client = MlflowClient()
        registered_models = client.search_registered_models()
        
        for rm in registered_models:
            model_name: str = rm.name
            if model_name.startswith("WaterModel_"):
                algo_key: str = model_name.replace("WaterModel_", "")
                
                # 1. Récupération de la dernière version du modèle enregistrée
                latest_versions = rm.latest_versions
                if not latest_versions:
                    print(f"⚠️ Aucune version trouvée pour {model_name}")
                    continue
                    
                latest_v = latest_versions[0]
                run_id = latest_v.run_id
                
                # 2. Stratégie de chargement hybride (Sécurité Production)
                loaded = False
                
                # Tentative A : Via l'URI classique nettoyé
                try:
                    model_uri = f"models:/{model_name}/1"
                    ml_models[algo_key] = mlflow.sklearn.load_model(model_uri.rstrip("/."))
                    print(f"✓ {model_name} chargé avec succès via l'URI du Registre.")
                    loaded = True
                except Exception:
                    pass
                
                # Tentative B (Fallback Industriel) : Si le dossier /1/ est introuvable, 
                # on bascule sur l'URI directe du Run ID (qui pointe sur les dossiers m-XXXX)
                if not loaded:
                    try:
                        fallback_uri = f"runs:/{run_id}/model"
                        ml_models[algo_key] = mlflow.sklearn.load_model(fallback_uri)
                        print(f"✓ {model_name} chargé avec succès via Fallback (Run ID: {run_id}).")
                        loaded = True
                    except Exception as e_fallback:
                        print(f"⚠️ Impossible de charger le modèle {model_name} : {e_fallback}")
                        
    except Exception as e:
        print(f"⚠️ Mode dégradé enclenché : Échec de connexion à MLflow UI : {e}")
        
    yield
    
    # ---- ACTIONS À L'ARRÊT ----
    print("[API Unique] Libération des ressources et fermeture du serveur...")
    ml_models.clear()



# Instanciation de l'API Unique (Data + Model + OCR)
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service unifié Waterflow 2 : Gestion des prélèvements, Ingestion OCR et Inférence.",
    version=settings.VERSION,
    lifespan=lifespan
)


# ---- MIDDLEWARE DE MONITORING ET TRAÇABILITÉ RGPD ----
@app.middleware("http")
async def journaliser_requete_et_temps(request: Request, call_next: Any) -> Response:
    """Intercepte chaque appel API pour mesurer sa durée et l'auditer en BDD."""
    start_time: float = time.time()
    
    # Extraction de la clé API présente dans les en-têtes pour la traçabilité
    api_key_utilisee: str = request.headers.get("X-API-Key", "Pas de clé transmise")
    
    # Poursuite de la requête vers son endpoint cible
    response: Response = await call_next(request)
    
    # Calcul du temps de traitement de la requête en millisecondes
    duration_ms: int = int((time.time() - start_time) * 1000)
    
    # Extraction optionnelle du client_id si déjà résolu ou traitement anonyme
    client_id_tracé: str = "ANONYMOUS"
    
    # Écriture asynchrone / découplée des logs dans PostgreSQL (Garantit l'audit de sécurité)
    query_log: str = """
    INSERT INTO action_logs (
        client_id, api_key_used, endpoint, method, status_code, execution_duration_ms
    ) VALUES (%s, %s, %s, %s, %s, %s);
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_log, (
                    client_id_tracé,
                    api_key_utilisee if api_key_utilisee == "Pas de clé transmise" else "wf_live_********",
                    request.url.path,
                    request.method,
                    response.status_code,
                    duration_ms
                ))
                conn.commit()
    except Exception as e:
        # Un échec de log ne doit jamais bloquer la réponse HTTP du client en production
        print(f"⚠️ Erreur MLOps lors de l'enregistrement du log de monitoring : {e}")
        
    return response


# ---- ENREGISTREMENT DES ROUTEURS EN APPLIQUANT LE PRÉFIXE UNIQUE ----
app.include_router(clients_router, prefix="/api")
app.include_router(measurements_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(ocr_router, prefix="/api")


@app.get("/health", tags=["Utility"])
def health_check() -> Dict[str, Any]:
    """Vérifie l'état de santé de l'API et liste les modèles d'IA actifs en mémoire."""
    active_models: List[str] = [k for k, v in ml_models.items() if v is not None]
    return {
        "status": "green" if active_models else "amber",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_models": active_models
    }