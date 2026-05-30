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

model_display = st.selectbox(
    "Sélectionnez l'algorithme d'inférence :",
    [
        "Régression Logistique (Données Standardisées)", 
        "Random Forest (Données Brutes)",
        "XGBoost Classifier (Données Brutes)",
        "Perceptron Multicouches - MLP (Données Standardisées)"
    ]
)

model_mapping = {
    "Régression Logistique (Données Standardisées)": "LogisticRegression",
    "Random Forest (Données Brutes)": "RandomForestClassifier",
    "XGBoost Classifier (Données Brutes)": "XGBClassifier",
    "Perceptron Multicouches - MLP (Données Standardisées)": "MLPClassifier"
}
selected_model_key = model_mapping[model_display]

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
    trihalomethanes = st.slider("Trihalométhanes (μg/L)", min_value=0.0, max_value=130.0, value=66.3, step=0.1)

turbidity = st.slider("Turbidité de l'eau (NTU)", min_value=0.0, max_value=7.0, value=3.8, step=0.1)

if st.button("Lancer l'analyse de l'échantillon", type="primary"):
    if not user_api_key:
        st.warning("⚠️ L'accès à l'inférence requiert une clé API valide dans la barre latérale.")
    else:
        # Payload calqué sur le schéma strict de PredictionRequest
        payload = {
            "model_choice": selected_model_key,
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
        
        with st.spinner("Transmission sécurisée et calcul par l'API..."):
            try:
                response = requests.post(f"{API_BASE_URL}/predict/", json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    prediction = result["prediction"]
                    status_label = result["status"]
                    
                    if prediction == 1:
                        st.success(f"### 🎉 Diagnostic : L'eau est estimée **{status_label}** !")
                    else:
                        st.error(f"### ❌ Diagnostic : L'eau est estimée **{status_label}** (Impropre).")
                        if "decision_reason" in result:
                            st.info(f"ℹ️ {result['decision_reason']}")
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
                        st.success(f"🎉 Analyse terminée ! ID Prélèvement généré : {data_json['prelevement_id']}")
                        st.write("**Métriques extraites de la fiche labo :**")
                        st.json(data_json["extracted_data"])
                    elif response_ocr.status_code == 401:
                        st.error("🚫 Droits insuffisants : Clé API invalide.")
                    else:
                        st.error(f"❌ Échec de l'extraction (Code {response_ocr.status_code}) : {response_ocr.text}")
                except Exception as e:
                    st.error(f"🔌 Erreur réseau : Impossible de joindre le module OCR : {e}")