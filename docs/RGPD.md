#  Note de Conformité RGPD & Gouvernance des Données
Projet : Waterflow 2 - Plateforme "Drink Safe"

Version : 2.0 (Alignée sur l'API Unique FastAPI et le Frontend Multi-Profils Flask)
Date : 25 Juin 2026

Statut : Conforme aux directives de la CNIL et du RGPD (Privacy by Design & by Default)

## 1. Introduction et Périmètre
Dans le cadre de l'industrialisation de la plateforme Waterflow 2 (Drink Safe) pour la collectivité territoriale, la collecte et le traitement de données physico-chimiques sur la potabilité de l'eau s'accompagnent de la gestion d'informations relatives aux clients finaux (exploitants, collectivités, particuliers) [1, 2, 10].

Cette note explicite la manière dont la plateforme intègre les exigences du Règlement Général sur la Protection des Données (RGPD), notamment en ce qui concerne la minimisation des données, le cloisonnement des accès par clé API, la traçabilité des actions et la politique de conservation [10, 18].

## 2. Identification des Données à Caractère Personnel (DCP)
Conformément au principe de minimisation des données (Article 5.1.c du RGPD), la plateforme ne collecte que les informations strictly nécessaires à la fourniture du service d'analyse et de facturation :

Données d'identité du client (DCP) :
client_id : Identifiant technique unique (UUID ou chaîne standardisée) [9, 10].
nom_structure : Dénomination sociale de la structure cliente (collectivité, entreprise, ou nom du particulier) [9, 11].
adresse_postale : Adresse physique requise pour la localisation géographique des prélèvements et la facturation [9, 11].
Données de sécurité (DCP indirectes) :
api_key : Jeton d'accès (token d'authentification) haché en base de données pour sécuriser les requêtes HTTP [9, 10].
Données techniques et de traçabilité (DCP indirectes) :
action_logs : Adresse IP d'origine (anonymisée à l'adresse réseau), client_id associé, route de l'API interrogée, code de statut HTTP et temps de traitement [12, 18].
Données d'analyse (Données non personnelles, mais associées au client) :
Mesures physico-chimiques de l'eau (pH, Turbidité, Chloramines, etc.) associées à un client_id [14].
## 3. Gouvernance des Accès et Isolation par Clé API
La sécurité et l'étanchéité des données reposent sur un modèle d'authentification standardisée par clé API.

                     [ Requête HTTP avec Header 'X-API-Key' ]
                                        │
                                        ▼
                            [ Middleware de Sécurité ]
                                        │
                  ┌─────────────────────┴─────────────────────┐
                  ▼                                           ▼
          [ Clé API Valide ]                        [ Clé API Invalide ]
                  │                                           │
                  ▼                                           ▼
       [ Extraction du client_id ]                     [ Erreur 401 ]
                  │                                     Unauthorized
                  ▼
   [ Requête SQL : Clauses WHERE client_id ]
                  │
                  ▼
 [ Restitution Uniquement des Données du Client ]
A. Séparation Stricte des Périmètres (Multi-Tenant)
Principe : Un client ne peut jamais accéder aux données d'un autre client.
Implémentation : Le middleware de l'API FastAPI intercepte l'en-tête X-API-Key. Il valide la clé en base de données PostgreSQL, extrait le client_id associé, et l'injecte de manière transparente dans les requêtes SQL [9, 10]. Toutes les requêtes de consultation (ex: GET /api/measurements) appliquent un filtre strict :
SELECT * FROM prelevements WHERE client_id = :id_client_authentifie;
L'application Flask hôte (sur le port 5001) répercute ce cloisonnement en affichant uniquement les tableaux de bord propres au compte authentifié via son fichier client.py.
B. Matrice de Droits et Rôles (RBAC) [9]
Fonctionnalités	Client Final [9]	Analyste Qualité [9]	Responsable d'Exploitation [9]
Dépôt de prélèvements (Standard & OCR) [9]	✅ Oui	❌ Non	❌ Non
Consultation de ses propres données [9]	✅ Oui	✅ Oui	❌ Non
Consultation de l'historique global [9]	❌ Non	✅ Oui	✅ Oui
Accès aux dashboards de performance ML [9]	❌ Non	✅ Oui	❌ Non
Suivi technique & Logs d'audit [9]	❌ Non	❌ Non	✅ Oui
Gestion des clés (Création/Régénération) [9]	❌ Non	✅ Oui	✅ Oui
## 4. Gestion et Cycle de Vie des Clés API
La clé API est le garant de l'identité numérique du client sur la plateforme. Sa gestion respecte des mesures de sécurité cryptographiques strictes :

