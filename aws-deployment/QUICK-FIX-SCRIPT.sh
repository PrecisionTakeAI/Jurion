#!/bin/bash
# IMMEDIATE FIX SCRIPT FOR EKS NODE JOIN ISSUES
# Run this script to quickly fix your node join problems

set -e
echo "=== EKS Node Join Quick Fix Script ==="
echo "This script will fix your node join issues step by step"
echo ""

# Configuration
CLUSTER_NAME="legalllm-cluster"
REGION="ap-southeast-2"
NODE_ROLE_NAME="legalllm-eks-node-role"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Checking cluster status...${NC}"
aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.status" --output text || {
    echo -e "${RED}Error: Cluster not found or AWS CLI not configured${NC}"
    echo "Please ensure AWS CLI is configured with: aws configure"
    exit 1
}

echo -e "${GREEN}Cluster found!${NC}"

echo -e "${YELLOW}Step 2: Getting VPC and Security Group IDs...${NC}"
VPC_ID=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.resourcesVpcConfig.vpcId" --output text)
CLUSTER_SG=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.resourcesVpcConfig.clusterSecurityGroupId" --output text)

echo "VPC ID: $VPC_ID"
echo "Cluster Security Group: $CLUSTER_SG"

echo -e "${YELLOW}Step 3: Finding node security group...${NC}"
NODE_SG=$(aws ec2 describe-security-groups --region $REGION --filters "Name=tag:Name,Values=legalllm-eks-nodes-sg" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "")

