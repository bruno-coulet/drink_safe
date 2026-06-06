"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Endpoints de Prédiction et Inférence IA
Description : Gestion des requêtes de classification de la potabilité,
              application des règles métiers de l'OMS et traçabilité SQL.
-------------------------------------------------------------------------------
"""

from typing import Any, Dict, Optional

import pandas as pd
import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.config import settings
from src.dependencies.auth import get_current_client

router = APIRouter(prefix="/predict", tags=["Inférence & Modèle IA"])


class PredictionRequest(BaseModel):
    """Schéma de validation pour une demande d'inférence en temps réel."""

    model_choice: str = Field(
        ..., description="Nom de la classe de l'algorithme (ex: LogisticRegression)"
    )
    ph: float = Field(..., description="Potentiel Hydrogène (0.0 - 14.0)")
    Hardness: float = Field(..., description="Dureté de l'eau en mg/L")
    Solids: float = Field(..., description="Total des solides dissous en ppm")
    Chloramines: float = Field(..., description="Concentration en chloramines en ppm")
    Sulfate: float = Field(..., description="Concentration en sulfates en mg/L")
    Conductivity: float = Field(..., description="Conductivité électrique en μS/cm")
    Organic_carbon: float = Field(..., description="Carbone organique total en ppm")
    Trihalomethanes: float = Field(
        ..., description="Concentration en trihalométhanes en μg/L"
    )
    Turbidity: float = Field(..., description="Turbidité de l'eau en NTU")
    observations: Optional[str] = Field(
        None, description="Note contextuelle optionnelle"
    )


@router.post("/", status_code=status.HTTP_200_OK)
def executer_prediction(
    payload: PredictionRequest, client_id: str = Depends(get_current_client)
) -> Dict[str, Any]:
    """Arbitre la potabilité d'un échantillon via garde-fous OMS et modèles MLflow.

    Args:
        payload (PredictionRequest): Caractéristiques physico-chimiques soumises.
        client_id (str): Identifiant du client authentifié par clé API (RGPD).

    Returns:
        Dict[str, Any]: Résultat de la potabilité (0 ou 1) et métadonnées du modèle.
    """
    # 1. COUCHE GARDE-FOU MÉTIER (Business Rules basées sur les normes OMS)
    raison_rejet: Optional[str] = None

    if payload.ph < 6.5 or payload.ph > 8.5:
        raison_rejet = "pH hors des limites permissibles de l'OMS (6.5 - 8.5)."
    elif payload.Turbidity > 5.0:
        raison_rejet = (
            "Turbidité supérieure à la recommandation maximale de l'OMS (5.0 NTU)."
        )
    elif payload.Chloramines > 4.0:
        raison_rejet = (
            "Concentration en chloramines supérieure au seuil de sécurité (4.0 mg/L)."
        )
    elif payload.Trihalomethanes > 80.0:
        raison_rejet = (
            "Taux de trihalométhanes supérieur au seuil de sécurité (80.0 ppm)."
        )

    if raison_rejet:
        # Enregistrement immédiat du rejet sanitaire en BDD pour archivage historique
        _sauvegarder_prelevement_en_bdd(
            client_id, payload, prediction=0, model_ver="Garde-fou OMS"
        )
        return {
            "prediction": 0,
            "status": "Non Potable",
            "model_used": "Business Rules OMS",
            "decision_reason": f"Rejet automatique par garde-fou : {raison_rejet}",
        }

    # 2. ACCÈS AU REGISTRE DE MODÈLES (Lazy Loading MLOps Dynamique)
    from src.api import ml_models

    model = ml_models.get(payload.model_choice)

    # Si le modèle n'est pas en mémoire, on cherche la dernière version à la volée
    if model is None:
        print(
            f"[Lazy Load] Modèle '{payload.model_choice}' non trouvé en mémoire. Recherche de la dernière version..."
        )
        try:
            import mlflow.sklearn
            from mlflow.tracking import MlflowClient

            client = MlflowClient()
            nom_registre = f"WaterModel_{payload.model_choice}"

            # On récupère toutes les versions enregistrées pour ce modèle
            versions = client.search_model_versions(f"name='{nom_registre}'")
            if not versions:
                raise ValueError("Aucune version enregistrée trouvée.")

            # On identifie le numéro de la version la plus récente
            derniere_version = max([int(v.version) for v in versions])
            model_uri = f"models:/{nom_registre}/{derniere_version}"

            print(
                f"[Lazy Load] Téléchargement de la version {derniere_version} depuis {model_uri}..."
            )
            model = mlflow.sklearn.load_model(model_uri)

            # Mise en cache pour les prochaines requêtes
            ml_models[payload.model_choice] = model
            print(
                f"[Lazy Load] ✓ {nom_registre} (v{derniere_version}) mis en cache avec succès !"
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Impossible de charger le modèle '{payload.model_choice}' : {str(e)}",
            )

    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Le modèle '{payload.model_choice}' est indisponible pour le moment.",
        )

    # 3. EXÉCUTION DE L'INFÉRENCE MACHINE LEARNING
    try:
        raw_features = payload.model_dump()
        raw_features.pop("model_choice")
        raw_features.pop("observations")

        # Passage au format attendu par Scikit-Learn / XGBoost
        df_input = pd.DataFrame([raw_features])
        prediction = model.predict(df_input)
        potability_result: int = int(prediction[0])
        status_label: str = "Potable" if potability_result == 1 else "Non Potable"

        # Enregistrement de la décision finale du modèle ML en base de données
        version_utilisee: str = f"{payload.model_choice}_v1"
        _sauvegarder_prelevement_en_bdd(
            client_id, payload, potability_result, version_utilisee
        )

        return {
            "prediction": potability_result,
            "status": status_label,
            "model_used": payload.model_choice,
            "model_version": "1",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du calcul de la prédiction : {str(e)}",
        )


def _sauvegarder_prelevement_en_bdd(
    client_id: str, payload: PredictionRequest, prediction: int, model_ver: str
) -> None:
    """Fonction utilitaire privée pour persister l'analyse historique dans PostgreSQL."""
    query_insert: str = """
    INSERT INTO prelevements (
        client_id, provenance, ph, hardness, solids, chloramines,
        sulfate, conductivity, organic_carbon, trihalomethanes,
        turbidity, prediction_potability, model_version, observations
    ) VALUES (%s, 'Saisie', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query_insert,
                    (
                        client_id,
                        payload.ph,
                        payload.Hardness,
                        payload.Solids,
                        payload.Chloramines,
                        payload.Sulfate,
                        payload.Conductivity,
                        payload.Organic_carbon,
                        payload.Trihalomethanes,
                        payload.Turbidity,
                        prediction,
                        model_ver,
                        payload.observations,
                    ),
                )
                conn.commit()
    except Exception as e:
        print(f"⚠️ Alerte MLOps : Impossible d'historiser le prélèvement en BDD : {e}")
