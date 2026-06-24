"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Blueprint Analyste Qualité
Description : Interface de supervision métier — consultation globale des
              prélèvements avec filtres multicritères, indicateurs clés,
              et suivi des versions de modèle via MLflow.
              Accès restreint au rôle "analyste".
-------------------------------------------------------------------------------
"""

import os
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
import requests
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

analyste_bp = Blueprint("analyste", __name__, template_folder="templates")

API_BASE_URL: str = os.getenv("API_URL", "http://localhost:8000/api")


def role_requis(role: str) -> Callable:
    """Décorateur qui restreint l'accès à un rôle de session spécifique."""
    def decorateur(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            if session.get("role") != role:
                flash("Accès réservé aux Analystes Qualité.", "danger")
                return redirect(url_for("auth.login"))
            return f(*args, **kwargs)
        return wrapper
    return decorateur


def _filtrer(
    donnees: List[Dict],
    client_id: str,
    provenance: str,
    resultat: str,
    date_debut: str,
    date_fin: str,
) -> List[Dict]:
    """Applique les filtres multicritères sur la liste des prélèvements."""
    filtrees = donnees

    if client_id and client_id != "tous":
        filtrees = [d for d in filtrees if d.get("client_id") == client_id]

    if provenance and provenance != "toutes":
        filtrees = [d for d in filtrees if d.get("provenance") == provenance]

    if resultat and resultat != "tous":
        if resultat == "Potable":
            filtrees = [d for d in filtrees if d.get("prediction_potability") == 1]
        elif resultat == "Non Potable":
            filtrees = [d for d in filtrees if d.get("prediction_potability") == 0]
        elif resultat == "Non analysé":
            filtrees = [d for d in filtrees if d.get("prediction_potability") is None]

    if date_debut:
        filtrees = [d for d in filtrees if d.get("cree_le", "") >= date_debut]
    if date_fin:
        filtrees = [d for d in filtrees if d.get("cree_le", "") <= date_fin + "T23:59:59"]

    return filtrees


@analyste_bp.route("/")
@role_requis("analyste")
def dashboard():
    """Charge tous les prélèvements et applique les filtres de la requête."""
    headers = {"X-API-Key": session["api_key"]}
    donnees: List[Dict] = []
    erreur: Optional[str] = None

    try:
        resp = requests.get(
            f"{API_BASE_URL}/measurements/admin", headers=headers, timeout=15
        )
        if resp.status_code == 200:
            donnees = resp.json()
        else:
            erreur = f"Erreur API ({resp.status_code}) : {resp.text}"
    except requests.RequestException as e:
        erreur = f"Impossible de joindre l'API : {e}"

    # Extraction des valeurs distinctes pour les menus de filtres
    clients_ids = sorted({d.get("client_id", "") for d in donnees if d.get("client_id")})
    provenances = sorted({d.get("provenance", "") for d in donnees if d.get("provenance")})

    # Récupération des filtres depuis la requête GET
    f_client = request.args.get("client_id", "tous")
    f_prov = request.args.get("provenance", "toutes")
    f_result = request.args.get("resultat", "tous")
    f_debut = request.args.get("date_debut", "")
    f_fin = request.args.get("date_fin", "")

    donnees_filtrees = _filtrer(donnees, f_client, f_prov, f_result, f_debut, f_fin)

    # Indicateurs clés calculés côté serveur
    total = len(donnees_filtrees)
    potables = sum(1 for d in donnees_filtrees if d.get("prediction_potability") == 1)
    non_potables = sum(1 for d in donnees_filtrees if d.get("prediction_potability") == 0)

    return render_template(
        "analyste/dashboard.html",
        donnees=donnees_filtrees,
        total=total,
        potables=potables,
        non_potables=non_potables,
        clients_ids=clients_ids,
        provenances=provenances,
        filtres={"client_id": f_client, "provenance": f_prov, "resultat": f_result,
                 "date_debut": f_debut, "date_fin": f_fin},
        erreur=erreur,
    )
