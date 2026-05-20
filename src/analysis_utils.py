"""
Utilitaires pour l'analyse exploratoire (EDA) et l'évaluation de modèles.

Rassemble les fonctions de :
- filtrage de features
- calculs de corrélations
- visualisations avancées avec Matplotlib/Seaborn
- évaluation unifiée de modèles de régression supportant la recherche d'hyperparamètres (Grid/Random Search).

Développé pour Python 3.10+ et Scikit-Learn.
"""

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV


# --- Manipulation de Features & Corrélations ---

def select_existing_features(features: Iterable[str], columns: Iterable[str]) -> List[str]:
    """
    Filtre une liste de variables souhaitées pour ne conserver que celles réellement présentes.

    Évite les erreurs d'exécution de type KeyError lors des sélections de colonnes.

    Parameters
    ----------
    features : Iterable[str]
        Liste ou itérable des colonnes cibles idéales.
    columns : Iterable[str]
        Liste ou itérable des colonnes présentes dans le DataFrame (ex: df.columns).

    Returns
    -------
    List[str]
        Liste filtrée des variables présentes, conservant l'ordre d'origine de `features`.
    """
    col_set = set(columns)
    return [c for c in features if c in col_set]


def top_correlated_features(
    X: pd.DataFrame,
    y: pd.Series,
    n: int = 6,
    numeric_only: bool = True,
) -> Tuple[pd.Series, List[str]]:
    """
    Calcule la corrélation linéaire de Pearson des variables numériques avec la variable cible (target).

    Parameters
    ----------
    X : pd.DataFrame
        Le DataFrame contenant les variables explicatives.
    y : pd.Series
        La variable cible (target).
    n : int, default=6
        Nombre de variables les plus fortement corrélées (en valeur absolue) à retourner.
    numeric_only : bool, default=True
        Si True, calcule les corrélations uniquement pour les colonnes numériques.

    Returns
    -------
    Tuple[pd.Series, List[str]]
        - pd.Series : Les coefficients de corrélation de toutes les variables avec la target.
        - List[str] : La liste des n colonnes affichant la corrélation absolue la plus élevée.
    """
    num_cols = X.select_dtypes(include=["number"]).columns
    df_corr = X[num_cols].copy()
    df_corr["target"] = y
    corr_target = df_corr.corr(numeric_only=numeric_only)["target"].drop("target")
    top_cols = (
        corr_target.abs().sort_values(ascending=False).head(n).index.tolist()
    )
    return corr_target, top_cols


# --- Visualisations Graphiques (EDA) ---

def plot_numeric_histograms(
    X: pd.DataFrame,
    bins: int = 40,
    n_cols: int = 3,
    figsize_per_col: Tuple[int, int] = (5, 3),
) -> None:
    """
    Génère une grille d'histogrammes pour toutes les variables numériques du DataFrame.

    Parameters
    ----------
    X : pd.DataFrame
        Le DataFrame contenant les variables numériques à visualiser.
    bins : int, default=40
        Nombre de classes (intervalles) pour les histogrammes.
    n_cols : int, default=3
        Nombre de graphiques (colonnes) à afficher par ligne de la grille.
    figsize_per_col : Tuple[int, int], default=(5, 3)
        Dimensions (largeur, hauteur) individuelles de chaque graphique.
    """
    num_cols = X.select_dtypes(include=["number"]).columns
    n_plots = len(num_cols)
    if n_plots == 0:
        return
    n_rows = math.ceil(n_plots / n_cols)
    plt.figure(figsize=(n_cols * figsize_per_col[0], n_rows * figsize_per_col[1]))
    for i, col in enumerate(num_cols, 1):
        plt.subplot(n_rows, n_cols, i)
        # Ajout du paramètre kde=True pour une meilleure lecture des distributions
        sns.histplot(X[col].dropna(), bins=bins, kde=True)
        plt.xlabel("")
        plt.ylabel("")
        plt.grid(True, alpha=0.3)
        plt.title(col)
    plt.tight_layout()
    plt.show()



