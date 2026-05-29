# Waterflow
## Classification Binaire & MLOps
## Centralisation Middleware, Ingestion OCR & MLOps

## Contexte du projet
Ce projet est réalisé en binôme dans le cadre d'un [bachelor en développement en intelligence artificielle.](https://laplateforme.io/bachelor-it/developpeur-en-intelligence-artificielle/)   
Il implémente :
- un pipeline complet de Machine Learning destiné à prédire la potabilité de l'eau à partir de caractéristiques physico-chimiques.

- une architecture industrielle multiniveau (N-Tier) hautement découplée visant à automatiser :
    - l'analyse
    - le suivi et la prédiction de la potabilité de l'eau. 
    
Réalisé sous l'environnement WSL2, le système intègre :
- une interface utilisateur réactive
- un middleware d'unification et de persistance relationnelle
- un serveur d'inférence protégé par des garde-fous sanitaires
- un serveur de tracking de modèles d'Intelligence Artificielle.


## Jeu de donnée

Le jeu de données contient :
- 3 276 étendues d'eau différentes (observations)
- 9 mesures 9 mesures physico-chimiques de la qualité de l'eau (features)
- une étiquette binaire (1 = potable, 0 = non potable)


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
uv run python run_middleware.py
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

## Architecture de la Stack Réseau

L'infrastructure applicative est segmentée en services isolés et conteneurisés communiquant par API REST :

| Composant | Framework / Image | Port par défaut | Rôle principal |
| --- | --- | --- | --- |
| **Interface UI** | Streamlit | `8501` | Présentation IHM, curseurs de simulation et téléversement de rapports de laboratoire. |
| **Middleware** | Flask | `8080` | Unique point d'entrée applicatif, gestion des Blueprints (`/api/v1`), routage et persistance métier. |
| **Serveur d'Inférence** | FastAPI | `8000` | Application des règles métiers de l'OMS et calcul des prédictions de potabilité en temps réel. |
| **Registre MLOps** | MLflow Server | `5000` | Image officielle de gestion du cycle de vie des modèles, du tracking et du Model Registry. |
| **Base de Données** | PostgreSQL 16 | `5432` | SGBDR industriel unifié (Stockage applicatif métier + Tables de métadonnées MLflow). |

---

## Architecture MLOps & Persistance Réseaux

Le stockage à plat par fichier SQLite (`mlflow.db`) a été abandonné au profit d'une centralisation relationnelle robuste :
1. **Backend Store** : MLflow est interconnecté à l'instance **PostgreSQL 16-Alpine**. Au démarrage, l'image télécharge dynamiquement son composant de liaison `psycopg2-binary` et structure nativement ses tables SQL dans la base `waterflow_db`.
2. **Artifact Store** : Les fichiers sérialisés des modèles (`.pkl`) et les métadonnées de l'environnement d'exécution sont persistés dans le répertoire local `./artifacts`, monté comme volume Docker.
3. **Persistance Applicative** : Le middleware Flask orchestre l'écriture des entités métiers au sein de cette même base de données PostgreSQL, garantissant des identifiants réels et uniques calculés nativement par le SGBD (`SERIAL PRIMARY KEY`).

---

## Scénarios de Démarrage (Quickstart)

Pour s'adapter à votre cas d'usage   
Le projet propose deux parcours distincts : 
- **Scénario A** ré-entraîne l'intégralité des modèles d'IA
- **Scénario B** lance directement l'application de production avec les derniers modèles enregistrés.

Dans les deux cas, vous devez impérativement créer un fichier `.env` à la racine du projet (exclu de Git) :

```env
POSTGRES_PASSWORD=MonMotDePasseSecurise123!

DATABASE_URL=postgresql://admin_waterflow:MonMotDePasseSecurise123!@127.0.0.1:5432/waterflow_db

SECRET_KEY=UneCleDeSessionFlaskSecurisee

FASTAPI_URL=[http://127.0.0.1:8000/predict](http://127.0.0.1:8000/predict)

MLFLOW_TRACKING_URI=[http://127.0.0.1:5000](http://127.0.0.1:5000)
```

