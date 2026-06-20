Bloquant — bugs fonctionnels silencieux

### 1. Le schéma SQL prelevements réel ≠ celui attendu par le code

Trois définitions divergentes de la même table :

┌───────────────────────────────────────────────┬───────────────────────┬───────────────┐
│                    Source                     │ prediction_potability │ model_version │
├───────────────────────────────────────────────┼───────────────────────┼───────────────┤
│ docs/data_model.md:86-87 (doc)                │ ✅ présent            │ ✅ présent    │
├───────────────────────────────────────────────┼───────────────────────┼───────────────┤
│ src/config.py:67-82 (réellement exécuté par   │ ❌ absent             │ ❌ absent     │
│ init_db)                                      │                       │               │
├───────────────────────────────────────────────┼───────────────────────┼───────────────┤
│ src/experiment.py:49-64 (script_init_db)      │ ❌ absent             │ ❌ absent     │
└───────────────────────────────────────────────┴───────────────────────┴───────────────┘

Or predictions.py:153-157 fait un INSERT ... (prediction_potability, model_version, ...). Ces colonnes n'existent pas dalève column does not exist… mais l'exception est avalée par le try/except de _sauvegarder_prelevement_en_bdd
(predictions.py:169, simple pr

Conséquence : aucune prédictiot tu ne le vois pas car l'APIrenvoie quand même 200. La doc décrit le bon schéma, le code crée l'ancien.

### Correction schéma SQL
Migration manuelle (sans perdre les données), ajout des 2 colonnes manquantes :
```bash
docker compose exec postgres-db psql -U admin_waterflow -d waterflow_db -c \
"ALTER TABLE prelevements ADD COLUMN IF NOT EXISTS prediction_potability INT, ADD COLUMN IF NOT EXISTS model_version VARCHAR(100);"
```

Pour confirmer que les colonnes existent ensuite :
```bash
docker compose exec postgres-db psql -U admin_waterflow -d waterflow_db -c "\d prelevements"
```
`prediction_potability` et `model_version` sont maintenant dans la liste.


---

### 2. Colonne de tri 'date_prelevement' inexistante
Sérieux — casse le mode Dévelo

``measurements.py`` lignes87 et114 font ``ORDER BY date_prelevement DESC``
La colonne réelle s'appelle ``cree_le`` (config.py:81).
``date_prelevement`` n'existe nulle part. → GET/api/measurements/ et /api/measurements/admin renvoient 500 systématiquement.


- front/app.py n'appelle que POST /predict et POST /ocr — jamais le GET des prélèvements
- L'échec d'écriture des prédictions est silencieux (bug #1).
- Les tests OMS (test_unit.py)rt échoue, donc la suite passe au vert sans rien détecter. Le test fonctionnel ne couvre que la création client + OCR


### Correction problème 2 — colonne de tri 'date_prelevement'

- ``measurements.py`` : les 2 ``SELECT`` utilisent désormais ``ORDER BY cree_le DESC`` (au lieu de ``date_prelevement`` qui n'existait pas).
- Choix : corriger le code plutôt que renommer la colonne, pour rester cohérent avec la table ``clients``, la doc ``data_model.md`` et la base déjà créée.

Aucune action en BDD n'est nécessaire
on ne touche qu'à des requêtes ``SELECT``

Mais le conteneur api-unique tourne avec le code monté en volume

Selon que uvicorn a ``--reload`` ou non, il faut peut-être redémarrer le conteneur api-unique pour recharger le code :
```bash
docker restart api-unique
```
Ensuite, pour valider le problème 2 :
```bash
curl -s -H "X-API-Key: wf_live_Ir4nM1bMP5BIXpzLYEU6xIxIfuj3cXEpCCYGEIkuGzs" http://127.0.0.1:8000/api/measurements/
```
Cette commande doit renvoyer une liste JSON (même vide []) au lieu d'une erreur 500.

---

### 3. URI MLflow malformée hors Docker
Conception / maintenabilité

``config.py`` ligne 47 :
 MLFLOW_TRACKING_URI = "http://mlflow-back:5000" if IS_DOCKER else "http:// 127.0.0.1:5000"
 Il y a un espace parasite dans l'URL, et aucun .strip() ici (contrairement à DATABASE_URL:44 qui, lui, nettoie).

 En Docker ça passe

 Avec ``uv run uvicorn ... --reload``, MLflow est injoignable


### Correction URI MLflow
suppression de l'espace dans l'URL

---

### 4. Double source de vérité du schéma : config.init_db() et experiment.script_init_db()
redéfinissent les mêmes 3 tabl permis la dérive du #1. Uneseule fonction devrait faire foi.

### Solution Problème 4 — source unique du schéma

- ``experiment.py`` importe maintenant ``init_db`` depuis config et l'appelle directement.
- La fonction ``script_init_db()`` (dupliquée, ~50 lignes) est supprimée, ainsi que l'import ``psycopg2`` devenu inutile.
- Résultat : ``config.init_db()`` est désormais la seule définition du schéma → plus de risque de dérive entre l'API et le pipeline d'entraînement.



---

### 5. Stratégie de version modèle incohérent
Mineur

``api.py`` ligne 84 précharge ``models:/{name}/1``
(version 1 figée)

``predictions.py`` ligne 98 en lazy-load prend max(version)

Après un réentraînement, le résultat dépend de si le modèle vient du cache de démarrage ou du lazy-load.
De plus, ``predictions.py`` ligne 135 renvoie ``"model_version": "1"`` codé en dur.

#### correction

A. Chargement : api.py:84 précharge models:/{name}/1 — version 1 figée. Mais predictions.py:98 en lazy-load prend max(version) — la dernière. Après un réentraînement (v2, v3…), selon que le modèle vient du cache de démarrage ou du lazy-load, tu sers une version différente. Comportement non déterministe.

B. Version rapportée : predictions.py:128 enregistre _v1 en base et :135 renvoie "1" — codés en dur, quelle que soit la version réellement utilisée.

La correction

1. api.py doit charger la dernière version (latest_v.version), comme le lazy-load.
2. Pour pouvoir rapporter la vraie version, on mémorise « quelle version est en cache » dans un petit registre parallèle ml_model_versions.

Pourquoi un dict parallèle plutôt que de transformer ml_models ? Parce que model.predict(...) et health_check consomment directement les objets modèles ; un registre séparé évite de toucher à ces appels. C'est le changement le moins invasif.

3. predictions.py lit/écrit cette version et la renvoie réellement.

Récapitulatif des changements

api.py
- Nouveau registre ml_model_versions (ligne 48) qui mémorise la version chargée par modèle.
- Préchargement : models:/{model_name}/{version} avec la dernière version (latest_v.version) au lieu de /1 figé (lignes 79, 87). Le hack .rstrip("/."), devenu inutile, a été retiré.
- Version mémorisée dans les deux chemins de chargement (Tentative A et Fallback B).
- ml_model_versions.clear() ajouté à l'arrêt (ligne 115).

predictions.py
- Lit la version depuis le registre (version_modele, fallback "inconnue").
- En lazy-load, enregistre la version réelle dans le registre.
- Persiste _v{version} réel et renvoie "model_version": version_modele au lieu de "1".

Résultat : préchargement et lazy-load servent désormais la même stratégie (dernière version), et la version rapportée/persistée reflète la réalité.

Pour appliquer et vérifier

Le code de api-unique est monté en volume, mais le préchargement ne s'exécute qu'au démarrage (lifespan). Il faut donc redémarrer le conteneur :
```bash
docker restart api-unique
```

Puis, après une prédiction valide (eau dans les normes OMS pour passer le garde-fou), la réponse JSON doit contenir le vrai numéro, ex. "model_version": "1" (ou la dernière version réelle si tu as réentraîné). Tu peux aussi le vérifier en base :
```bash
docker exec postgres-db psql -U admin_waterflow -d waterflow_db -c \
"SELECT provenance, prediction_potability, model_version, cree_le FROM prelevements ORDER BY cree_le DESC LIMIT 5;"
```




---


### 6. Traçabilité RGPD incomplète
Mineurs

 le middleware écrit toujours ``client_id = "ANONYMOUS"`` (api.py:138, codé en dur)
 alors que le README et ``data_model.md`` vendent un audit par client. La colonne existe mais n'est jamais renseignée.

#### Correction

L'approche la plus propre : la dépendance get_current_client résout déjà api_key → client_id via une requête SQL. On lui fait déposer ce client_id dans request.state, et le middleware le relit après l'exécution de l'endpoint. Zéro requête SQL supplémentaire (on réutilise celle qui existe déjà), pas de duplication de logique.

auth.py
- get_current_client reçoit maintenant request: Request et dépose le client_id résolu dans request.state.client_id avant de le retourner.

api.py (middleware)
- Lit getattr(request.state, "client_id", "ANONYMOUS") au lieu de la valeur figée. La lecture se fait après await call_next, donc une fois la dépendance d'auth exécutée.

┌────────────────────────────────┬──────┬───────────────────────────────────┐
│            Requête             │ Auth │       client_id journalisé        │
├────────────────────────────────┼──────┼───────────────────────────────────┤
│ GET /measurements/ avec clé    │ 200  │ TEST_RGPD_1781973419 ✅ (vrai     │
│ valide                         │      │ client)                           │
├────────────────────────────────┼──────┼───────────────────────────────────┤
│ GET /measurements/ sans clé    │ 401  │ ANONYMOUS ✅ (comportement        │
│                                │      │ attendu)                          │
└────────────────────────────────┴──────┴───────────────────────────────────┘

Pourquoi ça marche

request.state est adossé au scope de la requête, partagé entre la dépendance (qui l'écrit) et le middleware (qui le lit après l'endpoint). Aucune requête SQL supplémentaire : on réutilise celle que get_current_client faisait déjà. Les endpoints non authentifiés (ex. création de client) ou les échecs d'auth retombent proprement sur ANONYMOUS.

---

### 7. Unités contradictoires
Mineurs

le garde-fou parle de « Trihalométhanes > 80.0 ppm » (predictions.py:65) alors que le champ et la doc sont en µg/L.


Scientifiquement, le seuil OMS réel des THM est 80 µg/L (≈ 0,08 ppm). « 80 ppm » est une erreur d'unité connue du descriptif Kaggle de ce dataset.
Il y a donc deux positions défendables :

1. Cohérence avec la source → tout en ppm.
C'est le moins surprenant pour qui relit le dataset, et la valeur numérique 80 reste celle utilisée par le modèle.

2. Exactitude scientifique → tout en µg/L
en assumant que le descriptif se trompe.

Problème 7 réglé, aligné sur ppm partout (la source = le descriptif du dataset).

Fichiers modifiés :
- predictions.py:36 — description du champ → ppm
- measurements.py:31 — idem
- front/app.py:104 — label du slider → ppm
- data_model.md:34 — modèle de données → ppm












