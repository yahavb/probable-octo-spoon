#!/bin/sh
  
echo "Creating docker image repositories"
aws cloudformation create-stack --stack-name spotsighandler-ecr-repos --template-body file://./ecr-repos.json
