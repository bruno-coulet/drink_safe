"""
-------------------------------------------------------------------------------
Projet : Waterflow 2
Composant : Utilitaire — Génération des hash bcrypt pour les mots de passe admin
Description : Génère les valeurs à placer dans .env pour les variables
              ADMIN_ANALYSTE_PASSWORD_HASH et ADMIN_EXPLOITATION_PASSWORD_HASH.

Usage :
    uv run python scripts/hash_admin_passwords.py
    (saisie interactive des mots de passe souhaités)
-------------------------------------------------------------------------------
"""

import getpass
from werkzeug.security import generate_password_hash


def main() -> None:
    print("--- Génération des hash bcrypt pour les mots de passe admin ---\n")

    for role in ("analyste", "exploitation"):
        mdp = getpass.getpass(f"Mot de passe pour '{role}' : ")
        confirmation = getpass.getpass("Confirmer : ")

        if mdp != confirmation:
            print(f"[ERREUR] Les mots de passe pour '{role}' ne correspondent pas.\n")
            continue

        hash_bcrypt = generate_password_hash(mdp)
        var = f"ADMIN_{role.upper()}_PASSWORD_HASH"
        print(f"\nAjouter dans .env :")
        print(f"{var}={hash_bcrypt}\n")


if __name__ == "__main__":
    main()
