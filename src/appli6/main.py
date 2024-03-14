"""
Prediction de la survie d'un individu sur le Titanic
"""

import argparse
import pandas as pd

from src.data.import_data import import_yaml_config, split_and_count
from src.pipeline.build_pipeline import split_train_test, create_pipeline
from src.models.train_evaluate import evaluate_model

parser = argparse.ArgumentParser(description="Paramètres du random forest")
parser.add_argument("--n_trees", type=int, default=20, help="Nombre d'arbres")
args = parser.parse_args()

n_trees = args.n_trees


config = import_yaml_config("configuration/config.yaml")
jeton_api = config.get("jeton_api")
data_path = config.get("data_path", "data/raw/data.csv")
data_train_path = config.get("train_path", "data/derived/train.csv")
data_test_path = config.get("test_path", "data/derived/test.csv")

MAX_DEPTH = None
MAX_FEATURES = "sqrt"


# IMPORT ET EXPLORATION DONNEES --------------------------------

TrainingData = pd.read_csv(data_path)


# Usage example:
ticket_count = split_and_count(TrainingData, "Ticket", "/")
name_count = split_and_count(TrainingData, "Name", ",")


# SPLIT TRAIN/TEST --------------------------------

X_train, X_test, y_train, y_test = split_train_test(
    TrainingData, test_size=0.1,
    train_path=data_train_path,
    test_path=data_test_path
)


# PIPELINE ----------------------------


# Create the pipeline
pipe = create_pipeline(
    n_trees, max_depth=MAX_DEPTH, max_features=MAX_FEATURES
)


# ESTIMATION ET EVALUATION ----------------------

pipe.fit(X_train, y_train)


# Evaluate the model
score, matrix = evaluate_model(pipe, X_test, y_test)
print(f"{score:.1%} de bonnes réponses sur les données de test pour validation")
print(20 * "-")
print("matrice de confusion")
print(matrix)
