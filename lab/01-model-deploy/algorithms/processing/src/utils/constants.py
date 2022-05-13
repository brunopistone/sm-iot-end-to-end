import os

BASE_PATH = os.path.join("/", "opt", "ml")
INPUT_PATH = os.path.join(BASE_PATH, "input", "data", "train")
MODEL_PATH = os.path.join(BASE_PATH, "artifact")
OUTPUT_PATH = os.path.join(BASE_PATH, "output")
OUTPUT_PATH_DATA = os.path.join(BASE_PATH, "output", "data")
PARAM_FILE = os.path.join(BASE_PATH, "input", "config", "hyperparameters.json")
PROCESSING_PATH = os.path.join(BASE_PATH, "processing")
PROCESSING_PATH_INPUT = os.path.join(PROCESSING_PATH, "input")
PROCESSING_PATH_OUTPUT = os.path.join(PROCESSING_PATH, "output")
