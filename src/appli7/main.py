"""
Prédiction du prix au m² des logements vendus en petite couronne parisienne
à partir des données DVF enrichies par des données socio-économiques (Filosofi)
"""

import argparse
import logging
import os
from pathlib import Path

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from dotenv import load_dotenv
from lightgbm import LGBMRegressor
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OrdinalEncoder
from skore import EstimatorReport

from src.data.import_data import download_sources, get_melodi_indicator
from src.validation.check import (
    check_code_commune_formatting,
    check_data_leakage,
    check_missing_values,
)

load_dotenv()
con = duckdb.connect(database=":memory:")

logging.basicConfig(
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.INFO,
    handlers=[logging.FileHandler("recording.log"), logging.StreamHandler()],
)

# Le niveau DEBUG n'est activé que pour nos messages : au niveau global,
# les librairies utilisées (matplotlib notamment) inonderaient le log
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

LEARNING_RATE = 0.03
NUM_LEAVES = 31
NUMERIC_FEATURES = [
    "log_surface",
    "log_distance_eiffel",
    "nombre_pieces_principales",
    "nombre_lots",
    "log_surface_terrain",
    "ratio_carrez",
    "nbre_menages",
    "tx_pauvrete",
    "nv_vie_moyen",
    "part_proprietaires",
    "part_logements_sociaux",
    "part_logements_avant_1945",
    "surface_moyenne_logements",
    "NIVVIE_MEDIAN",
    "TAUX_PAUVRETE",
]
CATEGORICAL_FEATURES = ["code_commune", "type_local"]
DEPARTEMENTS_PARIS = ["75", "92", "93", "94"]

jeton_api = os.environ["JETON_API"]

DATA_LOCATION = Path("data/raw")
DERIVED_DATA_LOCATION = Path("data/derived")
SOURCES = {
    "dvf.parquet": (
        "https://minio.lab.sspcloud.fr/"
        "projet-formation/nouvelles-sources/data/geoparquet/dvf.parquet"
    ),
    "filosofi_carreaux_200m_2021.parquet": (
        "https://www.data.gouv.fr/api/1/datasets/r/55432374-a91d-43d0-923d-4514dc3eb951"
    ),
}


# ENVIRONMENT CONFIGURATION ---------------------------

parser = argparse.ArgumentParser(description="Paramètres du modèle LightGBM")
parser.add_argument("--n_trees", type=int, default=1500, help="Nombre d'arbres")
args = parser.parse_args()

n_trees = args.n_trees

logger.debug(f"Valeur de l'argument n_trees: {n_trees}")


# IMPORT DES DONNEES  ---------------------------------------

logger.debug(f"\n{80 * '-'}\nLecture des données\n{80 * '-'}")

DATA_LOCATION.mkdir(parents=True, exist_ok=True)

for nom_fichier, url_source in SOURCES.items():
    chemin = DATA_LOCATION / nom_fichier
    if chemin.exists():
        logger.info(
            f"{nom_fichier} déjà présent ({chemin.stat().st_size / 1e6:.0f} Mo)"
        )
    else:
        logger.info(f"Téléchargement de {nom_fichier} ...")
        download_sources(url_source, chemin)
        logger.info(f"  -> {chemin.stat().st_size / 1e6:.0f} Mo")

dvf = gpd.read_parquet(DATA_LOCATION / "dvf.parquet")


# QUALITY DIAGNOSTICS  ---------------------------------------

logger.debug(f"\n{80 * '-'}\nValidation des données\n{80 * '-'}")

# DuckDB ne sait pas lire la colonne geometry, on regarde les autres colonnes
dvf_attributs = dvf.drop(columns="geometry")

column_names = con.sql("SELECT column_name FROM (DESCRIBE dvf_attributs)").to_df()[
    "column_name"
]  # DuckDB ici, sinon dvf_attributs.columns serait OK

check_code_commune_formatting(connection=con, df=dvf_attributs)

for var in column_names:
    check_missing_values(connection=con, df=dvf_attributs, variable=var)


# RESTRICTION DU CHAMP ---------------------------------------

logger.info("Restriction aux départements de la petite couronne")

dvf = dvf.loc[dvf["code_departement"].isin(DEPARTEMENTS_PARIS)]
dvf = dvf.loc[dvf["valeur_fonciere"] < 1e6]


# DONNEES SUPPLEMENTAIRES -----------------------

# 1/ Données carroyées Filosofi (carreaux de 200m) ===============

filo_cols = [
    "idcar_200m",
    "ind",
    "men",
    "men_pauv",
    "men_prop",
    "ind_snv",
    "log_soc",
    "log_av45",
    "men_surf",
    "geometry",
]
filo = gpd.read_parquet(
    DATA_LOCATION / "filosofi_carreaux_200m_2021.parquet", columns=filo_cols
)
filo = filo.rename(
    columns={
        "men": "nbre_menages",
        "men_pauv": "nbre_menages_pauvres",
        "men_prop": "nbre_menages_prop",
        "ind_snv": "somme_nv_vie",
        "log_soc": "nbre_logements_sociaux",
        "log_av45": "nbre_logements_avant_1945",
        "men_surf": "surface_totale_logements",
    }
)

