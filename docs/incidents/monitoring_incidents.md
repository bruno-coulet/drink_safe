# Documentation de l'Observabilité et Gestion des Incidents (MCO)
**Projet : Waterflow 2 (Drink Safe)**

Ce document synthétise la stratégie de monitoring applicatif et la méthodologie de résolution d'incidents mises en œuvre sur la plateforme Drink Safe, conformément aux attentes MLOps et aux exigences de Maintien en Condition Opérationnelle (MCO).

---

## 1. Monitorer l'application IA (Compétence C20)

Pour garantir la haute disponibilité du service et la détection proactive des anomalies, la plateforme s'appuie sur une stack d'observabilité complète et découplée.

### 1.1 Architecture de Supervision (Stack Prometheus / Grafana)
Le monitoring repose sur trois composants aux rôles stricts :
*   **Exposition (FastAPI)** : L'API Unique expose un point de terminaison `/metrics` via la librairie `prometheus_client`
*   **Stockage Time-Series (Prometheus)** : Un conteneur Prometheus (port 9090) récupère ces métriques à intervalles réguliers (toutes les 15 secondes)

*   **Visualisation (Grafana)** : Un tableau de bord Grafana (port 3000) interroge Prometheus en PromQL pour afficher l'état de santé du système

La **configuration de Grafana** et l'**importation du tableau de bord** s'effectuent de manière automatisée au démarrage du conteneur, grâce aux fichiers YAML (`datasources.yml` et `dashboards.yml`) présents dans le dossier `monitoring/`.

### 1.2 Le Tableau de Bord "RED"
Le suivi en temps réel pour le Responsable d'Exploitation repose sur la méthode RED, qui trace les trois indicateurs vitaux d'une API :
*   **Rate (Trafic)** : Le volume de requêtes HTTP par seconde (`http_requests_total`)

*   **Errors (Fiabilité)** : Le pourcentage d'erreurs serveur 5xx générées par le backend 
*   **Duration (Performance)** : La latence des requêtes, calculée au 95ème centile pour identifier les goulots d'étranglement 

### 1.3 Audit Trail et Journalisation Structurée
*   **Logs JSON structurés** : Pour faciliter le diagnostic, l'application génère des logs au format JSON contenant le contexte de l'événement (ID client, endpoint, durée, erreur exacte). Ce format évite les "prints" sauvages impossibles à filtrer 

*   **Middleware d'Audit (Base de données)** : Un middleware HTTP intercepte chaque requête, anonymise la clé API pour des raisons de sécurité, et consigne l'action (date, route, code statut, durée) dans la table PostgreSQL `action_logs`. Cela permet de répondre aux audits RGPD tout en surveillant l'utilisation de l'API 
*   **Métriques métiers (Custom)** : Le système incrémente des compteurs spécifiques, comme `ocr_failures_total`, pour tracer spécifiquement les pannes du service d'extraction documentaire externe sans noyer les logs globaux 

---

## 2. Résolution des incidents techniques (Compétence C21)

Face aux pannes et aux bogues, l'équipe applique la méthodologie stricte **DDCR** : *Détection, Diagnostic, Correction, Retour d'expérience* 

### 2.1 Traitement des pannes de services externes (Exemple OCR.space)
Le projet intègre une forte dépendance au service tiers OCR.space. En cas d'indisponibilité de ce dernier, l'incident est géré de bout en bout :
1.  **Détection** : Une alerte remonte sur Grafana via le pic d'erreurs 5xx sur la route `/ocr`, ou via l'incrémentation du compteur Prometheus `ocr_failures_total` 

2.  **Diagnostic** : Les logs JSON structurés permettent d'identifier instantanément s'il s'agit d'un "Timeout" réseau ou d'un dépassement de quota ("IsErroredOnProcessing") 
3.  **Correction (Fallback gracieux)** : Au lieu de crasher, l'API FastAPI intercepte l'exception. Elle renvoie au frontend Flask un statut HTTP 201 ou 200 (`pending`), déclenchant un message d'avertissement visuel propre pour l'utilisateur. Le prélèvement est enregistré sans rompre l'expérience utilisateur globale 
4.  **Déploiement et Documentation** : Ce comportement est documenté de manière formelle dans le fichier `docs/incidents/incident_ocr.md` 

### 2.2 Suivi des Bogues de Modélisation et d'Architecture (Bugfix)
Tous les incidents internes (régressions, erreurs de logique) sont diagnostiqués, fixés, testés, puis consignés dans le registre `docs/bugfix.md`  

Parmi les cas résolus :
*   **Désynchronisation MLOps (Crash Inférence 503)** : L'API échouait à charger les modèles car elle démarrait avant le serveur MLflow  
**Fix :** Mise en place d'un chargement dynamique (Lazy Loading) à la première requête avec mise en cache RAM, et partage des volumes Docker d'artefacts (`./mlruns_artifacts`) 

*   **Conflits de Schéma SQL** : Des erreurs silencieuses se produisaient lors de l'insertion en base de données  
**Fix :** Centralisation de la fonction d'initialisation de la BDD (Single Source of Truth) dans `src/config.py` et application stricte des exceptions  
Auparavant, le code utilisait un bloc `try/except` trop large qui "masquait" les erreurs de la base de données : si une colonne manquait à cause d'un décalage de schéma, l'erreur était ignorée silencieusement et l'API renvoyait un succès (HTTP 200) sans rien sauvegarder. 
**application stricte :** le code ne masque plus ces problèmes, il intercepte spécifiquement les erreurs d'écriture SQL et les remonte proprement dans les logs d'exploitation pour éviter toute perte de données silencieuse
*   **Vérification (Tests)** : La non-régression et le bon déploiement de la solution sont validés systématiquement par la suite de tests PyTest (unitaires, fonctionnels, et de performance) exécutée via GitHub Actions  
Les réponses de l'API sont ainsi garanties conformes et fiables avant toute mise en production.