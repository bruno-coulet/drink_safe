# Architecture Technique - Waterflow 2
- choix de conception
- unification des conteneurs sous des dénominations standardisées
- mécanismes de communication réseau et de persistance des données.

## 1. Les Choix Techniques Majeurs
L'industrialisation de Waterflow 2 repose sur une simplification drastique de la stack réseau tout en garantissant des performances élevées et une maintenabilité optimale.

### API Unique Modulaire (FastAPI)

- Unification de :
    - la gestion des données
    - l'inférence des modèles
    - l'ingestion OCR
sous un seul conteneur backend.

- Modularité par Routeurs (APIRouter) :
Segmentation sémantique et logique du code sans introduire la complexité d'une architecture microservices.

- Stratégie MLOps de Lazy Loading :
Chargement dynamique des modèles à la volée avec mise en cache RAM pour éviter les blocages au démarrage (Cold Start).

- Conteneurisation Standardisée :
Orchestration de la stack via Docker Compose avec des services aux noms simplifiés (postgres, mlflow, api, mlops-training).

- IHM de Présentation (Flask) :
Transition d'un prototype Streamlit vers une application Flask multi-profils (Port 5001) exécutée sur la machine hôte.

## 2. Architecture Globale et Flux Réseau
La stack logicielle est segmentée en couches distinctes communiquant par requêtes HTTP sécurisées ou via le réseau virtuel isolé de Docker :

                  [ MACHINE HÔTE (Windows / WSL2) ]
                                  │
                       ┌──────────┴──────────┐
                       │   Frontend FLASK    │ (Port 5001)
                       │ (Client/Analyste)   │
                       └──────────┬──────────┘
                                  │ (Appels HTTP via localhost:8000)
                                  ▼
                     [ RÉSEAU ISOLE DOCKER ]
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     ▼                     │
            │          ┌─────────────────────┐          │
            │          │    API Unique       │ (Port 8000 / api)
            │          │    (FastAPI)        │
            │          └────┬───────────┬────┘          │
            │               │           │               │
            │      (SQL)    ▼           ▼ (Appels HTTP Internes)
            │  ┌──────────────┐       ┌──────────────┐  │
            │  │  Base SQL    │       │   Serveur    │  │ (Port 5000 / mlflow)
            │  │ (PostgreSQL) │       │   MLflow     │  │
            │  └──────────────┘       └──────┬───────┘  │
            │   (Port 5432 /                 │          │
            │    postgres)                   │ (Volume) │
            │                                ▼          │
            │                       ┌────────────────┐  │
            │                       │ Volume Partagé │  │ (./mlruns_artifacts)
            │                       │  (.pkl / ML)   │  │
            │                       └────────────────┘  │
            └───────────────────────────────────────────┘
Unification de la Nomenclature des Services
Afin de rendre l'infrastructure hautement lisible et d'éliminer les conflits de configuration, tous les conteneurs ont été renommés :

- api : Port 8000
    Expose la logique métier (data, predict, ocr).

- mlflow : Port 5000
    Gère le tracking et le Model Registry.

- postgres : Port 5432
    Assure la persistance relationnelle globale.

- mlops-training
    Pipeline éphémère d'entraînement et d'équilibrage des modèles.

## 3. Modularité de l'API FastAPI
Pour éviter un "surcoût" (overhead) de communication et la complexité de déploiement de multiples microservices, l'API unique consolide les modules dans des fichiers de routes isolés ``src/routes/`` :

``clients.py`` : Création et gestion des comptes clients, génération sécurisée des clés API (en-tête X-API-Key)

``measurements.py`` : Route d'ingestion des prélèvements structurés et de consultation (avec isolation stricte par clé API pour la conformité RGPD)

``predictions.py`` : Application des Garde-fous OMS en amont et orchestration de l'inférence par vote majoritaire (consensus) sur les 4 modèles

``ocr.py`` : Réception des documents non structurés, transmission sécurisée au service externe OCR.space, parsing des regex et création automatique du prélèvement structuré

``monitoring.py`` : Journalisation d'audit, monitoring des temps de réponse et des statuts HTTP pour l'auditeur d'exploitation.

## 4. Stratégie MLOps & Lazy Loading
Découplage des Métadonnées et des Artefacts
Pour préserver les performances de la base PostgreSQL, l'architecture sépare les données :

**Backend Store :**

PostgreSQL Gère
- l'historique des expériences
- les métriques d'entraînement
- les cycles de vie des versions


**Artifact Store :**

Un volume Docker local ``./mlruns_artifacts`` stocke physiquement les modèles sérialisés ``model.pkl``
Ce dossier est monté en lecture-écriture sur les conteneurs ``mlflow``, ``api`` et ``mlops-training``


**Mécanisme de Lazy Loading :**

L'API FastAPI ne charge pas les modèles ML en mémoire vive lors de son initialisation.

Ce fonctionnement évite les plantages au démarrage si le serveur MLflow est indisponible (Cold Start)

Lors de la première requête de prédiction, l'API :
- interroge le registre MLflow à la volée.
- télécharge le binaire requis depuis le volume partagé ``./mlruns_artifacts``
- Le modèle est instancié puis stocké dans un cache RAM local.

Les requêtes suivantes consomment directement le modèle en cache avec un temps de réponse inférieur à 5ms.

## 5. Parade contre le DNS Rebinding (Erreur 403)
Au sein d'un réseau Docker isolé, les serveurs d'application HTTP (comme Uvicorn) bloquent par sécurité les requêtes qui contiennent des en-têtes d'hôtes virtuels internes (ex: Host: mlflow:5000). Ce mécanisme de protection contre le DNS Rebinding renvoie une erreur 403 (Forbidden).

Résolution Technique
Un patch d'interception HTTP a été intégré dans src/config.py. Ce script Python surcharge dynamiquement la bibliothèque requests lors des requêtes adressées au serveur MLflow :

L'adresse IP réelle ou le nom d'hôte interne Docker (http://mlflow:5000) est résolu.
L'en-tête de la requête HTTP est écrasé à la volée pour forcer la valeur attendue par le serveur MLflow.
Grâce à cette surcharge, l'API peut communiquer de façon fluide avec le Model Registry sans compromettre la sécurité globale.

## 6. Base de Données PostgreSQL : Justification et Conformité
Pourquoi PostgreSQL ?
Concurrence avancée : Indispensable pour traiter de front les requêtes du middleware Flask, les téléversements OCR et la journalisation d'audit.
Persistance native pour MLflow : Remplace l'ancienne base SQLite locale par un SGBDR de niveau production.
Isolation de sécurité (RGPD) : Permet l'établissement de relations d'intégrité strictes assurant qu'un client final ne peut accéder qu'à ses propres données de prélèvements à l'aide de sa clé API unique.


## 7. Transition vers le Frontend Flask
L'interface utilisateur experte a été migrée de Streamlit vers Flask (Port 5001). Cette évolution permet :

Une meilleure gestion de l'authentification et de l'état des sessions.
La mise en place de tableaux de bord différenciés selon le profil (Client, Analyste Qualité, Responsable d'Exploitation).
Séparation stricte Hôte/Réseau : Flask s'exécute sur l'hôte local WSL2 et interroge l'API FastAPI conteneurisée via http://localhost:8000 (et non via l'adresse interne réseau http://api:8000 qui n'est pas résoluble depuis l'hôte).
