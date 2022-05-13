# © 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

#!/bin/sh

ENV=$1
PIPELINE=$2

if [ -z ${ENV} ] ;
then
    echo "Environment not specified"
    exit 1
fi

if [ -z ${PIPELINE} ] ;
then
    echo "Environment not specified"
    exit 1
fi

SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

cd ${SCRIPTPATH}

cd ..

pip install -r requirements.txt

python run_pipeline.py -e ${ENV} -p ${PIPELINE} -i \
"compilation_input_shape=[1, 1, 1, 1]" \
"input_file_name=processed.csv" \
"model_package_group_name=mlops-iot-regressor" \
"processing_input_file_name=bottle.csv" \
"processing_instance_count=1" \
"processing_instance_type=ml.t3.large" \
"training_instance_count=1" \
"training_instance_type=ml.m5.large"