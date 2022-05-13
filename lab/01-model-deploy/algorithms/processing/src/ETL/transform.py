import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_na_rows(df):
    try:
        df = df.dropna(how='any', axis=0)

        return df
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

def drop_na_by_columns(df, *cols):
    try:
        for col in cols:
            df = df[df[col].notna()]
        return df
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

def keep_columns(df, *cols):
    try:
        df = df[list(cols)]

        return df
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e
