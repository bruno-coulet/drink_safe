from src.middleware import create_app

app = create_app()

if __name__ == "__main__":
    print("⚡ Démarrage du Middleware Centralisé Flask sur le port 8080...")
    app.run(host="localhost", port=8080, debug=True)