État d'Avancement Technique - Projet Waterflow 2
Ce document sert de snapshot d'état d'avancement pour le projet Waterflow 2. Il est destiné à être chargé en début de session (avec CLAUDE.md) pour économiser des tokens et donner immédiatement le contexte technique exact et à jour de l'architecture, des bogues résolus, des optimisations de modèles et du backlog.

1. Simplification de l'Architecture & Noms des Conteneurs
Tous les conteneurs du projet ont été renommés pour simplifier l'infrastructure, homogénéiser les configurations réseau et faciliter l'exploitation.

Service Docker	Nouveau Nom Conteneur	Image / Base	Ports Exposés	Rôle
Base de Données	postgres	postgres:16-alpine	5432:5432	SGBD PostgreSQL (métadonnées MLflow + données métier)
Serveur MLOps	mlflow	python:3.12-slim	5000:5000	Serveur de Tracking & Registre de Modèles MLflow
API Backend	api	waterflow-api (Custom)	8000:8000	API FastAPI (Modules Data, Model, OCR unifiés)
Pipeline MLOps	mlops-training	waterflow-mlops-training	Aucun (Éphémère)	Pipeline d'entraînement et d'évaluation des modèles
Règle réseau cruciale pour le Frontend Flask : Le frontend Flask tourne de manière isolée sur la machine hôte (WSL2) et non dans Docker. Il ne peut pas résoudre le nom d'hôte interne Docker http://api:8000. Pour interroger l'API FastAPI, Flask doit obligatoirement utiliser l'adresse de rebouclage locale mappée sur l'hôte : http://127.0.0.1:8000 (ou http://localhost:8000).

2. Historique des Incidents & Bogues Résolus
A. Crash au démarrage de l'API (python-multipart manquant)
Symptôme : Le conteneur api s'arrêtait brusquement au démarrage et bouclait indéfiniment en statut Restarting. Les logs Docker affichaient : Form data requires "python-multipart" to be installed.
Cause : La route POST /api/ocr/lab-report reçoit un fichier de rapport labo (image ou PDF) via un téléversement multipart. FastAPI nécessite impérativement la bibliothèque python-multipart pour ce type de parsing, mais celle-ci n'était pas déclarée.
Résolution : Ajout de la dépendance via uv add python-multipart et reconstruction de l'image de l'API.
B. Erreurs de Résolution DNS (Anciens noms de conteneurs)
Symptôme : Le script de l'entraînement et l'API principale n'arrivaient pas à se connecter à PostgreSQL ou à MLflow. Les logs indiquaient : socket.gaierror: [Errno -2] Name or service not known.
Cause : L'API et l'entraînement ciblaient l'ancienne adresse postgres-db ou mlflow-back. De plus, le fichier de configuration locale .env de la machine hôte écrasait les valeurs par défaut.
Résolution : Alignement de src/config.py (pointant vers @postgres:5432) et mise à jour de la variable MLFLOW_TRACKING_URI=http://mlflow:5000 dans le fichier .env.
C. Blocage du DNS Rebinding (Erreur HTTP 403)
Symptôme : Lors d'une prédiction, le lazy loading échouait avec une erreur 403 : Invalid Host header - possible DNS rebinding attack detected.
Cause : Uvicorn blocks les requêtes internes Docker si les en-têtes d'hôtes ne correspondent pas au nom de domaine attendu. Le middleware de parade interceptait les requêtes mais ciblait encore l'ancien nom de conteneur.
Résolution : Remplacement de mlflow-back par mlflow dans le middleware de surcharge des en-têtes (dans src/config.py).
3. Alignement de la Modélisation & Équilibrage des Classes
A. Biais de Potabilité et Traitement du Déséquilibre (models.py)
Le dataset Kaggle comportant environ 61 % de données non-potables (1998 non-potables contre 1278 potables), les modèles présentaient un biais systématique vers la prédiction majoritaire "Non Potable".

