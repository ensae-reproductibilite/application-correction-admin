"""
Prediction de la survie d'un individu sur le Titanic
"""

import os
from dotenv import load_dotenv
import argparse
from loguru import logger as logging

import pandas as pd
from sklearn.model_selection import train_test_split
from src.pipeline.build_pipeline import create_pipeline
from src.models.train_evaluate import evaluate_model

logging.add("logs.log")

# ENVIRONMENT CONFIGURATION ---------------------------

load_dotenv()


parser = argparse.ArgumentParser(description="Paramètres du random forest")
parser.add_argument(
    "--n_trees", type=int, default=20, help="Nombre d'arbres"
)
args = parser.parse_args()

MAX_DEPTH = None
MAX_FEATURES = "sqrt"

n_trees = args.n_trees
jeton_api = os.environ.get("JETON_API", "")
data_path = os.environ.get("DATA_PATH", "data.csv")


if jeton_api.startswith("$"):
    logging.info("API token has been configured properly")
else:
    logging.warning("API token has not been configured")


# IMPORT ET STRUCTURATION DONNEES --------------------------------

TrainingData = pd.read_csv("data.csv")

y = TrainingData["Survived"]
X = TrainingData.drop("Survived", axis="columns")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.1
)


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
