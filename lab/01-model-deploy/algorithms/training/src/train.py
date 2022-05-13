import appconfig
import logging
import matplotlib as mpl
import os
from RegressorModel import RegressorModel
import sys
import traceback
from utils import constants, utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mpl.rcParams['agg.path.chunksize'] = 10000

def __preprocess_data(df):
    try:
        train, test = utils.split_data(df)

        X_train, y_train, X_test, y_test = train.drop("T_degC", axis=1), train.drop("Salnty", axis=1), test.drop("T_degC", axis=1), test.drop("Salnty", axis=1)

        return X_train, y_train, X_test, y_test
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

def __read_data():
    try:
        logger.info("Reading dataset from source...")

        df = utils.load_data_csv(
            file_path=constants.INPUT_PATH,
            file_name=appconfig.args.input_file,
            percentage=appconfig.args.dataset_percentage)

        return df
    except Exception as e:
        stacktrace = traceback.format_exc()
        logger.error("{}".format(stacktrace))

        raise e

if __name__ == '__main__':
    try:
        '''
        Prepare data
        '''
        df = __read_data()

        X_train, y_train, X_test, y_test = __preprocess_data(df)

        rnn_model = RegressorModel()
        rnn_model.build(int(X_train.shape[1]))

        '''
        Train model
        '''

        history = rnn_model.fit(X_train, y_train, appconfig.args.epochs)

        '''
        Tensorflow saving
        '''
        # rnn_model.get_model().save(os.path.join(constants.MODEL_PATH, "saved_model", "1"), save_format='tf')

        '''
        Keras saving
        '''
        rnn_model.get_model().save(os.path.join(constants.MODEL_PATH, constants.MODEL_NAME + ".h5"), save_format='h5')

        '''
        Custom saving
        '''
        # utils.save_model_tf(model, constants.MODEL_PATH, constants.MODEL_NAME)

        '''
        Pickle saving
        '''
        # utils.save_to_pickle(rnn_model.get_tokenizer(), constants.MODEL_PATH, "bort_tokenizer")

        results = rnn_model.get_model().evaluate(X_test, y_test, batch_size=100)

        if len(results) > 0:
            logger.info("Test loss: {}".format(results[0]))

        if len(results) > 1:
            logger.info("Test mse: {}".format(results[1]))

    except Exception as e:
        stacktrace = traceback.format_exc()

        logger.error("{}".format(stacktrace))

        sys.exit(255)
