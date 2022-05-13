import appconfig
from ETL import extract, load, transform
import logging
from utils import constants

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    df = extract.load_data(constants.PROCESSING_PATH_INPUT, appconfig.args.input_file)

    df = transform.keep_columns(df, "T_degC", "Salnty")

    df = transform.drop_na_rows(df)

    load.save_data(df, constants.PROCESSING_PATH_OUTPUT, "processed.csv")
