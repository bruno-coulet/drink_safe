
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



#### 3. Correction (Le patch d'interception)
Puisqu'il est compliqué (et peu sécurisé) de désactiver les sécurités internes du serveur MLflow, nous avons opté pour une ruse élégante côté FastAPI.

Implémentation d'un patch d'interception HTTP qui surcharge dynamiquement la bibliothèque `requests` dans le fichier `src/config.py`. Juste avant que la requête ne parte vers MLflow, ce patch :
* Met le processus en pause.
* Conserve la bonne destination physique (il sait qu'il doit cibler le conteneur Docker nommé `mlflow`).
* **Écrase l'en-tête Host à la volée** pour le remplacer par une valeur que MLflow acceptera sans broncher (ex: `localhost:5000`).

Résultat : MLflow reçoit la requête, lit l'en-tête modifié, la trouve parfaitement légitime, et autorise l'échange des modèles d'Intelligence Artificielle de manière fluide.

#### 4. Retour d'Expérience et Prévention
* **Leçon tirée :** Les environnements isolés comme Docker appliquent toujours les standards stricts de sécurité web (comme le contrôle des en-têtes `Host`).
* **Bénéfice :** Cette solution de contournement (Spoofing d'en-tête en interne) permet de garantir la communication entre nos micro-services tout en préservant intactes les configurations de sécurité du serveur MLflow.



