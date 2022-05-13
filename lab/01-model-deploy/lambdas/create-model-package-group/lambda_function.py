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
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

sagemaker_client = boto3.client("sagemaker")

def describe_model_package_group(model_package_group_name):
    try:
        LOGGER.info("Describing {}".format(model_package_group_name))

        response = sagemaker_client.describe_model_package_group(
            ModelPackageGroupName=model_package_group_name
        )

        LOGGER.info("{}".format(response))

        return response
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        return ""

def create_model_package_group(model_package_group_name, model_package_group_description, tags=[]):
    try:
        LOGGER.info("Creating {}".format(model_package_group_name))

        response = sagemaker_client.create_model_package_group(
            ModelPackageGroupName=model_package_group_name,
            ModelPackageGroupDescription=model_package_group_description,
            Tags=tags
        )

        LOGGER.info("{}".format(response))

        return response
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

    model_package_group_name = data["model_package_group_name"]
    model_package_group_description = data["model_package_group_description"]

    check_model_package_group = describe_model_package_group(model_package_group_name)

    if check_model_package_group == "":
        create_model_package_group(model_package_group_name, model_package_group_description)

    return {
        "statusCode": "200",
        "model_package_group_name": model_package_group_name
    }
