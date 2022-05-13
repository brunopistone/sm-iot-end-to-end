import logging
import traceback
from utils import constants, utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(file_path, file_name, dataset_percentage=100):
    try:
        logger.info("Reading dataset from source...")

        df = utils.load_data_csv(
            file_path=file_path,
            file_name=file_name,
            percentage=dataset_percentage)

        return df
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e
