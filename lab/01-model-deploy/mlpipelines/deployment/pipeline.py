"""
This sample is non-production-ready template
© 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

import boto3
from botocore.exceptions import ClientError
import io
import json
import logging
import os
import requests
import sagemaker
import stat
import tarfile
import time
import traceback

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

iot_client = boto3.client('iot')
ggv2_client = boto3.client('greengrassv2')
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')
sm_client = boto3.client('sagemaker')

def create_component_version():
    try:
        pass
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def describe_model_package(model_package_arn):
    try:
        model_package = sm_client.describe_model_package(
            ModelPackageName=model_package_arn
        )

        LOGGER.info("{}".format(model_package))

        if len(model_package) == 0:
            error_message = ("No ModelPackage found for: {}".format(model_package_arn))
            LOGGER.error("{}".format(error_message))

            raise Exception(error_message)

        return model_package
    except ClientError as e:
        stacktrace = traceback.format_exc()
        error_message = e.response["Error"]["Message"]
        LOGGER.error("{}".format(stacktrace))

        raise Exception(error_message)

def get_approved_package(model_package_group_name):
    """Gets the latest approved model package for a model package group.

    Args:
        model_package_group_name: The model package group name.

    Returns:
        The SageMaker Model Package ARN.
    """
    try:
        # Get the latest approved model package
        response = sm_client.list_model_packages(
            ModelPackageGroupName=model_package_group_name,
            ModelApprovalStatus="Approved",
            SortBy="CreationTime",
            SortOrder="Descending",
            MaxResults=1,
        )
        approved_packages = response["ModelPackageSummaryList"]

        # Return error if no packages found
        if len(approved_packages) == 0:
            error_message = ("No approved ModelPackage found for ModelPackageGroup: {}".format(model_package_group_name))
            LOGGER.error("{}".format(error_message))

            raise Exception(error_message)

        model_package = approved_packages[0]
        LOGGER.info("Identified the latest approved model package: {}".format(model_package))

        return model_package
    except ClientError as e:
        stacktrace = traceback.format_exc()
        error_message = e.response["Error"]["Message"]
        LOGGER.error("{}".format(stacktrace))

        raise Exception(error_message)

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

def run_compilation_job(compilation_job_name, bucket_name, model_package, n_features, role):
    try:
        sm_client.create_compilation_job(
            CompilationJobName=compilation_job_name,
            RoleArn=role,
            InputConfig={
                'S3Uri': model_package["InferenceSpecification"]["Containers"][0]["ModelDataUrl"],
                'DataInputConfig': '{"input0":[1,%d,10,10]}' % n_features,
                'Framework': 'PYTORCH'
            },
            OutputConfig={
                'S3OutputLocation': 's3://{}/models/optimized/'.format(bucket_name),
                'TargetPlatform': {'Os': 'LINUX', 'Arch': 'X86_64'}
            },
            StoppingCondition={'MaxRuntimeInSeconds': 900}
        )

        while True:
            resp = sm_client.describe_compilation_job(CompilationJobName=compilation_job_name)
            if resp['CompilationJobStatus'] in ['STARTING', 'INPROGRESS']:
                print('Running...')
            else:
                print(resp['CompilationJobStatus'], compilation_job_name)
                break
            time.sleep(5)

        if resp['CompilationJobStatus'] in ["FAILED", "STOPPING", "STOPPED"]:
            raise Exception("Compilation job ended with status {}. {}".format(resp['CompilationJobStatus'], resp))
        else:
            return resp
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def run_deployment_ggv2(bucket_name, device_fleet_name, device_fleet_suffix, ggv2_deployment_name, model_package, wind_turbine_thing_group_arn):
    try:
        device_fleets = sm_client.list_device_fleets(
            NameContains="{}-{}".format(device_fleet_name, device_fleet_suffix))
        wind_turbine_device_fleet_name = device_fleets['DeviceFleetSummaries'][0]['DeviceFleetName']

        resp = ggv2_client.create_deployment(
            targetArn=wind_turbine_thing_group_arn,
            deploymentName=ggv2_deployment_name,
            components={
                "aws.greengrass.Cli": {
                    "componentVersion": "2.5.4"
                },
                "aws.greengrass.SageMakerEdgeManager": {
                    "componentVersion": "1.1.0",
                    "configurationUpdate": {
                        "merge": json.dumps(
                            {"DeviceFleetName": wind_turbine_device_fleet_name, "BucketName": bucket_name})
                    },
                    "runWith": {}
                },
                "aws.samples.windturbine.detector": {
                    "componentVersion": "{}.0.0".format(model_package["ModelPackageVersion"])
                },
                "aws.samples.windturbine.model": {
                    "componentVersion": "{}.0.0".format(model_package["ModelPackageVersion"])
                }
            })

        deployment_id = resp['deploymentId']
        iot_job_id = resp['iotJobId']

        LOGGER.info("GreenGrass Deployment Job ID: {}".format(iot_job_id))

        return resp
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def run_packaging_job(bucket_name, compilation_job_name, component_name, edge_packaging_job_name, model_name, model_package, role):
    try:
        resp = sm_client.create_edge_packaging_job(
            EdgePackagingJobName=edge_packaging_job_name,
            CompilationJobName=compilation_job_name,
            ModelName=model_name,
            ModelVersion="{}.0.0".format(model_package["ModelPackageVersion"]),
            RoleArn=role,
            OutputConfig={
                'S3OutputLocation': 's3://{}/models/packaged'.format(bucket_name),
                "PresetDeploymentType": "GreengrassV2Component",
                "PresetDeploymentConfig": json.dumps(
                    {"ComponentName": component_name,
                     "ComponentVersion": "{}.0.0".format(model_package["ModelPackageVersion"])}
                ),
            }
        )

        while True:
            resp = sm_client.describe_edge_packaging_job(EdgePackagingJobName=edge_packaging_job_name)
            if resp['EdgePackagingJobStatus'] in ['STARTING', 'INPROGRESS']:
                print('Running...')
            else:
                print(resp['EdgePackagingJobStatus'], compilation_job_name)
                break
            time.sleep(5)

        if resp['EdgePackagingJobStatus'] in ["FAILED", "STOPPING", "STOPPED"]:
            raise Exception("Packaging job ended with status {}. {}".format(resp['EdgePackagingJobStatus'], resp))
        else:
            return resp
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def setup_fleet(bucket_name, device_fleet_suffix, thing_group_name, region, num_agents=2):
    # create a new thing group
    thing_group_arn = None
    agent_pkg_bucket = 'sagemaker-edge-release-store-us-west-2-linux-x64'
    agent_config_package_prefix = 'wind_turbine_agent/config.tgz'

    try:
        s3_client.download_file(Bucket=bucket_name, Key=agent_config_package_prefix, Filename='/tmp/dump')
        LOGGER.info('The agent configuration package was already built! Skipping...')
        quit()
    except ClientError as e:
        pass

    try:
        thing_group_arn = iot_client.describe_thing_group(thingGroupName=thing_group_name)['thingGroupArn']
        LOGGER.info("Thing group found")
    except iot_client.exceptions.ResourceNotFoundException as e:
        LOGGER.info("Creating a new thing group")
        thing_group_arn = iot_client.create_thing_group(thingGroupName=thing_group_name)['thingGroupArn']

    LOGGER.info("Creating the directory structure for the agent")
    # create a structure for the agent files
    os.makedirs('agent/certificates/root', exist_ok=True)
    os.makedirs('agent/certificates/iot', exist_ok=True)
    os.makedirs('agent/logs', exist_ok=True)
    os.makedirs('agent/model', exist_ok=True)
    os.makedirs('agent/conf', exist_ok=True)
    os.system('chmod 777 -R agent')

    # then get some root certificates
    resp = requests.get('https://www.amazontrust.com/repository/AmazonRootCA1.pem')
    with open('agent/certificates/iot/AmazonRootCA1.pem', 'w') as c:
        c.write(resp.content.decode('utf-8'))

    # this certificate validates the edge manage package
    s3_client.download_file(
        Bucket=agent_pkg_bucket,
        Key='Certificates/%s/%s.pem' % (region, region),
        Filename='agent/certificates/root/%s.pem' % region
    )
    # adjust the permissions of the files
    os.chmod('agent/certificates/iot/AmazonRootCA1.pem', stat.S_IRUSR | stat.S_IRGRP)
    os.chmod('agent/certificates/root/%s.pem' % region, stat.S_IRUSR | stat.S_IRGRP)

    LOGGER.info("Processing the agents...")
    for agent_id in range(num_agents):
        setup_agent(agent_id, bucket_name, device_fleet_suffix, region, thing_group_name, thing_group_arn)

    LOGGER.info("Creating the final package...")
    with io.BytesIO() as f:
        with tarfile.open(fileobj=f, mode='w:gz') as tar:
            tar.add('agent', recursive=True)
        f.seek(0)
        LOGGER.info("Uploading to S3")
        s3_client.upload_fileobj(f, Bucket=bucket_name, Key=agent_config_package_prefix)

    LOGGER.info("Done!")

def setup_agent(agent_id, bucket_name, device_fleet_suffix, region, thing_group_name, thing_group_arn):
    policy_name = 'WindTurbineFarmPolicy-{}'.format(device_fleet_suffix)
    base = "agent/certificates/iot/edge_device_%d_%s.pem"
    fleet_name = 'wind-turbine-farm-{}'.format(device_fleet_suffix)

    thing_arn_template = thing_group_arn.replace('thinggroup', 'thing').replace(thing_group_name, '%s')

    cred_host = iot_client.describe_endpoint(endpointType='iot:CredentialProvider')['endpointAddress']
    policy_alias = 'SageMakerEdge-%s' % fleet_name

    # register the device in the fleet
    # the device name needs to have 36 chars
    dev_name = "edge-device-%d" % agent_id
    dev = [{'DeviceName': dev_name, 'IotThingName': dev_name}]

    try:
        sm_client.describe_device(DeviceFleetName=fleet_name, DeviceName=dev_name)
        LOGGER.info("Device was already registered on SageMaker Edge Manager")
    except ClientError as e:
        if e.response['Error']['Code'] != 'ValidationException': raise e
        LOGGER.info("Registering a new device %s on fleet %s" % (dev_name, fleet_name))
        sm_client.register_devices(DeviceFleetName=fleet_name, Devices=dev)
        iot_client.add_thing_to_thing_group(
            thingGroupName=thing_group_name,
            thingGroupArn=thing_group_arn,
            thingName='edge-device-%d' % agent_id,
            thingArn=thing_arn_template % ('edge-device-%d' % agent_id)
        )

    # if you reach this point you need to create new certificates
    # generate the certificates
    cert = base % (agent_id, 'cert')
    key = base % (agent_id, 'pub')
    pub = base % (agent_id, 'key')

    cert_meta = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert_meta['certificateArn']
    with open(cert, 'w') as c:
        c.write(cert_meta['certificatePem'])
    with open(key, 'w') as c:
        c.write(cert_meta['keyPair']['PrivateKey'])
    with open(pub, 'w') as c:
        c.write(cert_meta['keyPair']['PublicKey'])

    # attach the certificates to the policy and to the thing
    iot_client.attach_policy(policyName=policy_name, target=cert_arn)
    iot_client.attach_thing_principal(thingName='edge-device-%d' % agent_id, principal=cert_arn)

    LOGGER.info("Finally, let's create the agent config file")
    agent_params = {
        "sagemaker_edge_core_device_name": dev_name,
        "sagemaker_edge_core_device_fleet_name": fleet_name,
        "sagemaker_edge_core_capture_data_buffer_size": 30,
        "sagemaker_edge_core_capture_data_batch_size": 10,
        "sagemaker_edge_core_capture_data_push_period_seconds": 4,
        "sagemaker_edge_core_folder_prefix": "wind_turbine_data",
        "sagemaker_edge_core_region": region,
        "sagemaker_edge_core_root_certs_path": "./agent/certificates/root",
        "sagemaker_edge_provider_aws_ca_cert_file": "./agent/certificates/iot/AmazonRootCA1.pem",
        "sagemaker_edge_provider_aws_cert_file": "./%s" % cert,
        "sagemaker_edge_provider_aws_cert_pk_file": "./%s" % key,
        "sagemaker_edge_provider_aws_iot_cred_endpoint": "https://%s/role-aliases/%s/credentials" % (
        cred_host, policy_alias),
        "sagemaker_edge_provider_provider": "Aws",
        "sagemaker_edge_provider_s3_bucket_name": bucket_name,
        "sagemaker_edge_core_capture_data_destination": "Cloud"
    }
    with open('agent/conf/config_edge_device_%d.json' % agent_id, 'w') as conf:
        conf.write(json.dumps(agent_params, indent=4))

def update_device_fleet(bucket_name, device_fleet_name, device_fleet_suffix):
    try:
        device_fleets = sm_client.list_device_fleets(
            NameContains="{}-{}".format(device_fleet_name, device_fleet_suffix))
        wind_turbine_device_fleet_name = device_fleets['DeviceFleetSummaries'][0]['DeviceFleetName']

        update_device_fleet_response = sm_client.update_device_fleet(
            DeviceFleetName=wind_turbine_device_fleet_name,
            OutputConfig={
                'S3OutputLocation': 's3://{}'.format(bucket_name),
            },
        )

        return update_device_fleet_response
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def upload_inference_package(bucket_name, inference_package, model_package):
    try:
        s3_resource.meta.client.upload_file(
            inference_package,
            bucket_name,
            "artifacts/inference/{}.0.0/{}".format(model_package["ModelPackageVersion"],
                                                   inference_package.split("/")[-1]))
    except Exception as e:
        stacktrace = traceback.format_exc()
        LOGGER.error("{}".format(stacktrace))

        raise e

def get_pipeline(
    region,
    bucket_name,
    component_name,
    device_fleet_name,
    device_fleet_suffix,
    inference_recipes_entrypoint,
    model_name,
    model_package_group_arn,
    n_features,
    thing_group_name,
    inference_package=None,
    role=None,
    pipeline_name="DeploymentPipeline"):
    """Gets a SageMaker ML Pipeline instance working with on abalone data.

    Args:
        region: AWS region to create and run the pipeline.
        role: IAM role to create and run steps and pipeline.
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        an instance of a pipeline
    """

    sagemaker_session = get_session(region, bucket_name)

    model_package_approved = get_approved_package(model_package_group_arn)
    model_package = describe_model_package(model_package_approved["ModelPackageArn"])

    compilation_job_name = "{}-{}".format(pipeline_name, str(int(time.time()*1000)))

    compilation_resp = run_compilation_job(
        compilation_job_name,
        bucket_name,
        model_package,
        n_features,
        role
    )

    LOGGER.info("Compilation Job: {}".format(compilation_resp))

    edge_packaging_job_name = "{}-{}".format(pipeline_name, str(int(time.time() * 1000)))

    packaging_resp = run_packaging_job(
        bucket_name,
        compilation_job_name,
        component_name,
        edge_packaging_job_name,
        model_name,
        model_package,
        role
    )

    LOGGER.info("Packaging Job: {}".format(packaging_resp))

    thing_groups = iot_client.list_thing_groups(namePrefixFilter=thing_group_name)
    wind_turbine_thing_group_arn = thing_groups['thingGroups'][0]['groupArn']

    upload_inference_package(bucket_name, inference_package, model_package)

    with open(inference_recipes_entrypoint) as f:
        recipe = f.read()

    recipe = recipe.replace('_BUCKET_', bucket_name)
    recipe = recipe.replace('_VERSION_', str(model_package["ModelPackageVersion"]) + ".0.0")

    ggv2_client.create_component_version(inlineRecipe=recipe)

    setup_fleet(
        bucket_name,
        device_fleet_suffix,
        region,
        thing_group_name
    )

    update_device_fleet_response = update_device_fleet(bucket_name, device_fleet_name, device_fleet_suffix)

    LOGGER.info("Update Device Fleet: {}".format(update_device_fleet_response))

    ggv2_deployment_name = 'wind-turbine-anomaly-ggv2-%d' % int(time.time() * 1000)

    run_deployment_ggv2(
        bucket_name,
        device_fleet_name,
        device_fleet_suffix,
        ggv2_deployment_name,
        model_package,
        wind_turbine_thing_group_arn)

    return None
