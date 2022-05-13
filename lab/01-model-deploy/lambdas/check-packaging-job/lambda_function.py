"""
This sample is non-production-ready template
© 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

import boto3
import json
import logging
import time
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

sagemaker_client = boto3.client("sagemaker")

def check_package_edge(edge_manager_job_name):
    try:
        counter = 0

        while True:
            resp = sagemaker_client.describe_edge_packaging_job(EdgePackagingJobName=edge_manager_job_name)

            LOGGER.info("Edge manager job: {}".format(resp))
            LOGGER.info("Status: {}".format(resp['EdgePackagingJobStatus']))

            if resp['EdgePackagingJobStatus'] in ['STARTING', 'INPROGRESS']:
                counter += 30
            else:
                break

            if counter > 480:
                break
            else:
                time.sleep(30)

        return resp['EdgePackagingJobStatus']
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def lambda_handler(event, context):
    if isinstance(event, bytes):
        data = json.loads(event)

    if isinstance(event, dict):
        if "body" in event:
            if isinstance(event["body"], dict):
                data = event["body"]
            else:
                data = json.loads(event["body"])
        else:
            data = event

    LOGGER.info("{}".format(data))
    print("{}".format(data))

    edge_manager_job_name = data["edge_manager_job_name"]

    edge_manager_job_status = check_package_edge(edge_manager_job_name)

    if edge_manager_job_status in ["FAILED", "STOPPING", "STOPPED"]:
        error_message = ("Edge packaging job {} finished with status {}".format(edge_manager_job_name, edge_manager_job_status))

        raise Exception(error_message)
    else:
        return {
            "statusCode": 200,
            "edge_manager_job_status": edge_manager_job_status
        }
