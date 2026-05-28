# Waterflow - Classification Binaire & MLOps

## Contexte du projet
Ce projet est réalisé en binôme dans le cadre d'un [bachelor en développement en intelligence artificielle.](https://laplateforme.io/bachelor-it/developpeur-en-intelligence-artificielle/)   
Il implémente un pipeline complet de Machine Learning destiné à prédire la potabilité de l'eau à partir de caractéristiques physico-chimiques.

Le jeu de données contient :
- 9 mesures de la qualité de l'eau (features)
- une étiquette (1 = potable, 0 = non potable)
- 3 276 étendues d'eau différentes (observations)

Il n'est pas stocké dans le dépôt Git pour des raisons d'optimisation de l'espace.   
Il doit être [téléchargé directement](https://drive.google.com/file/d/1C-tYJcgJDx5AuF7_oz7U4bbY0PERiFLo/view), ainsi que [son descriptif](https://drive.google.com/file/d/1VSRPKK6ys0Kn3gSYDHgrQogdBAHXcEKg/view).

---
---
---
## Quickstart Allégé (Lancement Rapide Production)

Cette procédure permet de démarrer immédiatement l'application complète pour tester l'interface utilisateur et réaliser des prédictions en temps réel, sans passer par la phase de ré-entraînement des modèles.

### 1. Terminal 1 : Démarrer l'infrastructure Docker (MLflow)
Assurez-vous que **Docker Desktop** est allumé, puis lancez le conteneur de tracking :
```bash
docker compose up -d
```

*L'interface graphique de suivi MLflow devient accessible sur :*   [http://127.0.0.1:5000](http://127.0.0.1:5000)

### 2. Terminal 2 : API Backend (FastAPI)

Ouvrez un nouveau terminal à la racine. L'API va scanner le Model Registry de MLflow au démarrage pour charger l'ensemble de vos modèles d'IA en mémoire :

```bash
uv run uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

*Documentation Swagger interactive disponible sur :*   
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)


### 3. Terminal 3 : Middleware (Flask)
Lance le serveur Flask pour qu'il écoute sur le port 8080
```bash
uv run python src/run_middleware.py
```



### 4. Terminal 4 : Interface Frontend (Streamlit)

Ouvrez un troisième terminal à la racine et lancez l'interface de démonstration utilisateur :

```bash
uv run streamlit run front/app.py
```

*Interface utilisateur disponible sur : [http://localhost:8501*](https://www.google.com/search?q=http://localhost:8501)

### 4. Effectuer une prédiction

* Ouvrir votre navigateur web sur [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501).
* Sélectionner l'algorithme souhaité dans le menu déroulant dynamique (**Régression Logistique**, **Random Forest**, **XGBoost**, ou **MLP Classifier**).
* Ajuster les curseurs des paramètres physico-chimiques de l'eau.
* Cliquer sur **Analyser l'échantillon** pour recevoir instantanément le diagnostic de potabilité sécurisé.

---
---
---


## Stack Technique Fixe

* **Système d'exploitation** : WSL2 (Ubuntu 22.04 LTS) sur Windows 11
* **Langage** : Python 3.12 (Dépendances clés : `scikit-learn`, `xgboost`, `pandas`, `fastapi`, `streamlit`)
* **Gestionnaire de packages** : `uv` (Astral) - Configuration du projet comme package local via `pyproject.toml`
* **MLOps** : MLflow (Tracking & Model Registry)
* **Conteneurisation** : Docker & Docker Compose

---

## Structure des Données

Les données sont segmentées dans le répertoire `data/` :

* `data/raw/water_potability.csv` : Jeu de données brut d'origine.
* `data/processed/water_imputed.csv` : Données nettoyées après imputation par la médiane, prêtes pour les algorithmes d'arbres (**Random Forest**, **XGBoost**).
* `data/processed/water_std.csv` : Données imputées et standardisées via `StandardScaler`, obligatoires pour les modèles sensibles à la variance (**Régression Logistique**, **MLP Classifier**).

---

## Architecture MLOps et Persistance

Le suivi des entraînements repose sur une architecture hybride :

1. **Serveur MLflow** : S'exécute de manière isolée dans un conteneur Docker, accessible sur le port `5000`.
2. **Backend Store** : Les métadonnées et métriques sont enregistrées localement sur l'hôte dans un fichier de base de données SQLite `mlflow.db`.
3. **Artifact Store** : Les fichiers de modèles sérialisés (`.pkl`) et les environnements sont stockés dans le répertoire local `runs/`, monté comme volume Docker vers `/app/runs`.

Cette configuration garantit la persistance totale des données en dehors du cycle de vie du conteneur Docker.

---

## Quickstart (Pipeline Complet)

### 1. Initialisation de l'environnement virtuel

L'environnement et la synchronisation des dépendances (groupes de développement et de test compris) sont gérés de manière optimisée par `uv` :

```bash
uv sync --group dev --group test
uv pip install -e .
```

### 2. Démarrage de l'infrastructure Docker

Le serveur de suivi MLflow doit obligatoirement être instancié en arrière-plan avant toute exécution de pipeline :

```bash
docker compose up -d
```

### 3. Cycle de Pré-traitement et d'Entraînement Automatisé

Le script d'expérimentation intègre une sécurité réseau qui valide la disponibilité du serveur MLflow sur le port 5000 avant de lancer les calculs. Il attribue automatiquement le bon dataset (`water_std.csv` ou `water_imputed.csv`) selon les exigences mathématiques de l'algorithme :

```bash
uv run src/experiment.py
```

*Note : L'alignement et l'entraînement des 4 modèles prend environ 1 à 2 minutes selon la puissance CPU de votre instance WSL2.*

### 4. Validation par la suite de tests logiciels

L'application intègre 3 niveaux de tests (unitaires, fonctionnels paramétrés pour les 4 modèles, et TNR de non-régression) exécutables via `pytest` :

```bash
uv run pytest -v
```

---

## Protocole d'Expérimentation

Afin d'évaluer l'impact des pré-traitements sur la performance, quatre configurations de référence sont exécutées en parallèle au sein de l'expérience `experiment_water_quality` et publiées de façon automatisée dans le registre :

| Modèle Enregistré | Dataset utilisé | Type de données | Clé API correspondante |
| --- | --- | --- | --- |
| **WaterModel_LogisticRegression** | `water_std.csv` | Standardisé | `LogisticRegression` |
| **WaterModel_RandomForestClassifier** | `water_imputed.csv` | Brut / Imputé | `RandomForestClassifier` |
| **WaterModel_XGBClassifier** | `water_imputed.csv` | Brut / Imputé | `XGBClassifier` |
| **WaterModel_MLPClassifier** | `water_std.csv` | Standardisé | `MLPClassifier` |

L'analyse comparative des performances s'effectue via l'interface graphique unifiée de MLflow à l'adresse suivante : `http://127.0.0.1:5000`.

---

## Implémentation d'une couche "Garde-fou Métier" (Business Rules)

Afin de pallier les aberrations mathématiques et les défauts d'extrapolations des modèles de Machine Learning sur les valeurs extrêmes (par exemple : un pH de 1 classé comme potable par manque de données similaires à l'entraînement), une couche de règles métiers strictes a été intégrée en amont de l'inférence.

