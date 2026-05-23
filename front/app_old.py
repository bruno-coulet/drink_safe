'''
application Stremlit
'''

import streamlit as st
import requests
import os

# 1. Configuration de la page
st.set_page_config(
    page_title="Water Flow - Analyse de Potabilité",
    page_icon="💧",
    layout="centered"
)

# URL de l'API, localhost en local, mais on prévoit une variable d'environnement pour le futur VPS
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/predict")

# 2. Header de l'application
st.title("💧 Évaluation de la Potabilité de l'Eau")
st.write(
    "Cette application utilise un modèle de Machine Learning pour analyser les paramètres "
    "physico-chimiques de l'eau et déterminer si elle est propre à la consommation humaine."
)
st.markdown("---")

st.subheader("Configuration du modèle")
# Boîte de sélection pour l'algorithme
model_display = st.selectbox(
    "Choisissez l'algorithme d'analyse :",
    ["Régression Logistique (Données Standardisées)", "Random Forest (Données Brutes)"]
)

# Correspondance entre l'affichage et la clé technique attendue par l'API FastAPI
model_mapping = {
    "Régression Logistique (Données Standardisées)": "logistic_regression",
    "Random Forest (Données Brutes)": "random_forest"
}
selected_model_key = model_mapping[model_display]

st.markdown("---")

# 3. Formulaire de saisie des caractéristiques de l'eau
st.subheader("Paramètres de l'échantillon")

# On crée deux colonnes pour rendre le formulaire plus compact et élégant
col1, col2 = st.columns(2)

with col1:
    ph = st.slider("pH (Potentiel Hydrogène)", min_value=0.0, max_value=14.0, value=7.2, step=0.1)
    hardness = st.number_input("Dureté (Hardness en mg/L)", min_value=0.0, value=200.0, step=1.0)
    solids = st.number_input("Solides totaux dissous (Solids en ppm)", min_value=0.0, value=20000.0, step=100.0)
    chloramines = st.slider("Chloramines (ppm)", min_value=0.0, max_value=15.0, value=7.3, step=0.1)

with col2:
    sulfate = st.number_input("Sulfates (mg/L)", min_value=0.0, value=330.0, step=1.0)
    conductivity = st.number_input("Conductivité électrique (μS/cm)", min_value=0.0, value=420.0, step=1.0)
    organic_carbon = st.slider("Carbone Organique Total (ppm)", min_value=0.0, max_value=30.0, value=14.2, step=0.1)
    trihalomethanes = st.slider("Trihalométhanes (μg/L)", min_value=0.0, max_value=130.0, value=66.3, step=0.1)

# La turbidité prend toute la largeur en bas
st.markdown(" ")
st.write("**Clarté de l'eau**")
turbidity = st.slider("Turbidité (NTU)", min_value=0.0, max_value=7.0, value=4.0, step=0.1)

st.markdown("---")

# 4. Bouton de prédiction et appel à l'API
if st.button("Analyser l'échantillon", type="primary"):
    
    # Préparation du dictionnaire JSON au format exact attendu par l'API (Pydantic)
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
        "Turbidity": turbidity
    }
    
    with st.spinner("Analyse en cours par l'algorithme..."):
        try:
            # Envoi de la requête POST au backend FastAPI
            response = requests.post(API_URL, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                prediction = result["prediction"]
                status = result["status"]
                
                # Affichage du résultat avec un style adapté
                if prediction == 1:
                    st.success(f"### L'eau est estimée **{status}** !")
                else:
                    st.error(f"### ⚠️ Résultat : L'eau est estimée **{status}** (Impropre).")
            
            elif response.status_code == 503:
                st.warning("🎛️ Le serveur est en ligne mais le modèle n'a pas encore été chargé depuis MLflow.")
            else:
                st.error(f"❌ Erreur du serveur (Code {response.status_code}) : {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("🔌 Impossible de contacter l'API FastAPI. Vérifie qu'elle est bien lancée sur le port 8000.")
        except Exception as e:
            st.error(f"💥 Une erreur inattendue est survenue : {e}")