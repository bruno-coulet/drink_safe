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
Le suivi des expériences repose sur une architecture hybride :
1. **Serveur MLflow** : S'exécute de manière isolée dans un conteneur Docker, accessible sur le port `5000`.
2. **Backend Store** : Les métadonnées et métriques sont enregistrées localement sur l'hôte dans un fichier de base de données SQLite `mlflow.db`.
3. **Artifact Store** : Les fichiers de modèles sérialisés (`.pkl`) et les environnements sont stockés dans le répertoire local `runs/`, monté comme volume Docker vers `/app/runs`.

Cette configuration garantit la persistance totale des données en dehors du cycle de vie du conteneur Docker.

## Quickstart

### 1. Initialisation de l'environnement virtuel
L'environnement et la synchronisation des dépendances sont gérés de manière optimisée par `uv` :
```bash
# Installation et synchronisation des dépendances du projet
uv sync

```

### 2. Démarrage de l'infrastructure Docker

Le serveur de suivi MLflow doit être instancié en arrière-plan avant toute exécution de pipeline :

```bash
# Lancement du serveur MLflow via Docker Compose
docker compose up -d

```

### 3. Cycle de Pré-traitement et d'Entraînement

Le pipeline s'exécute séquentiellement depuis le terminal WSL2 :

```bash
# Génération des datasets (via l'exécution séquentielle du Notebook ou des scripts dédiés)
# Lancement de la suite d'entraînement multi-modèles
uv run src/train.py

```

## Protocole d'Expérimentation

Afin d'évaluer l'impact des pré-traitements sur la performance, deux configurations de référence sont exécutées en parallèle au sein de l'expérience `experiment_water_quality` :

| Modèle | Dataset utilisé | Hyperparamètres clés | Métriques de suivi |
| --- | --- | --- | --- |
| **Logistic Regression** | `water_std.csv` (Standardisé) | `max_iter=1000` | Accuracy, F1-Score, Precision, Recall |
| **Random Forest** | `water_imputed.csv` (Brut) | `n_estimators=100`, `n_jobs=-1` | Accuracy, F1-Score, Precision, Recall |

L'analyse comparative des performances et l'accès au Model Registry s'effectuent via l'interface graphique unifiée à l'adresse suivante : `http://127.0.0.1:5000`.
