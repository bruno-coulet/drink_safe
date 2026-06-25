# Journal de Résolution des Incidents et Bogues (Maintien en Condition Opérationnelle)

## 1. Incidents Critiques & Bloquants (SLA & Modélisation)

### Incident A : Désynchronisation d'état MLOps ("State Mismatch" & Crash Inférence)
* **Symptôme :** Lors d'une requête de prédiction sur l'endpoint `/api/predict`, l'API renvoyait une erreur `503 Service Unavailable` :
  `{"detail":"Impossible de charger le modèle 'LogisticRegression' : No such file or directory: '/app/artifacts/1/.../artifacts/model/.'"}`.
* **Causes racines :**
  1. **Asynchronisme de démarrage :** L'API FastAPI démarrait plus vite que le script d'entraînement initial. Elle cherchait le registre MLflow et le dictionnaire `ml_models` au démarrage (via le lifespan) et tombait sur un registre vide.
  2. **Chargement statique rigide :** Les appels d'inférence recherchaient une version de modèle figée en dur (`models:/WaterModel/1`). Dès qu'un réentraînement avait lieu (générant une version 2 ou 3), l'ancien fichier binaire `.pkl` de la version 1 était nettoyé ou déplacé sur le disque, provoquant une rupture d'accès.
  3. **Isolation des conteneurs :** Le conteneur d'entraînement éphémère `mlops-training` s'exécutait et stockait ses artefacts binaires `.pkl` dans son propre conteneur éphémère. Le dossier `./mlruns_artifacts` n'était pas monté en volume partagé sur ce conteneur, empêchant l'API et le serveur MLflow d'accéder physiquement au modèle.
* **Résolutions appliquées :**
  * **Volume partagé :** Ajout du volume `./mlruns_artifacts` sur le conteneur `mlops-training` dans le fichier `docker-compose.yml`, et implémentation d'une temporisation native (`sleep 15`) pour attendre que le serveur MLflow ait fini de démarrer avant de lancer l'entraînement.
  * **Lazy Loading Dynamique (Cache-Aside) :** Modification du code (`src/routes/predictions.py`). L'API FastAPI ne charge plus les modèles au démarrage. À la première requête d'inférence, elle interroge dynamiquement le Model Registry pour obtenir le numéro de version le plus récent, télécharge le binaire `.pkl` depuis le volume local partagé, et le place dans son cache mémoire RAM pour les requêtes suivantes (Zero Downtime lors des réentraînements).

---

### Incident B : Échec Silencieux d'Écriture des Prédictions (Écart de Schéma SQL)
* **Symptôme :** Les prédictions étaient renvoyées avec succès (HTTP 200) aux clients, mais aucune prédiction ni aucun numéro de version de modèle n'était réellement persisté en base de données PostgreSQL. Aucun message d'erreur n'apparaissait dans les consoles d'exécution standard.
* **Causes racines :**
  * **Divergence de schéma :** La table `prelevements` en base de données avait été créée via une ancienne version de script (`src/config.py` ou `src/experiment.py`) dans laquelle les colonnes `prediction_potability` (type `INTEGER`/`BOOLEAN`) et `model_version` (type `VARCHAR`) étaient absentes, bien que correctement documentées dans le fichier de conception `docs/data_model.md`.
  * **Capture d'exception trop large :** Dans la fonction `_sauvegarder_prelevement_en_bdd` du fichier `predictions.py`, le bloc d'insertion SQL était encapsulé dans un `try/except Exception` générique qui interceptait l'erreur Postgres de colonne inexistante (`column does not exist`) et la masquait sans la logger, laissant l'API répondre un faux code de succès HTTP 200.
* **Résolutions appliquées :**
  * **Migration SQL :** Ajout manuel des colonnes manquantes en base de données PostgreSQL via une requête d'altération de table :
    ```sql
    ALTER TABLE prelevements ADD COLUMN prediction_potability INTEGER;
    ALTER TABLE prelevements ADD COLUMN model_version VARCHAR(50);
    ```
  * **Sécurisation du code :** Nettoyage du bloc de capture d'exceptions pour remonter proprement les erreurs d'écriture de base de données dans les terminaux d'exploitation.

---

## 2. Incidents Majeurs & Dysfonctionnements d'API

### Incident C : Erreur HTTP 500 sur la Consultation Expert des Prélèvements
* **Symptôme :** L'appel aux endpoints experts `GET /api/measurements` et `GET /api/measurements/admin` provoquait systématiquement une erreur interne `HTTP 500 Internal Server Error`, alors que le frontend Flask ne rapportait aucun problème (car il n'appelait que les routes de dépôt `POST`).
* **Causes racines :**
  * **Colonne SQL inexistante :** Le code des requêtes SQL de lecture dans `measurements.py` tentait d'effectuer un tri via la clause `ORDER BY date_prelevement DESC`. Or, la colonne de date réelle définie en base de données s'appelait `cree_le`.
* **Résolutions appliquées :**
  * **Correction de requête :** Remplacement de la variable de tri par la colonne de base réelle `ORDER BY cree_le DESC` dans le fichier `measurements.py` pour préserver l'historique chronologique inverse sans altérer le schéma physique existant de la base de données.

---