def plot_qualitative(
    X: pd.DataFrame,
    top_n: int = 20,
    n_cols: int = 2,
    figsize_per_col: Tuple[int, int] = (6, 4),
    figsize: Optional[Tuple[int, int]] = None,
    height_per_row: int = 4,
) -> None:
    """
    Génère une grille de diagrammes en barres horizontales pour les variables qualitatives.

    Pratique pour observer la distribution des modalités et repérer les classes ultra-majoritaires.

    Parameters
    ----------
    X : pd.DataFrame
        Le DataFrame contenant les variables catégorielles ou booléennes.
    top_n : int, default=20
        Nombre maximal de modalités les plus fréquentes affichées par variable.
    n_cols : int, default=2
        Nombre de graphiques à afficher par ligne de la grille.
    figsize_per_col : Tuple[int, int], default=(6, 4)
        Dimensions (largeur, hauteur) par subplot si `figsize` n'est pas fourni.
    figsize : Tuple[int, int], optional
        Taille globale de la figure Matplotlib. Si fourni, outrepasse les calculs automatiques.
    height_per_row : int, default=4
        Hauteur allouée à chaque ligne de la grille dans le calcul automatique de la taille.
    """
    cat_cols = X.select_dtypes(include=["object", "category", "string", "bool"]).columns
    n_plots = len(cat_cols)
    if n_plots == 0:
        return

    n_rows = math.ceil(n_plots / n_cols)
    if figsize is None:
        figsize = (n_cols * figsize_per_col[0], n_rows * height_per_row)

    plt.figure(figsize=figsize)

    for i, col in enumerate(cat_cols, 1):
        plt.subplot(n_rows, n_cols, i)
        vc = X[col].astype("string").value_counts(dropna=False).head(top_n)
        sns.barplot(x=vc.values, y=vc.index, color="#439cc8")
        plt.xlabel("")
        plt.ylabel("")
        plt.title(col)
        plt.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_missing_bar(
    X: pd.DataFrame,
    top_n: Optional[int] = None,
    figsize: Tuple[int, int] = (8, 4),
) -> None:
    """
    Affiche un graphique en barres représentant le pourcentage de valeurs manquantes par colonne.

    Parameters
    ----------
    X : pd.DataFrame
        Le DataFrame à analyser.
    top_n : int, optional
        Si spécifié, affiche uniquement les n colonnes possédant le plus haut taux de NaN.
    figsize : Tuple[int, int], default=(8, 4)
        Dimensions (largeur, hauteur) du graphique.
    """
    missing_pct = (X.isna().mean() * 100).sort_values(ascending=False)
    if top_n is not None:
        missing_pct = missing_pct.head(top_n)

    plt.figure(figsize=figsize)
    sns.barplot(x=missing_pct.values, y=missing_pct.index, color="#439cc8")
    plt.xlabel("% de valeurs manquantes")
    plt.ylabel("Colonnes")
    plt.title("Taux de valeurs manquantes par colonne")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_scatter_vs_target(
    X: pd.DataFrame,
    y: pd.Series,
    cols: Iterable[str],
    transform_y: Optional[str] = None,
    figsize: Tuple[int, int] = (15, 10),
    alpha: float = 0.2,
    s: int = 10,
) -> None:
    """
    Trace des graphiques en nuage de points (Scatter Plots) de variables sélectionnées en fonction de la target.

    Permet de visualiser rapidement les relations non-linéaires ou la présence d'outliers.

    Parameters
    ----------
    X : pd.DataFrame
        Le DataFrame contenant les variables explicatives.
    y : pd.Series
        La variable cible (target).
    cols : Iterable[str]
        Liste des colonnes de X à tracer sur l'axe des abscisses.
    transform_y : {"log1p", None}, optional
        Si "log1p", applique la transformation $\log(1+y)$ sur la cible pour le graphique.
    figsize : Tuple[int, int], default=(15, 10)
        Dimensions globales de la figure.
    alpha : float, default=0.2
        Opacité/transparence des points (utile pour limiter les effets d'overlapping).
    s : int, default=10
        Taille des points dans le nuage.
    """
    if transform_y == "log1p":
        y_vals = np.log1p(y.values)
    else:
        y_vals = y.values

    cols = list(cols)
    if not cols:
        return

    n_rows = math.ceil(len(cols) / 3)
    plt.figure(figsize=figsize)
    for i, col in enumerate(cols, 1):
        plt.subplot(n_rows, 3, i)
        mask = X[col].notna()
        sns.scatterplot(x=X.loc[mask, col], y=y_vals[mask], s=s, alpha=alpha)
        plt.title(f"{transform_y + ' ' if transform_y else ''}target vs {col}")
    plt.tight_layout()
    plt.show()


def plot_corr_heatmap(
    df: pd.DataFrame,
    method: str = "pearson",
    title: str = "Heatmap des corrélations",
    figsize: Tuple[int, int] = (12, 10),
    annot: bool = True,
    fmt: str = ".2f",
    vmin: float = -1,
    vmax: float = 1,
    cmap: str = "coolwarm",
) -> None:
    """
    Affiche la matrice de corrélation des variables numériques sous forme de Heatmap.

    Parameters
    ----------
    df : pd.DataFrame
        Le DataFrame contenant les données.
    method : {"pearson", "kendall", "spearman"}, default="pearson"
        Méthode de calcul du coefficient de corrélation.
    title : str, default="Heatmap des corrélations"
        Titre principal du graphique.
    figsize : Tuple[int, int], default=(12, 10)
        Dimensions de la figure.
    annot : bool, default=True
        Si True, inscrit la valeur numérique du coefficient dans chaque cellule.
    fmt : str, default=".2f"
        Format de chaîne de caractères pour les annotations (ex : ".2f" pour 2 décimales).
    vmin : float, default=-1
        Valeur minimale de l'échelle de couleurs.
    vmax : float, default=1
        Valeur maximale de l'échelle de couleurs.
    cmap : str, default="coolwarm"
        Palette de couleurs de Seaborn à utiliser.
    """
    corr = df.select_dtypes(include=[np.number]).corr(method=method)
    plt.figure(figsize=figsize)
    sns.heatmap(corr, annot=annot, fmt=fmt, vmin=vmin, vmax=vmax, cmap=cmap)
    plt.title(title)
    plt.tight_layout()
    plt.show()


