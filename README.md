# Waterflow - Classification Binaire & MLOps

## Contexte du projet
Ce projet est réalisé en binôme dans le cadre d'un [bachelor en développement en intelligence artificielle.](https://laplateforme.io/bachelor-it/developpeur-en-intelligence-artificielle/)   
Il implémente un pipeline complet de Machine Learning destiné à prédire la potabilité de l'eau à partir de caractéristiques physico-chimiques.

Le jeu de données original n'est pas stocké dans le dépôt Git pour des raisons d'optimisation de l'espace ; il doit être [téléchargé directement](https://drive.google.com/file/d/1C-tYJcgJDx5AuF7_oz7U4bbY0PERiFLo/view), ainsi que [son descriptif](https://drive.google.com/file/d/1VSRPKK6ys0Kn3gSYDHgrQogdBAHXcEKg/view)

## Stack Technique Fixe
- **Système d'exploitation** : WSL2 (Ubuntu 22.04 LTS) sur Windows 11
- **Langage** : Python 3.12 (Dépendances clés : `scikit-learn`, `pandas`, `pathlib`)
- **Gestionnaire de packages** : `uv` (Astral)
- **MLOps** : MLflow (Tracking & Model Registry via base de données SQLite locale)
- **Conteneurisation** : Docker & Docker Compose

## Structure des Données
Le cycle de vie des données est segmenté au sein du répertoire `data/` :
- `data/raw/water_potability.csv` : Jeu de données brut d'origine.
- `data/processed/water_imputed.csv` : Données nettoyées après traitement des valeurs manquantes (imputation), prêtes pour les algorithmes d'arbres.
- `data/processed/water_std.csv` : Données imputées et standardisées via `StandardScaler`, obligatoires pour les modèles linéaires.

## Architecture MLOps et Persistance
Le suivi des entrainements repose sur une architecture hybride :
1. **Serveur MLflow** : S'exécute de manière isolée dans un conteneur Docker, accessible sur le port `5000`.
2. **Backend Store** : Les métadonnées et métriques sont enregistrées localement sur l'hôte dans un fichier de base de données SQLite `mlflow.db`.
3. **Artifact Store** : Les fichiers de modèles sérialisés (`.pkl`) et les environnements sont stockés dans le répertoire local `runs/`, monté comme volume Docker vers `/app/runs`.

Cette configuration garantit la persistance totale des données en dehors du cycle de vie du conteneur Docker.

## Quickstart (Pipeline Complet)

### 1. Initialisation de l'environnement virtuel
L'environnement et la synchronisation des dépendances sont gérés de manière optimisée par `uv` :
```bash
# Installation et synchronisation des dépendances du projet (incluant le groupe test)
uv sync --group test

```

### 2. Démarrage de l'infrastructure Docker

Le serveur de suivi MLflow doit être instancié en arrière-plan avant toute exécution de pipeline :

```bash
# Lancement du serveur MLflow via Docker Compose
docker compose up -d

```

### 3. Cycle de Pré-traitement et d'Entraînement

Le pipeline extrait dynamiquement le nom des classes pour enregistrer les versions de manière isolée :

```bash
# Lancement de la suite d'entraînement multi-modèles (génère WaterModel_LogisticRegression et WaterModel_RandomForestClassifier)
uv run src/train.py

```

### 4. Validation par les Tests Logitiels

L'application intègre 3 niveaux de tests (unitaires, fonctionnels et non-régression) exécutables via `pytest` :

```bash
# Exécution de la suite de tests validée
uv run pytest -v

```

## Quickstart Allégé (Lancement Rapide Production)

Cette procédure permet de démarrer immédiatement l'application complète pour tester l'interface utilisateur et réaliser des prédictions en temps réel, sans passer par la phase de ré-entraînement des modèles.

### 1. Démarrer l'infrastructure et l'API Backend

Dans un premier terminal WSL2, initialisez l'environnement et lancez le serveur d'API (FastAPI) qui chargera automatiquement les modèles disponibles depuis le Model Registry :

```bash
# Lancer le conteneur Docker MLflow (nécessaire pour l'API)
docker compose up -d

# Lancer le serveur backend API sur le port 8000
uv run uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload

```

### 2. Démarrer l'interface Frontend

Ouvrez un **second terminal WSL2** indépendant et lancez l'application graphique Streamlit :

```bash
# Lancer l'interface utilisateur sur le port 8501
uv run streamlit run front/app.py

```

### 3. Effectuer une prédiction

* Ouvrez votre navigateur web sur votre machine hôte Windows à l'adresse : [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)
* Sélectionnez l'algorithme souhaité dans le menu déroulant dynamique (**Régression Logistique** ou **Random Forest**).
* Ajustez les curseurs des paramètres physico-chimiques de l'eau.
* Cliquez sur le bouton **Analyser l'échantillon** pour recevoir instantanément le diagnostic de potabilité par le modèle interrogé.

## Protocole d'Expérimentation

Afin d'évaluer l'impact des pré-traitements sur la performance, deux configurations de référence sont exécutées en parallèle au sein de l'expérience `experiment_water_quality` et publiées de façon automatisée dans le registre :

| Modèle Enregistré | Dataset utilisé | Hyperparamètres clés | Métriques de suivi | Clé API correspondante |
| --- | --- | --- | --- | --- |
| **WaterModel_LogisticRegression** | `water_std.csv` (Standardisé) | `max_iter=1000` | Accuracy, F1-Score, Precision, Recall | `LogisticRegression` |
| **WaterModel_RandomForestClassifier** | `water_imputed.csv` (Brut) | `n_estimators=100`, `n_jobs=-1` | Accuracy, F1-Score, Precision, Recall | `RandomForestClassifier` |

L'analyse comparative des performances et l'accès au Model Registry s'effectuent via l'interface graphique unifiée de MLflow à l'adresse suivante : `http://127.0.0.1:5000`.