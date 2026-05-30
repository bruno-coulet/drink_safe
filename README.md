# Waterflow 2
## Centralisation API Unique, Ingestion OCR & MLOps

## Contexte du projet
Ce projet est réalisé dans le cadre d'un [bachelor en développement en intelligence artificielle](https://laplateforme.io/bachelor-it/developpeur-en-intelligence-artificielle/).   
Il implémente :
- un pipeline complet de Machine Learning destiné à prédire la potabilité de l'eau à partir de caractéristiques physico-chimiques.
- une architecture industrielle multiniveau hautement découplée et conteneurisée via **Docker Compose** visant à automatiser l'analyse, le suivi, l'ingestion OCR et la prédiction. 
    
Réalisé sous l'environnement WSL2, le système intègre :
- une interface utilisateur réactive (Streamlit).
- une **API Unique unifiée (FastAPI)** gérant l'ingestion des données (Data), l'extraction documentaire (OCR) et les prédictions (Model) protégées par des garde-fous sanitaires.
- un serveur de tracking et registre de modèles d'Intelligence Artificielle (MLflow) connecté à une base PostgreSQL.

## Jeu de données
Le jeu de données contient :
- 3 276 étendues d'eau différentes (observations)
- 9 mesures physico-chimiques de la qualité de l'eau (features)
- une étiquette binaire (1 = potable, 0 = non potable)


Il n'est pas stocké dans le dépôt Git pour des raisons d'optimisation de l'espace. Il doit être [téléchargé directement](https://drive.google.com/file/d/1C-tYJcgJDx5AuF7_oz7U4bbY0PERiFLo/view), ainsi que [son descriptif](https://drive.google.com/file/d/1VSRPKK6ys0Kn3gSYDHgrQogdBAHXcEKg/view).


---

## Quickstart (Lancement Rapide Production)

Cette procédure permet de démarrer immédiatement l'application complète en s'appuyant sur l'infrastructure Docker pré-configurée.

### 1. Démarrer l'infrastructure et l'API
Assurez-vous que **Docker Desktop** (avec intégration WSL2) est actif, puis déployez l'environnement (Base de données, serveur MLflow et API Unique) :
```bash
docker compose up -d postgres-db mlflow-back api-unique
```

L'interface graphique de suivi MLflow devient accessible sur : http://127.0.0.1:5000
L'API Unique et sa documentation Swagger sont disponibles sur : http://127.0.0.1:8000/docs

### 2. Interface Frontend (Streamlit)

Déployez l'IHM finale destinée aux experts et administrateurs depuis votre hôte local :

```bash
uv run streamlit run front/app.py
```

Interface utilisateur disponible sur : http://localhost:8501

---

## Stack Technique Fixe

* **Système d'exploitation :** Windows 11 avec WSL2 (Ubuntu)
* **Langage :** Python 3.12 (scikit-learn, xgboost, pandas, fastapi, streamlit)
* **Gestionnaire de packages :** `uv` (Astral)
* **MLOps :** MLflow (Tracking & Model Registry)
* **Conteneurisation & Persistance :** Docker, Docker Compose & PostgreSQL 16

### Structure des Données

Les données sont segmentées et partagées avec les conteneurs dans le répertoire `data/` :

* `data/raw/water_potability.csv` : Jeu de données brut d'origine.
* `data/processed/water_imputed.csv` : Données imputées par la médiane (pour Random Forest, XGBoost).
* `data/processed/water_std.csv` : Données imputées et standardisées (pour Régression Logistique, MLP Classifier).

### Architecture de la Stack Réseau

L'infrastructure applicative est segmentée en services isolés communiquant par requêtes HTTP :

| Composant | Framework / Image | Port | Mode de déploiement | Rôle principal |
| --- | --- | --- | --- | --- |
| **Interface UI** | Streamlit | 8501 | Hôte local (WSL2) | Présentation IHM, filtres experts et téléversement de rapports labo (OCR). |
| **API Unique** | FastAPI (`api-unique`) | 8000 | Conteneur Docker | Point d'entrée unifié : gestion clients, ingestion OCR, persistance SQL et inférence IA. |
| **Registre MLOps** | MLflow (`mlflow-back`) | 5000 | Conteneur Docker | Gestion du cycle de vie des modèles, du tracking d'expériences et du Model Registry. |
| **Base de Données** | PostgreSQL 16 (`postgres-db`) | 5432 | Conteneur Docker | SGBDR industriel unifié (Stockage applicatif métier + Tables de métadonnées MLflow). |