# --- Évaluation Multi-Modèles Réutilisable ---

def evaluate_regression_model(
    algo: Any,
    param_grid: Optional[Dict[str, Any]],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    search_type: str = 'grid',
    scoring: str = 'r2',
    cv: int = 5,
    inverse_transform_y: Optional[str] = None
) -> Dict[str, Any]:
    """
    Entraîne, optimise par recherche d'hyperparamètres (optionnel) et évalue un modèle de régression.

    Affiche les performances standard ($R^2$, RMSE, MAE) sur l'ensemble de test et prend en charge
    la transformation inverse automatique de la variable cible si celle-ci a été transformée en log.

    Parameters
    ----------
    algo : Any
        L'instance de l'algorithme Scikit-Learn non entraîné (ex : RandomForestRegressor()).
    param_grid : Dict[str, Any] ou None
        La grille d'hyperparamètres à tester. Si None ou vide, le modèle est entraîné directement
        avec ses paramètres par défaut (sans recherche d'hyperparamètres).
    X_train : pd.DataFrame
        Features de l'ensemble d'entraînement.
    y_train : pd.Series
        Target de l'ensemble d'entraînement.
    X_test : pd.DataFrame
        Features de l'ensemble de test.
    y_test : pd.Series
        Target de l'ensemble de test.
    search_type : {'grid', 'random'}, default='grid'
        Type de recherche d'hyperparamètres à appliquer si `param_grid` est fourni.
    scoring : str, default='r2'
        La métrique Scikit-Learn utilisée pour guider la validation croisée.
    cv : int, default=5
        Nombre de plis (folds) pour la validation croisée.
    inverse_transform_y : {'expm1', None}, optional
        Si 'expm1', applique `np.expm1()` sur les prédictions et la target de test avant de calculer
        et afficher les métriques, ce qui permet d'évaluer le modèle dans l'unité réelle de la donnée.

    Returns
    -------
    Dict[str, Any]
        Un dictionnaire contenant les artéfacts et résultats d'évaluation :
        - "best_model" : Le modèle entraîné (éventuellement le meilleur estimateur issu de la recherche).
        - "best_params" : Les hyperparamètres retenus par le modèle.
        - "r2" : Score R² calculé sur l'ensemble de test.
        - "rmse" : Racine de l'erreur quadratique moyenne sur le test.
        - "mae" : Erreur absolue moyenne sur le test.
        - "cv_results" : L'attribut `.cv_results_` de l'objet de recherche (ou None si pas d'optimisation).
    """
    if param_grid is None or len(param_grid) == 0:
        best_model = algo
        best_model.fit(X_train, y_train)
        best_params = algo.get_params()
        cv_results = None
    else:
        if search_type == 'grid':
            search = GridSearchCV(algo, param_grid, cv=cv, scoring=scoring, n_jobs=-1)
        elif search_type == 'random':
            search = RandomizedSearchCV(algo, param_grid, cv=cv, scoring=scoring, n_jobs=-1, random_state=42)
        else:
            raise ValueError("search_type doit être 'grid' ou 'random'")
        
        search.fit(X_train, y_train)
        best_model = search.best_estimator_
        best_params = search.best_params_
        cv_results = search.cv_results_  # Correction : .cv_results_ est un attribut, pas une méthode.

    # Prédictions sur le jeu de Test
    y_pred = best_model.predict(X_test)

    # Gestion de la transformation inverse pour l'évaluation métier (ex: Target en Log)
    if inverse_transform_y == 'expm1':
        y_test_eval = np.expm1(y_test)
        y_pred_eval = np.expm1(y_pred)
        unit = " (Unités réelles)"
    else:
        y_test_eval = y_test
        y_pred_eval = y_pred
        unit = ""

    # Calcul des métriques de régression
    r2 = r2_score(y_test_eval, y_pred_eval)
    rmse = mean_squared_error(y_test_eval, y_pred_eval) ** 0.5
    mae = mean_absolute_error(y_test_eval, y_pred_eval)

    # Affichage des résultats
    print(f"=== Modèle : {algo.__class__.__name__} ===")
    print(f"Meilleurs paramètres : {best_params}")
    print(f"R2 (Test){unit} : {r2:.4f}")
    print(f"RMSE : {rmse:.2f}")
    print(f"MAE  : {mae:.2f}")

    return {
        "best_model": best_model,
        "best_params": best_params,
        "r2": r2,
        "rmse": rmse,
        "mae": mae,
        "cv_results": cv_results
    }