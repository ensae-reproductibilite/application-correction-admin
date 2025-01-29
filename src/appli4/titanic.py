"""
Prediction de la survie d'un individu sur le Titanic
"""

import os
from dotenv import load_dotenv
import argparse

import os
import argparse
import pandas as pd

from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import confusion_matrix


# ENVIRONMENT CONFIGURATION ---------------------------

parser = argparse.ArgumentParser(description="Paramètres du random forest")
parser.add_argument(
    "--n_trees", type=int, default=20, help="Nombre d'arbres"
)
args = parser.parse_args()

n_trees = args.n_trees

load_dotenv()


# FUNCTIONS --------------------------


def split_and_count(df, column, separator):
    """
    Split a column in a DataFrame by a separator and count the number of resulting elements.

    Args:
        df (pandas.DataFrame): The DataFrame containing the column to split.
        column (str): The name of the column to split.
        separator (str): The separator to use for splitting.

    Returns:
        pandas.Series: A Series containing the count of elements after splitting.

    """
    return df[column].str.split(separator).str.len()


def split_train_test(data, test_size, train_path="train.csv", test_path="test.csv"):
    """
    Split the data into training and testing sets based on the specified test size.
    Optionally, save the split datasets to CSV files.

    Args:
        data (pandas.DataFrame): The input data to split.
        test_size (float): The proportion of the dataset to include in the test split.
        train_path (str, optional): The file path to save the training dataset.
            Defaults to "train.csv".
        test_path (str, optional): The file path to save the testing dataset.
            Defaults to "test.csv".

    Returns:
        tuple: A tuple containing the training and testing datasets.
    """
    y = data["Survived"]
    X = data.drop("Survived", axis="columns")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size)

    if train_path:
        pd.concat([X_train, y_train]).to_csv(train_path)
    if test_path:
        pd.concat([X_test, y_test]).to_csv(test_path)

    return X_train, X_test, y_train, y_test


def create_pipeline(
    n_trees,
    numeric_features=["Age", "Fare"],
    categorical_features=["Embarked", "Sex"],
    max_depth=None,
    max_features="sqrt",
):
    """
    Create a pipeline for preprocessing and model definition.

    Args:
        n_trees (int): The number of trees in the random forest.
        numeric_features (list, optional): The numeric features to be included in the pipeline.
            Defaults to ["Age", "Fare"].
        categorical_features (list, optional): The categorical features to be included
            in the pipeline.
            Defaults to ["Embarked", "Sex"].
        max_depth (int, optional): The maximum depth of the random forest. Defaults to None.
        max_features (str, optional): The maximum number of features to consider
            when looking for the best split.
            Defaults to "sqrt".

    Returns:
        sklearn.pipeline.Pipeline: The pipeline object.
    """
    # Variables numériques
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", MinMaxScaler()),
        ]
    )

    # Variables catégorielles
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder()),
        ]
    )

    # Preprocessing
    preprocessor = ColumnTransformer(
        transformers=[
            ("Preprocessing numerical", numeric_transformer, numeric_features),
            (
                "Preprocessing categorical",
                categorical_transformer,
                categorical_features,
            ),
        ]
    )

    # Pipeline
    pipe = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_trees, max_depth=max_depth, max_features=max_features
                ),
            ),
        ]
    )

    return pipe


def evaluate_model(pipe, X_test, y_test):
    """
    Evaluate the model by calculating the score and confusion matrix.

    Args:
        pipe (sklearn.pipeline.Pipeline): The trained pipeline object.
        X_test (pandas.DataFrame): The test data.
        y_test (pandas.Series): The true labels for the test data.

    Returns:
        tuple: A tuple containing the score and confusion matrix.
    """
    score = pipe.score(X_test, y_test)
    matrix = confusion_matrix(y_test, pipe.predict(X_test))
    return score, matrix



jeton_api = os.environ.get("JETON_API", "")
data_path = os.environ.get("DATA_PATH", "data.csv")
MAX_DEPTH = None
MAX_FEATURES = "sqrt"


if jeton_api.startswith("$"):
    print("API token has been configured properly")
else:
    print("API token has not been configured")


# IMPORT ET EXPLORATION DONNEES --------------------------------

TrainingData = pd.read_csv("data.csv")


# Usage example:
ticket_count = split_and_count(TrainingData, "Ticket", "/")
name_count = split_and_count(TrainingData, "Name", ",")


# SPLIT TRAIN/TEST --------------------------------

X_train, X_test, y_train, y_test = split_train_test(TrainingData, test_size=0.1)


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
