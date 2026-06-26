# État d'Avancement Technique - Projet Waterflow 2

Ce document sert de snapshot d'état d'avancement pour le projet Waterflow 2. Il est destiné à être chargé en début de session pour donner immédiatement le contexte technique exact et à jour de l'architecture, des bogues résolus, des optimisations de modèles et du backlog.

## 1. Simplification de l'Architecture & Noms des Conteneurs

Tous les conteneurs du projet ont été renommés pour simplifier l'infrastructure, homogénéiser les configurations réseau et faciliter l'exploitation.

| Service Docker | Nouveau Nom Conteneur | Image / Base | Ports Exposés | Rôle |
| :--- | :--- | :--- | :--- | :--- |
| **Base de Données** | `postgres` | `postgres:16-alpine` | `5432:5432` | SGBD PostgreSQL (métadonnées MLflow + données métier) |
| **Serveur MLOps** | `mlflow` | `python:3.12-slim` | `5000:5000` | Serveur de Tracking & Registre de Modèles MLflow |
| **API Backend** | `api` | `waterflow-api` (Custom) | `8000:8000` | API FastAPI (Modules Data, Model, OCR unifiés) |
| **Pipeline MLOps** | `mlops-training` | `waterflow-mlops-training` | Aucun (Éphémère) | Pipeline d'entraînement et d'évaluation des modèles |

**Bonnes pratiques d'architecture appliquées :**
- **Centralisation des chemins :** `src/config.py` centralise tous les chemins du projet de manière dynamique via la bibliothèque `Pathlib` (`ROOT_DIR`).
- **Séparation des responsabilités (Code API vs ETL) :** Les scripts de préparation de données (`analysis_utils.py`, `cleaning_utils.py`) ont été isolés dans `scripts/dat_prep/` pour conserver un backend API pur et léger.
- **Sécurité et Injections :** Les mécanismes de vérification de clés API sont modularisés dans le dossier `src/dependencies/auth.py`.

*Règle réseau cruciale pour le Frontend Flask :* Le frontend Flask tourne de manière isolée sur la machine hôte (WSL2) et non dans Docker. Il ne peut pas résoudre le nom d'hôte interne Docker `http://api:8000`. Pour interroger l'API FastAPI, Flask doit obligatoirement utiliser l'adresse de rebouclage locale mappée sur l'hôte : `http://127.0.0.1:8000`.

## 2. Historique des Incidents & Bogues Résolus

**A. Crash au démarrage de l'API (python-multipart manquant)**
- **Cause :** L'API OCR a besoin de parser des formulaires multipart pour les fichiers PDF/Images.
- **Résolution :** Ajout de la dépendance via `uv add python-multipart`.

**B. Erreurs de Résolution DNS (Anciens noms de conteneurs)**
- **Résolution :** Alignement de `src/config.py` (pointant vers `@postgres:5432`) et mise à jour de la variable `MLFLOW_TRACKING_URI=http://mlflow:5000`.

**C. Blocage du DNS Rebinding (Erreur HTTP 403)**
- **Résolution :** Remplacement de `mlflow-back` par `mlflow` dans le middleware de surcharge des en-têtes.

**D. Avertissement CI/CD Github Actions (Node.js 20 deprecated)**
- **Symptôme :** Avertissements sur le workflow `ci.yml` en raison de l'obsolescence de Node.js 20 sur les serveurs GitHub.
- **Résolution :** Refactorisation des appels d'actions (`checkout`, `setup-python`, `setup-uv`) avec les tags de version majeure récents (`@v4`, `@v5`) pour forcer l'usage du moteur Node.js 24.

## 3. Alignement de la Modélisation & Équilibrage des Classes

**A. Biais de Potabilité et Traitement du Déséquilibre**
- Ajout de `class_weight='balanced'` pour les modèles classiques.
- Ajout de `scale_pos_weight=1.56` pour XGBoost.

**B. Le "Happy Path" de Conformité OMS**
Les valeurs par défaut de l'IHM ont été recalibrées sur l'échantillon parfait de la ligne 666 pour contourner les garde-fous stricts de l'OMS intégrés à l'API.

## 4. Optimisation de l'Entraînement & Métriques MLOps Avancées

Quatre améliorations méthodologiques majeures auditables sous MLflow :
1. **Pondération dynamique du Perceptron (MLP) :** Calcul manuel de `compute_sample_weight`.
2. **Validation Croisée Stratifiée (5 Folds) :** Injection dans MLflow des moyennes (`cv_mean_`) et écarts-types (`cv_std_`).
3. **Intégration de l'AUC-PR :** Journalisation de l'`average_precision_score`.
4. **Matrice de Confusion absolue :** Variables TN, TP, FN, FP remontées sans préfixe polluant (`cm_`).
5. **Stratégie de Données :** Le script d'entraînement charge dynamiquement le jeu de données standardisé (`water_std.csv`) pour les modèles linéaires (Régression Logistique, MLP) et le jeu brut imputé (`water_imputed.csv`) pour les arbres de décision.

## 5. Statut de l'API Ingestion OCR (Nouveau Composant)

- **Implémentation validée :** Le routeur `/ocr` est implémenté dans `src/routes/ocr.py` et intégré au point de montage principal de FastAPI.
- **Fonctionnement :** Il gère la réception des fichiers documentaires (UploadFile), l'interrogation du moteur externe distant (OCR.space), l'extraction du texte brut via expressions régulières pour isoler les mesures, et la création immédiate d'un prélèvement en base de données.

## 6. Statut du Frontend Flask

L'interface graphique est développée sous Flask (Port 5001) sur la machine hôte.
- **Mode Debug :** Doit s'exécuter avec `debug=True` pour rafraîchir les templates HTML.
- **Routage WSL2/Docker :** Interroge l'API via `http://localhost:8000`.

## 7. Backlog Technique Restant


- [x] **Intégration continue (CI/CD) :** Valider le fonctionnement de `.github/workflows/ci.yml` (corrigé sur Node 24) et la suite de tests unitaires/fonctionnels.
- [ ] **Audit Trail & Monitoring :** Finaliser l'exploitation des journaux de la table `action_logs` pour tracer l'utilisation des clés API et rendre la vue exploitable pour l'Analyste Qualité.
- [ ] **Nettoyage final :** Unifier les références de conteneurs dans le `README.md` et préparer la soutenance métier.

