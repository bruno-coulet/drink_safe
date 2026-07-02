### État d'Avancement Technique - Projet Waterflow 2

Ce document sert de snapshot d'état d'avancement pour le projet Waterflow 2. L'objectif est de fournir un contexte clair sur l'architecture, les fonctionnalités implémentées et le backlog restant.

#### 1. Architecture et Services
Tous les conteneurs sont configurés et fonctionnels sous Docker Compose :
*   **postgres (Port 5432)** : Base de données relationnelle globale.
*   **mlflow (Port 5000)** : Registre de modèles.
*   **api (Port 8000)** : API FastAPI unifiée (Data, Predict, OCR, Monitoring).
*   **mlops-training** : Pipeline éphémère d'entraînement et évaluation.
*   **prometheus (Port 9090)** : Récupération des métriques temporelles.
*   **grafana (Port 3000)** : Tableaux de bord de supervision.
*   **Interface** : L'IHM Flask tourne localement (Port 5001) et s'adresse à localhost:8000.

#### 2. Historique des Incidents & Bogues Résolus
*   **Incident A (Crash Inférence 503) :** Résolu via l'implémentation du Mock de la librairie mlflow dans les tests fonctionnels (PyTest), permettant la validation CI sans dépendance au volume Docker absolu. En production, le modèle est chargé dynamiquement (Lazy Loading).
*   **Biais de Modélisation (Prédiction) :** Le bug logique de comptage du consensus (somme des classes au lieu du comptage des occurrences) dans `predictions.py` a été corrigé. Le consensus est désormais strict et mathématiquement valide.
*   **Incident OCR (Timeout Service Externe) :** Implémentation d'un fallback gracieux gérant les ralentissements extrêmes du service gratuit `OCR.space`. L'API FastAPI (timeout 60s) intercepte la panne réseau (RequestException), génère un log d'erreur JSON structuré explicite, et renvoie un statut "pending" (HTTP 201) au lieu de crasher. Le frontend Flask (timeout 75s) affiche alors un bandeau d'avertissement propre à l'utilisateur.
*   **Incident OCR (Quota / IsErroredOnProcessing) :** Correction d'un cas non couvert par le fallback : OCR.space peut renvoyer HTTP 200 avec `IsErroredOnProcessing: true` lorsque le quota de la clé API est atteint. Ce cas levait une 422 sans grâce. Le fallback a été étendu pour intercepter ce chemin et retourner le même statut "pending" (HTTP 201) avec log structuré et incrémentation du compteur Prometheus `ocr_failures_total`. Un log DEBUG de la réponse brute (`ocr_raw_response`) a été ajouté pour faciliter le diagnostic futur. Correction complémentaire : `cursor.fetchone()` peut retourner `None` — une garde explicite a été ajoutée avant l'accès à l'index `[0]`.

#### 3. Conformité et Modélisation (Base de Données)
*   Le schéma applicatif a été fusionné sous PostgreSQL.
*   L'isolation multi-tenant est active via l'en-tête `X-API-Key`.
*   Un middleware journalise les temps d'exécution et anonymise l'ID client pour la table `action_logs`.

#### 4. Statut du Frontend Flask
*   L'interface graphique a été entièrement développée et connectée aux différents modules de l'API.

#### 5. API Data & Gouvernance des Accès (Sécurité)
*   **Authentification par Clé API :** Mise en place d'une sécurité stricte basée sur l'en-tête `X-API-Key`, garantissant le cloisonnement des données (Multi-Tenancy RGPD) pour chaque client.
*   **Gestion des entités (Admin) :** Finalisation de la route `POST /api/clients`. Le système génère désormais une clé API unique de manière cryptographique, ne stocke que son empreinte (hachage SHA-256) dans PostgreSQL, et renvoie la clé en clair une unique fois à l'IHM pour le Responsable d'Exploitation.
*   **Amorçage de la base :** Implémentation du script `seed_admins.py` permettant l'injection automatisée des profils administrateurs initiaux en base de données.

#### 6. API OCR & Ingestion Automatisée (User Story #2)
*   **Intégration du service externe :** La route `POST /api/ocr/lab-report` est pleinement opérationnelle. Elle réceptionne des fichiers binaires (PDF/Images) via des requêtes `multipart/form-data` et communique avec l'API tierce *OCR.space*.
*   **Persistance relationnelle :** Les mesures physico-chimiques extraites du texte brut sont automatiquement insérées dans la table `prelevements` de PostgreSQL sous la provenance "OCR". Le système respecte de manière stricte les contraintes d'intégrité (clé étrangère client_id).

#### 7. Interface Web Expert (Frontend Flask)
*   **Gestion des Profils :** Mise en place d'un système de connexion multi-rôles robuste (boutons radio) orientant vers des tableaux de bord spécifiques (Client Final, Analyste Qualité, Responsable d'Exploitation).
*   **Interconnexion avec FastAPI :** Le frontend communique désormais avec succès avec l'API Unique pour la soumission des prédictions, le téléversement des fiches laboratoires (OCR) et la création de nouveaux clients.

#### 8. Tests et Intégration Continue (CI)
*   **Suite de tests PyTest :** Le projet intègre une couverture de tests automatisés structurée en trois niveaux :
    *   `test_unit.py` (Validation des garde-fous OMS et des schémas Pydantic).
    *   `test_functionnal.py` (Validation du scénario de bout-en-bout avec intégration BDD).
    *   `test_non_regression.py` (Vérification des performances ML par rapport aux seuils critiques).
*   **Intégration Continue (CI) :** Les GitHub Actions (`ci.yml`) sont configurées et s'exécutent automatiquement à chaque push sur le dépôt, garantissant la stabilité du code.

#### 9. Supervision, Monitoring & Gestion d'Incidents (MLOps)
*   **Observabilité :** Exposition de la route `/metrics` sur l'API et implémentation du client Prometheus.
*   **Tableau de Bord RED :** Création d'un dashboard Grafana surveillant en temps réel les requêtes par seconde (Rate), le taux d'erreurs 5xx (Errors) et la latence au 95ème centile (Duration).
*   **Résilience OCR :** Isolement de la panne du service externe empêchant la propagation de l'erreur (éviter un pic 5xx). L'incident est tracé via des logs JSON structurés et documenté formellement dans `docs/incidents/incident_ocr.md`.

#### 10. Backlog Technique Restant
*   ~~**Audit Trail & Monitoring (Priorité 1) :** Étendre l'exploitation des journaux de la table action_logs pour tracer l'utilisation des clés API et les temps de réponse sur l'interface d'Exploitation.~~ **[Terminé : Couvert par Prometheus/Grafana et le Dashboard RED]**
*   **Nettoyage final (Priorité 2) :** Unifier les documentations et le README pour le rendu final.
*   **Déploiement continu - CD (Bonus) :** Étendre le pipeline `.github/workflows/ci.yml` pour automatiser le build des images Docker ou le déploiement.