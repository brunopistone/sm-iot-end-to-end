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
from sagemaker.inputs import CreateModelInput, TrainingInput, TransformInput
from sagemaker.model import Model
from sagemaker.pytorch.estimator import PyTorch
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.transformer import Transformer
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import CacheConfig, CreateModelStep, ProcessingStep, TrainingStep, TransformStep
import time
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

## By enabling cache, if you run this pipeline again, without changing the input
## parameters it will skip the training part and reuse the previous trained model
cache_config = CacheConfig(enable_caching=True, expire_after="30d")
ts = time.strftime('%Y-%m-%d-%H-%M-%S')

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

def get_pipeline(
    region,
    model_package_group_name,
    preprocessing_framework_version,
    preprocessing_instance_count,
    preprocessing_instance_type,
    preprocessing_input_files_path,
    preprocessing_entrypoint,
    postprocessing_output_files_path,
    training_framework_version,
    training_python_version,
    training_instance_count,
    training_instance_type,
    training_entrypoint,
    transform_instance_count,
    transform_instance_type,
    s3_bucket_name,
    training_hyperparameters={},
    training_metrics=[],
    role=None,
    pipeline_name="TrainingPipeline"):

    sagemaker_session = get_session(region, s3_bucket_name)

    """
        Pipeline Parameters
    """

    # Data prep
    preprocessing_instance_type = ParameterString(  # instance type for data preparation
        name="ProcessingInstanceType",
        default_value=preprocessing_instance_type
    )
    preprocessing_instance_count = ParameterInteger(  # number of instances used for data preparation
        name="ProcessingInstanceCount",
        default_value=preprocessing_instance_count
    )

    # Training
    training_instance_type = ParameterString(  # instance type for training the model
        name="TrainingInstanceType",
        default_value=training_instance_type
    )
    training_instance_count = ParameterInteger(  # number of instances used to train your model
        name="TrainingInstanceCount",
        default_value=training_instance_count  # wind_turbine.py supports only 1 instance
    )

    # Batch prediction
    transform_instance_type = ParameterString(  # instance type for batch transform jobs
        name="TransformInstanceType",
        default_value=transform_instance_type
    )
    transform_instance_count = ParameterInteger(  # number of instances used for batch prediction
        name="TransformInstanceCount",
        default_value=transform_instance_count
    )

    # Dataset input data: S3 path
    input_data = ParameterString(
        name="InputData",
        default_value="s3://{}/{}".format(s3_bucket_name, preprocessing_input_files_path),
    )

    # Batch prediction output: S3 path
    output_batch_data = ParameterString(
        name="OutputBatchData",
        default_value="s3://%s/%s/output" % (s3_bucket_name, postprocessing_output_files_path),
    )

    # Model Package parameters
    model_approval_status = ParameterString(
        name="ModelApprovalStatus", default_value="PendingManualApproval"
    )

    model_package_group_name = ParameterString(
        name="ModelPackageGroupName", default_value=model_package_group_name
    )

    """
        Preprocessing Step
    """

    script_processor = SKLearnProcessor(
        framework_version=preprocessing_framework_version,
        role=role,
        instance_type=preprocessing_instance_type,
        instance_count=preprocessing_instance_count,
        max_runtime_in_seconds=7200,
    )

    step_process = ProcessingStep(
        name="WindTurbineDataPreprocess",
        code=preprocessing_entrypoint,
        processor=script_processor,
        inputs=[
            ProcessingInput(source=input_data, destination='/opt/ml/processing/input')
        ],
        outputs=[
            ProcessingOutput(
                output_name='train_data',
                source='/opt/ml/processing/train',
                destination='s3://{}/{}/train_data'.format(s3_bucket_name, postprocessing_output_files_path)),
            ProcessingOutput(
                output_name='statistics',
                source='/opt/ml/processing/statistics',
                destination='s3://{}/{}/statistics'.format(s3_bucket_name, postprocessing_output_files_path))
        ],
        job_arguments=['--num-dataset-splits', '20']
    )

    """
        Training Step
    """

    estimator = PyTorch(
        training_entrypoint,
        framework_version=training_framework_version,
        role=role,
        sagemaker_session=sagemaker_session,
        instance_type=training_instance_type,
        instance_count=training_instance_count,
        py_version=training_python_version,
        hyperparameters=training_hyperparameters,
        metric_definitions=training_metrics,
        output_path="s3://{}/models".format(s3_bucket_name)
    )

    step_train = TrainingStep(
        name="WindTurbineAnomalyTrain",
        estimator=estimator,
        inputs={"train": TrainingInput(
            s3_data=step_process.properties.ProcessingOutputConfig.Outputs["train_data"].S3Output.S3Uri,
            content_type="application/x-npy"
        )},
        cache_config=cache_config
    )

    """
        Register Model Step
    """

    step_register_model = RegisterModel(
        name="RegisterModel",
        estimator=estimator,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        model_package_group_name=model_package_group_name,
        approval_status=model_approval_status,
        content_types=["application/json"],
        response_types=["application/json"],
        inference_instances=[transform_instance_type],
        transform_instances=[transform_instance_type]
    )

    """
        Evaluation Model Step
    """

    model = Model(
        image_uri=sagemaker.image_uris.retrieve(
            framework="pytorch",  # we are using the SageMaker pre-built PyTorch inference image
            region=region,
            version=training_framework_version,
            py_version=training_python_version,
            instance_type=training_instance_type,
            image_scope='inference'
        ),
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=sagemaker_session,
        role=role
    )

    step_create_model = CreateModelStep(
        name="WindTurbineAnomalyCreateModel",
        model=model,
        inputs=CreateModelInput(
            instance_type=transform_instance_type
        )
    )

    step_transform = TransformStep(
        name="WindTurbineAnomalyTransform",
        transformer=Transformer(
            model_name=step_create_model.properties.ModelName,
            instance_type=transform_instance_type,
            instance_count=transform_instance_count,
            output_path=output_batch_data,
            accept='application/x-npy',
            max_payload=20,
            strategy='MultiRecord',
            assemble_with='Line'
        ),
        inputs=TransformInput(
            data=step_process.properties.ProcessingOutputConfig.Outputs["train_data"].S3Output.S3Uri,
            content_type="application/x-npy")
    )

    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            preprocessing_instance_type,
            preprocessing_instance_count,
            training_instance_type,
            training_instance_count,
            transform_instance_type,
            transform_instance_count,
            input_data,
            output_batch_data,
            model_approval_status,
            model_package_group_name
        ],
        steps=[
            step_process,
            step_train,
            step_register_model,
            step_create_model,
            step_transform],
        sagemaker_session=sagemaker_session,
    )

    return pipeline
