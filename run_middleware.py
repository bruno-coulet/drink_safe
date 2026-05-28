from middleware import create_app

# On cible directement le fichier __init__.py du package
# from src.middleware.__init__ import create_app

app = create_app()

if __name__ == "__main__":
    print("Démarrage du Middleware Centralisé Flask sur le port 8080...")
    app.run(host="localhost", port=8080, debug=True)