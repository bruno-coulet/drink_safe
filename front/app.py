"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Interface Web Expert (Frontend Flask)
Description : Application Flask multi-rôles exposant trois espaces distincts :
              Client (prélèvements + OCR), Analyste (supervision métier),
              Responsable d'Exploitation (monitoring infrastructure).
              L'authentification repose sur la clé API pour les clients et
              sur des mots de passe d'environnement pour les rôles admin.
-------------------------------------------------------------------------------
"""

import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

load_dotenv()


def create_app() -> Flask:
    """Crée et configure l'application Flask (pattern Application Factory)."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    from auth import auth_bp
    from client import client_bp
    from analyste import analyste_bp
    from exploitation import exploitation_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp, url_prefix="/client")
    app.register_blueprint(analyste_bp, url_prefix="/analyste")
    app.register_blueprint(exploitation_bp, url_prefix="/exploitation")

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("FLASK_PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
