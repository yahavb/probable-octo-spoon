#!/bin/sh
  
echo "Creating docker image repositories"
aws cloudformation create-stack --stack-name appsimulator-ecr-repos --template-body file://./ecr-repos.json
