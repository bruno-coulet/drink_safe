"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Blueprint d'Authentification
Description : Gère le login et le logout pour les trois rôles.
              - Client : clé API brute validée contre FastAPI (hash côté API).
              - Admins (analyste, exploitation) : mot de passe vérifié contre
                un hash bcrypt stocké dans les variables d'environnement
                (ADMIN_*_PASSWORD_HASH). Générer les hashes via :
                  uv run python scripts/hash_admin_passwords.py
-------------------------------------------------------------------------------
"""

import os
import requests
from werkzeug.security import check_password_hash
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)

API_BASE_URL: str = os.getenv("API_URL", "http://localhost:8000/api")
ADMIN_ANALYSTE_HASH: str = os.getenv("ADMIN_ANALYSTE_PASSWORD_HASH", "")
ADMIN_EXPLOITATION_HASH: str = os.getenv("ADMIN_EXPLOITATION_PASSWORD_HASH", "")
ADMIN_ANALYSTE_API_KEY: str = os.getenv("ADMIN_ANALYSTE_API_KEY", "")
ADMIN_EXPLOITATION_API_KEY: str = os.getenv("ADMIN_EXPLOITATION_API_KEY", "")


def _valider_cle_client(api_key: str) -> bool:
    """Vérifie qu'une clé API client est valide en interrogeant FastAPI."""
    try:
        resp = requests.get(
            f"{API_BASE_URL}/measurements",
            headers={"X-API-Key": api_key},
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _verifier_mot_de_passe(mdp_saisi: str, hash_env: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt stocké en variable d'environnement.

    Retourne False si le hash n'est pas configuré plutôt que de lever une exception,
    ce qui évite de bloquer le login sans message d'erreur cryptique.
    """
    if not hash_env:
        return False
    try:
        return check_password_hash(hash_env, mdp_saisi)
    except Exception:
        return False


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Affiche et traite le formulaire de connexion selon le rôle sélectionné."""
    if request.method == "POST":
        role = request.form.get("role", "client")
        credential = request.form.get("credential", "").strip()

        if not credential:
            flash("Identifiant ou mot de passe manquant.", "danger")
            return render_template("login.html")

        if role == "client":
            if _valider_cle_client(credential):
                session["role"] = "client"
                session["api_key"] = credential
                return redirect(url_for("client.dashboard"))
            flash("Clé API invalide ou révoquée.", "danger")

        elif role == "analyste":
            if _verifier_mot_de_passe(credential, ADMIN_ANALYSTE_HASH) and ADMIN_ANALYSTE_API_KEY:
                session["role"] = "analyste"
                session["api_key"] = ADMIN_ANALYSTE_API_KEY
                return redirect(url_for("analyste.dashboard"))
            flash("Mot de passe analyste incorrect.", "danger")

        elif role == "exploitation":
            if _verifier_mot_de_passe(credential, ADMIN_EXPLOITATION_HASH) and ADMIN_EXPLOITATION_API_KEY:
                session["role"] = "exploitation"
                session["api_key"] = ADMIN_EXPLOITATION_API_KEY
                return redirect(url_for("exploitation.dashboard"))
            flash("Mot de passe exploitation incorrect.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Invalide la session et redirige vers la page de connexion."""
    session.clear()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))
