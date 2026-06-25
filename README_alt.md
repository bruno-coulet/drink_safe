# Waterflow 2 - Plateforme MLOps "Drink Safe"

## Contexte du projet
Waterflow 2 est l'industrialisation d'un pipeline de Machine Learning destiné à classifier la potabilité de l'eau à partir de mesures physico-chimiques.

Cette architecture unifiée remplace le prototype initial par une infrastructure professionnelle et modulaire. Elle intègre une API unique multi-routes (Data, Inférence, OCR), une base de données PostgreSQL pour la persistance et l'isolation RGPD, un serveur Flask pour l'interface expert, et un registre MLflow pour le suivi des modèles.

## Stack Technique
* **OS / Environnement** : WSL2 (Ubuntu) sur Windows 11
* **Langage & Gestionnaire** : Python 3.12 / uv (Astral)
* **Backend** : FastAPI (API Unique)
* **Frontend** : Flask
* **Base de données** : PostgreSQL 16
* **MLOps** : MLflow (Tracking & Registry)
* **Conteneurisation** : Docker & Docker Compose
* **CI/CD** : GitHub Actions

## Quickstart (Lancement en local)

### 1. Démarrage de l'infrastructure de base (BDD & MLflow)
Depuis votre terminal WSL2, lancez les services de stockage et de tracking :
```bash
docker compose up -d postgres mlflow
```
*Attendez environ 15 secondes pour que la base de données et MLflow s'initialisent correctement.*

### 2. Entraînement des Modèles (MLOps)
L'API nécessite que les modèles soient préalablement entraînés. Lancez le conteneur d'entraînement :
```bash
docker compose up mlops-training
```
*Ce conteneur éphémère va générer les modèles (Régression Logistique, Random Forest, XGBoost, MLP), les publier dans MLflow et sauvegarder les fichiers physiques `.pkl` dans le volume partagé local `./mlruns_artifacts`.*

### 3. Lancement de l'API Unique (FastAPI)
Démarrez le middleware applicatif :
```bash
docker compose up -d api
```
*L'API est désormais accessible sur `http://localhost:8000`. Grâce au Lazy Loading, les algorithmes d'IA seront chargés dynamiquement en mémoire RAM uniquement lors de la toute première requête de prédiction, évitant ainsi les erreurs de Cold Start.*

### 4. Lancement de l'Interface Web (Flask)
Sur votre machine hôte, activez votre environnement virtuel et lancez le frontend applicatif :
```bash
uv sync --frozen
uv run flask --app front/app run --debug --port 5001
```
*L'interface d'administration experte est accessible dans votre navigateur à l'adresse `http://localhost:5001`.*

## Authentification & Comptes de Test
La sécurité et le cloisonnement des données (Multi-Tenancy RGPD) sont assurés par un système d'authentification par clé API. La clé doit être transmise dans l'en-tête HTTP `X-API-Key`.

* **Clé d'un client de test valide** : `wf_live_123456789`

### Exemple d'appel API (Dépôt de prélèvement structuré)
```bash
curl -X 'POST' \
  'http://localhost:8000/api/measurements' \
  -H 'X-API-Key: wf_live_123456789' \
  -H 'Content-Type: application/json' \
  -d '{
  "model_choice": "XGBClassifier",
  "ph": 7.04,
  "Hardness": 155.68,
  "Solids": 52060.23,
  "Chloramines": 2.58,
  "Sulfate": 365.08,
  "Conductivity": 323.00,
  "Organic_carbon": 14.17,
  "Trihalomethanes": 48.25,
  "Turbidity": 2.00
}'
```

## Tests et Intégration Continue (CI/CD)
La robustesse de la plateforme est validée par une suite de tests automatisés (Unitaires, Fonctionnels et Non-Régression) pilotée par **PyTest**. Le workflow GitHub Actions (`.github/workflows/ci.yml`) déclenche l'exécution des tests à chaque `push` ou `pull_request`.

**Choix d'Architecture CI :**
Sur cette infrastructure locale, la CI ré-entraîne les modèles à la volée avant de jouer les tests. Ce choix est justifié et optimisé car le dataset d'apprentissage est très léger (3276 observations) et le serveur MLflow est instancié de zéro (vierge) sur chaque runner GitHub Ubuntu. Cela permet de valider simultanément l'intégrité du code métier, les calculs de l'IA (AUC-PR, F1-Score) et le flux réseau complet.

## Limites Connues
* **Ingestion documentaire (OCR)** : Le service tiers OCR.space et le parseur Regex associé extraient parfaitement les 9 mesures physico-chimiques requises. Néanmoins, l'extraction de la date de prélèvement exacte depuis les formats PDF ou images n'est pas encore prise en charge. Le système pallie cette limite en horodatant automatiquement l'intégration de la fiche en base de données.

