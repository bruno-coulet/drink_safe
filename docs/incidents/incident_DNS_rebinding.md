
### Incident - Blocage réseau interne (Erreur HTTP 403 DNS Rebinding)

- **Date** : 03/07/2026
- **Sévérité** : Majeure (Impossible pour l'API de communiquer avec le Model Registry)
- **Auteur** : Bruno Coulet

> **Attaque DNS Rebinding :**
> Technique de piratage où un attaquant crée un vrai nom de domaine sur internet, mais modifie son adresse IP à la volée pour pointer vers le réseau interne privé d'une entreprise. Pour se protéger, les serveurs modernes bloquent toutes les requêtes dont l'en-tête `Host` ne correspond pas exactement à ce qu'ils attendent.


#### 1. Détection
* Lors des tests d'intégration réseau au sein de l'infrastructure Docker, les appels de l'API pour récupérer les modèles d'Intelligence Artificielle échouaient systématiquement.
* Les logs de l'API FastAPI affichaient un refus de connexion avec une erreur `HTTP 403 (Forbidden)` lors de la tentative de contact du registre à l'adresse interne `http://mlflow:5000`.

#### 2. Diagnostic (Analyse de l'En-tête Host et DNS Rebinding)
L'erreur ne provenait pas d'une mauvaise URL, mais d'un mécanisme de sécurité réseau :

* **Le fonctionnement normal (L'en-tête Host) :** Quand une API fait une requête HTTP vers un serveur, elle inclut une information invisible appelée l'en-tête `Host`. Cela indique au serveur distant le nom du site recherché (ex: `Host: google.com`).
* **Le problème avec Docker :** Dans notre architecture Docker Compose, les conteneurs discutent entre eux en utilisant des noms internes virtuels. L'API FastAPI essaie donc de joindre le registre à l'adresse `http://mlflow:5000`. La requête part avec l'en-tête `Host: mlflow:5000`.
* **La sécurité (L'erreur 403) :** Quand le serveur de MLflow reçoit cette requête, son pare-feu interne s'affole. Il est configuré pour répondre à `localhost` ou à son IP publique, mais ne reconnaît pas le nom `mlflow:5000`. Il suspecte une attaque par **DNS Rebinding** et rejette la requête.



#### 3. Correction (De l'applicatif vers l'infrastructure)

##### Intention initiale (Solution logicielle) :
Dans un premier temps, une solution de contournement consistant à créer un patch d'interception HTTP dans l'API (fichier `src/config.py`) a été envisagée. L'idée était de surcharger dynamiquement la bibliothèque requests pour écraser l'en-tête `Host` à la volée et usurper l'identité de `localhost:5000` lors de la communication avec MLflow.

##### Solution finale retenue (Implémentation Infrastructure) :
La stratégie de résolution a évolué pour privilégier une approche plus robuste, centralisée au niveau de l'infrastructure plutôt que dans le code applicatif.
Puisque le serveur MLflow s'appuie sur Uvicorn, nous avons configuré ce dernier pour accepter nativement le trafic réseau provenant du sous-réseau Docker. Le correctif a été appliqué directement dans le fichier `docker-compose.yml` en injectant les variables d'environnement suivantes au conteneur `mlflow` :

- `UVICORN_PROXY_HEADERS=true`
- `UVICORN_FORWARDED_ALLOW_IPS=*`


**Résultat :**   
Le serveur MLflow est explicitement configuré pour faire confiance au proxy interne de Docker.   
Il lit les requêtes de l'API FastAPI, les trouve légitimes, et autorise l'échange des modèles d'Intelligence Artificielle de manière fluide, sans aucune modification du code source Python.

#### 4. Retour d'Expérience et Prévention
Les environnements isolés comme Docker appliquent toujours les standards stricts de sécurité web (comme le contrôle des en-têtes Host).   
Résoudre un problème réseau au niveau de l'infrastructure (Docker Compose) est souvent plus propre et plus stable que de développer des surcharges complexes (patches/spoofing) dans le code applicatif.

**Bénéfice :**   
Cette solution maintient le code de l'API agnostique des contraintes de l'infrastructure réseau.   
Elle garantit la communication entre les micro-services en utilisant les mécanismes de sécurité prévus nativement par les serveurs web modernes (Uvicorn), assurant ainsi un Maintien en Condition Opérationnelle optimal.



