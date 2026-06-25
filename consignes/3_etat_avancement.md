# État d'Avancement Technique - Projet Waterflow 2

Ce document sert de snapshot d'état d'avancement pour le projet **Waterflow 2**. Il est destiné à être chargé en début de session (avec `CLAUDE.md`) pour économiser des tokens et donner immédiatement le contexte technique exact et à jour de l'architecture, des bogues résolus et des prochaines étapes.

---

## 1. Simplification de l'Architecture & Noms des Conteneurs [89, 94]

Tous les conteneurs du projet ont été renommés pour simplifier l'infrastructure, homogénéiser les configurations réseau et faciliter l'exploitation.

### Cartographie des Noms de Conteneurs [94]
| Ancien Nom | Nouveau Nom | Image Docker | Ports Exposés | Rôle |
| :--- | :--- | :--- | :--- | :--- |
| `postgres-db` | `postgres` | `postgres:16-alpine` | `5432:5432` | SGBD PostgreSQL (métadonnées MLflow + données métier) |
| `mlflow-back` | `mlflow` | `python:3.12-slim` | `5000:5000` | Serveur de Tracking & Registre de Modèles MLflow |
| `api-unique` | `api` | `waterflow-api` (Custom) | `8000:8000` | API FastAPI (Modules Data, Model, OCR unifiés) [94] |
| `mlops-training` | `mlops-training` | `waterflow-mlops-training` | *Aucun (Éphémère)* | Pipeline d'entraînement et enregistrement des modèles [97] |

### Fichier `docker-compose.yml` de Référence
```yaml
services:
  # 1. BASE DE DONNÉES POSTGRESQL
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=admin_waterflow
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=waterflow_db
    volumes:
      - postgres_waterflow_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin_waterflow -d waterflow_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # 2. SERVEUR DE TRACKING MLOPS MLFLOW
  mlflow:
    image: python:3.12-slim
    container_name: mlflow
    ports:
      - "5000:5000"
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - UVICORN_PROXY_HEADERS=true
      - UVICORN_FORWARDED_ALLOW_IPS=*
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./mlruns_artifacts:/app/artifacts
    restart: unless-stopped
    command: sh -c "pip install --no-cache-dir mlflow psycopg2-binary && mlflow server --backend-store-uri postgresql://admin_waterflow:${POSTGRES_PASSWORD}@postgres:5432/waterflow_db --default-artifact-root /app/artifacts --host 0.0.0.0 --port 5000"

  # 3. API UNIQUE FASTAPI (Data + Model + OCR)
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: api
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - DATABASE_URL=postgresql://admin_waterflow:${POSTGRES_PASSWORD}@postgres:5432/waterflow_db
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - OCR_SPACE_API_KEY=${OCR_SPACE_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      mlflow:
        condition: service_started
    volumes:
      - ./data:/app/data
      - ./mlruns_artifacts:/app/artifacts
      - ./src:/app/src
    restart: unless-stopped

  # 4. PIPELINE D'ENTRAÎNEMENT ISOLE (ÉPHÉMÈRE)
  mlops-training:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mlops-training
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - DATABASE_URL=postgresql://admin_waterflow:${POSTGRES_PASSWORD}@postgres:5432/waterflow_db
      - MLFLOW_TRACKING_URI=http://mlflow:5000
    depends_on:
      postgres:
        condition: service_healthy
      mlflow:
        condition: service_started
    volumes:
      - ./data:/app/data
      - ./mlruns_artifacts:/app/artifacts
    command: sh -c "echo 'Attente initialisation de MLflow...' && sleep 15 && python -m src.experiment"

volumes:
  postgres_waterflow_data:
    driver: local
```

---

## 2. Historique des Incidents & Bogues Résolus [18, 33]

### A. Erreur de Dépendance : `python-multipart` Manquant dans l'API
*   **Symptôme** : Le conteneur `api` s'arrêtait brusquement au démarrage et bouclait indéfiniment en statut `Restarting`. Les logs Docker affichaient : `Form data requires "python-multipart" to be installed.`
*   **Cause** : La route `POST /api/ocr/lab-report` reçoit un fichier de rapport labo (image ou PDF) [17, 32]. Pour gérer cette route de téléversement (`UploadFile`), FastAPI nécessite impérativement la bibliothèque `python-multipart`, mais celle-ci n'était pas installée dans l'environnement du projet.
*   **Résolution** :
    1. Ajout de la dépendance via `uv` : `uv add python-multipart`.
    2. Reconstruction et relancement du conteneur API : `docker compose up -d --build api`.

