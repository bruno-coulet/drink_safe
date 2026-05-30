# Gestion des Incidents : Désynchronisation d'état MLOps

Ce document décrit un scénario d'incident rencontré lors du passage en production de l'API Unique, son diagnostic et sa résolution.

## L'Incident : Le "State Mismatch" (Désynchronisation)

**Symptôme :** Lors d'une requête de prédiction sur l'endpoint `/predict`, l'API renvoie une erreur 503 : 
`{"detail":"Impossible de charger le modèle 'LogisticRegression' : No such file or directory: '/app/artifacts/1/.../artifacts/model/.'"}`

**Diagnostic en 3 étapes :**
1. **L'API (FastAPI) démarre avant l'entraînement :** Si l'API cherche les modèles dans son dictionnaire `ml_models` au démarrage (via le `lifespan`), elle trouve un registre vide.
2. **Le chargement statique échoue :** Si l'on hardcode la requête MLflow pour chercher la version `1` du modèle (`models:/WaterModel/1`), l'API plantera dès que le modèle sera ré-entraîné (Version 2) car l'ancien fichier `.pkl` n'existera plus sur le disque.
3. **Le conteneur égoïste :** Le conteneur `mlops-training` s'exécutait et enregistrait ses artefacts dans son propre système de fichiers éphémère, sans les partager avec l'API, car le volume `./mlruns_artifacts` n'était pas monté sur ce conteneur.

---

## La Résolution

La correction a nécessité une double intervention : une modification de l'infrastructure (Docker) et une mise à jour du design pattern dans l'API (Code).

### 1. Correction de l'infrastructure (`docker-compose.yml`)
Il a fallu s'assurer que le conteneur d'entraînement écrit les fichiers binaires (`.pkl`) dans le même volume partagé que MLflow et l'API, et ajouter une temporisation pour éviter que le script ne plante avant le démarrage du serveur MLflow.

```yaml
  mlops-training:
    # ...
    volumes:
      - ./data:/app/data
      - ./mlruns_artifacts:/app/artifacts  # Résolution de l'isolement des fichiers
    command: sh -c "echo 'Attente initialisation MLflow...' && sleep 15 && python -m src.experiment"

```

### 2. Implémentation du Lazy Loading Dynamique (Code)

Plutôt que de charger les modèles au démarrage de l'API, on utilise le pattern **Lazy Loading** (Cache-Aside) avec une résolution dynamique de la dernière version.

*Fichier modifié : `src/routes/predictions.py*`

```python
    # ACCÈS AU REGISTRE DE MODÈLES (Lazy Loading MLOps Dynamique)
    from src.api import ml_models
    model = ml_models.get(payload.model_choice)
    
    # Si le modèle n'est pas en mémoire (Cache Miss), on cherche la dernière version à la volée
    if not model:
        print(f"[Lazy Load] Modèle '{payload.model_choice}' non trouvé en cache. Recherche de la dernière version...")
        try:
            from mlflow.tracking import MlflowClient
            import mlflow.sklearn
            
            client = MlflowClient()
            nom_registre = f"WaterModel_{payload.model_choice}"
            
            # Récupération de toutes les versions enregistrées
            versions = client.search_model_versions(f"name='{nom_registre}'")
            if not versions:
                raise ValueError("Aucune version enregistrée trouvée.")
                
            # Identification de la version la plus récente
            derniere_version = max([int(v.version) for v in versions])
            model_uri = f"models:/{nom_registre}/{derniere_version}"
            
            print(f"[Lazy Load] Téléchargement de la version {derniere_version} depuis {model_uri}...")
            model = mlflow.sklearn.load_model(model_uri)
            
            # Mise en cache (RAM) pour accélérer les prochaines requêtes
            ml_models[payload.model_choice] = model
            print(f"[Lazy Load] ✓ {nom_registre} (v{derniere_version}) mis en cache avec succès !")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Impossible de charger le modèle '{payload.model_choice}' : {str(e)}"
            )

```

## Conclusion et Bénéfices

* **Résilience totale :** L'API peut démarrer de façon asynchrone, même avant que les modèles ne soient entraînés.
* **Mise à jour à chaud (Zero Downtime) :** Si un modèle est ré-entraîné (V2), il suffit de vider le dictionnaire `ml_models` pour que la requête suivante télécharge automatiquement la nouvelle version sans redémarrer le conteneur API.
* **Synchronisation Registre/Stockage :** MLflow, PostgreSQL et le volume local partagent désormais la même source de vérité.
