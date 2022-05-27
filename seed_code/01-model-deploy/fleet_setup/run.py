import argparse
import boto3
from botocore.exceptions import ClientError
import io
import json
import logging
import os
import requests
import shutil
import stat
import tarfile

logger = logging.getLogger(__name__)

iot_client = boto3.client('iot')
sm_client = boto3.client('sagemaker')
s3_client = boto3.client('s3')


def setup_agent(agent_id, args, thing_group_name, thing_group_arn):
    policy_name = 'WindTurbineFarmPolicy-{}'.format(args.device_fleet_suffix)
    base = "agent/certificates/iot/edge_device_%d_%s.pem"
    fleet_name = 'wind-turbine-farm-{}'.format(args.device_fleet_suffix)

    thing_arn_template = thing_group_arn.replace('thinggroup', 'thing').replace(thing_group_name, '%s')

    cred_host = iot_client.describe_endpoint(endpointType='iot:CredentialProvider')['endpointAddress']
    policy_alias = 'SageMakerEdge-%s' % fleet_name

    # register the device in the fleet    
    # the device name needs to have 36 chars
    dev_name = "edge-device-%d" % agent_id

    """
        Check if Thing is added to thing group
    """
    response = iot_client.list_thing_groups_for_thing(
        thingName='edge-device-%d' % agent_id,
        maxResults=100
    )

    logger.info("List thins per agent edge-device-{}".format(agent_id))
    logger.info(response)

    found = False

    if "thingGroups" in response and len(response["thingGroups"]) > 0:
        for group in response["thingGroups"]:
            if group["groupName"] == thing_group_name:
                logger.info("Agent edge-device-{} already in the group {}".format(agent_id, thing_group_name))
                found = True
                break

    if not found:
        logger.info("Adding agent edge-device-{} to group {}".format(agent_id, thing_group_name))

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

    logger.info("Finally, let's create the agent config file")
    agent_params = {
        "sagemaker_edge_core_device_name": dev_name,
        "sagemaker_edge_core_device_fleet_name": fleet_name,
        "sagemaker_edge_core_capture_data_buffer_size": 30,
        "sagemaker_edge_core_capture_data_batch_size": 10,
        "sagemaker_edge_core_capture_data_push_period_seconds": 4,
        "sagemaker_edge_core_folder_prefix": "wind_turbine_data",
        "sagemaker_edge_core_region": args.aws_region,
        "sagemaker_edge_core_root_certs_path": "./agent/certificates/root",
        "sagemaker_edge_provider_aws_ca_cert_file": "./agent/certificates/iot/AmazonRootCA1.pem",
        "sagemaker_edge_provider_aws_cert_file": "./%s" % cert,
        "sagemaker_edge_provider_aws_cert_pk_file": "./%s" % key,
        "sagemaker_edge_provider_aws_iot_cred_endpoint": "https://%s/role-aliases/%s/credentials" % (
        cred_host, policy_alias),
        "sagemaker_edge_provider_provider": "Aws",
        "sagemaker_edge_provider_s3_bucket_name": args.artifact_bucket,
        "sagemaker_edge_core_capture_data_destination": "Cloud"
    }
    with open('agent/conf/config_edge_device_%d.json' % agent_id, 'w') as conf:
        conf.write(json.dumps(agent_params, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", type=str, default=os.environ.get("LOGLEVEL", "INFO").upper())
    parser.add_argument("--artifact-bucket", type=str, required=True)
    parser.add_argument("--aws-region", type=str, required=True)
    parser.add_argument("--device-fleet-suffix", type=str, required=True)
    parser.add_argument("--num-agents", type=int, default=2)
    parser.add_argument("--thing-group-name", type=str, required=True)

    args, _ = parser.parse_known_args()

    # Configure logging to output the line number and message
    log_format = "%(levelname)s: [%(filename)s:%(lineno)s] %(message)s"
    logging.basicConfig(format=log_format, level=args.log_level)

    # create a new thing group
    thing_group_arn = None
    agent_pkg_bucket = 'sagemaker-edge-release-store-us-west-2-linux-x64'
    agent_config_package_prefix = 'wind_turbine_agent/config.tgz'

    try:
        thing_group_arn = iot_client.describe_thing_group(thingGroupName=args.thing_group_name)['thingGroupArn']
        logger.info("Thing group found")
    except iot_client.exceptions.ResourceNotFoundException as e:
        logger.info("Creating a new thing group")
        thing_group_arn = iot_client.create_thing_group(thingGroupName=args.thing_group_name)['thingGroupArn']

    logger.info("Creating the directory structure for the agent")
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
        Key='Certificates/%s/%s.pem' % (args.aws_region, args.aws_region),
        Filename='agent/certificates/root/%s.pem' % args.aws_region
    )
    # adjust the permissions of the files
    os.chmod('agent/certificates/iot/AmazonRootCA1.pem', stat.S_IRUSR | stat.S_IRGRP)
    os.chmod('agent/certificates/root/%s.pem' % args.aws_region, stat.S_IRUSR | stat.S_IRGRP)

    logger.info("Processing the agents...")
    for agent_id in range(args.num_agents):
        setup_agent(agent_id, args, args.thing_group_name, thing_group_arn)

    logger.info("Creating the final package...")
    with io.BytesIO() as f:
        with tarfile.open(fileobj=f, mode='w:gz') as tar:
            tar.add('agent', recursive=True)
        f.seek(0)
        logger.info("Uploading to S3")
        s3_client.upload_fileobj(f, Bucket=args.artifact_bucket, Key=agent_config_package_prefix)

    shutil.rmtree('agent')

    logger.info("Done!")
