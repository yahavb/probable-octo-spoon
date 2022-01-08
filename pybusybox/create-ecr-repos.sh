#!/bin/sh
  
echo "Creating docker image repositories"
aws cloudformation create-stack --stack-name py-busywork-ecr-repos --template-body file://./ecr-repos.json
