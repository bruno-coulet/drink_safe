import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification

# 1. On connecte Python au conteneur Docker (port 5000)
mlflow.set_tracking_uri("http://127.0.0.1:5000")

# 2. On crée l'expérience avec le nom exact demandé par le sujet
EXPERIMENT_NAME = "experiment_water_quality"
mlflow.set_experiment(EXPERIMENT_NAME)

print(f"🚀 Expérience '{EXPERIMENT_NAME}' initialisée sur le serveur Docker.")

# 3. Un "Faux Run" rapide pour valider que tout le pipeline fonctionne
# (Ton binôme viendra y greffer ses vrais modèles plus tard)
X, y = make_classification(n_samples=100, n_features=9, random_state=42)

with mlflow.start_run(run_name="baseline_test_docker"):
    # Enregistrement de faux paramètres et métriques pour tester l'UI
    mlflow.log_param("model_type", "LogisticRegression")
    mlflow.log_metric("accuracy", 0.85)
    
    # Entraînement éclair
    model = LogisticRegression()
    model.fit(X, y)
    
    # Enregistrement du modèle dans le registre d'artéfacts du conteneur
    mlflow.sklearn.log_model(
        sk_model=model, 
        artifact_path="model",
        registered_model_name="WaterPotabilityBaseline"
    )
    
    print("✅ Run de test enregistré avec succès dans Docker !")