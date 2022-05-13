"""
This sample is non-production-ready template
© 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

import boto3
from datetime import datetime
import json
import logging
import os
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

KMS_ALIAS = os.environ.get("KMS_ALIAS", None)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", None)
S3_COMPILED_PATH = os.environ.get("S3_COMPILED_PATH", "output/compiled")

sagemaker_client = boto3.client("sagemaker")

ACCOUNT_ID = boto3.client('sts').get_caller_identity().get('Account')
REGION = boto3.session.Session().region_name
KMS_KEY = "arn:aws:kms:{}:{}:alias/{}".format(REGION, ACCOUNT_ID, KMS_ALIAS)

def create_compile_neo(role, compilation_input_shape, trained_model_path, platform_os, platform_arch):
    try:
        neo_job_name = "sagemaker-neo-job-keras-{}".format(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))

        LOGGER.info("{}".format(trained_model_path))

        sagemaker_client.create_compilation_job(
            CompilationJobName=neo_job_name,
            RoleArn=role,
            InputConfig={
                "S3Uri": trained_model_path,
                "DataInputConfig": '{"input_token": ' + compilation_input_shape + '}',
                "Framework": "KERAS"
            },
            OutputConfig={
                "S3OutputLocation": "s3://{}/{}/{}".format(
                    S3_BUCKET_NAME,
                    S3_COMPILED_PATH,
                    neo_job_name
                ),
                "TargetPlatform": {
                    "Os": platform_os,
                    "Arch": platform_arch,
                },
                "KmsKeyId": KMS_KEY
            },
            StoppingCondition={"MaxRuntimeInSeconds": 900}
        )

        return neo_job_name
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

    role = data["execution_role"]
    compilation_input_shape = data.get("compilation_input_shape")
    platform_arch = data.get("platform_arch")
    platform_os = data.get("platform_os")
    trained_model_path = data["trained_model_path"]

    compilation_job_name = create_compile_neo(role, compilation_input_shape, trained_model_path, platform_os, platform_arch)

    neo_model_path = "s3://{}/{}/{}/model-{}_{}.tar.gz".format(S3_BUCKET_NAME, S3_COMPILED_PATH, compilation_job_name, platform_os, platform_arch)

    return {
        "statusCode": "200",
        "compilation_job_name": compilation_job_name,
        "neo_job_status": "STARTING",
        "neo_model_path": neo_model_path
    }
