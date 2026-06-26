"""
-------------------------------------------------------------------------------
Projet : Drink safe
Composant : Endpoints de Prédiction et Inférence IA
Description : Gestion des requêtes de classification de la potabilité,
              application des règles métiers de l'OMS, inférence mono-modèle,
              comparaison des 4 modèles (consensus), enrichissement d'un
              prélèvement existant par son ID, et traçabilité SQL.
-------------------------------------------------------------------------------
"""

from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import settings
from src.dependencies.auth import get_current_client

import mlflow.sklearn
from mlflow.tracking import MlflowClient

router = APIRouter(prefix="/predict", tags=["Inférence & Modèle IA"])

# Catalogue des modèles exposés (doit correspondre aux clés de src.models.get_models)
MODELES_DISPONIBLES: List[str] = [
    "LogisticRegression",
    "RandomForestClassifier",
    "XGBClassifier",
    "MLPClassifier",
]


class WaterSample(BaseModel):
    """Caractéristiques physico-chimiques d'un échantillon d'eau."""
    ph: float = Field(..., description="Potentiel Hydrogène (0.0 - 14.0)")
    Hardness: float = Field(..., description="Dureté de l'eau en mg/L")
    Solids: float = Field(..., description="Total des solides dissous en ppm")
    Chloramines: float = Field(..., description="Concentration en chloramines en ppm")
    Sulfate: float = Field(..., description="Concentration en sulfates en mg/L")
    Conductivity: float = Field(..., description="Conductivité électrique en μS/cm")
    Organic_carbon: float = Field(..., description="Carbone organique total en ppm")
    Trihalomethanes: float = Field(..., description="Concentration en trihalométhanes en ppm")
    Turbidity: float = Field(..., description="Turbidité de l'eau en NTU")
    observations: Optional[str] = Field(None, description="Note contextuelle optionnelle")


class PredictionRequest(WaterSample):
    """Demande d'inférence ciblant un modèle précis."""
    model_choice: str = Field(..., description="Nom de la classe de l'algorithme (ex: LogisticRegression)")


def _garde_fou_oms(payload: WaterSample) -> Optional[str]:
    """Retourne la raison d'un rejet sanitaire OMS, ou None si l'échantillon est conforme."""
    if payload.ph < 6.5 or payload.ph > 8.5:
        return "pH hors des limites permissibles de l'OMS (6.5 - 8.5)."
    if payload.Turbidity > 5.0:
        return "Turbidité supérieure à la recommandation maximale de l'OMS (5.0 NTU)."
    if payload.Chloramines > 4.0:
        return "Concentration en chloramines supérieure au seuil de sécurité (4.0 mg/L)."
    if payload.Trihalomethanes > 80.0:
        return "Taux de trihalométhanes supérieur au seuil de sécurité (80.0 ppm)."
    return None


def _charger_modele(model_choice: str) -> Tuple[Any, str]:
    """Récupère un modèle du cache RAM, ou le charge à la volée depuis MLflow (lazy loading).

    Args:
        model_choice (str): Nom de l'algorithme (clé de get_models).

    Returns:
        Tuple[Any, str]: L'instance du modèle et sa version.

    Raises:
        HTTPException: 503 si le modèle est introuvable ou non chargeable.
    """
    from src.api import ml_models, ml_model_versions

    model = ml_models.get(model_choice)
    if model is not None:
        return model, ml_model_versions.get(model_choice, "inconnue")

    print(f"[Lazy Load] Modèle '{model_choice}' absent du cache. Recherche de la dernière version...")
    try:
        client = MlflowClient()
        nom_registre = f"WaterModel_{model_choice}"
        versions = client.search_model_versions(f"name='{nom_registre}'")
        if not versions:
            raise ValueError("Aucune version enregistrée trouvée.")
        derniere_version = max(int(v.version) for v in versions)
        model_uri = f"models:/{nom_registre}/{derniere_version}"
        model = mlflow.sklearn.load_model(model_uri)
        ml_models[model_choice] = model
        ml_model_versions[model_choice] = str(derniere_version)
        print(f"[Lazy Load] ✓ {nom_registre} (v{derniere_version}) mis en cache.")
        return model, str(derniere_version)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de charger le modèle '{model_choice}' : {str(e)}"
        )


