# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""A CLI to create or update and run pipelines."""
from __future__ import absolute_import

import argparse
import json
import os
import sys
import yaml

from _utils import get_pipeline_driver, convert_struct, get_pipeline_custom_tags

def _parse(env):
    """
       Parse YML from STDIN and return object data
    """
    try:
        with open(os.path.join(os.curdir, "configs", env + ".yml"), 'r') as file:
            elements = yaml.load(file, Loader=yaml.FullLoader)
        file.close()

        return elements
    except yaml.scanner.ScannerError:
        sys.stderr.write("Invalid Yaml\n")
        exit(1)

def main():  # pragma: no cover
    """The main harness that creates or updates and runs the pipeline.

    Creates or updates the pipeline and runs it.
    """
    parser = argparse.ArgumentParser(
        "Creates or updates and runs the pipeline for the pipeline script."
    )

    parser.add_argument(
        "-e",
        "--env",
        dest="env",
        type=str,
        help="Environment for the pipeline",
        default="dev"
    )

    parser.add_argument(
        "-p",
        "--pipeline-name",
        dest="pipeline_name",
        type=str,
        help="Pipeline to run",
        default="training"
    )

    parser.add_argument(
        '-i',
        '--input',
        nargs='*',
        help='Pipeline input parameters',
        required=False,
        default=dict()
    )

    args = parser.parse_args()

    try:
        pipelines = _parse(args.env)

        pipeline_args = pipelines[args.pipeline_name]

        if len(args.input) > 0:
            res = []
            for sub in args.input:
                if '=' in sub:
                    res.append(map(str.strip, sub.split('=', 1)))
            res = dict(res)
            args.input = res

        print("{}".format(pipeline_args))

        pipeline = get_pipeline_driver(args.pipeline_name, pipeline_args)

        print("###### Creating/updating a SageMaker Pipeline with the following definition:")
        parsed = json.loads(pipeline.definition())
        print(json.dumps(parsed, indent=2, sort_keys=True))

        upsert_response = pipeline.upsert(
            role_arn=pipeline_args["role"]
        )

        print("\n###### Created/Updated SageMaker Pipeline: Response received:")
        print(upsert_response)

        execution = pipeline.start(
            parameters=args.input
        )
        print(f"\n###### Execution started with PipelineExecutionArn: {execution.arn}")

        print("Waiting for the execution to finish...")
        execution.wait()
        print("\n#####Execution completed. Execution step details:")

        print(execution.list_steps())
    except Exception as e:  # pylint: disable=W0703
        print(f"Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