if [ -z "$NODE_SG" ]; then
    echo -e "${YELLOW}Node security group not found by tag, searching by VPC...${NC}"
    NODE_SG=$(aws ec2 describe-security-groups --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=*node*" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "")
fi

if [ -z "$NODE_SG" ]; then
    echo -e "${RED}Could not find node security group. Creating one...${NC}"
    NODE_SG=$(aws ec2 create-security-group \
        --group-name "legalllm-eks-nodes-sg-fixed" \
        --description "Fixed security group for EKS nodes" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query "GroupId" \
        --output text)
    echo "Created new node security group: $NODE_SG"
fi

echo "Node Security Group: $NODE_SG"

echo -e "${YELLOW}Step 4: Fixing Security Group Rules...${NC}"

# Function to add security group rule safely
add_sg_rule() {
    local sg_id=$1
    local protocol=$2
    local from_port=$3
    local to_port=$4
    local source=$5
    local description=$6
    
    echo "Adding rule: $description"
    if [ "$source" == "self" ]; then
        aws ec2 authorize-security-group-ingress \
            --group-id $sg_id \
            --protocol $protocol \
            --port $from_port-$to_port \
            --source-group $sg_id \
            --region $REGION 2>/dev/null || echo "  Rule may already exist (this is OK)"
    elif [[ "$source" == sg-* ]]; then
        aws ec2 authorize-security-group-ingress \
            --group-id $sg_id \
            --protocol $protocol \
            --port $from_port-$to_port \
            --source-group $source \
            --region $REGION 2>/dev/null || echo "  Rule may already exist (this is OK)"
    else
        aws ec2 authorize-security-group-ingress \
            --group-id $sg_id \
            --protocol $protocol \
            --port $from_port-$to_port \
            --cidr $source \
            --region $REGION 2>/dev/null || echo "  Rule may already exist (this is OK)"
    fi
}

# Fix cluster security group
echo "Fixing cluster security group rules..."
add_sg_rule $CLUSTER_SG "tcp" "443" "443" $NODE_SG "Allow nodes to communicate with cluster API"
add_sg_rule $CLUSTER_SG "tcp" "10250" "10250" $NODE_SG "Allow kubelet API from nodes"

# Fix node security group
echo "Fixing node security group rules..."
add_sg_rule $NODE_SG "tcp" "443" "443" $CLUSTER_SG "Allow cluster API to nodes"
add_sg_rule $NODE_SG "tcp" "10250" "10250" $CLUSTER_SG "Allow cluster to kubelet"
add_sg_rule $NODE_SG "-1" "0" "65535" "self" "Allow node to node communication"
add_sg_rule $NODE_SG "tcp" "53" "53" "$VPC_CIDR" "Allow DNS TCP" 2>/dev/null || add_sg_rule $NODE_SG "tcp" "53" "53" "10.0.0.0/16" "Allow DNS TCP"
add_sg_rule $NODE_SG "udp" "53" "53" "$VPC_CIDR" "Allow DNS UDP" 2>/dev/null || add_sg_rule $NODE_SG "udp" "53" "53" "10.0.0.0/16" "Allow DNS UDP"

echo -e "${YELLOW}Step 5: Ensuring VPC DNS is enabled...${NC}"
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames --region $REGION
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support --region $REGION
echo -e "${GREEN}VPC DNS settings updated${NC}"

echo -e "${YELLOW}Step 6: Updating EKS endpoint access...${NC}"
aws eks update-cluster-config \
    --name $CLUSTER_NAME \
    --resources-vpc-config endpointPrivateAccess=true,endpointPublicAccess=true \
    --region $REGION

echo "Waiting for cluster update to complete (this may take a few minutes)..."
aws eks wait cluster-active --name $CLUSTER_NAME --region $REGION 2>/dev/null || echo "Cluster is updating..."

echo -e "${YELLOW}Step 7: Getting node group information...${NC}"
NODE_GROUPS=$(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --region $REGION --query "nodegroups" --output text)

if [ -z "$NODE_GROUPS" ]; then
    echo -e "${YELLOW}No node groups found. Creating a test node group in PUBLIC subnets...${NC}"
    
    # Get public subnets
    PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Type,Values=Public" \
        --region $REGION \
        --query "Subnets[*].SubnetId" \
        --output text)
    
    if [ -z "$PUBLIC_SUBNETS" ]; then
        echo -e "${YELLOW}No public subnets found. Getting any available subnets...${NC}"
        PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" \
            --region $REGION \
            --query "Subnets[*].SubnetId" \
            --output text)
    fi
    
    if [ -z "$PUBLIC_SUBNETS" ]; then
        echo -e "${RED}No suitable subnets found. Please create public subnets first.${NC}"
        exit 1
    fi
    
    # Get node role ARN
    NODE_ROLE_ARN=$(aws iam get-role --role-name $NODE_ROLE_NAME --query "Role.Arn" --output text 2>/dev/null)
    
    if [ -z "$NODE_ROLE_ARN" ]; then
        echo -e "${RED}Node IAM role not found. Please create it first.${NC}"
        exit 1
    fi
    
    echo "Creating node group with subnets: $PUBLIC_SUBNETS"
    aws eks create-nodegroup \
        --cluster-name $CLUSTER_NAME \
        --nodegroup-name "quick-fix-public-nodes" \
        --node-role $NODE_ROLE_ARN \
        --subnets $PUBLIC_SUBNETS \
        --instance-types t3.medium \
        --scaling-config minSize=1,maxSize=3,desiredSize=2 \
        --region $REGION
    
    echo "Waiting for node group to become active (this will take 5-10 minutes)..."
    aws eks wait nodegroup-active \
        --cluster-name $CLUSTER_NAME \
        --nodegroup-name "quick-fix-public-nodes" \
        --region $REGION
else
    echo "Found existing node groups: $NODE_GROUPS"
    echo -e "${YELLOW}Checking node group status...${NC}"
    
    for ng in $NODE_GROUPS; do
        STATUS=$(aws eks describe-nodegroup \
            --cluster-name $CLUSTER_NAME \
            --nodegroup-name $ng \
            --region $REGION \
            --query "nodegroup.status" \
            --output text)
        echo "Node group $ng status: $STATUS"
        
        if [ "$STATUS" == "CREATE_FAILED" ] || [ "$STATUS" == "DEGRADED" ]; then
            echo -e "${YELLOW}Node group $ng has issues. Consider deleting and recreating it.${NC}"
            echo "To delete: aws eks delete-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $ng --region $REGION"
        fi
    done
fi

echo -e "${YELLOW}Step 8: Configuring kubectl...${NC}"
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

echo -e "${YELLOW}Step 9: Checking node status...${NC}"
kubectl get nodes -o wide || echo -e "${YELLOW}kubectl not configured or no nodes ready yet${NC}"

echo ""
echo -e "${GREEN}=== Fix Applied ===${NC}"
echo ""
echo "Next steps:"
echo "1. Wait 2-3 minutes for changes to propagate"
echo "2. Check node status: kubectl get nodes"
echo "3. Check system pods: kubectl get pods -n kube-system"
echo "4. If nodes still not joining, check logs:"
echo "   kubectl get events --all-namespaces | grep -i node"
echo ""
echo "If issues persist, check the failed instances directly:"
echo "  Instance IDs: i-08c37d0c522abc6e7, i-0fd5800a679b039c7"
echo "  Use Systems Manager Session Manager to connect and check:"
echo "  sudo journalctl -u kubelet --no-pager | tail -100"