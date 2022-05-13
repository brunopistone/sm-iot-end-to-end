from argparse import ArgumentParser
import logging
import os
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

"""
Put Sagemaker Arguments HERE
"""
def initialize_parameters(parser):
    parser.add_argument('--input_file', type=str, default=None)
    parser.add_argument('--root_dir', type=str, default=retrieve_environment_variables()["ROOT_DIR"])

    return parser.parse_args()

def retrieve_environment_variables():
    envs = {}

    envs["ROOT_DIR"] = os.path.dirname(os.path.realpath(__file__))

    return envs

def retrieve_parameters():
    parser = ArgumentParser()

    try:
        args = initialize_parameters(parser)
    except KeyError as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))
        # this happens when running form a notebook, not from the command line
        args = {}

    envs = retrieve_environment_variables()

    return args, envs

args, envs = retrieve_parameters()
