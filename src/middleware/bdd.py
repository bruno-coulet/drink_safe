"""
Persistance de données (PostgreSQL)
Définition des schémas de tables (Clients, Prélèvements, Logs)
pour assurer la conformité et la traçabilité RGPD.
"""

# Emplacement futur pour tes classes de base de données, par exemple :
# class Client(db.Model):
#     client_id = db.Column(db.String(50), primary_key=True)
#     api_key = db.Column(db.String(255), unique=True)

import os
import psycopg2
from dotenv import load_dotenv

# Charger les variables d'environnement (.env)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def init_db():
    """Connecte PostgreSQL et crée la table prelevements si elle n'existe pas."""
    print("Connexion à PostgreSQL et initialisation de la table...")
    
    # Structure SQL de ta table applicative
    # Le mot-clé SERIAL va forcer PostgreSQL à générer de vrais ID (1, 2, 3...)
    query_create_table = """
    CREATE TABLE IF NOT EXISTS prelevements (
        id SERIAL PRIMARY KEY,
        date_prelevement VARCHAR(50),
        client_id VARCHAR(50),
        provenance VARCHAR(50),
        ph FLOAT,
        hardness FLOAT,
        solids FLOAT,
        chloramines FLOAT,
        sulfate FLOAT,
        conductivity FLOAT,
        organic_carbon FLOAT,
        trihalomethanes FLOAT,
        turbidity FLOAT,
        observations TEXT
    );
    """
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(query_create_table)
        conn.commit()
        cursor.close()
        conn.close()
        print("Base de données initialisée avec succès ! La table 'prelevements' est prête.")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de PostgreSQL : {e}")

if __name__ == "__main__":
    init_db()