Correctif Modèles Classiques : Ajout du paramètre class_weight='balanced' pour la Régression Logistique et le Random Forest Classifier afin d'ajuster pénalités et seuils.
Correctif XGBoost : Alignement du modèle de gradient boosting via l'ajout du paramètre spécifique scale_pos_weight=1.56 (calculé sur le ratio d'imquilibre exact des classes 1998/1278) dans models.py.
B. Le "Happy Path" de Conformité OMS
Afin de surmonter la barrière réglementaire de l'OMS (qui élimine d'office les échantillons ayant des Chloramines > 4.0 mg/L, alors que la moyenne brute du dataset d'origine est de 7.1 mg/L), les valeurs d'analyse par défaut de l'IHM ont été recalibrées sur la ligne 666 du dataset, échantillon parfaitement potable et conforme :

pH : 7.04 (seuil : [6.5 - 8.5])
Chloramines : 2.58 mg/L (seuil : < 4.0 mg/L)
Turbidité : 2.00 NTU (seuil : < 5.0 NTU)
Sulfate : 365.08 mg/L
Trihalométhanes : 48.25 ppm (seuil : < 80 ppm)
4. Optimisation de l'Entraînement & Métriques MLOps Avancées (experiment.py)
Pour professionnaliser l'évaluation du modèle et garantir l'auditabilité des expériences directement sous l'interface MLflow, 4 améliorations méthodologiques majeures ont été implémentées :

A. Pondération de l'entraînement du Perceptron (MLP)
Mécanisme : Le classifieur MLP ne supportant pas nativement le paramètre class_weight, la pondération a été déportée au niveau du calcul des échantillons d'entraînement.
Implémentation : Calcul de compute_sample_weight('balanced', y_train) et injection dynamique via les arguments du pipeline scikit-learn (model__sample_weight=weights) lors du .fit(). Un système de détection automatique applique ce support de sample_weight de manière générique sur l'ensemble du catalogue de modèles.
B. Validation Croisée Stratifiée (5 Folds)
Bénéfice : Élimine les biais d'évaluation ponctuels et apporte une mesure de stabilité statistique (variance).
Implémentation : Calcul d'une validation croisée stratifiée sur 5 segments de l'ensemble d'entraînement X_train. Publication automatique dans MLflow des métriques de synthèse de la distribution : la moyenne (cv_mean_*) et l'écart-type (cv_std_*) pour l'Accuracy, le F1-score, la Précision et le Rappel.
C. Intégration de l'AUC-PR (Courbe Précision-Rappel)
Bénéfice : Métrique d'évaluation beaucoup plus rigoureuse que le ROC-AUC sur les données déséquilibrées, car la courbe Precision-Recall se concentre sur la classe minoritaire et ne masque pas l'impact des Faux Positifs.
Implémentation : Calcul et journalisation systématique de la métrique average_precision_score (AUC-PR) pour chaque run d'entraînement.
D. Journalisation de la Matrice de Confusion
Bénéfice : Permet à l'analyste qualité d'interpréter instantanément la répartition des erreurs du modèle (Faux Positifs vs Faux Négatifs) sans avoir à charger localement les données ou recréer un script d'analyse.
Implémentation : Extraction et écriture directe dans MLflow des métriques d'erreur de base : Vrais Positifs (TP), Vrais Négatifs (TN), Faux Positifs (FP) et Faux Négatifs (FN).
5. Statut du Frontend Flask
L'interface graphique est développée sous Flask (Port 5001) sur la machine hôte.

Mode Debug : Flask doit s'exécuter en mode debug (--debug ou debug=True) pour rafraîchir dynamiquement les templates HTML (front/templates/) sans conserver de cache obsolète.
Routage WSL2/Docker : Flask interroge l'API via http://localhost:8000 (et non http://api:8000).
6. Backlog Technique Restant
[ ] Intégration continue (CI/CD) : Valider le fonctionnement automatique du fichier .github/workflows/ci.yml contenant l'environnement uv et la suite de tests PyTest (test_unit.py, test_functionnal.py, test_non_regression.py).
[ ] Audit Trail & Monitoring : Étendre l'exploitation des journaux de la table action_logs pour tracer l'utilisation des clés API et les temps de réponse.
[ ] Nettoyage final : Finaliser l'unification des références de conteneurs dans le README.md et les livrables d'architecture associés.
