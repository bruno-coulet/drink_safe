"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Blueprint Client Final
Description : Interface du client final — soumettre un prélèvement par
              curseurs manuels ou par extraction OCR (fiche laboratoire).
              Toutes les routes exigent que la session contienne role="client".
-------------------------------------------------------------------------------
"""

import os
import requests
from functools import wraps
from typing import Any, Callable, Dict, Optional
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

client_bp = Blueprint("client", __name__, template_folder="templates")

API_BASE_URL: str = os.getenv("API_URL", "http://localhost:8000/api")


def role_requis(role: str) -> Callable:
    """Décorateur qui restreint l'accès à un rôle de session spécifique."""
    def decorateur(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            if session.get("role") != role:
                flash("Accès non autorisé. Connectez-vous avec le bon profil.", "danger")
                return redirect(url_for("auth.login"))
            return f(*args, **kwargs)
        return wrapper
    return decorateur


@client_bp.route("/")
@role_requis("client")
def dashboard():
    """Page principale du client : formulaire de prédiction et upload OCR."""
    # 1. Vérification que le client est bien connecté
    if "api_key" not in session or session.get("role") != "client":
        return redirect(url_for("auth.login"))

    # 2. Récupération des informations depuis la session Flask
    donnees_client = {
        "client_id": session.get("client_id", "ID inconnu"),
        "nom_structure": session.get("nom_structure", "Client")
    }

    # 3. Transmission de l'objet 'client' au fichier HTML
    return render_template(
        "client/dashboard.html",
        client=donnees_client
    )


@client_bp.route("/predict", methods=["POST"])
@role_requis("client")
def predict():
    """Soumet un prélèvement manuel aux 4 modèles et affiche le consensus."""
    payload: Dict[str, Any] = {
        "ph": float(request.form.get("ph", 7.0)),
        "Hardness": float(request.form.get("hardness", 200.0)),
        "Solids": float(request.form.get("solids", 20000.0)),
        "Chloramines": float(request.form.get("chloramines", 3.2)),
        "Sulfate": float(request.form.get("sulfate", 330.0)),
        "Conductivity": float(request.form.get("conductivity", 420.0)),
        "Organic_carbon": float(request.form.get("organic_carbon", 14.2)),
        "Trihalomethanes": float(request.form.get("trihalomethanes", 66.3)),
        "Turbidity": float(request.form.get("turbidity", 3.8)),
        "observations": "Soumission manuelle depuis le portail Flask",
    }
    headers = {"X-API-Key": session["api_key"]}
    resultat: Optional[Dict] = None
    erreur: Optional[str] = None

    try:
        resp = requests.post(
            f"{API_BASE_URL}/predict/all", json=payload, headers=headers, timeout=15
        )
        if resp.status_code == 200:
            resultat = resp.json()
        else:
            erreur = f"Erreur API ({resp.status_code}) : {resp.text}"
    except requests.RequestException as e:
        erreur = f"Impossible de joindre l'API : {e}"

    return render_template(
        "client/dashboard.html",
        resultat=resultat,
        erreur=erreur,
        form_values=request.form,
    )


@client_bp.route("/ocr", methods=["POST"])
@role_requis("client")
def ocr():
    """Transmet une fiche laboratoire à l'API OCR et affiche les données extraites."""
    fichier = request.files.get("fichier")
    if not fichier or fichier.filename == "":
        flash("Aucun fichier sélectionné.", "warning")
        return redirect(url_for("client.dashboard"))

    headers = {"X-API-Key": session["api_key"]}
    resultat_ocr: Optional[Dict] = None
    resultat_pred: Optional[Dict] = None
    erreur: Optional[str] = None

    try:
        resp_ocr = requests.post(
            f"{API_BASE_URL}/ocr/lab-report",
            files={"file": (fichier.filename, fichier.read(), fichier.content_type)},
            headers=headers,
            timeout=30,
        )
        if resp_ocr.status_code == 201:
            resultat_ocr = resp_ocr.json()
            prelevement_id = resultat_ocr.get("prelevement_id")
            resp_pred = requests.post(
                f"{API_BASE_URL}/predict/from-prelevement/{prelevement_id}",
                headers=headers,
                timeout=15,
            )
            if resp_pred.status_code == 200:
                resultat_pred = resp_pred.json()
        else:
            erreur = f"Échec OCR ({resp_ocr.status_code}) : {resp_ocr.text}"
    except requests.RequestException as e:
        erreur = f"Erreur réseau : {e}"

    return render_template(
        "client/dashboard.html",
        resultat_ocr=resultat_ocr,
        resultat_pred=resultat_pred,
        erreur=erreur,
    )