### Incident D : Double Source de Vérité pour le Schéma de Base de Données
* **Symptôme :** Des écarts de schéma apparaissaient régulièrement entre les tables créées par l'API et les tables manipulées par le conteneur d'entraînement, provoquant des ruptures de contraintes SQL lors de l'exécution en parallèle des services.
* **Causes racines :**
  * **Duplication de code :** Deux fonctions distinctes de ~50 lignes ré-implémentaient la création des tables : `config.init_db()` (utilisée par l'API FastAPI au démarrage) et `experiment.script_init_db()` (utilisée par le script d'entraînement autonome). Cette duplication a favorisé le décalage de schéma constaté dans l'Incident B.
* **Résolutions appliquées :**
  * **Single Source of Truth :** Suppression intégrale de la fonction redondante `script_init_db()` dans le script d'entraînement `experiment.py`. Ce script importe et utilise désormais la fonction unique et centralisée `init_db()` du module de configuration de l'API (`src/config.py`), éliminant définitivement tout risque de désynchronisation future.

---

## 3. Incidents Mineurs & Améliorations de Robustesse

### Incident E : Incohérence et Non-déterminisme des Versions de Modèles IA
* **Symptôme :** Selon que l'API utilisait le cache mémoire initial ou sollicitait le lazy loading à chaud après un réentraînement, elle servait des prédictions provenant de versions de modèles différentes. De plus, la réponse JSON retournée renvoyait systématiquement la chaîne `"model_version": "1"` codée en dur.
* **Causes racines :**
  * **Stratégies de chargement opposées :** Le fichier `api.py` chargeait la version figée `models:/{name}/1` au démarrage, tandis que le lazy-load de `predictions.py` récupérait la version la plus haute `max(version)` du Model Registry.
  * **Métadonnées statiques :** La fonction d'écriture de prédiction persistait systématiquement le suffixe `_v1` en base de données et affichait `1` dans le retour JSON sans vérifier le modèle réellement instancié.
* **Résolutions appliquées :**
  * **Harmonisation des versions :** Alignement d'api.py pour charger systématiquement la dernière version disponible (`latest_v.version`) au démarrage, en parfaite cohérence avec le comportement du lazy-load.
  * **Registre dynamique de versions :** Implémentation d'un dictionnaire parallèle en mémoire vive `ml_model_versions` qui enregistre dynamiquement la version réelle chargée pour chaque modèle. L'API lit désormais cette information dynamique pour renvoyer la valeur exacte au client et l'enregistrer proprement dans la table `prelevements`.

---

### Incident F : Échec de la Traçabilité de l'Audit RGPD (Logs anonymes forcés)
* **Symptôme :** La table de logs de sécurité et d'auditabilité `action_logs` enregistrait systématiquement la valeur textuelle `"ANONYMOUS"` dans la colonne `client_id`, rendant impossible l'imputabilité des requêtes à un client en cas de compromission de clé ou de litige.
* **Causes racines :**
  * **Valeur écrite en dur :** Le middleware de journalisation globale dans `api.py` écrivait la chaîne `"ANONYMOUS"` de manière statique car il s'exécutait en dehors du contexte d'extraction et de validation SQL de la clé API géré par la dépendance FastAPI d'authentification.
* **Résolutions appliquées :**
  * **Utilisation de request.state :** La dépendance d'authentification `get_current_client` a été mise à jour pour stocker l'identifiant client extrait de la clé API (`client_id`) dans le scope de la requête HTTP partagée via `request.state.client_id`.
  * **Middleware dynamique :** Le middleware relit cet identifiant à la fin de l'exécution de la route HTTP (après l'appel à `await call_next`). Les requêtes réussies sont ainsi journalisées sous leur identifiant client réel, tandis que les requêtes anonymes ou non authentifiées retombent de manière sécurisée et automatique sur le label `"ANONYMOUS"`.

---

### Incident G : Espace Parasite dans l'URI de MLflow (Échec hors Docker)
* **Symptôme :** Lors des phases de développement local (hors Docker) à l'aide de la commande `uv run uvicorn...`, le serveur MLflow était systématiquement déclaré injoignable par l'API.
* **Causes racines :**
  * **Erreur de saisie :** Une espace parasite s'était glissée dans l'adresse de fallback local du fichier `config.py` : `"http:// 127.0.0.1:5000"`. Contrairement à la variable `DATABASE_URL`, l'URI de tracking ne bénéficiait d'aucun traitement de nettoyage de chaîne (comme `.strip()`).
* **Résolutions appliquées :**
  * **Nettoyage :** Retrait de l'espace parasite dans la chaîne de caractères de configuration.

---

### Incident H : Contradiction d'Unités pour les Trihalométhanes (THM)
* **Symptôme :** Le seuil de sécurité sanitaire configuré pour les Trihalométhanes (THM) rejetait les échantillons supérieurs à `80.0` dans le code, mais les documentations et formulaires oscillaient contradictoirement entre les unités de microgrammes par litre (`µg/L`) et de parties par million (`ppm`).
* **Causes racines :**
  * **Erreur du descriptif source :** Scientifiquement, le seuil de potabilité réglementaire de l'OMS pour les THM est de `80 µg/L` (soit environ `0,08 ppm`). Le descriptif initial du dataset d'origine Kaggle mentionnait par erreur l'unité `ppm` pour la valeur `80`.
* **Résolutions appliquées :**
  * **Alignement complet :** Pour éviter d'introduire des décalages d'échelle numériques qui fausseraient les prédictions de l'IA (qui a appris sur des valeurs brutes proches de 80), l'unité a été standardisée sur le terme **`ppm`** sur l'ensemble de la chaîne de l'application (modèle de données, formulaires frontend Flask, guides d'API, curseurs d'IHM et code de validation).
