#!/bin/bash
# EKS Node Diagnostics Script
# Run this to identify why nodes aren't joining the cluster

set -e

echo "=== EKS Node Diagnostics ==="
echo "Starting comprehensive diagnostics..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get cluster name
CLUSTER_NAME="legallm-cluster"
REGION="ap-southeast-2"

echo -e "\n${YELLOW}1. Checking Cluster Status${NC}"
aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query 'cluster.status' --output text

echo -e "\n${YELLOW}2. Checking Cluster Endpoint${NC}"
CLUSTER_ENDPOINT=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query 'cluster.endpoint' --output text)
echo "Endpoint: $CLUSTER_ENDPOINT"

echo -e "\n${YELLOW}3. Testing Cluster Connectivity${NC}"
# Extract hostname from endpoint
ENDPOINT_HOST=$(echo $CLUSTER_ENDPOINT | sed 's|https://||' | cut -d'/' -f1)
nc -zv $ENDPOINT_HOST 443 2>&1 || echo -e "${RED}Cannot reach cluster endpoint!${NC}"

echo -e "\n${YELLOW}4. Checking Node Group Status${NC}"
aws eks list-nodegroups --cluster-name $CLUSTER_NAME --region $REGION --output table

echo -e "\n${YELLOW}5. Checking Failed Instances${NC}"
INSTANCE_IDS="i-0972b538a751f2009 i-0ad13691027ccf19f"
for INSTANCE_ID in $INSTANCE_IDS; do
    echo -e "\n${YELLOW}Instance: $INSTANCE_ID${NC}"
    
    # Get instance status
    aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION \
        --query 'Reservations[0].Instances[0].[State.Name,PrivateIpAddress,PublicIpAddress,SubnetId]' \
        --output table 2>/dev/null || echo "Instance not found or terminated"
done

echo -e "\n${YELLOW}6. Checking IAM Role Policies${NC}"
NODE_ROLE_NAME="LegalLLM-EKSNodeRole"
aws iam list-attached-role-policies --role-name $NODE_ROLE_NAME --output table 2>/dev/null || echo "Role not found"

echo -e "\n${YELLOW}7. Checking Security Groups${NC}"
# Get VPC ID
VPC_ID=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION \
    --query 'cluster.resourcesVpcConfig.vpcId' --output text)
echo "VPC ID: $VPC_ID"

# List security groups
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[?contains(GroupName, `eks`) || contains(GroupName, `node`)].{Name:GroupName,ID:GroupId}' \
    --output table --region $REGION

echo -e "\n${YELLOW}8. Checking VPC DNS Settings${NC}"
aws ec2 describe-vpcs --vpc-ids $VPC_ID --region $REGION \
    --query 'Vpcs[0].{DNS:EnableDnsSupport,Hostnames:EnableDnsHostnames}' --output table

echo -e "\n${YELLOW}9. Getting System Logs from Failed Instance (if accessible)${NC}"
# Try to get system log from one of the instances
aws ec2 get-console-output --instance-id i-0972b538a751f2009 --region $REGION \
    --output text | tail -50 2>/dev/null || echo "Cannot retrieve console output"

echo -e "\n${GREEN}Diagnostics complete!${NC}"
echo -e "${YELLOW}Look for any errors above, especially in connectivity and IAM roles.${NC}"