Génération Sécurisée : Les clés API sont générées de manière cryptographiquement forte à l'aide de bibliothèques Python sécurisées (ex: secrets.token_urlsafe(32)).
Stockage Haché : Pour éviter qu'une compromission de la base de données PostgreSQL ne dévoile les clés d'accès des clients en clair, la plateforme utilise la stratégie de hachage des clés (via un sel et l'algorithme SHA-256 ou bcrypt). Seule la signature hachée est stockée.
Protocole de Régénération (En cas de compromission) :
L'administrateur (Analyste ou Responsable d'Exploitation) peut déclencher la route POST /api/clients/{id}/regenerate-key [9, 11].
La clé API précédente est immédiatement marquée comme révoquée (désactivée) en base de données.
Une nouvelle clé est générée, renvoyée une seule fois à l'écran du client, puis hachée et sauvegardée.
Le client doit immédiatement mettre à jour sa configuration locale (ou sur l'interface Flask) sous peine d'obtenir une erreur 401 Unauthorized.
## 5. Politique de Journalisation (Audit Trail) et Logs
La journalisation des accès est une obligation légale pour répondre aux exigences de sécurité du RGPD (Article 32) et permettre des audits de sécurité en cas d'incident.

Données journalisées (action_logs) :
Horodatage exact (timestamp).
Identifiant technique du client (client_id).
Route d'API appelée (ex: /api/ocr/lab-report).
Code statut HTTP de réponse (ex: 200, 401, 500).
Temps de traitement en millisecondes (duration).
Sécurité des logs : Les logs d'exploitation ne contiennent aucune mesure physico-chimique en clair ni de données de facturation. Ils sont stockés de manière centralisée dans PostgreSQL et accessibles uniquement au Responsable d'Exploitation via l'interface exploitation/dashboard.html [9, 12].
## 6. Durées de Conservation des Données
Conformément à l'obligation de limitation de la conservation (Article 5.1.e du RGPD), les données sont purgées ou anonymisées une fois l'objectif atteint :

Catégorie de Données	Durée de Conservation	Base Légale / Justification	Action de Fin de Cycle
Profils Clients	Durée de la relation contractuelle	Exécution d'un contrat	Suppression définitive de la ligne en base de données sous 30 jours après résiliation.
Prélèvements & Mesures	5 ans	Intérêt légitime (Analyses statistiques et évolution temporelle de la potabilité)	Anonymisation complète (suppression du lien client_id). Les mesures physico-chimiques brutes sont conservées à des fins d'entraînement de l'IA.
Fiches Labo (PDF/Images)	Immédiat (après parsing OCR)	Minimisation des données	Suppression physique définitive du disque temporaire (temp/) dès que l'extraction par l'API OCR a été validée [17].
Journaux d'Accès (Logs)	1 an (strict)	Obligation légale (CNIL - Sécurité des systèmes d'information)	Suppression automatique ou archivage déconnecté.
## 7. Exercice des Droits des Utilisateurs
La plateforme met à disposition des clients finaux les mécanismes nécessaires au respect de leurs droits individuels :

Droit d'accès et de portabilité (Article 15 & 20) : Depuis son tableau de bord Flask, le client dispose d'un bouton d'export lui permettant de télécharger l'intégralité de son historique d'analyses et ses données de profil au format structuré JSON ou CSV.
Droit de rectification (Article 16) : Les demandes de modification d'adresse ou de raison sociale sont transmises aux administrateurs pour mise à jour rapide de la table clients.
Droit à l'oubli / Effacement (Article 17) : En cas de départ de la collectivité, toutes les DCP sont supprimées. Les prélèvements d'eau sont anonymisés pour préserver l'historique d'apprentissage des modèles sans compromettre la vie privée
