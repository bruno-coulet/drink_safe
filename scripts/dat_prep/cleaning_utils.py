"""
Utilitaires pour le nettoyage et la préparation de données.

Fonctions d'exploration rapide des colonnes
Met en œuvre un paradigme 'fit_transform' / 'transform' déterministe afin d'éviter tout risque
de fuite de données (Data Leakage) entre les ensembles d'entraînement et de test.

Développé pour Python 3.10+ et Pandas.
"""

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd


# --- Exploration & Diagnostic ---

def get_missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule le taux de remplissage, le nombre de valeurs manquantes et le type de chaque colonne.

    Parameters
    ----------
    df : pd.DataFrame
        Le DataFrame à analyser.

    Returns
    -------
    pd.DataFrame
        Un DataFrame contenant les colonnes ['type', 'missing_count', 'fill_rate_%'],
        trié par nombre de valeurs manquantes décroissant.
    """
    return pd.DataFrame({
        'type': df.dtypes,
        'missing_count': df.isna().sum(),
        'fill_rate_%': (df.count() / len(df) * 100).round(2)
    }).sort_values(by='missing_count', ascending=False)


def get_special_columns(df: pd.DataFrame, max_modalities: int = 20) -> Dict[str, List[str]]:
    """
    Identifie et catégorise les colonnes du DataFrame selon leurs propriétés structurelles.

    Pratique pour isoler rapidement les variables à traiter lors de l'EDA ou avant un encodage.

    Parameters
    ----------
    df : pd.DataFrame
        Le DataFrame à analyser.
    max_modalities : int, default=20
        Seuil de cardinalité au-delà duquel une variable textuelle est considérée
        comme ayant une forte cardinalité (ex: identifiants, adresses, descriptions).

    Returns
    -------
    Dict[str, List[str]]
        Un dictionnaire contenant les listes de noms de colonnes pour les clés suivantes :
        - "empty" : Colonnes intégralement vides (uniquement des NaN).
        - "constant" : Colonnes contenant une seule valeur unique (ou constantes avec NaN).
        - "numeric" : Colonnes de type numérique (int, float).
        - "categorical" : Colonnes de type objet, chaîne de caractères ou catégorie.
        - "high_cardinality" : Colonnes textuelles dont le nombre de valeurs uniques dépasse `max_modalities`.
        - "boolean" : Colonnes assimilables à des booléens (valeurs incluses dans {True, False, 1, 0, NaN}).
    """
    string_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
    return {
        "empty": df.columns[df.isna().all()].tolist(),
        "constant": df.columns[df.nunique(dropna=False) <= 1].tolist(),
        "numeric": df.select_dtypes(include=['number']).columns.tolist(),
        "categorical": string_cols,
        "high_cardinality": [c for c in string_cols if df[c].nunique(dropna=True) > max_modalities],
        "boolean": [col for col in df.columns if set(df[col].dropna().unique()).issubset({True, False, 1, 0})]
    }


# --- Nettoyage Vectorisé (Performant) ---

def normalize_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise les colonnes textuelles en minuscules et supprime les accents de manière vectorisée.

    Cette fonction convertit les chaînes en forme décomposée (NFD) pour filtrer les caractères
    diacritiques, garantissant un traitement rapide même sur de grands volumes de données.
    Les chaînes résiduelles assimilables à du vide ('nan', 'none') sont reconverties en vrais NaN.

    Parameters
    ----------
    df : pd.DataFrame
        Le DataFrame contenant les features textuelles à normaliser.

    Returns
    -------
    pd.DataFrame
        Une copie du DataFrame original avec les colonnes textuelles nettoyées.
    """
    df = df.copy()
    string_cols = df.select_dtypes(include=['object', 'string']).columns
    for col in string_cols:
        df[col] = df[col].astype(str).str.lower()
        df[col] = df[col].str.normalize('NFD').str.replace(r'[\u0300-\u036f]', '', regex=True)
        df[col] = df[col].replace({'nan': np.nan, 'none': np.nan})
    return df


# --- Pipeline Anti-Leakage (Train / Test Split Compliant) ---

