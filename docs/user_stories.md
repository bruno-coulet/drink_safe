# User Stories & Cahier des Charges Fonctionnel

🔵 <span style="color:#2f80ed; font-weight:bold;">Acteur - Qui ?</span>

🟠 <span style="color:#f2994a; font-weight:bold;">Action / Le Besoin - Quoi ?</span>

🟣 <span style="color:#9b51e0; font-weight:bold;">Contrainte / La Règle Métier - Comment ?</span>

---

## Backlog des User Stories Principales

### User Storie #1 : Ingestion des prélèvements standards
🔵 **En tant que** <span style="color:#2f80ed; font-weight:bold;">Client de la collectivité territoriale</span>

🟠 **Je veux** <span style="color:#f2994a; font-weight:bold;">déposer mes prélèvements d'eau et récupérer instantanément mes résultats de potabilité</span>

🟣 **Afin de** <span style="color:#9b51e0; font-weight:bold;">sécuriser mes analyses via une API simple, authentifiée par une clé API unique plutôt que par un système complexe.</span>

### User Storie #2 : Ingestion automatisée par OCR (Fiches Laboratoire)
🔵 **En tant que** <span style="color:#2f80ed; font-weight:bold;">Client ou Agent de terrain</span>

🟠 **Je veux** <span style="color:#f2994a; font-weight:bold;">déposer une photo ou un document PDF de rapport de prélèvement</span>

🟣 **Afin d'** <span style="color:#9b51e0; font-weight:bold;">éviter la saisie manuelle grâce à un service d'IA OCR qui extrait automatiquement la date, l'ID client, les mesures physico-chimiques et les observations.</span>

### User Storie #3 : Supervision des données et de l'IA
🔵 **En tant qu'** <span style="color:#2f80ed; font-weight:bold;">Analyste Qualité</span>

🟠 **Je veux** <span style="color:#f2994a; font-weight:bold;">disposer d'une plateforme unique pour consulter l'ensemble des prélèvements, les prédictions et les tableaux de bord</span>

🟣 **Afin de** <span style="color:#9b51e0; font-weight:bold;">valider la cohérence des données et suivre l'évolution des performances du modèle de Machine Learning.</span>

### User Storie #4 : Supervision technique de l'infrastructure
🔵 **En tant que** <span style="color:#2f80ed; font-weight:bold;">Responsable d'Exploitation</span>

🟠 **Je veux** <span style="color:#f2994a; font-weight:bold;">accéder à un tableau de bord centralisant les indicateurs de santé du système (erreurs, temps de réponse, volume de requêtes)</span>

🟣 **Afin de** <span style="color:#9b51e0; font-weight:bold;">garantir la haute disponibilité de la plateforme et intervenir rapidement en cas d'incident technique.</span>

---

## 2. Règles de Gestion : Comptes et Sécurité

### Structure d'un Compte Client
Chaque entité cliente de la collectivité possède un profil persistant en base de données PostgreSQL contenant :
* `client_id` : Identifiant unique du client.
* `nom_structure` : Dénomination sociale ou nom de la structure.
* `adresse_postale` : Adresse physique pour la facturation/suivi.
* `api_key` : Jeton d'accès (token) sécurisé généré par la plateforme.

### Matrice des Droits et Autorisations

| Fonctionnalité | <span style="color:#2f80ed; font-weight:bold;">Client Final</span> | <span style="color:#2f80ed; font-weight:bold;">Analyste Qualité</span> | <span style="color:#2f80ed; font-weight:bold;">Responsable Exploitation</span> |
| :--- | :---: | :---: | :---: |
| Appeler l'API d'ingestion (Données brutes) | **✅ Oui** | ❌ Non | ❌ Non |
| Appeler l'API OCR (Upload PDF/Image) | **✅ Oui** | ❌ Non | ❌ Non |
| Consulter ses propres données & prédictions | **✅ Oui** | **✅ Oui** | ❌ Non |
| Consulter l'historique de TOUS les clients | ❌ Non | **✅ Oui** | **✅ Oui** |
| Accéder aux Dashboards de performance ML | ❌ Non | **✅ Oui** | ❌ Non |
| Monitorer les logs, erreurs et volumes réseau | ❌ Non | ❌ Non | **✅ Oui** |
| Créer un client / Générer une Clé API | ❌ Non | **✅ Oui** | **✅ Oui** |

---

## 3. Spécifications Fonctionnelles des Profils