### Scénario A : Pipeline Complet (Entraînement des Modèles MLOps)
Suivez ces étapes si vous venez de cloner le projet pour la première fois ou si vous souhaitez mettre à jour les modèles prédictifs.

1. Initialisation de l'environnement virtuel et des dépendances
L'environnement virtuel et la synchronisation des dépendances (groupes de développement et de test compris) sont gérés de manière optimisée par uv :

```Bash
uv sync --group dev --group test
uv pip install -e .
```

2. Récupération du Dataset d'origine
Téléchargez le fichier de données officiel water_potability.csv et placez-le impérativement à la racine de votre projet ou dans le dossier data/ prévu à cet effet.

3. Déploiement de l'infrastructure de tracking (Docker)
Le serveur de suivi MLflow et PostgreSQL doivent être démarrés pour historiser l'expérience :

Bash
docker compose up -d
Vérifiez l'accès à l'interface de suivi sur : http://127.0.0.1:5000

4. Exécution du cycle d'entraînement automatisé
Le script d'expérimentation valide la disponibilité du serveur MLflow avant de lancer les calculs. Il applique les transformations adéquates et entraîne simultanément votre catalogue d'IA (Random Forest, XGBoost, etc.) en consignant les métriques et artefacts :

```Bash
uv run src/experiment.py
```

Note : L'alignement et l'entraînement prennent environ 1 à 2 minutes selon la puissance CPU de votre instance WSL2. Vos modèles sont désormais stockés dans le registre de modèles MLflow.

### Scénario B : Lancement de l'Application en Production
Suivez ces étapes pour démarrer l'écosystème complet interconnecté (Interface, Middleware, Inférence et BDD).

1. Démarrage de l'infrastructure Docker (PostgreSQL & MLflow)
Instanciez la base de données et le serveur de tracking. L'interpolation Docker se charge de sécuriser vos identifiants :

```Bash
docker compose up -d
```

2. Initialisation physique des tables applicatives
Exécutez le script d'initialisation de la couche d'accès aux données pour concevoir la table des prélèvements sous PostgreSQL :

```Bash
uv run python src/middleware/bdd.py
```

3. Lancement du Serveur d'Inférence (FastAPI)
Ouvrez un terminal WSL2 dédié et lancez le cœur d'inférence. Au démarrage, il se connecte à MLflow pour charger à la volée le meilleur modèle en moins d'une seconde :

```Bash
uv run uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

4. Démarrage du Middleware Centralisé (Flask)
Dans un nouveau terminal, démarrez le chef d'orchestre de l'application qui gère la logique métier sur le port 8080 :

```Bash
uv run python run_middleware.py
```

5. Démarrage de l'Interface Graphique (Streamlit)
Dans un dernier terminal, déployez l'IHM web destinée aux experts et aux utilisateurs finaux :

```Bash
uv run streamlit run front/app.py
```

L'application complète est accessible à l'adresse : http://localhost:8501





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

## Couche "Garde-fou Métier" (Business Rules)

Afin de pallier les risques d'aberrations statistiques ou de faux-positifs des modèles de Machine Learning sur les valeurs extrêmes non rencontrées lors de la phase d'entraînement   

*par exemple : un pH de 1 classé comme potable par manque de données similaires à l'entraînement*

Une couche de règles métiers strictes est exécutée en amont de l'inférence.

Basée sur les seuils toxicologiques de l'OMS et de l'US EPA, elle filtre et rejette automatiquement l'échantillon si les limites de sécurité vitales sont dépassées :

* **pH** < 6.5 ou **pH** > 8.5
* **Turbidité** > 5.0 NTU
* **Chloramines** > 4.0 mg/L
* **Trihalométhanes** > 80 ppm

Ce couplage garantit la sécurité absolue de l'utilisateur tout en laissant le modèle de Machine Learning arbitrer les corrélations minérales et structurelles complexes (sulfates, conductivité, dureté).







