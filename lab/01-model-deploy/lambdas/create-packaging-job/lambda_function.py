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
S3_PACKAGED_FILES_PATH = os.environ.get("S3_PACKAGED_FILES_PATH", "output/packaged")

sagemaker_client = boto3.client("sagemaker")

ACCOUNT_ID = boto3.client('sts').get_caller_identity().get('Account')
REGION = boto3.session.Session().region_name
KMS_KEY = "arn:aws:kms:{}:{}:alias/{}".format(REGION, ACCOUNT_ID, KMS_ALIAS)

def create_package_edge_manager(role, edge_model_name, edge_model_version, neo_job_name, deployment_configs=None):
    try:
        edge_manager_job_name = "edge-manager-job-keras-{}".format(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))

        if deployment_configs is None:
            sagemaker_client.create_edge_packaging_job(
                EdgePackagingJobName=edge_manager_job_name,
                CompilationJobName=neo_job_name,
                ModelName=edge_model_name,
                ModelVersion=edge_model_version,
                RoleArn=role,
                OutputConfig={
                    "S3OutputLocation": "s3://{}/{}/{}".format(
                        S3_BUCKET_NAME,
                        S3_PACKAGED_FILES_PATH,
                        edge_manager_job_name
                    ),
                    "KmsKeyId": KMS_KEY
                }
            )
        else:
            sagemaker_client.create_edge_packaging_job(
                EdgePackagingJobName=edge_manager_job_name,
                CompilationJobName=neo_job_name,
                ModelName=edge_model_name,
                ModelVersion=edge_model_version,
                RoleArn=role,
                OutputConfig={
                    "S3OutputLocation": "s3://{}/{}/{}".format(
                        S3_BUCKET_NAME,
                        S3_PACKAGED_FILES_PATH,
                        edge_manager_job_name
                    ),
                    "KmsKeyId": KMS_KEY,
                    "PresetDeploymentType": 'GreengrassV2Component',
                    'PresetDeploymentConfig': str(deployment_configs)
                }
            )

        return edge_manager_job_name
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

    deployment_configs = data.get("deployment_configs", None)
    role = data["execution_role"]
    edge_model_name = data["edge_model_name"]
    edge_model_version = data["edge_model_version"]
    neo_job_name = data["neo_job_name"]

    if deployment_configs is not None:
        try:
            deployment_configs = json.loads(deployment_configs)
            deployment_configs["ComponentVersion"] = edge_model_version + ".0.0"
            deployment_configs = json.dumps(deployment_configs)
        except:
            LOGGER.info("Deployment config is not a valid JSON")
            deployment_configs = None

    edge_manager_job_name = create_package_edge_manager(role, edge_model_name, edge_model_version, neo_job_name, deployment_configs)

    edge_manager_model_path = "s3://{}/{}/{}/{}-{}.tar.gz".format(S3_BUCKET_NAME, S3_PACKAGED_FILES_PATH, edge_manager_job_name, edge_model_name, edge_model_version)

    return {
        "statusCode": "200",
        "edge_manager_job_name": edge_manager_job_name,
        "edge_manager_job_status": "STARTING",
        "edge_manager_model_path": edge_manager_model_path
    }