---

## Architecture MLOps, Persistance Réseau & Sécurité

### 1. Découplage BDD (Métadonnées) vs Volume Local (Artefacts)

Afin d'éviter l'encombrement des tables relationnelles par des binaires lourds (`.pkl`), l'architecture sépare physiquement le stockage :

* **Backend Store (BDD) :** MLflow est interconnecté à l'instance PostgreSQL. Il structure nativement ses tables SQL dans la base `waterflow_db`.
* **Artifact Store (Volume) :** Les fichiers sérialisés des modèles sont enregistrés sur le disque de la machine hôte dans le répertoire local `./mlruns_artifacts`. Ce dossier est monté comme volume partagé sur `mlflow-back`, `mlops-training` et `api-unique`.
* **Lazy Loading Dynamique :** L'API charge les modèles en mémoire (RAM) à la volée depuis le volume partagé lors de la première requête de prédiction, garantissant une résilience totale aux redémarrages.

### 2. Parade contre le DNS Rebinding (Erreur HTTP 403)

Les serveurs HTTP exécutés dans un réseau Docker isolé rejettent par défaut les requêtes contenant des en-têtes d'hôtes virtuels internes (ex: `Host: mlflow-back:5000`). Un patch d'interception HTTP surcharge dynamiquement la bibliothèque `requests` dans l'API pour forcer l'en-tête attendu par le serveur et neutraliser ce blocage.

---

## Scénarios d'Exécution & Cycle de Vie

**Pré-requis :** Créez un fichier `.env` à la racine du projet :

```env
POSTGRES_PASSWORD=MonMotDePasseSecurise123!
OCR_SPACE_API_KEY=VotreCleApiOcrSpace
SECRET_KEY=UneCleDeSessionSecurisee
```

### Scénario : Entraînement Initial (MLOps Pipeline)

Pour entraîner les modèles et populer le registre MLflow (à exécuter lors du premier déploiement ou pour mettre à jour les modèles) :

1. Assurez-vous que l'infrastructure de base tourne (`postgres-db` et `mlflow-back`).
2. Lancez le conteneur d'entraînement éphémère :

```bash
docker compose up mlops-training
```

*Note : Ce conteneur intègre une temporisation native (`sleep 15`) pour attendre la pleine disponibilité du serveur MLflow avant de lancer les calculs.* Il entraîne les 4 architectures, publie les métriques et écrit les artefacts binaires dans le volume partagé avant de s'arrêter proprement (`exited with code 0`).

### Couche "Garde-fou Métier" (Business Rules)

Une couche de règles métiers strictes est exécutée en amont de l'inférence. Basée sur les seuils de l'OMS, elle rejette automatiquement l'échantillon (sans faire appel à l'IA) si les limites vitales sont dépassées :

* pH < 6.5 ou pH > 8.5
* Turbidité > 5.0 NTU
* Chloramines > 4.0 mg/L
* Trihalométhanes > 80 ppm


## Guide de lancement : Développement vs Production

Pour piloter le projet, il est important de choisir le mode de lancement adapté :

1. Mode Production (Déploiement complet)
Pour une exécution réelle (VPS) ou pour tester l'architecture complète avec ses conteneurs isolés.

```shell
docker compose up -d
```

Cela lance tous les services (BDD, MLflow, API) de manière isolée et persistante.

Accès API sur http://127.0.0.1:8000.

2. Mode Développement (Édition de code)
Utile si l'on modifie le code source (src/) pour voir les changements en temps réel.

Pré-requis : 
- Demarer les services de données lancés avec Docker
    - `docker compose up -d postgres-db mlflow-back`
- Arrêter le conteneur API
    - `docker compose stop api-unique`

```shell
uv run uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

Le mode --reload redémarre l'API instantanément à chaque sauvegarde de fichier.