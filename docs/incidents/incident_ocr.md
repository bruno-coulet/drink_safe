# Incident #001 - Panne du service externe OCR.space

**Date** : 2026-07-02 (Simulation d'incident)
**Sévérité** : Majeure (Fonctionnalité d'ingestion OCR totalement bloquée, entraînant des erreurs 504 puis un crash de l'interface client)
**Auteur** : Équipe Waterflow 2

## Détection
* Détection initiale : Crash de l'interface utilisateur lors du téléversement d'une fiche laboratoire.
* Détection Monitoring : Le compteur Prometheus `ocr_failures_total` s'incrémente [2]. Une alerte Grafana peut être déclenchée sur la métrique `rate(http_requests_total{endpoint="/api/ocr/lab-report",status=~"5.."}[5m]) > 0.1` [3].

## Diagnostic
1. **Panne du service tiers** : L'API distante `api.ocr.space` ne répond plus dans le temps imparti (Timeout > 15s) ou renvoie une erreur (Bad Gateway) [2].
2. **Impact API (Backend)** : L'API FastAPI n'était pas résiliente. Elle levait une `HTTPException` directe faisant échouer l'appel.
3. **Impact Frontend (Flask)** : Même après avoir ajouté un message de secours côté API, le client Flask s'attendait strictement à recevoir des mesures physico-chimiques. Ne les trouvant pas, le template HTML a déclenché une erreur fatale Jinja2 (`TypeError: Object of type Undefined is not JSON serializable`).

## Correction
Mise en place d'une dégradation gracieuse du service (Fallback) en deux étapes :
* **Côté API (`src/routes/ocr.py`)** : Ajout d'un bloc `try/except` interceptant le `Timeout`. L'API ne crashe plus et renvoie désormais un statut `pending` (HTTP 200) accompagné d'un message d'attente [2].
* **Côté Frontend (`front/client.py`)** : Ajout d'une condition pour intercepter la réponse JSON `{"status": "pending"}`. Le client est désormais redirigé proprement vers son tableau de bord avec une alerte visuelle jaune (`flash("warning")`) expliquant que le service est ralenti, évitant ainsi le crash de la page HTML.

## Prévention et Retour d'Expérience (MCO)
* **Visibilité** : Remplacement des exceptions fatales et des `print()` par des **logs structurés au format JSON** (`logger.error("ocr_call_failed", ...)`), incluant le `client_id` et la durée de la panne (`duration_ms`), permettant un diagnostic rapide en exploitation [4].
* **Résilience** : Le système est désormais découplé de la santé de l'OCR externe. L'application continue de fonctionner pour les autres routes (prédiction standard, consultation) même si l'OCR est hors-service [2].
* **Amélioration future** : Mettre en place un système de file d'attente (retry asynchrone) pour traiter automatiquement le document dès que l'OCR.space sera de nouveau en ligne [1].
