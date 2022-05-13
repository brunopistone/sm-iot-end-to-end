import logging
import os
import traceback
from utils import utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_data(df, file_path, file_name):
    try:
        logger.info("Reading dataset from source...")

        utils.save_to_csv(
            df,
            os.path.join(file_path, file_name)
        )
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e
