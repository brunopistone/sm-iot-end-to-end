# SageMaker End to End lab for IoT devices using Edge Manager 

In this repository, we are stepping through an end to end implementation of Machine Learning (ML) models using Amazon SageMaker,
by targeting as deployment environment simulated remote edge devices using [Amazon SageMaker Edge Manager](https://docs.aws.amazon.com/sagemaker/latest/dg/edge.html) 
and [AWS IoT GreenGrass](https://docs.aws.amazon.com/greengrass/v1/developerguide/what-is-gg.html).

This is a sample code repository for demonstrating how to organize your code for build and train your model, by starting from 
an implementation through notebooks for arriving to a code structure architecture for implementing ML pipeline using Amazon 
SageMaker Pipeline, and how to setup a repository for deploying ML models using CI/CD.

This repository is enriched by CloudFormation templates for setting up the ML environment, by creating the SageMaker Studio 
environment, Networking, and CI/CD for deploying ML models

Everything can be tested by using the example notebooks for running training on SageMaker using the following frameworks:
* PyTorch

## Environment Setup

Setup the ML environment by deploying the [CloudFormation](./infrastructure_templates) templates described as below:

1. [00-networking](./infrastructure_templates/00-networking/template.yml): This template is creating a networking resources,  
such as VPC, Private Subnets, Security Groups, for a secure environment for Amazon SageMaker Studio. The necessary variables 
used by SageMaker Studio are stored using [AWS Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-systems-manager.html)
2. [01-sagemaker-studio](./infrastructure_templates/01-sagemaker-studio-environment/template.yml): This template is creating 
the SageMaker Studio environment, with the necessary execution role used during the experimentation and the execution of the 
SageMaker Jobs. *Optional parameters*:
   1. *SecurityGroupId*: Provide a Security Group for studio if you want to use your own networking setup, otherwise the parameter
   is read by using AWS SSM after the deployment of the template [00-networking](./infrastructure_templates/00-networking/template.yml)
   2. *SubnetId*: Provide a Subnet (Public or Private) for studio if you want to use your own networking setup, otherwise the parameter
   is read by using AWS SSM after the deployment of the template [00-networking](./infrastructure_templates/00-networking/template.
   3. *VpcId*: Provide a Vpc ID for studio if you want to use your own networking setup, otherwise the parameter is read by 
   using AWS SSM after the deployment of the template [00-networking](./infrastructure_templates/00-networking/template.
3. [02-ci-cd](./infrastructure_templates/02-ci-cd/template.yml): This template is creating the CI/CD pipelines using 
[AWS CodeBuild](https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html) and [AWS CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html).
It creates two CI/CD pipelines, linked to two AWS CodeCommit repositories, one for training and one for deployment, that can 
be triggered through pushes on the main branch or with the automation part deployed in the next stack. *Mandatory parameters*:
   1. *PipelineSuffix*: Suffix to use for creating the CI/CD pipelines
   2. *RepositoryTrainingName*: Name for the repository where the build and train code will be stored
   3. *RepositoryDeploymentName*:  Name for the repository where the deployment code will be stored
   4. *S3BucketArtifacts*: Name of the Amazon S3 Bucket that will be created in the next stack used for storing code and model artifacts
4. [03-ml-environment](./infrastructure_templates/03-ml-environment/template.yml): This template is creating the necessary resources for the 
ML workflow, such as Amazon S3 bucket for storing code and model artifacts, [Amazon SageMaker Model Registry](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html) 
for versioning trained ML models, and [Amazon EventBridge Rule](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html) 
for monitoring updates in the SageMaker Model Registry and start the CI/CD pipeline for deploying ML models in the production environments.

## Labs

### Build and Train ML models

The code structure defined for the [Build and Train ML models](./lab/00-model-build-train) is the following:

* [algorithms](./lab/00-model-build-train/algorithms): The code used by the ML pipelines for processing and training ML models is stored in this folder
  * [algorithms/preprocessing](./lab/00-model-build-train/algorithms/preprocessing): This folder contains the python code for performing processing of data
  using Amazon SageMaker Processing Jobs
  * [algorithms/training](./lab/00-model-build-train/algorithms/training): This folder contains the python code for training a custom ML model 
  using Amazon SageMaker Training Jobs
* [mlpipelines](./lab/00-model-build-train/mlpipelines): This folder contains some utilities scripts created in the official AWS example 
[Amazon SageMaker secure MLOps](https://github.com/aws-samples/amazon-sagemaker-secure-mlops) and it contains the definition for the 
Amazon SageMaker Pipeline used for training
  * [mlpipelines](./lab/00-model-build-train/mlpipelines/training): This folder contains the python code for the ML pipelines used for training
* [notebooks](./lab/00-model-build-train/notebooks): This folder contains the lab notebooks to use for this workshop:
  * [notebooks/00-Data-Visualization](./lab/00-model-build-train/notebooks/00-Data-Visualization.ipynb): Explore the input data and test the processing scripts 
  in the notebook
  * [notebooks/01-Training-with-Pytorch](./lab/00-model-build-train/notebooks/01-Training-with-Pytorch.ipynb): SageMaker 
  End to End approach for processing data using SageMaker Processing, Training the ML model using SageMaker Training, Register 
  the trained model version by using Amazon SageMaker Model Registry, evaulate your model by creating inference data using 
  Amazon SageMaker Batch Transform
  * [notebooks/02-SageMaker-Pipeline-Training](./lab/00-model-build-train/notebooks/02-SageMaker-Pipeline-Training.ipynb): Define 
  the workflow steps and test the entire end to end using Amazon SageMaker Pipeline