### B. Erreurs de Résolution DNS (Anciens noms de conteneurs)
*   **Symptôme** : Le script de l'entraînement et l'API principale n'arrivaient pas à se connecter à PostgreSQL ou à MLflow. Les logs indiquaient : `socket.gaierror: [Errno -2] Name or service not known` et des exceptions de connexion.
*   **Cause** : L'API et l'entraînement ciblaient l'ancienne adresse `postgres-db` ou `mlflow-back` [94]. De plus, le fichier de configuration locale `.env` de la machine hôte contenait les anciennes valeurs qui outrepassaient la configuration par défaut.
*   **Résolution** :
    *   Nettoyage des références dans `src/config.py` (pointant maintenant vers `@postgres:5432`).
    *   Mise à jour des variables de configuration locales dans le fichier `.env` de l'hôte (`MLFLOW_TRACKING_URI=http://mlflow:5000`).
    *   Reconstruction de l'image de l'entraînement pour y copier la configuration actualisée : `docker compose up -d --build mlops-training`.

### C. Échec de Chargement de l'IA : Parade DNS Rebinding (Erreur HTTP 403)
*   **Symptôme** : Lors d'une prédiction, le lazy loading échouait avec une erreur 503 : `Impossible de charger le modèle... API request to endpoint failed with error code 403. Response body: 'Invalid Host header - possible DNS rebinding attack detected'` [95].
*   **Cause** : Pour contrer l'erreur 403 provoquée par la sécurité Uvicorn au sein du réseau Docker, l'API intègre un patch d'interception HTTP [96]. Ce middleware surchargeait l'en-tête `Host` avec l'ancien nom de conteneur `mlflow-back`, qui a été rejeté après renommage.
*   **Résolution** : Mise à jour du patch réseau (dans `src/config.py`) pour écraser l'en-tête avec le nouveau nom de conteneur d'hôte : `mlflow` (ou `mlflow:5000`).

### D. Biais Système vers "Non Potable" et Rejet par les Garde-fous OMS
*   **Symptôme** : Toutes les valeurs d'analyse standards retournaient systématiquement un diagnostic "Non Potable" [98].
*   **Cause 1 - Déséquilibre des Classes** : Le dataset Kaggle comporte ~61% de données non-potables [47]. Les distributions statistiques des classes potable et non-potable étant quasiment identiques, les modèles prédisaient systématiquement la classe majoritaire par défaut.
*   **Cause 2 - Garde-fous OMS stricts** : Les garde-fous métiers automatisés rejettent directement l'échantillon si les limites vitales (comme Chloramines > 4.0 mg/L) sont dépassées [98]. La moyenne de Chloramine du dataset étant de 7.1 mg/L, le garde-fou court-circuitait 99% des échantillons potables réels.
*   **Résolution** :
    *   **Ré-équilibrage** : Ajout du paramètre `class_weight='balanced'` dans `src/models.py` pour forcer les modèles à pénaliser les erreurs sur la classe minoritaire.
    *   **Mise à jour des valeurs par défaut** : Injection d'un échantillon d'eau potable et respectueux des normes OMS (Ligne 666 du dataset d'origine) dans le formulaire de l'interface :
        *   `pH` : 7.04
        *   `Hardness` : 155.68
        *   `Solids` : 52060.23
        *   `Chloramines` : 2.58 (< 4.0 ppm, validé) [98]
        *   `Sulfate` : 365.08
        *   `Conductivity` : 323.00
        *   `Organic_carbon` : 14.17
        *   `Trihalomethanes` : 48.25
        *   `Turbidity` : 2.00 (< 5.0 NTU, validé) [98]

---

## 3. Statut du Frontend Flask

L'interface graphique est développée sous **Flask** (en remplacement de Streamlit) [18].

*   **Mode Debug** : Pour rafraîchir en temps réel les gabarits HTML (`front/templates/`) sans que Flask serve des pages obsolètes en cache, il doit tourner en mode Debug :
    *   `uv run flask --app app run --debug --port 5001` (ou `debug=True` dans `app.py`).
*   **Réseau Hôte vs Docker** : Le serveur Flask tournant directement sur l'hôte local, il ne peut pas résoudre l'adresse interne Docker `http://api:8000`. Il doit impérativement interroger l'API unique via **`http://127.0.0.1:8000`** (ou `localhost:8000`) qui est mappé sur l'hôte.

---

## 4. Backlog Technique Restant

- [ ] **Mise à jour de la documentation** : Remplacer les anciennes occurrences de `postgres-db`, `mlflow-back` et `api-unique` dans le `README.md` et le dossier `docs/` pour correspondre à la nouvelle infrastructure standardisée [94].
- [ ] **Mise à jour des schémas d'architecture** : Mettre à jour les fichiers Mermaid (`.mmd`) dans `docs/` pour harmoniser les noms des briques réseau.
- [ ] **Mise en place de la CI (GitHub Actions)** : Écrire le workflow `.github/workflows/ci.yml` pour jouer automatiquement les tests PyTest lors des push et PR [18].
- [ ] **Monitoring Applicatif** : Structurer l'exposition des logs d'accès, de traitement OCR et de temps d'inférence [18].
