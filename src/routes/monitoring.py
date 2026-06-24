"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Route de Monitoring et Supervision (Responsable d'Exploitation)
Description : Expose les journaux d'accès (action_logs) et les métriques
              agrégées pour la supervision de l'infrastructure.
Endpoints :
    GET /api/monitoring/logs (journaux filtrables)
    GET /api/monitoring/metrics (agrégats 24h : taux d'erreur, durée moyenne, top endpoints)

-------------------------------------------------------------------------------
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
import psycopg2

from src.config import settings
from src.dependencies.auth import get_current_client

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Supervision"])


@router.get("/logs", response_model=List[Dict[str, Any]])
def lister_logs(
    limite: int = Query(default=100, ge=1, le=500),
    status_code: Optional[int] = Query(default=None),
    endpoint: Optional[str] = Query(default=None),
    _: str = Depends(get_current_client),
) -> List[Dict[str, Any]]:
    """Retourne les journaux d'accès filtrables pour la supervision d'exploitation.

    Args:
        limite: Nombre maximum d'entrées retournées (1-500).
        status_code: Filtre optionnel sur le code HTTP (ex: 401, 500).
        endpoint: Filtre optionnel sur le chemin de la route (ex: /api/predict).

    Returns:
        Liste des entrées de journaux triées par date décroissante.
    """
    conditions: List[str] = []
    params: List[Any] = []

    if status_code is not None:
        conditions.append("status_code = %s")
        params.append(status_code)
    if endpoint is not None:
        conditions.append("endpoint ILIKE %s")
        params.append(f"%{endpoint}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limite)

    query = f"""
        SELECT id, client_id, endpoint, method, status_code,
               execution_duration_ms, execute_le
        FROM action_logs
        {where_clause}
        ORDER BY execute_le DESC
        LIMIT %s;
    """

    with psycopg2.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            colonnes = [desc[0] for desc in cursor.description]
            lignes = cursor.fetchall()

    return [dict(zip(colonnes, ligne)) for ligne in lignes]


@router.get("/metrics", response_model=Dict[str, Any])
def metriques_agregees(
    _: str = Depends(get_current_client),
) -> Dict[str, Any]:
    """Retourne les métriques agrégées de l'infrastructure (dernières 24h).

    Returns:
        Dictionnaire contenant total requêtes, taux d'erreur, durée moyenne,
        et répartition par endpoint.
    """
    query_global = """
        SELECT
            COUNT(*)                                        AS total_requetes,
            ROUND(AVG(execution_duration_ms)::numeric, 1)  AS duree_moyenne_ms,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) AS total_erreurs,
            COUNT(DISTINCT client_id)                       AS clients_actifs
        FROM action_logs
        WHERE execute_le >= NOW() - INTERVAL '24 hours';
    """

    query_par_endpoint = """
        SELECT endpoint, COUNT(*) AS nb_appels,
               ROUND(AVG(execution_duration_ms)::numeric, 1) AS duree_moy_ms
        FROM action_logs
        WHERE execute_le >= NOW() - INTERVAL '24 hours'
        GROUP BY endpoint
        ORDER BY nb_appels DESC
        LIMIT 10;
    """

    with psycopg2.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query_global)
            row = cursor.fetchone()
            total, duree_moy, erreurs, clients = row if row else (0, 0, 0, 0)

            cursor.execute(query_par_endpoint)
            cols = [d[0] for d in cursor.description]
            top_endpoints = [dict(zip(cols, r)) for r in cursor.fetchall()]

    taux_erreur = round((erreurs / total * 100), 1) if total else 0.0

    return {
        "periode": "24 dernières heures",
        "total_requetes": total,
        "duree_moyenne_ms": duree_moy,
        "total_erreurs": erreurs,
        "taux_erreur_pct": taux_erreur,
        "clients_actifs": clients,
        "top_endpoints": top_endpoints,
    }