def _inferer(model: Any, payload: WaterSample) -> Tuple[int, Optional[float]]:
    """Exécute l'inférence d'un modèle sur un échantillon.

    Returns:
        Tuple[int, Optional[float]]: La prédiction (0/1) et la probabilité d'être potable.
    """
    raw_features = payload.model_dump()
    raw_features.pop("observations", None)
    raw_features.pop("model_choice", None)

    df_input = pd.DataFrame([raw_features])
    potability_result: int = int(model.predict(df_input)[0])

    score_potabilite: Optional[float] = None
    if hasattr(model, "predict_proba"):
        classes = list(model.classes_)
        proba = model.predict_proba(df_input)[0]
        if 1 in classes:
            score_potabilite = round(float(proba[classes.index(1)]), 4)

    return potability_result, score_potabilite


def _comparer_modeles(payload: WaterSample) -> Dict[str, Any]:
    """Applique le garde-fou OMS puis les 4 modèles, sans rien persister.

    La persistance est laissée à l'appelant (INSERT pour une saisie directe,
    UPDATE pour l'enrichissement d'un prélèvement existant).

    Returns:
        Dict[str, Any]: consensus, comptage des votes, détail par modèle et la
        chaîne `model_ver` à stocker en base.
    """
    raison_rejet = _garde_fou_oms(payload)
    if raison_rejet:
        return {
            "prediction_consensus": 0,
            "status_consensus": "Non Potable",
            "votes_potable": 0,
            "votes_total": 0,
            "decision_reason": f"Rejet automatique par garde-fou : {raison_rejet}",
            "details": [],
            "model_ver": "Garde-fou OMS",
        }

    details: List[Dict[str, Any]] = []
    for nom in MODELES_DISPONIBLES:
        model, version_modele = _charger_modele(nom)
        pred, score = _inferer(model, payload)
        details.append({
            "model": nom,
            "prediction": pred,
            "status": "Potable" if pred == 1 else "Non Potable",
            "score_potabilite": score,
            "model_version": version_modele,
        })

    votes_potable: int = sum(d["prediction"] for d in details)
    votes_total: int = len(details)
    # Vote majoritaire ; égalité -> principe de précaution (Non Potable)
    prediction_consensus: int = 1 if votes_potable > votes_total / 2 else 0

    return {
        "prediction_consensus": prediction_consensus,
        "status_consensus": "Potable" if prediction_consensus == 1 else "Non Potable",
        "votes_potable": votes_potable,
        "votes_total": votes_total,
        "decision_reason": None,
        "details": details,
        "model_ver": f"Consensus {votes_potable}/{votes_total} modeles",
    }


@router.post("/", status_code=status.HTTP_200_OK)
def executer_prediction(
    payload: PredictionRequest,
    client_id: str = Depends(get_current_client)
) -> Dict[str, Any]:
    """Arbitre la potabilité d'un échantillon via garde-fou OMS puis un modèle choisi.

    Args:
        payload (PredictionRequest): Caractéristiques physico-chimiques + modèle ciblé.
        client_id (str): Identifiant du client authentifié par clé API (RGPD).

    Returns:
        Dict[str, Any]: Prédiction (0/1), score, modèle et version utilisés.
    """
    raison_rejet = _garde_fou_oms(payload)
    if raison_rejet:
        _sauvegarder_prelevement_en_bdd(client_id, payload, prediction=0, model_ver="Garde-fou OMS")
        return {
            "prediction": 0,
            "status": "Non Potable",
            "model_used": "Business Rules OMS",
            "decision_reason": f"Rejet automatique par garde-fou : {raison_rejet}",
            "score_potabilite": None
        }

    model, version_modele = _charger_modele(payload.model_choice)
    try:
        potability_result, score_potabilite = _inferer(model, payload)
        _sauvegarder_prelevement_en_bdd(
            client_id, payload, potability_result, f"{payload.model_choice}_v{version_modele}"
        )
        return {
            "prediction": potability_result,
            "status": "Potable" if potability_result == 1 else "Non Potable",
            "model_used": payload.model_choice,
            "model_version": version_modele,
            "score_potabilite": score_potabilite
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du calcul de la prédiction : {str(e)}"
        )


