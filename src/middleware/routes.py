'''
aiguillage
écris les fonctions @app.route("/api/v1/analyse", methods=["POST"])
intercepte les requêtes de Streamlit
vérifie la clé API FastAPI.
'''

import requests
from flask import Blueprint, request, jsonify
from src.middleware.config import Config 

# Crée le Blueprint (nom, package) avec préfixe automatique obligatoire pour l'API
middleware_bp = Blueprint("middleware", __name__, url_prefix="/api/v1")

@middleware_bp.route("/analyse", methods=["POST"])
def relayer_analyse():
    """
    Route d'aiguillage principale : intercepte les requêtes de Streamlit,
    et joue son rôle de relais vers le serveur d'inférence FastAPI.
    """
    donnees_front = request.json
    print(f"📩 [Middleware Flask] Payload reçu du Front -> {donnees_front}")
    
    try:
        # Relais vers FastAPI en utilisant la constante de Config
        reponse_fastapi = requests.post(Config.FASTAPI_URL, json=donnees_front, timeout=5)
        resultat = reponse_fastapi.json()
        print(f"🚀 [FastAPI] Réponse reçue -> {resultat}")
        
        return jsonify(resultat), reponse_fastapi.status_code

    except requests.exceptions.ConnectionError:
        print("❌ Erreur : Impossible de joindre l'API FastAPI sur le port 8000")
        return jsonify({"error": "Le serveur d'inférence FastAPI est injoignable."}), 503