Basée sur les seuils sanitaires et toxicologiques de l'OMS et de l'US EPA, elle filtre et rejette automatiquement l'échantillon si les limites de sécurité vitales sont dépassées :

* **pH** < 6.5 ou **pH** > 8.5
* **Turbidité** > 5.0 NTU
* **Chloramines** > 4.0 mg/L
* **Trihalométhanes** > 80 ppm

Ce couplage garantit la sécurité absolue de l'utilisateur tout en laissant le modèle de Machine Learning arbitrer les corrélations minérales et structurelles complexes (sulfates, conductivité, dureté).

---

## Conclusion et Perspectives

Le projet **Waterflow** démontre la viabilité d'une infrastructure MLOps moderne, découplée et hautement automatisée sous environnement WSL2. L'intégration réussie de la chaîne de liaison (**Frontend Streamlit $\rightarrow$ Backend FastAPI $\rightarrow$ Model Registry MLflow via Docker**) fournit un cadre industriel robuste pour le déploiement de modèles de Machine Learning.

### Principaux Jalons Atteints :

1. **Génie Logiciel & Typage Strict** : Configuration du projet comme package éditable local via `pyproject.toml`, adoption de `uv` pour une gestion déterministe, et structuration de l'API avec des schémas Pydantic.
2. **Registre de Modèles Dynamique** : Suppression des structures conditionnelles rigides (`if/else`) à l'entraînement et au déploiement au profit d'un mapping basé sur la réflexion d'objets Python (`__class__.__name__`), rendant la stack 100 % extensible.
3. **Qualité et Non-Régression** : Sécurisation du pipeline par l'implémentation de tests logiciels paramétrés couvrant simultanément l'ensemble de notre catalogue d'IA.

### Perspectives d'Évolution (Vers Waterflow 2) :

* **Persistance des Données Clients** : Modélisation d'une base de données relationnelle PostgreSQL pour tracer l'historique des requêtes d'analyses et assurer la conformité RGPD.
* **Sécurisation des Accès** : Implémentation d'un système d'authentification par clé API unique par client pour restreindre l'utilisation des routes d'inférence.
* **Ingestion de Rapports Automatisée** : Création d'un module d'OCR connecté pour parser des fiches d'analyses de laboratoire au format PDF ou image et alimenter automatiquement le pipeline.
