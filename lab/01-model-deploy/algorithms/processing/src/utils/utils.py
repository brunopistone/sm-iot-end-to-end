import csv
import json
import logging
import os
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit, train_test_split
import traceback
from utils import constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_percentage(df, percentage=50):
    df = df.head(int(len(df) * (percentage / 100)))

    return df

def load_data_csv(file_path, file_name, percentage=100):
    try:
        logger.info("Try reading {}".format(os.path.join(file_path, file_name)))

        df = pd.read_csv(
            os.path.join(file_path, file_name),
            sep=",",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            escapechar='\\',
            encoding='utf-8',
            error_bad_lines=False
        )

        df = get_percentage(df, percentage)

        return df
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

def load_data_csv_s3(protocol, file_path, file_name, percentage=100):
    try:
        logger.info("Try reading {}".format(os.path.join(file_path, file_name)))

        df = pd.read_csv(
            "{}://{}/{}".format(protocol, file_path, file_name),
            sep=",",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            escapechar='\\',
            encoding='utf-8'
        )

        df = get_percentage(df, percentage)

        return df
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

def read_parameters_sagemaker(parameter_file):
    try:
        with open(parameter_file, encoding='utf-8') as file:
            parameters = json.load(file)
        file.close()

        if "epochs" not in parameters:
            parameters["epochs"] = 10
            constants.EPOCHS = 10
        else:
            parameters["epochs"] = int(parameters["epochs"])
            constants.EPOCHS = int(parameters["epochs"])

        if "dataset_percentage" not in parameters:
            parameters["dataset_percentage"] = 100
            constants.DATASET_PERCENTAGE = 100
        else:
            parameters["dataset_percentage"] = int(parameters["dataset_percentage"])
            constants.DATASET_PERCENTAGE = int(parameters["dataset_percentage"])

        if "train_percentage" not in parameters:
            parameters["train_percentage"] = 0.8
            constants.TRAIN_PERCENTAGE = 0.8
        else:
            parameters["train_percentage"] = float(parameters["train_percentage"])
            constants.TRAIN_PERCENTAGE = float(parameters["train_percentage"])

        return parameters
    except Exception as e:
        stacktrace = traceback.format_exc()

        logger.error("{}".format(stacktrace))

        parameters = {
            "dataset_percentage": 100,
            "epochs": 10,
            "train_percentage": 0.8
        }

        constants.EPOCHS = int(parameters["epochs"])
        constants.DATASET_PERCENTAGE = int(parameters["dataset_percentage"])
        constants.TRAIN_PERCENTAGE = float(parameters["train_percentage"])

        return parameters

def save_to_csv(df, file_path, sep=","):
    try:
        logger.info("Try saving {}".format(file_path))

        df.to_csv(
            file_path,
            header=True,
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            sep=sep,
            index=False,
            encoding='utf-8')
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

def split_data(data, train_percentage):
    try:
        train, test = train_test_split(data, test_size=1.0 - train_percentage)

        return train, test
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

def split_data_balanced(data, labels):
    X_train, y_train, X_test, y_test = None, None, None, None

    sss = StratifiedShuffleSplit(train_size=constants.TRAIN_PERCENTAGE, n_splits=1, test_size=1.0 - constants.TRAIN_PERCENTAGE, random_state=0)

    for train_index, test_index in sss.split(data, labels):
        X_train, X_test = data[train_index], data[test_index]
        y_train, y_test = labels[train_index], labels[test_index]

    return X_train, y_train, X_test, y_test
