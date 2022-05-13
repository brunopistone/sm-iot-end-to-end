import logging
from tensorflow.keras import Model
from tensorflow.keras.layers import Dense, Flatten, Input
from tensorflow.keras.losses import MeanSquaredError
from tensorflow.keras.optimizers import Adam
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

class RegressorModel:
    def __init__(self):
        self.model = None

    def build(self, shape, fine_tuning=False):
        try:
            input_ids_in = Input(shape=(1, 1, shape,), name='input_token', dtype='float32')

            X = Flatten()(input_ids_in)
            X = Dense(2, activation="relu")(X)
            X = Dense(1)(X)

            self.model = Model(
                inputs=[input_ids_in],
                outputs=[X]
            )

            if fine_tuning:
                for layer in self.model.layers[:3]:
                    layer.trainable = False

            optimizer = Adam(learning_rate=1e-2)
            loss_obj = MeanSquaredError()
            
            self.model.compile(optimizer=optimizer, loss=loss_obj, metrics=["mae"])

            LOGGER.info("{}".format(self.model.summary()))
        except Exception as e:
            stacktrace = traceback.format_exc()
            LOGGER.error("{}".format(stacktrace))

            raise e

    def fit(self, X_train, y_train, epochs=10, batch_size=100):

        history = self.model.fit(
            X_train,
            y_train,
            validation_split=0.2,
            epochs=int(epochs),
            batch_size=batch_size
        )

        return history

    def get_model(self):
        return self.model
