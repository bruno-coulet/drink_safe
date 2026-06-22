"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Interface Utilisateur Graphique (Frontend)
Description : Application Streamlit connectée à l'API unique FastAPI. Gère 
              la configuration des métriques, les appels aux endpoints 
              sécurisés (Inférence, OCR) et l'injection de la clé API.
-------------------------------------------------------------------------------
"""

import os
from pathlib import Path
import base64
import requests
import pandas as pd
import streamlit as st

# 1. Configuration de la page IHM
st.set_page_config(
    page_title="Waterflow 2 - Portail Expert",
    page_icon="💧",
    layout="centered"
)

def get_base_64(file_path: Path) -> str:
    """Encode une image locale en Base64 pour l'injection CSS."""
    with open(file_path, "rb") as file_object:
        data = file_object.read()
    return base64.b64encode(data).decode()

# Injection du fond d'écran stylisé
try:
    img_path = Path(__file__).resolve().parent / "assets" / "eau.webp"
    img_base64 = get_base_64(img_path)
    css = f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(0, 0, 0, 0.35), rgba(0, 0, 0, 0.35)), url("data:image/webp;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .stApp .block-container {{
        background: rgba(0, 0, 0, 0.65);
        border-radius: 1.25rem;
        padding: 2rem;
        backdrop-filter: blur(4px);
    }}
    .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp span {{
        color: #ffffff !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
except Exception:
    pass

# URL unique de l'API FastAPI unifiée
API_BASE_URL: str = os.getenv("API_URL", "http://localhost:8000/api")

# 2. Barre latérale de Sécurité (Gestion de la clé API exigée par le RGPD)
st.sidebar.title("🔐 Authentification")
user_api_key = st.sidebar.text_input(
    "Clé API Client (X-API-Key)", 
    type="password", 
    help="Saisissez la clé wf_live_... fournie par l'administrateur pour débloquer les services."
)

st.title("💧 Évaluation de la Potabilité de l'Eau")
st.write("Portail d'analyse industrielle centralisé (Version 2.0 - API Unique).")
st.markdown("---")

# 3. Formulaire d'inférence en temps réel
st.subheader("1. Analyse par curseurs manuels")

st.caption("L'échantillon est soumis simultanément aux 4 modèles ; le verdict final est le consensus (vote majoritaire).")

col1, col2 = st.columns(2)
with col1:
    ph = st.slider("pH (Potentiel Hydrogène)", min_value=0.0, max_value=14.0, value=7.2, step=0.1)
    hardness = st.number_input("Dureté (mg/L)", min_value=0.0, value=200.0, step=1.0)
    solids = st.number_input("Solides totaux (ppm)", min_value=0.0, value=20000.0, step=100.0)
    chloramines = st.slider("Chloramines (ppm)", min_value=0.0, max_value=15.0, value=3.2, step=0.1)

with col2:
    sulfate = st.number_input("Sulfates (mg/L)", min_value=0.0, value=330.0, step=1.0)
    conductivity = st.number_input("Conductivité électrique (μS/cm)", min_value=0.0, value=420.0, step=1.0)
    organic_carbon = st.slider("Carbone Organique Total (ppm)", min_value=0.0, max_value=30.0, value=14.2, step=0.1)
    trihalomethanes = st.slider("Trihalométhanes (ppm)", min_value=0.0, max_value=130.0, value=66.3, step=0.1)

turbidity = st.slider("Turbidité de l'eau (NTU)", min_value=0.0, max_value=7.0, value=3.8, step=0.1)

if st.button("Lancer l'analyse de l'échantillon", type="primary"):
    if not user_api_key:
        st.warning("⚠️ L'accès à l'inférence requiert une clé API valide dans la barre latérale.")
    else:
        # Payload calqué sur le schéma WaterSample (sans model_choice : les 4 modèles sont sollicités)
        payload = {
            "ph": ph,
            "Hardness": hardness,
            "Solids": solids,
            "Chloramines": chloramines,
            "Sulfate": sulfate,
            "Conductivity": conductivity,
            "Organic_carbon": organic_carbon,
            "Trihalomethanes": trihalomethanes,
            "Turbidity": turbidity,
            "observations": "Soumission manuelle depuis le portail Streamlit"
        }
        headers = {"X-API-Key": user_api_key}

        with st.spinner("Transmission sécurisée et calcul par les 4 modèles..."):
            try:
                response = requests.post(f"{API_BASE_URL}/predict/all", json=payload, headers=headers, timeout=15)

                if response.status_code == 200:
                    result = response.json()
                    statut = result["status_consensus"]

                    if result.get("decision_reason"):
                        # Rejet sanitaire OMS : aucun modèle n'est consulté
                        st.error(f"### ❌ Diagnostic : L'eau est estimée **{statut}** (Impropre).")
                        st.info(f"ℹ️ {result['decision_reason']}")
                    else:
                        votes = f"{result['votes_potable']}/{result['votes_total']} modèles pour 'Potable'"
                        if result["prediction_consensus"] == 1:
                            st.success(f"### 🎉 Consensus : L'eau est estimée **{statut}** ({votes}).")
                        else:
                            st.error(f"### ❌ Consensus : L'eau est estimée **{statut}** ({votes}).")

                        # Tableau comparatif des 4 modèles
                        st.write("**Détail par modèle :**")
                        st.dataframe(
                            [
                                {
                                    "Modèle": d["model"],
                                    "Prédiction": d["status"],
                                    "Score potabilité": d["score_potabilite"],
                                    "Version": d["model_version"],
                                }
                                for d in result["details"]
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )
                elif response.status_code == 401:
                    st.error("🚫 Authentification refusée : Clé API invalide ou révoquée.")
                else:
                    st.error(f"❌ Erreur API (Code {response.status_code}) : {response.text}")
            except Exception as e:
                st.error(f"🔌 Erreur de connexion avec l'API unifiée : {e}")

# 4. Ingestion automatisée par Rapport Laboratoire (OCR)
st.markdown("---")
st.subheader("2. Ingestion automatisée par Rapport Laboratoire (OCR)")

fichier_importe = st.file_uploader(
    "Téléversez une fiche d'analyse officielle (PDF, PNG, JPG)", 
    type=["pdf", "png", "jpg", "jpeg"]
)

if fichier_importe is not None:
    if st.button("Lancer l'extraction OCR", type="secondary"):
        if not user_api_key:
            st.warning("⚠️ Une clé API est obligatoire pour enregistrer les données extraites par OCR.")
        else:
            files_payload = {
                'file': (fichier_importe.name, fichier_importe.getvalue(), fichier_importe.type)
            }
            headers = {"X-API-Key": user_api_key}
            
            with st.spinner("Numérisation et extraction par l'API OCR.space..."):
                try:
                    response_ocr = requests.post(
                        f"{API_BASE_URL}/ocr/lab-report", 
                        files=files_payload, 
                        headers=headers, 
                        timeout=25
                    )
                    
                    if response_ocr.status_code == 201:
                        data_json = response_ocr.json()
                        prelevement_id = data_json["prelevement_id"]
                        st.success(f"🎉 Fiche numérisée et enregistrée ! ID Prélèvement : {prelevement_id}")
                        st.write("**Métriques extraites de la fiche labo :**")
                        st.json(data_json["extracted_data"])

                        # Enchaînement : prédiction des 4 modèles sur le prélèvement créé (enrichit la même ligne)
                        with st.spinner("Analyse de potabilité par les 4 modèles..."):
                            response_pred = requests.post(
                                f"{API_BASE_URL}/predict/from-prelevement/{prelevement_id}",
                                headers=headers,
                                timeout=15,
                            )

                        if response_pred.status_code == 200:
                            res = response_pred.json()
                            statut = res["status_consensus"]
                            if res.get("decision_reason"):
                                st.error(f"### ❌ Diagnostic : eau estimée **{statut}** (Impropre).")
                                st.info(f"ℹ️ {res['decision_reason']}")
                            else:
                                votes = f"{res['votes_potable']}/{res['votes_total']} modèles pour 'Potable'"
                                if res["prediction_consensus"] == 1:
                                    st.success(f"### 🎉 Consensus : eau estimée **{statut}** ({votes}).")
                                else:
                                    st.error(f"### ❌ Consensus : eau estimée **{statut}** ({votes}).")
                                st.write("**Détail par modèle :**")
                                st.dataframe(
                                    [
                                        {
                                            "Modèle": d["model"],
                                            "Prédiction": d["status"],
                                            "Score potabilité": d["score_potabilite"],
                                            "Version": d["model_version"],
                                        }
                                        for d in res["details"]
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                        else:
                            st.warning(
                                f"⚠️ Extraction réussie, mais prédiction indisponible "
                                f"(Code {response_pred.status_code}) : {response_pred.text}"
                            )
                    elif response_ocr.status_code == 401:
                        st.error("🚫 Droits insuffisants : Clé API invalide.")
                    else:
                        st.error(f"❌ Échec de l'extraction (Code {response_ocr.status_code}) : {response_ocr.text}")
                except Exception as e:
                    st.error(f"🔌 Erreur réseau : Impossible de joindre le module OCR : {e}")


# 5. Consultation des prélèvements (vue Analyste Qualité)
st.markdown("---")
st.subheader("3. Consultation des prélèvements (Analyste Qualité)")
st.caption("Vue globale (GET /measurements/admin) avec filtres par client, provenance, date et résultat.")


def _label_resultat(valeur) -> str:
    """Convertit prediction_potability (0/1/None) en libellé lisible."""
    if pd.isna(valeur):
        return "Non analysé"
    return "Potable" if int(valeur) == 1 else "Non Potable"


if not user_api_key:
    st.info("Saisissez une clé API dans la barre latérale pour consulter les prélèvements.")
else:
    if st.button("Charger tous les prélèvements", type="secondary"):
        headers = {"X-API-Key": user_api_key}
        with st.spinner("Récupération de la vue globale..."):
            try:
                resp = requests.get(f"{API_BASE_URL}/measurements/admin", headers=headers, timeout=15)
                if resp.status_code == 200:
                    st.session_state["prelevements"] = resp.json()
                elif resp.status_code == 401:
                    st.error("🚫 Authentification refusée : Clé API invalide ou révoquée.")
                else:
                    st.error(f"❌ Erreur API (Code {resp.status_code}) : {resp.text}")
            except Exception as e:
                st.error(f"🔌 Erreur de connexion avec l'API unifiée : {e}")

    donnees = st.session_state.get("prelevements")
    if donnees is not None:
        df = pd.DataFrame(donnees)
        if df.empty:
            st.info("Aucun prélèvement enregistré pour le moment.")
        else:
            # Colonnes dérivées (résultat lisible + date exploitable pour le filtre)
            df["resultat"] = df["prediction_potability"].apply(_label_resultat)
            if "cree_le" in df.columns:
                df["cree_le"] = pd.to_datetime(df["cree_le"], errors="coerce")

            # --- Filtres multicritères ---
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                clients = ["(tous)"] + sorted(df["client_id"].dropna().unique().tolist())
                f_client = st.selectbox("Client", clients)
            with col_f2:
                provenances = ["(toutes)"] + sorted(df["provenance"].dropna().unique().tolist())
                f_prov = st.selectbox("Provenance", provenances)
            with col_f3:
                f_result = st.selectbox("Résultat modèle", ["(tous)", "Potable", "Non Potable", "Non analysé"])

            df_f = df.copy()
            if f_client != "(tous)":
                df_f = df_f[df_f["client_id"] == f_client]
            if f_prov != "(toutes)":
                df_f = df_f[df_f["provenance"] == f_prov]
            if f_result != "(tous)":
                df_f = df_f[df_f["resultat"] == f_result]

            # Filtre par plage de dates (si la colonne est exploitable)
            if "cree_le" in df_f.columns and df_f["cree_le"].notna().any():
                dmin = df_f["cree_le"].min().date()
                dmax = df_f["cree_le"].max().date()
                plage = st.date_input("Période (date de prélèvement)", value=(dmin, dmax))
                if isinstance(plage, (list, tuple)) and len(plage) == 2:
                    debut, fin = plage
                    df_f = df_f[(df_f["cree_le"].dt.date >= debut) & (df_f["cree_le"].dt.date <= fin)]

            # --- Indicateurs clés ---
            c1, c2, c3 = st.columns(3)
            c1.metric("Prélèvements", len(df_f))
            c2.metric("Potables", int((df_f["resultat"] == "Potable").sum()))
            c3.metric("Non potables", int((df_f["resultat"] == "Non Potable").sum()))

            st.dataframe(df_f, use_container_width=True, hide_index=True)