@router.post("/all", status_code=status.HTTP_200_OK)
def executer_prediction_multi(
    payload: WaterSample,
    client_id: str = Depends(get_current_client)
) -> Dict[str, Any]:
    """Compare les 4 modèles sur un échantillon saisi et persiste un consensus (nouvelle ligne).

    Args:
        payload (WaterSample): Caractéristiques physico-chimiques de l'échantillon.
        client_id (str): Identifiant du client authentifié par clé API (RGPD).

    Returns:
        Dict[str, Any]: Consensus, comptage des votes et détail par modèle.
    """
    try:
        resultat = _comparer_modeles(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du calcul comparatif : {str(e)}"
        )

    _sauvegarder_prelevement_en_bdd(
        client_id, payload, resultat["prediction_consensus"], resultat["model_ver"]
    )
    return {k: v for k, v in resultat.items() if k != "model_ver"}


@router.post("/from-prelevement/{prelevement_id}", status_code=status.HTTP_200_OK)
def executer_prediction_from_prelevement(
    prelevement_id: int,
    client_id: str = Depends(get_current_client)
) -> Dict[str, Any]:
    """Enrichit un prélèvement existant (ex. issu de l'OCR) avec la prédiction des 4 modèles.

    Charge les mesures du prélèvement appartenant au client, applique le garde-fou OMS
    et les 4 modèles, puis MET À JOUR la ligne (aucune nouvelle ligne créée).

    Args:
        prelevement_id (int): Identifiant du prélèvement à enrichir.
        client_id (str): Identifiant du client authentifié par clé API (RGPD).

    Returns:
        Dict[str, Any]: Consensus, détail par modèle et identifiant du prélèvement.

    Raises:
        HTTPException: 404 si le prélèvement n'existe pas ou n'appartient pas au client.
    """
    payload = _charger_prelevement(prelevement_id, client_id)
    try:
        resultat = _comparer_modeles(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du calcul comparatif : {str(e)}"
        )

    _maj_prediction_prelevement(
        prelevement_id, client_id, resultat["prediction_consensus"], resultat["model_ver"]
    )
    reponse = {k: v for k, v in resultat.items() if k != "model_ver"}
    reponse["prelevement_id"] = prelevement_id
    return reponse


def _charger_prelevement(prelevement_id: int, client_id: str) -> WaterSample:
    """Charge les mesures d'un prélèvement appartenant au client (isolation RGPD)."""
    query: str = """
    SELECT ph, hardness, solids, chloramines, sulfate, conductivity,
           organic_carbon, trihalomethanes, turbidity, observations
    FROM prelevements
    WHERE id = %s AND client_id = %s;
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (prelevement_id, client_id))
                row = cursor.fetchone()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la lecture du prélèvement : {str(e)}"
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prélèvement {prelevement_id} introuvable pour ce client."
        )

    return WaterSample(
        ph=row["ph"], Hardness=row["hardness"], Solids=row["solids"],
        Chloramines=row["chloramines"], Sulfate=row["sulfate"], Conductivity=row["conductivity"],
        Organic_carbon=row["organic_carbon"], Trihalomethanes=row["trihalomethanes"],
        Turbidity=row["turbidity"], observations=row["observations"],
    )


def _maj_prediction_prelevement(
    prelevement_id: int,
    client_id: str,
    prediction: int,
    model_ver: str
) -> None:
    """Met à jour la prédiction d'un prélèvement existant (UPDATE, pas d'INSERT)."""
    query: str = """
    UPDATE prelevements
    SET prediction_potability = %s, model_version = %s
    WHERE id = %s AND client_id = %s;
    """
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (prediction, model_ver, prelevement_id, client_id))
                conn.commit()
    except Exception as e:
        print(f"⚠️ Alerte MLOps : Impossible de mettre à jour la prédiction du prélèvement : {e}")


def _sauvegarder_prelevement_en_bdd(
    client_id: str,
    payload: WaterSample,
    prediction: int,
    model_ver: str
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
                cursor.execute(query_insert, (
                    client_id, payload.ph, payload.Hardness, payload.Solids,
                    payload.Chloramines, payload.Sulfate, payload.Conductivity,
                    payload.Organic_carbon, payload.Trihalomethanes,
                    payload.Turbidity, prediction, model_ver, payload.observations
                ))
                conn.commit()
    except Exception as e:
        print(f"Alerte MLOps : Impossible d'historiser le prélèvement en BDD : {e}")
