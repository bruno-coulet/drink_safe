# Concevoir et implémenter Waterflow 2 en suivant les étapes suivantes :
## Analyse du besoin et spécifications
- Formaliser le contexte métier et les profils utilisateurs.
- Rédiger les spécifications fonctionnelles (user stories, critères
d’acceptation) pour client, agent, analyste, responsable.
- Proposer une architecture technique :
 API (une seule API peut porter Data + Model + OCR, plutôt
que 3 APIs séparées)
- API Data (prélèvements),
- API Model (prédiction Waterflow existante),
- API OCR (ingestion de fiches labo),
- base de données,
- logs de monitoring,
- mécanismes de test
- CI/CD,
- intégration avec OCR.space.
## Modélisation et base de données
- Concevoir un MCD/MPD incluant au minimum :
- clients (ID client, dénomination, adresse, clé API…),
- prélèvements (date, lieu, mesures, ID client, provenance :
“Saisie” / “OCR”),
- journaux d’accès et de traitements (pour la traçabilité
RGPD),
- [si nécessaire] éventuelles tables de support (types de
mesures, statuts…).
- Implémenter la base SQL (PostgreSQL / MariaDB…) et les scripts
de création.
- Programmer des scripts d’import/agrégation cohérents avec
le modèle. Au moins un script attendu.
## API Data et modèle d’authentification par clé API
- Implémenter une API REST Data exposant au moins :
- POST /api/clients (réservé aux administrateurs) : création
d’un client avec ID, nom, adresse et génération de la clé
API.
- GET /api/clients (admin) : liste ou détail des clients.
- POST /api/measurements (client + clé API) : dépôt de
mesures structurées pour créer un prélèvement.
- GET /api/measurements (client + clé API) : liste des
prélèvements du client (filtrage par clé API).
- GET /api/measurements/admin (expert) : vue globale
filtrable.
- Gérer la validation des requêtes (schémas, types, formats) et
le contrôle d’accès par clé API.
- Documenter cette API (OpenAPI / Swagger) afin de la rendre
intégrable par des systèmes externes.
## API Model
- Réutiliser ou adapter le modèle et l’API de prédiction du projet
Waterflow (Flask ou FastAPI) en l’intégrant dans la nouvelle
architecture.
- Exposer une route, par exemple POST /api/predict, prenant en
entrée un prélèvement (ou un ID de prélèvement) et renvoyant
la prédiction + métadonnées (version de modèle, scores).
- Assurer au minimum le suivi des versions,des expériences et
quelques métriques via MLflow (monitoring modèle). Un suivi
exhaustif des expériences est optionnel.
- Écrire des tests unitaires et d’intégration (2 ou 3) pour valider le
pipeline de prédiction.
## API OCR avec OCR.space
- Après une veille comparative sur des services d’IA équivalents
répondant aux besoins de l’application, intégrer l’API
OCR.space (https://api.ocr.space/parse/image) ou un autre
service équivalent, pour traiter des fichiers image/PDF de
fiches de laboratoire.
- Concevoir une route, par exemple :
- POST /api/ocr/lab-report (client + clé API) :
- reçoit un fichier (image/PDF) représentant une
fiche laboratoire ;
- appelle OCR.space (via file ou base64Image) avec la
clé API OCR de la plateforme ;
- parse la réponse JSON pour extraire les champs
utiles (date, ID client, mesures physico-chimiques,
etc.) ;
- crée un prélèvement structuré identique à celui de
POST /api/measurements (ou utilise la même logique
métier) ;
- renvoie au client un identifiant de prélèvement et
les données extraites.
- Documenter cette route et les erreurs possibles (timeout OCR,
fichier illisible, champs manquants).
## Interface web expert
Développer une interface simple (Dash, Streamlit ou Flask) pour :
- consulter tous les prélèvements
- filtrer par client, provenance (Saisie / OCR), date, résultat
modèle,
- [option] afficher quelques indicateurs clés (nombre de
prélèvements, répartition potables / non potables, etc.),
- [option] visualiser quelques journaux d’accès (dans une
vue d’administration).
## Tests, CI/CD, monitoring et incidents
- Écrire des tests unitaires et d’intégration (PyTest…) pour :
- API Data, API Model, API OCR, validation des schémas de
données,
- au moins un test de bout en bout (dépôt de fiche labo →
OCR → prélèvement structuré → prédiction modèle).
- Mettre en place une CI simple (GitHub Actions, GitLab CI)
exécutant les tests à chaque push/PR.
- Conteneuriser l’application (Docker) pour faciliter le
déploiement et la reproductibilité.
- Mettre en place un mécanisme de monitoring applicatif :
- journalisation des requêtes (client, route, status, durée),
- quelques métriques (nombre de requêtes OCR, taux
d’erreur, temps moyen de traitement).
- [Optionnel] ajouter une interface Prometheus + Grafana
pour visualiser les journaux, logs et indicateurs ou
métriques
- Mettre en place une intégration continue minimale (GitHub
Actions, GitLab CI…) qui installe les dépendances et exécute la
suite de tests à chaque push. La livraison continue (build et
déploiement automatique) est un bonus si elle est réalisée.
- Prévoir au moins un scénario d’incident (par exemple, service
OCR indisponible, clé API OCR invalide, fail d’import) et
documenter :
- la détection de l’incident (logs, métriques),
- le diagnostic,
- la correction et sa vérification,
- la mise à jour du code / de la configuration et son
versionnement.
Dimensions RGPD et gouvernance des accès
L’introduction de l’ID client + clé API permet de traiter des enjeux RGPD
concrets, en base de données et dans les logs :
- séparation stricte des périmètres : un client ne voit que ses données ;
- minimisation des données personnelles stockées (ID technique +
adresse) ;
- journalisation des accès par clé API pour pouvoir répondre à un audit
de sécurité ;
- documentation des durées et règles de conservation des données
(prélèvements, logs).
Les étudiant·es devront :
- expliciter, dans la documentation, quelles données sont considérées
comme personnelles ;
- décrire comment les journaux d’accès sont gérés, à quelles fins et
pour combien de temps ;
- expliquer comment la génération et la régénération des clés API sont
gérées (régénération en cas de compromission). Au minimum, la
documentation doit expliquer comment un client ne peut accéder
qu’à ses données (clé API + filtres) et comment une clé compromise
pourrait être régénérée.
Livrables
Vous livrerez les éléments suivants pour les présenter devant une audience
professionnelle:
- Présentation orale (diapositives) :
- mise en situation, analyse du besoin, profils utilisateurs,
- architecture, modèle de données, stratégie d’authentification
par clé API,
- intégration d’OCR.space,
- démonstration de la plateforme,
- tests, CI/CD, monitoring, incident traité.
- Repository GitHub public comprenant au minimum :
- README.md (contexte, installation, exemples d’appels API,
comptes de test, limites) ;
- dossier docs/ (cahier des charges, user stories, MCD/MPD,
diagramme d’architecture, note RGPD, fiche incident) ;
- code de la base de données et des scripts d’import ;
- API Data, API Model, API OCR ;
- interface web expert ;
- tests automatisés ;
- configuration de CI/CD ;
- configuration Docker ;
- fichiers d’exemple pour l’API OCR (fiches labo anonymisées)


Lis les fichiers du dossier consignes/ pour comprendre le besoin métier et la liste des tâches attendues.
Pour tous tes choix de développement, appuie-toi strictement sur l'architecture technique décrite dans le fichier docs/archi.md
