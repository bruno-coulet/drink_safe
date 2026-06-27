# État d'Avancement Technique - Projet Waterflow 2

Ce document sert de snapshot d'état d'avancement pour le projet Waterflow 2.

## 1. Architecture et Services
Tous les conteneurs sont configurés et fonctionnels sous Docker Compose :
- `postgres` (Port 5432) : Base de données relationnelle globale.
- `mlflow` (Port 5000) : Registre de modèles.
- `api` (Port 8000) : API FastAPI unifiée (Data, Predict, OCR, Monitoring).
- `mlops-training` : Pipeline éphémère d'entraînement et évaluation.
- Interface : L'IHM Flask tourne localement (Port 5001) et s'adresse à `localhost:8000`.

## 2. Historique des Incidents & Bogues Résolus
* **Incident A (Crash Inférence 503) :** Résolu via l'implémentation du Mock de la librairie `mlflow` dans les tests fonctionnels (PyTest), permettant la validation CI sans dépendance au volume Docker absolu. En production, le modèle est chargé dynamiquement (Lazy Loading).
* **Biais de Modélisation (Prédiction) :** Le bug logique de comptage du consensus (somme des classes au lieu du comptage des occurrences) dans `predictions.py` a été corrigé. Le consensus est désormais strict et mathématiquement valide.

## 3. Conformité et Modélisation (Base de Données)
* Le schéma applicatif a été fusionné sous PostgreSQL.
* L'isolation multi-tenant est active via l'en-tête `X-API-Key`.
* Un middleware journalise les temps d'exécution et anonymise l'ID client pour la table `action_logs`.

## 4. Statut du Frontend Flask
* L'interface graphique a été entièrement développée et connectée aux différents modules de l'API.

## 5. Backlog Technique Restant (Mise à jour)
- [x] **Intégration continue (CI) :** Scripts PyTest corrigés à 100% (Mock MLOps), pipeline `.github/workflows/ci.yml` opérationnelle au prochain push.
- [x] **Audit Trail & Monitoring :** Routes implémentées (`/api/monitoring/stats` et `/logs`) pour la restitution des KPI (temps de réponse, taux d'erreurs) au Responsable d'Exploitation.
- [ ] **Déploiement continu (CD) :** [Optionnel] Configurer le pipeline GitHub Actions pour automatiser le build et le push de l'image sur DockerHub ou le déploiement sur VPS.
- [ ] **Nettoyage final :** Relecture globale de la documentation et du README.md pour la sou
