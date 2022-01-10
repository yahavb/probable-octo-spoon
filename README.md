# probable-octo-spoon
Playing with EKS, Fargate, and Karpenter 


* Create k8s cluster

* Create AWS Identity and Access Management (IAM) OpenID Connect (OIDC) provider.

```
aws eks describe-cluster --name fg-bliz-us-west-2 --query "cluster.identity.oidc.issuer" --output text
https://oidc.eks.us-west-2.amazonaws.com/id/F9B0F7368F54F66E058DE79AF6B505C2

$eksctl utils associate-iam-oidc-provider --cluster  fg-bliz-us-west-2 --approve
2022-01-07 14:19:11 [ℹ]  eksctl version 0.70.0
2022-01-07 14:19:11 [ℹ]  using region us-west-2
2022-01-07 14:19:12 [ℹ]  will create IAM Open ID Connect provider for cluster "atvi-arm-us-west-2" in "us-west-2"
2022-01-07 14:19:12 [✔]  created IAM Open ID Connect provider for cluster "atvi-arm-us-west-2" in "us-west-2"
```

* Configuring the Amazon VPC CNI plugin to use IAM roles for service accounts

```
eksctl create iamserviceaccount \
    --name aws-node \
    --namespace kube-system \
    --cluster fg-bliz-us-west-2 \
    --attach-policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy \
    --approve \
    --override-existing-serviceaccounts
```

```
eksctl create addon \
    --name vpc-cni \
    --version latest \
    --cluster fg-bliz-us-west-2 \
    --service-account-role-arn arn:aws:iam::498254202105:role/eksctl-fg-bliz-us-west-2-addon-iamserviceacc-Role1-1IXWZVWEIAJSF \
    --force
```

* Deploy  the AWS Load Balancer Controller to an Amazon EKS cluster

```bash
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.3.1/docs/install/iam_policy.json

aws iam create-policy \
>     --policy-name AWSLoadBalancerControllerIAMPolicy \
>     --policy-document file://iam_policy.json
{
    "Policy": {
        "PolicyName": "AWSLoadBalancerControllerIAMPolicy",
        "PolicyId": "ANPAZP7C3APSXCU44EK3A",
        "Arn": "arn:aws:iam::652773884901:policy/AWSLoadBalancerControllerIAMPolicy",
        "Path": "/",
        "DefaultVersionId": "v1",
        "AttachmentCount": 0,
        "PermissionsBoundaryUsageCount": 0,
        "IsAttachable": true,
        "CreateDate": "2022-01-07T22:37:51+00:00",
        "UpdateDate": "2022-01-07T22:37:51+00:00"
    }
}

eksctl create iamserviceaccount \
  --cluster=atvi-arm-us-west-2 \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::652773884901:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve
```

```
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=atvi-arm-us-west-2 \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller 

kubectl get deployment -n kube-system aws-load-balancer-controller
```

* Deploy Karpenter

```bash
export CLUSTER_NAME=atvi-arm-us-west-2
export AWS_DEFAULT_REGION=us-west-2
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

SUBNET_IDS=$(aws cloudformation describe-stacks \
    --stack-name eksctl-${CLUSTER_NAME}-cluster \
    --query 'Stacks[].Outputs[?OutputKey==`SubnetsPrivate`].OutputValue' \
    --output text)
aws ec2 create-tags \
    --resources $(echo $SUBNET_IDS | tr ',' '\n') \
    --tags Key="kubernetes.io/cluster/${CLUSTER_NAME}",Value=
```

```
TEMPOUT=$(mktemp)
curl -fsSL https://karpenter.sh/docs/getting-started/cloudformation.yaml > $TEMPOUT \
&& aws cloudformation deploy \
  --stack-name Karpenter-${CLUSTER_NAME} \
  --template-file ${TEMPOUT} \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ClusterName=${CLUSTER_NAME}
```

