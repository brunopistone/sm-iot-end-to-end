# © 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

#!/bin/sh

ENV=$1
PIPELINE=$2

if [ -z ${PIPELINE} ] ;
then
    echo "Pipeline not specified"
    exit 1
fi

## This section is to create a package for the pipeline

#mkdir dist
#cp -r pipelines/${PIPELINE} dist/
#cp -r pipelines/configs dist/
#cp pipelines/*.py dist/
#
#cd dist
#cp ${PIPELINE}/buildspec.sh ./
#cp ${PIPELINE}/README.md ./
#rm -rf ${PIPELINE}/buildspec.sh
#rm -rf ${PIPELINE}/README.md
#tar -czvf ${PIPELINE}.tar.gz *
#
#ls | grep -v ${PIPELINE}.tar.gz | xargs rm -rf

##########################################################

./pipelines/${PIPELINE}/buildspec.sh ${ENV} ${PIPELINE}