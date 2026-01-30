"""
Prediction de la survie d'un individu sur le Titanic
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import argparse
import logging

import duckdb
import pandas as pd

from sklearn.model_selection import train_test_split
from pipeline.build_pipeline import create_pipeline
from models.train_evaluate import evaluate_model


logging.basicConfig(
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler("recording.log"),
        logging.StreamHandler()
    ]
)

# ENVIRONMENT CONFIGURATION ---------------------------

load_dotenv()

parser = argparse.ArgumentParser(description="Paramètres du random forest")
parser.add_argument(
    "--n_trees", type=int, default=20, help="Nombre d'arbres"
)
args = parser.parse_args()

n_trees = args.n_trees
jeton_api = os.environ.get("JETON_API", "")

URL_RAW = "https://minio.lab.sspcloud.fr/lgaliana/ensae-reproductibilite/data/raw/data.parquet" #<1>
data_path = os.environ.get("data_path", URL_RAW)
data_train_path = os.environ.get("train_path", "data/derived/train.parquet")
data_test_path = os.environ.get("test_path", "data/derived/test.parquet")

MAX_DEPTH = None
MAX_FEATURES = "sqrt"

if jeton_api.startswith("$"):
    logging.info("API token has been configured properly")
else:
    logging.warning("API token has not been configured")

Path(data_train_path).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(database=":memory:")


# IMPORT ET STRUCTURATION DONNEES --------------------------------

TrainingData = con.sql(
    f"SELECT * FROM read_parquet('{data_path}')"
).to_df()

y = TrainingData["Survived"]
X = TrainingData.drop("Survived", axis="columns")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.1
)
pd.concat([X_train, y_train], axis = 1).to_parquet(data_train_path, index=False)
pd.concat([X_test, y_test], axis = 1).to_parquet(data_test_path, index=False)


# PIPELINE ----------------------------

pipe = create_pipeline(
    n_trees, max_depth=MAX_DEPTH, max_features=MAX_FEATURES
)


# ESTIMATION ET EVALUATION ----------------------

pipe.fit(X_train, y_train)
score, matrix = evaluate_model(pipe, X_test, y_test)

logging.info(f"{score:.1%} de bonnes réponses sur les données de test pour validation")
logging.info(20 * "-")
logging.info("matrice de confusion")
logging.info(matrix)
