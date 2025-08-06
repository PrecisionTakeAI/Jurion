#!/bin/bash
# Script to fix common EKS node joining issues
# Run this to fix your current cluster

set -e

echo "=== Fixing Current EKS Cluster ==="

CLUSTER_NAME="legallm-cluster"
REGION="ap-southeast-2"

echo "1. Update aws-auth ConfigMap"
# This is the most common issue - nodes can't authenticate

# Get the node instance role ARN
NODE_ROLE_ARN=$(aws iam get-role --role-name LegalLLM-EKSNodeRole --query 'Role.Arn' --output text)

# Create the aws-auth ConfigMap
cat <<EOF > aws-auth-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: ${NODE_ROLE_ARN}
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
EOF

# Apply the ConfigMap
kubectl apply -f aws-auth-cm.yaml

echo "2. Check and fix security group rules"

# Get cluster security group
CLUSTER_SG=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION \
    --query 'cluster.resourcesVpcConfig.clusterSecurityGroupId' --output text)

echo "Cluster Security Group: $CLUSTER_SG"

# Ensure all traffic is allowed within the cluster security group
aws ec2 authorize-security-group-ingress \
    --group-id $CLUSTER_SG \
    --protocol all \
    --source-group $CLUSTER_SG \
    --region $REGION 2>/dev/null || echo "Rule already exists"

echo "3. Restart failed instances (if they still exist)"

INSTANCE_IDS="i-0972b538a751f2009 i-0ad13691027ccf19f"
for INSTANCE_ID in $INSTANCE_IDS; do
    echo "Restarting instance: $INSTANCE_ID"
    aws ec2 reboot-instances --instance-ids $INSTANCE_ID --region $REGION 2>/dev/null || \
        echo "Instance $INSTANCE_ID not found or already terminated"
done

echo "4. Check node logs after restart (wait 2 minutes)"
sleep 120

kubectl get nodes

echo ""
echo "If nodes still don't join, check the user data script on the instances:"
echo "aws ec2 describe-instance-attribute --instance-id <instance-id> --attribute userData --region $REGION"
echo ""
echo "The user data should contain the bootstrap command like:"
echo "/etc/eks/bootstrap.sh $CLUSTER_NAME"