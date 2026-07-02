## Les API d'OCR Cloud "Classiques" (Ex: OCR.space, suggéré par le sujet)

**Fonctionnement :**
Envoi de l'image via requête HTTP, retour d'un JSON brut contenant le texte extrait

Avantages : Gratuit en développement, très facile à intégrer dans une API Flask/FastAPI, écosystème mature

**Inconvénients :**
Le JSON retourné est souvent très "plat". Il faudra coder une logique de parsing (avec des expressions régulières) pour associer chaque valeur (ex: 7,6) à sa mesure (pH).
**Adéquation au projet :**
Excellente pour un MVP rapide (Chemin critique)

## Les services Cloud "Document Intelligence"
(Ex: AWS Textract, Azure Document Intelligence, Google Cloud Vision)

**Fonctionnement :**
Services IA spécialisés dans l'extraction de formulaires et de tableaux.
**Avantages :**
Compréhension native de la structure "Clé-Valeur". Il peut isoler automatiquement que la ligne "Turbidité" correspond à la valeur "0,7 NTU"

**Inconvénients :**
Nécessite de créer des comptes Cloud (AWS/GCP), de gérer des permissions complexes (IAM) et d'ajouter un SDK lourd à un environnement uv.
**Adéquation au projet :**
Très performant, mais ajoute une complexité opérationnelle (overhead) non nécessaire pour une équipe étudiante sur un cycle court

## Les solutions Open Source / Locales
(Ex: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) via pytesseract)

**Fonctionnement :**
Le moteur OCR tourne directement dans un conteneur Docker.
**Avantages :**
- 100% gratuit
- aucune dépendance externe
- parfait pour la conformité RGPD (les données ne quittent jamais mon serveur)

**Inconvénients :**
- Demande l'installation de binaires C++ dans le Dockerfile.
- La précision est souvent moins bonne sur des documents bruités sans utiliser de bibliothèques de traitement d'image comme OpenCV en amont.

**Adéquation au projet :**
Intéressant techniquement, mais risqué pour le timing du projet.

## conclusion
**Choix retenu :** API OCR.space
**Besoin :** Nous devons extraire le texte de fiches de laboratoire avec un minimum de configuration pour valider l'ingestion automatisée

**Équipe :** L'équipe a un temps limité. Un service externe permet de déléguer la complexité de la vision par ordinateur

**Contraintes :** Le service est gratuit en environnement de développement et s'intègre parfaitement via de simples requêtes HTTP dans notre middleware Flask protégé par clé API

**Atténuation du risque :** Bien que les données soient envoyées à un service tiers, nous nous assurons que les fiches labo (fournies anonymisées
) ne contiennent pas de PII (Personally Identifiable Information) critiques hors de l'ID technique, respectant ainsi notre démarche RGPD

