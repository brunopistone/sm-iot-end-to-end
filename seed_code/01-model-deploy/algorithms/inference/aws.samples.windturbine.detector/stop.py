import logging
import argparse
import os
import signal
from inference.windturbine import WindTurbine

turbine = None


def signal_handler(signum, frame):
    if turbine != None:
        turbine.halt()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--agent-socket', type=str, default="/tmp/edge_agent",
                        help='The unix socket path created by the agent')

    device_name = os.environ['AWS_IOT_THING_NAME']

    signal.signal(signal.SIGTERM | signal.SIGKILL, signal_handler)

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger('main')

    args = parser.parse_args()
    turbine_id = device_name[-1]
    log.info(f"Initializing the inference component for {device_name} which is turbine [{turbine_id}]")

    turbine = WindTurbine(turbine_id, args.agent_socket)

    turbine.unload_model('detector')

    turbine.halt()

    del turbine
