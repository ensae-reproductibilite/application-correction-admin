"""
Prediction de la survie d'un individu sur le Titanic
"""

import argparse
import pathlib
import pandas as pd
from joblib import dump

from src.data.import_data import import_yaml_config
from src.pipeline.build_pipeline import split_train_test, create_pipeline
from src.models.train_evaluate import evaluate_model

parser = argparse.ArgumentParser(description="Paramètres du random forest")
parser.add_argument("--n_trees", type=int, default=20, help="Nombre d'arbres")
args = parser.parse_args()

n_trees = args.n_trees

URL_RAW = "https://minio.lab.sspcloud.fr/lgaliana/ensae-reproductibilite/data/raw/data.csv"
config = import_yaml_config("configuration/config.yaml")
data_path = config.get("data_path", URL_RAW)
data_train_path = config.get("train_path", "data/derived/train.csv")
data_test_path = config.get("test_path", "data/derived/test.csv")

MAX_DEPTH = None
MAX_FEATURES = "sqrt"


# IMPORT ET STRUCTURATION DONNEES --------------------------------

p = pathlib.Path("data/derived/")
p.mkdir(parents=True, exist_ok=True)

TrainingData = pd.read_csv(data_path)

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

dump(pipe, 'model.joblib')

# Evaluate the model
score, matrix = evaluate_model(pipe, X_test, y_test)
print(f"{score:.1%} de bonnes réponses sur les données de test pour validation")
print(20 * "-")
print("matrice de confusion")
print(matrix)