logger.info(
    f"Reprojection de {dvf.shape[0]} transactions immobilières "
    f"du CRS {dvf.crs.to_epsg()} à {filo.crs.to_epsg()}"
)

dvf = dvf.to_crs(filo.crs)
dvf = dvf.sjoin(filo, how="left", predicate="within")


# 2/ Données au niveau communal (API Melodi) ====================

niveau_vie = get_melodi_indicator(
    code="MED_SL", value_name="NIVVIE_MEDIAN", jeton_api=jeton_api
)
taux_pauvrete = get_melodi_indicator(
    code="PR_MD60", value_name="TAUX_PAUVRETE", jeton_api=jeton_api
)

# Fusion avec les transactions

dvf = dvf.merge(niveau_vie, left_on="code_commune", right_on="CODGEO", how="left").drop(
    columns="CODGEO"
)
dvf = dvf.merge(
    taux_pauvrete, left_on="code_commune", right_on="CODGEO", how="left"
).drop(columns="CODGEO")

logger.debug(f"Aperçu des données enrichies:\n{dvf.head(5)}")


# DESCRIPTIVE STATISTICS ---------------------------------------

logger.debug(f"\n{80 * '-'}\nStatistiques descriptives\n{80 * '-'}")

sns.histplot(data=dvf, x="valeur_fonciere")
sns.histplot(data=dvf, x="valeur_fonciere", log_scale=True)

grid = sns.scatterplot(data=dvf, x="surface_reelle_bati", y="valeur_fonciere")
grid.set(xscale="log", yscale="log")


# FEATURE ENGINEERING    -----------------------------------------

logger.debug(f"\n{80 * '-'}\nFeature engineering\n{80 * '-'}")

dvf["tx_pauvrete"] = dvf["nbre_menages_pauvres"] / dvf["nbre_menages"]
dvf["nv_vie_moyen"] = dvf["somme_nv_vie"] / dvf["nbre_menages"]
# Dans Filosofi, chaque ménage occupe un logement : on peut donc rapporter
# les comptes de logements au nombre de ménages du carreau.
dvf["part_proprietaires"] = dvf["nbre_menages_prop"] / dvf["nbre_menages"]
dvf["part_logements_sociaux"] = dvf["nbre_logements_sociaux"] / dvf["nbre_menages"]
dvf["part_logements_avant_1945"] = (
    dvf["nbre_logements_avant_1945"] / dvf["nbre_menages"]
)
dvf["surface_moyenne_logements"] = dvf["surface_totale_logements"] / dvf["nbre_menages"]
dvf["prix_m2"] = dvf["valeur_fonciere"] / dvf["surface_reelle_bati"]

# On écarte le centile inférieur et supérieur de prix au m² : ventes multi-lots,
# démembrements ou erreurs de saisie DVF. Sans ce filtre le modèle apprend en
# bonne partie du bruit.
borne_basse, borne_haute = dvf["prix_m2"].quantile([0.01, 0.99])
dvf = dvf.loc[dvf["prix_m2"].between(borne_basse, borne_haute)]

# Les bornes ci-dessus sont tirées par Paris : on applique donc le même
# filtre au marché local, commune par commune.
prix_m2_par_commune = dvf.groupby("code_commune")["prix_m2"]
dvf = dvf.loc[
    dvf["prix_m2"].between(
        prix_m2_par_commune.transform("quantile", 0.01),
        prix_m2_par_commune.transform("quantile", 0.99),
    )
]

dvf["log_surface"] = np.log(dvf["surface_reelle_bati"])

# Ce qui est vendu en plus du logement lui-même : le prix DVF inclut les
# dépendances (cave, parking = lots supplémentaires) et le terrain des maisons.
# Le rapport surface Carrez / surface bâtie signale les ventes où la surface
# déclarée ne correspond pas au bien (pas de Carrez hors copropriété -> NaN).
dvf["log_surface_terrain"] = np.log1p(dvf["surface_terrain"].fillna(0))
dvf["ratio_carrez"] = dvf["lot1_surface_carrez"] / dvf["surface_reelle_bati"]

# Distance à la tour Eiffel (proxy de centralité, très corrélé au prix en IdF).
# On calcule la distance en Lambert-93 (mètres) puis on passe en log(1 + km).
tour_eiffel = gpd.GeoSeries.from_xy([2.2945], [48.8584], crs="EPSG:4326").to_crs(
    "EPSG:2154"
)
distance_eiffel_km = (
    dvf.geometry.to_crs("EPSG:2154").distance(tour_eiffel.iloc[0]) / 1000
)
dvf["log_distance_eiffel"] = np.log1p(distance_eiffel_km)