def fit_transform_clean(X_train: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Nettoie le jeu d'entraînement (Train Set) et calcule les statistiques associées pour imputation.

    Cette fonction calcule les métriques (médianes, modes, colonnes à supprimer) exclusivement
    sur le jeu d'entraînement, garantissant l'étanchéité du pipeline vis-à-vis du jeu de test.

    Parameters
    ----------
    X_train : pd.DataFrame
        Le DataFrame d'entraînement (Features uniquement).
    config : Dict[str, Any]
        Dictionnaire de configuration spécifiant les actions à mener. Exemple :
        {
            "drop_na_threshold": 0.40,
            "binary_cols": ["has_elevator", "is_renovated"],
            "replace_maps": {"floor": {"bajo": 0, "entresuelo": 0.5}},
            "numeric_median_cols": ["sq_mt_built", "n_rooms"]
        }

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any]]
        - pd.DataFrame : Le Train set nettoyé et imputé.
        - Dict[str, Any] : Le dictionnaire 'stats' contenant les valeurs calculées
          (médianes, modes, colonnes supprimées) à passer impérativement à `transform_clean`.
    """
    X = X_train.copy()
    stats = {}

    # 1. Suppression des colonnes dont le taux de valeurs manquantes dépasse le seuil
    threshold = config.get("drop_na_threshold", 1.0)
    high_na = X.columns[X.isna().mean() > threshold].tolist()
    stats["cols_to_drop"] = high_na
    X = X.drop(columns=high_na)

    # 2. Apprentissage et imputation du Mode pour les variables binaires / qualitatives
    bin_cols = [c for c in config.get("binary_cols", []) if c in X.columns]
    stats["modes"] = {c: X[c].mode()[0] for c in bin_cols if not X[c].mode().empty}
    for c in stats["modes"]:
        X[c] = X[c].fillna(stats["modes"][c])

    # 3. Remplacement des valeurs mapping (ex: textuel -> numérique ou corrections)
    for col, replace_map in config.get("replace_maps", {}).items():
        if col in X.columns:
            X[col] = X[col].replace(replace_map)

    # 4. Apprentissage et imputation de la Médiane pour les variables numériques
    num_cols = [c for c in config.get("numeric_median_cols", []) if c in X.columns]
    stats["medians"] = {}
    for c in num_cols:
        X[c] = pd.to_numeric(X[c], errors="coerce")
        stats["medians"][c] = X[c].median()
        X[c] = X[c].fillna(stats["medians"][c])

    return X, stats


def transform_clean(X_test: pd.DataFrame, stats: Dict[str, Any], config: Dict[str, Any]) -> pd.DataFrame:
    """
    Applique strictement les statistiques issues du Train Set sur le jeu de Test (ou d'Inférence).

    Aucune statistique (médiane, mode, etc.) n'est recalculée sur ce jeu de données,
    évitant ainsi le Data Leakage de manière rigoureuse.

    Parameters
    ----------
    X_test : pd.DataFrame
        Le DataFrame de test ou de validation à nettoyer.
    stats : Dict[str, Any]
        Le dictionnaire de statistiques généré par la fonction `fit_transform_clean`.
    config : Dict[str, Any]
        Le dictionnaire de configuration de nettoyage (utilisé pour ré-appliquer les replace_maps).

    Returns
    -------
    pd.DataFrame
        Le DataFrame de test nettoyé, aligné avec la structure et les valeurs du Train set.
    """
    X = X_test.copy()

    # 1. Alignement des colonnes supprimées
    X = X.drop(columns=stats.get("cols_to_drop", []), errors="ignore")

    # 2. Imputation par les modes appris sur le Train set
    for c, mode_val in stats.get("modes", {}).items():
        if c in X.columns:
            X[c] = X[c].fillna(mode_val)

    # 3. Application des replace_maps de la configuration
    for col, replace_map in config.get("replace_maps", {}).items():
        if col in X.columns:
            X[col] = X[col].replace(replace_map)

    # 4. Imputation par les médianes apprises sur le Train set
    for c, median_val in stats.get("medians", {}).items():
        if c in X.columns:
            X[c] = pd.to_numeric(X[c], errors="coerce")
            X[c] = X[c].fillna(median_val)

    return X
