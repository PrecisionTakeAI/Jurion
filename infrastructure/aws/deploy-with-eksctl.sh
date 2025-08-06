#!/bin/bash
# Complete EKS Deployment Script using eksctl
# This script will create a working EKS cluster with nodes that will definitely join

set -e

echo "=== EKS Cluster Deployment with eksctl ==="
echo "This will create a working cluster with properly configured nodes"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REGION="ap-southeast-2"
CLUSTER_NAME="legallm-cluster-v2"
KEY_PAIR_NAME="${1:-}"  # Pass your EC2 key pair name as first argument

echo -e "\n${YELLOW}Step 1: Prerequisites Check${NC}"

# Check if eksctl is installed
if ! command -v eksctl &> /dev/null; then
    echo "eksctl not found. Installing..."
    ./install-eksctl.sh
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
    exit 1
fi

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo "kubectl not found. Installing..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/
fi

echo -e "\n${YELLOW}Step 2: Check AWS Credentials${NC}"
aws sts get-caller-identity || {
    echo "AWS credentials not configured. Please run: aws configure"
    exit 1
}

# Update the config file with the key pair name if provided
if [ -n "$KEY_PAIR_NAME" ]; then
    echo -e "\n${YELLOW}Using SSH key pair: $KEY_PAIR_NAME${NC}"
    sed -i "s/your-key-pair/$KEY_PAIR_NAME/g" eksctl-cluster.yaml
else
    echo -e "\n${YELLOW}No SSH key pair provided. Disabling SSH access.${NC}"
    # Remove SSH section from config
    sed -i '/ssh:/,+2d' eksctl-cluster.yaml
fi

echo -e "\n${YELLOW}Step 3: Clean up any existing failed resources${NC}"
# Delete the old cluster if it exists
aws eks describe-cluster --name legallm-cluster --region $REGION &>/dev/null && {
    echo "Found old cluster. You may want to delete it first with:"
    echo "eksctl delete cluster --name legallm-cluster --region $REGION"
}

echo -e "\n${YELLOW}Step 4: Create EKS Cluster with eksctl${NC}"
echo "This will take about 15-20 minutes..."

# Create the cluster
eksctl create cluster -f eksctl-cluster.yaml

echo -e "\n${GREEN}✓ Cluster created successfully!${NC}"

echo -e "\n${YELLOW}Step 5: Verify Cluster and Nodes${NC}"

# Update kubeconfig
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

# Check nodes
echo "Checking nodes..."
kubectl get nodes

# Check system pods
echo -e "\nChecking system pods..."
kubectl get pods -n kube-system

echo -e "\n${GREEN}=== SUCCESS! ===${NC}"
echo "Your EKS cluster is ready with working nodes!"
echo ""
echo "Next steps:"
echo "1. Deploy your application: kubectl apply -f k8s/"
echo "2. Check cluster status: eksctl get cluster --name $CLUSTER_NAME --region $REGION"
echo "3. View nodes: kubectl get nodes"
echo ""
echo "To delete the cluster later:"
echo "eksctl delete cluster --name $CLUSTER_NAME --region $REGION"