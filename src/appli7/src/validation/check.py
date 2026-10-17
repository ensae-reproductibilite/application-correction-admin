"""
Data validation functions
"""

import logging

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


def check_code_commune_formatting(
    connection: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
):
    """Check that code_commune has 5 characters and starts with the department"""

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
    """Count the missing values of a variable"""

    query = f"SELECT COUNT(*) AS n_missing FROM df WHERE {variable} IS NULL"

    n_missing = connection.sql(query).fetchone()[0]

    message_ok = f"Pas de valeur manquante pour la variable {variable}"
    message_warn = f"{n_missing} valeurs manquantes pour la variable {variable}"
    if n_missing == 0:
        logger.info(message_ok)
    else:
        logger.warning(message_warn)


def check_unseen_categories(
    train_dataset: pd.DataFrame,
    test_dataset: pd.DataFrame,
    variable: str,
):
    """Check that every test category also appears in the training set

    Unseen categories are encoded as unknown (-1): the model has learned nothing
    about them, so their predictions are unreliable.
    """

    if set(test_dataset[variable].dropna().unique()) - set(
        train_dataset[variable].dropna().unique()
    ):
        logger.warning(f"Modalités de {variable} absentes de l'apprentissage")
    else:
        logger.info(
            f"Toutes les modalités de {variable} du test sont connues du modèle"
        )
