from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# URL de destination de l'API d'inférence (FastAPI)
FASTAPI_URL = "http://localhost:8000/predict"

@app.route("/api/v1/analyse", methods=["POST"])
def relayer_analyse():
    # 1. Flask reçoit les données envoyées par Streamlit
    donnees_front = request.json
    print(f"Middleware Flask : Payload reçu du Front -> {donnees_front}")
    
    try:
        # 2. Flask joue son rôle de relais et transfère le payload à FastAPI
        reponse_fastapi = requests.post(FASTAPI_URL, json=donnees_front, timeout=5)
        
        # 3. On récupère la vraie prédiction renvoyée par FastAPI
        resultat = reponse_fastapi.json()
        print(f"Réponse reçue de FastAPI -> {resultat}")
        
        # 4. On la renvoie directement à Streamlit
        return jsonify(resultat), reponse_fastapi.status_code

    except requests.exceptions.ConnectionError:
        print("❌ Erreur : Impossible de joindre l'API FastAPI sur le port 8000")
        return jsonify({"error": "Le serveur d'inférence FastAPI est injoignable."}), 503

if __name__ == "__main__":
    # Flask tourne par défaut sur le port 5000, mais comme MLflow l'utilise déjà,
    # On écoute sur localhost, port 8080
    app.run(host="localhost", port=8080, debug=True)