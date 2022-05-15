"""
This sample is non-production-ready template
© 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""
import json

import boto3
import logging
import sagemaker
from sagemaker import get_execution_role
from sagemaker.lambda_helper import Lambda
import sagemaker.session
from sagemaker.workflow.conditions import ConditionEquals, ConditionIn
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.lambda_step import LambdaOutput, LambdaOutputTypeEnum, LambdaStep
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.pipeline import Pipeline
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

def get_pipeline_parameters():
    try:

        edge_model_name = ParameterString(
            name="edge_model_name"
        )

        model_package_group_name = ParameterString(
            name="model_package_group_name"
        )

        return edge_model_name, model_package_group_name
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_session(region, default_bucket):
    try:
        boto_session = boto3.Session(region_name=region)

        sagemaker_client = boto_session.client("sagemaker")
        runtime_client = boto_session.client("sagemaker-runtime")

        return sagemaker.session.Session(
            boto_session=boto_session,
            sagemaker_client=sagemaker_client,
            sagemaker_runtime_client=runtime_client,
            default_bucket=default_bucket
        )
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_pipeline(
    region,
    deployment_configs,
    lambdas,
    s3_bucket_name,
    role=None,
    pipeline_name="InferencePipeline"):
    """Gets a SageMaker ML Pipeline instance working with on abalone data.

    Args:
        region: AWS region to create and run the pipeline.
        role: IAM role to create and run steps and pipeline.
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        an instance of a pipeline
    """
    sagemaker_session = get_session(region, s3_bucket_name)

    if role is None:
        role = get_execution_role()

    """
        Global parameters
    """

    deployment_configs = json.dumps(deployment_configs)

    """
        Pipeline parameters
    """

    edge_model_name, model_package_group_name = get_pipeline_parameters()

    """
        Get last approved model step
    """

    last_approved_model_output_param_1 = LambdaOutput(output_name="statusCode", output_type=LambdaOutputTypeEnum.String)
    last_approved_model_output_param_2 = LambdaOutput(output_name="neo_job_name", output_type=LambdaOutputTypeEnum.String)
    last_approved_model_output_param_3 = LambdaOutput(output_name="edge_model_version", output_type=LambdaOutputTypeEnum.String)

    create_last_approved_model_step = Lambda(
        function_arn=lambdas["get-last-approved-model"],
        function_name="get-last-approved-model",
        script="./../../../lambdas/get-last-approved-model/lambda_function.py",
        handler="lambda_function.lambda_handler",
        execution_role_arn=role
    )

    step_get_last_approved_model = LambdaStep(
        name="LambdaGetLastApprovedModel",
        lambda_func=create_last_approved_model_step,
        inputs={
            "model_package_group_name": model_package_group_name
        },
        outputs=[last_approved_model_output_param_1, last_approved_model_output_param_2, last_approved_model_output_param_3],
    )

    """
        Packaging job step
    """

    packaging_job_output_param_1 = LambdaOutput(output_name="statusCode", output_type=LambdaOutputTypeEnum.String)
    packaging_job_output_param_2 = LambdaOutput(output_name="edge_manager_job_name", output_type=LambdaOutputTypeEnum.String)
    packaging_job_output_param_3 = LambdaOutput(output_name="edge_manager_job_status", output_type=LambdaOutputTypeEnum.String)
    packaging_job_output_param_4 = LambdaOutput(output_name="edge_manager_model_path", output_type=LambdaOutputTypeEnum.String)

    create_packaging_job = Lambda(
        function_arn=lambdas["create-packaging-job"],
        function_name="create-packaging-job",
        script="./../../../lambdas/create-packaging-job/lambda_function.py",
        handler="lambda_function.lambda_handler",
        execution_role_arn=role
    )

    step_packaging_job = LambdaStep(
        name="LambdaPackageEdgeManager",
        lambda_func=create_packaging_job,
        inputs={
            "deployment_configs": deployment_configs,
            "execution_role": role,
            "edge_model_name": edge_model_name,
            "edge_model_version": step_get_last_approved_model.properties.Outputs["edge_model_version"],
            "neo_job_name": step_get_last_approved_model.properties.Outputs["neo_job_name"]
        },
        outputs=[packaging_job_output_param_1, packaging_job_output_param_2, packaging_job_output_param_3, packaging_job_output_param_4],
    )

    """
        Condition get last approved model step
    """

    cond_get_last_approved_model_eq = ConditionEquals(
        left=step_get_last_approved_model.properties.Outputs["neo_job_name"],
        right=""
    )

    step_cond_get_last_approved_model_eq = ConditionStep(
        name="CheckLastApprovedModel",
        conditions=[cond_get_last_approved_model_eq],
        if_steps=[],
        else_steps=[step_packaging_job]
    )

    # pipeline instance
    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            edge_model_name,
            model_package_group_name
        ],
        steps=[
            step_get_last_approved_model,
            step_cond_get_last_approved_model_eq
        ],
        sagemaker_session=sagemaker_session
    )

    return pipeline