### A. Client Final de la Collectivité
* **Authentification standardisée** : Accède aux services uniquement via sa <span style="color:#9b51e0; font-weight:bold;">Clé API</span> présente dans le header de ses requêtes HTTP.
* **Modes de transmission** : Dispose de deux routes d'ingestion distinctes (JSON structuré ou Fichier non structuré via OCR).
* **Restitution** : Accède à une interface simplifiée (IHM Streamlit) filtrée sur son propre identifiant pour suivre ses analyses.

### B. Analyste Qualité
* **Vision Métier Globale** : Ne subit aucune restriction sur la lecture des données de prélèvements pour mener ses analyses statistiques.
* **Évaluation de la Dérive (Drift)** : S'assure que les données envoyées par les clients ne divergent pas des distributions apprises à l'entraînement par les modèles sous MLflow.

### C. Responsable d’Exploitation
* **Garant du SLA** : Surveille les métriques d'infrastructure. Il valide que le couplage entre le Middleware Flask et le serveur d'inférence FastAPI ne génère pas de goulots d'étranglement ou de latences anormales.
* **Audit Trail** : Accède aux journaux d'appels pour tracer l'utilisation des clés API et détecter d'éventuels abus ou anomalies de requêtage.

<!-- # User stories principales

## BESOINS
<strong style="color: blue;">acteurs</strong>
<strong style="color: orange;">action</strong>
<strong style="color: violet;">contrainte</strong>



<strong style="color: blue;">1. Clients de la collectivité territoriale</strong>

<ul style="color: orange;">
    <li>déposer leurs prélèvements</li>
    <li>récupérer leurs résultats</li>
    <li>via une API simple</li>
    <li>sécurisée par une clé API plutôt que par un système d’authentification complexe.</li>
</ul>



<strong style="color: blue;">2. Clients ou agents de terrain de la collectivité territoriale</strong>

<ul style="color: orange;">
<li>éviter de saisir manuellement les fiches de laboratoire</li>
<li>déposer une photo ou un PDF de rapport de prélèvement</li>
<li>l’envoyer par API</li>
<li>laisser un service d’IA OCR extraire automatiquement les informations attendues :
    <ul>
    <li>date</li>
    <li>ID client</li>
    <li>mesures physico‑chimiques</li>
    <li>observations</li>
    </ul>
    </li>
</ul>
---

<strong style="color: blue;">3. Analystes qualité</strong>
<ul style="color: orange;">
    <li>disposer d’une plateforme unique pour consulter :
        <ul>
            <li>les prélèvements</li>
            <li>les prédictions du modèle</li>
            <li>les tableaux de bord</li>
        </ul>
   </li>
</ul>
---

<strong style="color: blue;">4. Responsable d’exploitation</strong>  
<ul style="color: orange;">
<li>disposer d’une plateforme unique pour :</li>
<ul>
    <li>consulter les indicateurs de santé du système :</li>
    <li>erreurs</li>
    <li>temps de réponse</li>
    <li>volume de requêtes</li>
    <li>etc...</li>
</ul> 
</ul> 

---
---
---
### Chaque client de la collectivité possède un compte client contenant :
- un identifiant client (ID client),
- une dénomination (nom de la structure),
- une adresse postale,
- une clé API générée par la plateforme.

**Les clients utilisent uniquement leur clé API pour :**
- appeler l’API d’ingestion de prélèvements,
- appeler l’API d’ingestion par OCR (fiches labo),
- consulter leurs données
- consulter les résultats d’analyse du modèle de la plateforme.
---
---
---


### Les administrateurs de la plateforme (analystes qualité / responsables d’exploitation ou rôle dédié)
sont les seuls à pouvoir :
- créer un compte client avec ID, nom et adresse
- générer et régénérer une clé API associée

---
---
---


## cahier des charges fonctionnel.



### Profils à prendre en compte

<strong style="color: blue;">Client final de la collectivité</strong>   
<span style="color: orange;">possède :</span>

- ID client
- clé API.

 <span style="color: orange;">peut :</span>
- déposer des prélèvements (données structurées ou fiche
labo PDF/image)
- consulter ses propres données et résultats via
API et/ou une vue simplifiée.   

---

<strong style="color: blue;">Analyste qualité</strong>   
<span style="color: orange;">Accède à tous les :</span>
- prélèvements
- dashboards
- prédictions
- données enrichies
- Cohérence des données et performances du modèle.

---

<strong style="color: blue;">Responsable d’exploitation</strong>   
<span style="color: orange;">Supervise la santé globale de la plateforme :</span>

- disponibilité
- volumes
- erreurs
- alertes

● Suit la gestion des clés API, les journaux d’accès et les incidents
techniques. -->
