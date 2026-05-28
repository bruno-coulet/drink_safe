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
    print(f"[Middleware Flask] Payload reçu du Front -> {donnees_front}")
    
    try:
        # Relais vers FastAPI en utilisant la constante de Config
        reponse_fastapi = requests.post(Config.FASTAPI_URL, json=donnees_front, timeout=5)
        resultat = reponse_fastapi.json()
        print(f"[FastAPI] Réponse reçue -> {resultat}")
        
        return jsonify(resultat), reponse_fastapi.status_code

    except requests.exceptions.ConnectionError:
        print("❌ Erreur : Impossible de joindre l'API FastAPI sur le port 8000")
        return jsonify({"error": "Le serveur d'inférence FastAPI est injoignable."}), 503
    


@middleware_bp.route("/upload-ocr", methods=["POST"])
def extraire_et_creer_prelevement():
    """
    [Route d'ingestion OCR : reçoit une fiche laboratoire (PDF/Image),
    simule l'extraction des données et valide la réception.
    """
    # 1. Vérification de la présence du fichier dans la requête HTTP Multi-part
    if 'file' not in request.files:
        print("[Middleware Flask] Aucun fichier trouvé dans la requête")
        return jsonify({"error": "Aucun fichier n'a été fourni dans le payload."}), 400
        
    fichier = request.files['file']
        
    if fichier.filename == '':
        return jsonify({"error": "Nom de fichier invalide ou vide."}), 400

    print(f"[Middleware Flask] Fichier reçu avec succès : {fichier.filename} ({fichier.content_type})")

    # 2. Simulation de la réponse OCR (En attente de ocr_engine.py)
    # On renvoie un dictionnaire simulant les 4 entités attendues par l'énoncé
    donnees_simulees_ocr = {
        "status": "Succès",
        "message": "Fichier intercepté par Flask. Moteur OCR en cours de configuration.",
        "extracted_data": {
            "date": "18/03/2025 09:30",  # Donnée issue de la fiche exemple AquaTest
            "client_id": "CLIENT-042",
            "provenance": "OCR",
            "mesures": {
                "ph": 7.6,
                "Hardness": 25.3,
                "Solids": 20000.0,
                "Chloramines": 3.1,
                "Sulfate": 210.0,
                "Conductivity": 650.0,
                "Organic_carbon": 12.0,
                "Trihalomethanes": 60.0,
                "Turbidity": 0.7
            },
            "observations": "Type de prélèvement : Puits privé"
        }
    }

    # Pour l'instant, retourne le JSON de simulation au Front
    return jsonify(donnees_simulees_ocr), 200