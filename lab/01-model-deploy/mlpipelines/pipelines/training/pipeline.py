"""
This sample is non-production-ready template
© 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

import boto3
import logging
import sagemaker
from sagemaker import get_execution_role
from sagemaker.inputs import TrainingInput
from sagemaker.lambda_helper import Lambda
from sagemaker.processing import Processor, ProcessingInput, ProcessingOutput
import sagemaker.session
from sagemaker.tensorflow import TensorFlow
from sagemaker.workflow.conditions import ConditionIn
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.lambda_step import LambdaOutput, LambdaOutputTypeEnum, LambdaStep
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

def get_ecr_arn(
        region,
        account_id,
        processing_ecr_image_name,
        processing_ecr_image_tag):
    try:
        processing_ecr_image = "{}.dkr.ecr.{}.amazonaws.com/{}:{}".format(account_id, region, processing_ecr_image_name, processing_ecr_image_tag)

        return processing_ecr_image
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_kms_key(
        region,
        account_id,
        kms_alias):
    try:
        kms_key = "arn:aws:kms:{}:{}:alias/{}".format(region, account_id, kms_alias)

        return kms_key
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_model_registry_params():
    try:
        model_approval_status = ParameterString(
            name="ModelApprovalStatus", default_value="PendingManualApproval"
        )

        return model_approval_status
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_pipeline_parameters():
    try:

        compilation_input_shape = ParameterString(
            name="compilation_input_shape", default_value="[1, 1, 1, 1]"
        )

        input_file_name = ParameterString(
            name="input_file_name"
        )

        model_package_group_name = ParameterString(
            name="model_package_group_name"
        )

        processing_input_file_name = ParameterString(
            name="processing_input_file_name"
        )

        processing_instance_count = ParameterInteger(
            name="processing_instance_count", default_value=1
        )

        processing_instance_type = ParameterString(
            name="processing_instance_type", default_value="ml.m5.xlarge"
        )

        training_instance_count = ParameterInteger(
            name="training_instance_count", default_value=1
        )

        training_instance_type = ParameterString(
            name="training_instance_type", default_value="ml.m5.xlarge"
        )

        return compilation_input_shape, input_file_name, model_package_group_name, processing_input_file_name, processing_instance_count, processing_instance_type, training_instance_count, training_instance_type
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_session(
        region,
        default_bucket):
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

def get_processing_processor(
        kms_key,
        processing_ecr_image,
        processing_instance_count,
        processing_instance_type,
        role):
    try:
        processor = Processor(
            image_uri=processing_ecr_image,
            role=role,
            instance_count=processing_instance_count,
            instance_type=processing_instance_type,
            output_kms_key=kms_key
        )

        return processor
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_training_estimator(
        hyperparameters,
        kms_key,
        sagemaker_framework_version,
        sagemaker_python_version,
        instance_count,
        instance_type,
        output_path,
        role,
        source_dir):
    try:
        estimator = TensorFlow(
            entry_point="train.py",
            framework_version=sagemaker_framework_version,
            py_version=sagemaker_python_version,
            source_dir=source_dir,
            output_path=output_path,
            hyperparameters=hyperparameters,
            enable_sagemaker_metrics=True,
            role=role,
            instance_count=instance_count,
            instance_type=instance_type,
            output_kms_key=kms_key
        )

        return estimator
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_processing_params(
        s3_bucket_name,
        s3_processing_input_files_path,
        s3_processing_output_files_path):
    try:
        processing_inputs = [
                     ProcessingInput(input_name="input",
                                     source="s3://{}/{}".format(s3_bucket_name, s3_processing_input_files_path),
                                     destination="/opt/ml/processing/input")
        ]

        processing_outputs = [
            ProcessingOutput(output_name="output",
                             source="/opt/ml/processing/output",
                             destination="s3://{}/{}".format(s3_bucket_name, s3_processing_output_files_path))
        ]

        return processing_inputs, processing_outputs
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_training_params(
        s3_bucket_name,
        s3_training_artifact_name,
        s3_training_artifact_path,
        s3_training_input_files_path,
        s3_training_output_files_path):
    try:
        output_path = "s3://{}/{}".format(
            s3_bucket_name,
            s3_training_output_files_path
        )

        source_dir = "s3://{}/{}/{}".format(
            s3_bucket_name,
            s3_training_artifact_path,
            s3_training_artifact_name
        )

        training_input = TrainingInput(
            s3_data="s3://{}/{}".format(
                s3_bucket_name,
                s3_training_input_files_path
            ),
            content_type="text/csv"
        )

        return output_path, source_dir, training_input
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_pipeline(
    region,
    account_id,
    kms_alias,
    lambdas,
    platform_arch,
    platform_os,
    processing_ecr_image_name,
    processing_ecr_image_tag,
    sagemaker_framework_version,
    sagemaker_python_version,
    s3_bucket_name,
    s3_processing_input_files_path,
    s3_processing_output_files_path,
    s3_training_artifact_path,
    s3_training_artifact_name,
    s3_training_input_files_path,
    s3_training_output_files_path,
    processing_arguments=[],
    training_hyperparameters={},
    role=None,
    pipeline_name="TrainingPipeline"):
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

    processing_ecr_image = get_ecr_arn(region, account_id, processing_ecr_image_name, processing_ecr_image_tag)

    kms_key = get_kms_key(region, account_id, kms_alias)

    processing_inputs, processing_outputs = get_processing_params(
        s3_bucket_name,
        s3_processing_input_files_path,
        s3_processing_output_files_path
    )

    output_path, source_dir, training_input = get_training_params(
        s3_bucket_name,
        s3_training_artifact_name,
        s3_training_artifact_path,
        s3_training_input_files_path,
        s3_training_output_files_path)

    """
        Pipeline parameters
    """

    compilation_input_shape, \
    input_file_name, \
    model_package_group_name, \
    processing_input_file_name, \
    processing_instance_count, \
    processing_instance_type, \
    training_instance_count, \
    training_instance_type = get_pipeline_parameters()

    processing_arguments.append("--input_file")
    processing_arguments.append(processing_input_file_name)
    training_hyperparameters["input_file"] = input_file_name

    """
        Processing step
    """

    processor = get_processing_processor(
        kms_key,
        processing_ecr_image,
        processing_instance_count,
        processing_instance_type,
        role
    )

    step_process = ProcessingStep(
        name="ProcessingJob",
        processor=processor,
        inputs=processing_inputs,
        outputs=processing_outputs,
        job_arguments=processing_arguments
    )

    """
        Training step
    """

    estimator = get_training_estimator(
        training_hyperparameters,
        kms_key,
        sagemaker_framework_version,
        sagemaker_python_version,
        training_instance_count,
        training_instance_type,
        output_path,
        role,
        source_dir)

    step_train = TrainingStep(
        depends_on=[step_process],
        name="TrainLinearRegressorDNNModel",
        estimator=estimator,
        inputs={
            "train": training_input
        }
    )

    """
        Compilation job step
    """

    compilation_job_output_param_1 = LambdaOutput(output_name="statusCode", output_type=LambdaOutputTypeEnum.String)
    compilation_job_output_param_2 = LambdaOutput(output_name="compilation_job_name", output_type=LambdaOutputTypeEnum.String)
    compilation_job_output_param_3 = LambdaOutput(output_name="neo_job_status", output_type=LambdaOutputTypeEnum.String)
    compilation_job_output_param_4 = LambdaOutput(output_name="neo_model_path", output_type=LambdaOutputTypeEnum.String)

    create_compilation_job = Lambda(
        function_arn=lambdas["create-compilation-job"],
        function_name="create-compilation-job",
        script="./../../../lambdas/create-compilation-job/lambda_function.py",
        handler="lambda_function.lambda_handler",
        execution_role_arn=role
    )

    step_compilation_neo = LambdaStep(
        name="LambdaCompileNeo",
        lambda_func=create_compilation_job,
        inputs={
            "execution_role": role,
            "compilation_input_shape": compilation_input_shape,
            "platform_arch": platform_arch,
            "platform_os": platform_os,
            "trained_model_path": step_train.properties.ModelArtifacts.S3ModelArtifacts
        },
        outputs=[compilation_job_output_param_1, compilation_job_output_param_2, compilation_job_output_param_3, compilation_job_output_param_4],
    )

    check_compilation_job_output_param_1 = LambdaOutput(output_name="statusCode", output_type=LambdaOutputTypeEnum.String)
    check_compilation_job_output_param_2 = LambdaOutput(output_name="neo_job_status", output_type=LambdaOutputTypeEnum.String)

    check_compilation_job = Lambda(
        function_arn=lambdas["check-compilation-job"],
        function_name="check-compilation-job",
        script="./../../../lambdas/check-compilation-job/lambda_function.py",
        handler="lambda_function.lambda_handler",
        execution_role_arn=role
    )

    step_check_compilation_neo = LambdaStep(
        name="LambdaCheckCompileNeo",
        lambda_func=check_compilation_job,
        inputs={
            "neo_job_name": step_compilation_neo.properties.Outputs["compilation_job_name"]
        },
        outputs=[check_compilation_job_output_param_1, check_compilation_job_output_param_2],
    )

    """
        Register model step
    """

    step_register_model = RegisterModel(
        name="RegisterModel",
        estimator=estimator,
        model_data=step_compilation_neo.properties.Outputs["neo_model_path"],
        model_package_group_name=model_package_group_name,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"]
    )

    """
        Condition compilation step
    """

    cond_compilation_in_failed = ConditionIn(
        value=step_check_compilation_neo.properties.Outputs["neo_job_status"],
        in_values=["FAILED", "STOPPING", "STOPPED"]
    )

    step_cond_compilation_in_failed = ConditionStep(
        name="CheckCompileNeoError",
        conditions=[cond_compilation_in_failed],
        if_steps=[],
        else_steps=[step_register_model]
    )

    # pipeline instance
    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            compilation_input_shape,
            input_file_name,
            model_package_group_name,
            processing_input_file_name,
            processing_instance_count,
            processing_instance_type,
            training_instance_count,
            training_instance_type
        ],
        steps=[
            step_process,
            step_train,
            step_compilation_neo,
            step_check_compilation_neo,
            step_cond_compilation_in_failed
        ],
        sagemaker_session=sagemaker_session
    )

    return pipeline