```
eksctl create iamidentitymapping \
  --username system:node:{{EC2PrivateDNSName}} \
  --cluster  ${CLUSTER_NAME} \
  --arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/KarpenterNodeRole-${CLUSTER_NAME} \
  --group system:bootstrappers \
  --group system:nodes
```

```
eksctl create iamserviceaccount \
  --cluster $CLUSTER_NAME --name karpenter --namespace karpenter \
  --attach-policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/KarpenterControllerPolicy-$CLUSTER_NAME \
  --approve
```


* Create a Fargate profile
```
eksctl create fargateprofile \
    --cluster atvi-arm-us-west-2 \
    --name atvi_fargate_profile \
    --namespace default \
    --labels project=atvi
```

```
aws eks create-fargate-profile \
    --fargate-profile-name coredns \
    --cluster-name atvi-arm-us-west-2 \
    --pod-execution-role-arn arn:aws:iam::652773884901:role/AmazonEKSFargatePodExecutionRole \
    --selectors namespace=kube-system,labels={k8s-app=kube-dns} \
    --subnets subnet-07ba6af31cdd29258 subnet-0af0631e6e28d2b6c subnet-0e7a1a265475f9212 subnet-03c703daa3a727086 subnet-02cfd255de99e0ade subnet-0a0725ab7d37bee63
```

```
aws eks create-fargate-profile     --fargate-profile-name coredns     --cluster-name atvi-arm-us-west-2     --pod-execution-role-arn arn:aws:iam::652773884901:role/AmazonEKSFargatePodExecutionRole     --selectors namespace=kube-system,labels={k8s-app=kube-dns}     --subnets subnet-03c703daa3a727086 subnet-02cfd255de99e0ade subnet-0a0725ab7d37bee63
{
    "fargateProfile": {
        "fargateProfileName": "coredns",
        "fargateProfileArn": "arn:aws:eks:us-west-2:652773884901:fargateprofile/atvi-arm-us-west-2/coredns/b0bf1b6d-670a-8f8c-f15c-1cc65281a156",
        "clusterName": "atvi-arm-us-west-2",
        "createdAt": "2022-01-07T15:23:37.600000-08:00",
        "podExecutionRoleArn": "arn:aws:iam::652773884901:role/AmazonEKSFargatePodExecutionRole",
        "subnets": [
            "subnet-03c703daa3a727086",
            "subnet-02cfd255de99e0ade",
            "subnet-0a0725ab7d37bee63"
        ],
        "selectors": [
            {
                "namespace": "kube-system",
                "labels": {
                    "k8s-app": "kube-dns"
                }
            }
        ],
        "status": "CREATING",
        "tags": {}
    }
}
```


```
aws iam attach-role-policy \
  --policy-arn arn:aws:iam::652773884901:policy/eks-fargate-logging-policy \
  --role-name AmazonEKSFargatePodExecutionRole
```

```
ClusterName=fg-bliz-us-west-2
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'
[[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
[[ -z ${FluentBitHttpPort} ]] && FluentBitHttpServer='Off' || FluentBitHttpServer='On'
curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml | sed 's/{{cluster_name}}/'${ClusterName}'/;s/{{region_name}}/'${RegionName}'/;s/{{http_server_toggle}}/"'${FluentBitHttpServer}'"/;s/{{http_server_port}}/"'${FluentBitHttpPort}'"/;s/{{read_from_head}}/"'${FluentBitReadFromHead}'"/;s/{{read_from_tail}}/"'${FluentBitReadFromTail}'"/' | kubectl apply -f - 
```


```
aws iam attach-role-policy \
  --policy-arn arn:aws:iam::498254202105:policy/eks-fargate-logging-policy \
  --role-name AmazonEKSFargatePodExecutionRole
```


# Enable fargate pods to assume IAM using IRSA

```
eksctl create iamserviceaccount \
    --name appsimulator \
    --namespace default \
    --cluster fg-atvi-arm-us-west-2 \
    --attach-policy-arn arn:aws:iam::652773884901:policy/appsimulator \
    --approve \
    --override-existing-serviceaccounts
```
