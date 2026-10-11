"""
Fonctions de validation de données
"""

import logging

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


def check_code_commune_formatting(
    connection: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
):
    """Vérifie que code_commune a 5 caractères et commence par le département"""

    query = (
        "SELECT COUNT(*) AS n_bad "
        "FROM df "
        "WHERE length(code_commune) <> 5 "
        "OR NOT starts_with(code_commune, code_departement)"
    )

    bad = connection.sql(query).fetchone()[0]

    if bad == 0:
        logger.info(
            "Test OK: colonne 'code_commune' toujours composée de 5 caractères "
            "commençant par le code département"
        )
    else:
        logger.warning(
            f"Problème dans la colonne code_commune: {bad} codes mal formés."
        )


def check_missing_values(
    connection: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
    variable: str = "valeur_fonciere",
):
    """Recense les valeurs manquantes d'une variable"""

    query = f"SELECT COUNT(*) AS n_missing FROM df WHERE {variable} IS NULL"

    n_missing = connection.sql(query).fetchone()[0]

    message_ok = f"Pas de valeur manquante pour la variable {variable}"
    message_warn = f"{n_missing} valeurs manquantes pour la variable {variable}"
    if n_missing == 0:
        logger.info(message_ok)
    else:
        logger.warning(message_warn)


def check_data_leakage(
    train_dataset: pd.DataFrame,
    test_dataset: pd.DataFrame,
    variable: str,
):
    """Vérifie que les modalités de l'apprentissage sont présentes dans le test"""

    if set(train_dataset[variable].dropna().unique()) - set(
        test_dataset[variable].dropna().unique()
    ):
        logger.error(f"Problème de data leakage pour la variable {variable}")
    else:
        logger.info(f"Pas de problème de data leakage pour la variable {variable}")