# Les valeurs manquantes des variables explicatives sont imputées dans le
# pipeline : on n'écarte que les lignes sans cible.
dvf_start_data = dvf.dropna(subset=["prix_m2"])


# PRIX AU M2 PAR COMMUNE ---------------------------------------

prix_m2_commune = (
    dvf.groupby(["code_commune", "nom_commune"])["prix_m2"].mean().sort_values()
)

logger.info(f"Communes au prix au m2 le plus bas :\n{prix_m2_commune.head(5)}")
logger.info(f"Communes au prix au m2 le plus élevé :\n{prix_m2_commune.tail(5)}")


# MODEL -----------------------------------------


def as_category(df):
    """Convertit les colonnes en dtype 'category' pour que LightGBM les
    reconnaisse automatiquement comme variables catégorielles."""
    return df.astype("category")


numeric_transformer = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="median")),
    ]
)

categorical_transformer = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "ordinal",
            OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
        ),
        ("as_category", FunctionTransformer(as_category)),
    ]
)

preprocessor = ColumnTransformer(
    transformers=[
        ("Preprocessing numerical", numeric_transformer, NUMERIC_FEATURES),
        ("Preprocessing categorical", categorical_transformer, CATEGORICAL_FEATURES),
    ]
).set_output(transform="pandas")

pipe_lgbm = Pipeline(
    [
        ("preprocessor", preprocessor),
        (
            "regressor",
            LGBMRegressor(
                n_estimators=n_trees,
                learning_rate=LEARNING_RATE,
                num_leaves=NUM_LEAVES,
                min_child_samples=10,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=0,
                verbose=-1,
            ),
        ),
    ]
)

# Le prix au m² est très asymétrique : on apprend sur log(1 + prix) et on
# repasse en euros à la prédiction.
pipe = TransformedTargetRegressor(
    regressor=pipe_lgbm, func=np.log1p, inverse_func=np.expm1
)


# TRAIN/TEST SPLIT -----------------------------------

features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
X = dvf_start_data[features]
y = dvf_start_data["prix_m2"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=0)

DERIVED_DATA_LOCATION.mkdir(parents=True, exist_ok=True)
pd.concat([X_train, y_train], axis=1).to_csv(DERIVED_DATA_LOCATION / "train.csv")
pd.concat([X_test, y_test], axis=1).to_csv(DERIVED_DATA_LOCATION / "test.csv")


# PIPELINE VALIDATION -----------------------------------

for string_var in CATEGORICAL_FEATURES:
    check_data_leakage(X_train, X_test, string_var)


# TRAINING AND EVALUATION --------------------------------------------

logger.debug(f"\n{80 * '-'}\nEntraînement du modèle\n{80 * '-'}")

pipe.fit(X_train, y_train)

rmse_train = root_mean_squared_error(y_train, pipe.predict(X_train))
rmse_test = root_mean_squared_error(y_test, pipe.predict(X_test))
logger.info(f"RMSE sur l'apprentissage : {rmse_train:,.0f} €/m²")
logger.info(f"RMSE sur le test : {rmse_test:,.0f} €/m²")

# RMSE par commune (top et bottom 5)
residuals = X_test[["code_commune"]].copy()
residuals["y_test"] = y_test
residuals["pred"] = pipe.predict(X_test)

rmse_commune = (
    residuals.groupby("code_commune")
    .apply(
        lambda d: root_mean_squared_error(d["y_test"], d["pred"]),
        include_groups=False,
    )
    .rename("rmse")
    .reset_index()
)

cog = dvf_start_data[["code_commune", "nom_commune"]].drop_duplicates()
rmse_commune = rmse_commune.merge(cog, on="code_commune").sort_values("rmse")

logger.info(f"Communes avec la RMSE la plus faible :\n{rmse_commune.head(5)}")
logger.info(f"Communes avec la RMSE la plus élevée :\n{rmse_commune.tail(5)}")


# MODEL EVALUATION WITH SKORE ---------------------

logger.debug(f"\n{80 * '-'}\nÉvaluation du modèle avec skore\n{80 * '-'}")

# skore réentraîne une copie du pipeline sur le même découpage
report = EstimatorReport(
    clone(pipe),
    X_train=X_train,
    y_train=y_train,
    X_test=X_test,
    y_test=y_test,
)

logger.debug(report)

# Tableau de métriques (RMSE, MAE, R², temps de calcul) sur train et test
metrics = report.metrics.summarize(data_source="both").frame()
logger.info(f"Métriques de performance:\n{metrics}")

# Graphique des erreurs de prédiction (prédit vs réel)
report.metrics.prediction_error().plot(kind="actual_vs_predicted")
plt.savefig("prediction_error.png", dpi=150, bbox_inches="tight")
plt.close()

# Importance des variables par permutation
importance = report.inspection.permutation_importance(data_source="test").frame()
logger.info(f"Importance des variables:\n{importance}")

logger.debug(f"\n{80 * '-'}\nFIN DU SCRIPT !\n{80 * '-'}")
