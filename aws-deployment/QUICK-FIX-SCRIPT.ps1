# IMMEDIATE FIX SCRIPT FOR EKS NODE JOIN ISSUES - PowerShell Version
# Run this script in PowerShell to quickly fix your node join problems

Write-Host "=== EKS Node Join Quick Fix Script (PowerShell) ===" -ForegroundColor Yellow
Write-Host "This script will fix your node join issues step by step" -ForegroundColor Yellow
Write-Host ""

# Configuration
$CLUSTER_NAME = "legalllm-cluster"
$REGION = "ap-southeast-2"
$NODE_ROLE_NAME = "legalllm-eks-node-role"

# Step 1: Check cluster status
Write-Host "Step 1: Checking cluster status..." -ForegroundColor Yellow
try {
    $clusterStatus = aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.status" --output text
    if ($LASTEXITCODE -ne 0) {
        throw "Cluster not found"
    }
    Write-Host "Cluster found! Status: $clusterStatus" -ForegroundColor Green
} catch {
    Write-Host "Error: Cluster not found or AWS CLI not configured" -ForegroundColor Red
    Write-Host "Please ensure AWS CLI is configured with: aws configure" -ForegroundColor Red
    exit 1
}

# Step 2: Get VPC and Security Group IDs
Write-Host "`nStep 2: Getting VPC and Security Group IDs..." -ForegroundColor Yellow
$VPC_ID = aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.resourcesVpcConfig.vpcId" --output text
$CLUSTER_SG = aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.resourcesVpcConfig.clusterSecurityGroupId" --output text

Write-Host "VPC ID: $VPC_ID"
Write-Host "Cluster Security Group: $CLUSTER_SG"

# Step 3: Find node security group
Write-Host "`nStep 3: Finding node security group..." -ForegroundColor Yellow
$NODE_SG = aws ec2 describe-security-groups --region $REGION --filters "Name=tag:Name,Values=legalllm-eks-nodes-sg" --query "SecurityGroups[0].GroupId" --output text 2>$null

if ($NODE_SG -eq "None" -or $NODE_SG -eq $null -or $NODE_SG -eq "") {
    Write-Host "Node security group not found by tag, searching by VPC..." -ForegroundColor Yellow
    $NODE_SG = aws ec2 describe-security-groups --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=*node*" --query "SecurityGroups[0].GroupId" --output text 2>$null
}

if ($NODE_SG -eq "None" -or $NODE_SG -eq $null -or $NODE_SG -eq "") {
    Write-Host "Could not find node security group. Creating one..." -ForegroundColor Red
    $NODE_SG = aws ec2 create-security-group `
        --group-name "legalllm-eks-nodes-sg-fixed" `
        --description "Fixed security group for EKS nodes" `
        --vpc-id $VPC_ID `
        --region $REGION `
        --query "GroupId" `
        --output text
    Write-Host "Created new node security group: $NODE_SG" -ForegroundColor Green
}

Write-Host "Node Security Group: $NODE_SG"

# Step 4: Fix Security Group Rules
Write-Host "`nStep 4: Fixing Security Group Rules..." -ForegroundColor Yellow

function Add-SecurityGroupRule {
    param(
        [string]$GroupId,
        [string]$Protocol,
        [int]$FromPort,
        [int]$ToPort,
        [string]$Source,
        [string]$Description
    )
    
    Write-Host "  Adding rule: $Description"
    
    if ($Source -eq "self") {
        aws ec2 authorize-security-group-ingress `
            --group-id $GroupId `
            --protocol $Protocol `
            --port "$FromPort-$ToPort" `
            --source-group $GroupId `
            --region $REGION 2>$null
    } elseif ($Source -like "sg-*") {
        aws ec2 authorize-security-group-ingress `
            --group-id $GroupId `
            --protocol $Protocol `
            --port "$FromPort-$ToPort" `
            --source-group $Source `
            --region $REGION 2>$null
    } else {
        aws ec2 authorize-security-group-ingress `
            --group-id $GroupId `
            --protocol $Protocol `
            --port "$FromPort-$ToPort" `
            --cidr $Source `
            --region $REGION 2>$null
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    Rule may already exist (this is OK)" -ForegroundColor Gray
    }
}

# Fix cluster security group
Write-Host "Fixing cluster security group rules..."
Add-SecurityGroupRule -GroupId $CLUSTER_SG -Protocol "tcp" -FromPort 443 -ToPort 443 -Source $NODE_SG -Description "Allow nodes to communicate with cluster API"
Add-SecurityGroupRule -GroupId $CLUSTER_SG -Protocol "tcp" -FromPort 10250 -ToPort 10250 -Source $NODE_SG -Description "Allow kubelet API from nodes"

# Fix node security group
Write-Host "Fixing node security group rules..."
Add-SecurityGroupRule -GroupId $NODE_SG -Protocol "tcp" -FromPort 443 -ToPort 443 -Source $CLUSTER_SG -Description "Allow cluster API to nodes"
Add-SecurityGroupRule -GroupId $NODE_SG -Protocol "tcp" -FromPort 10250 -ToPort 10250 -Source $CLUSTER_SG -Description "Allow cluster to kubelet"
Add-SecurityGroupRule -GroupId $NODE_SG -Protocol "-1" -FromPort 0 -ToPort 65535 -Source "self" -Description "Allow node to node communication"
Add-SecurityGroupRule -GroupId $NODE_SG -Protocol "tcp" -FromPort 53 -ToPort 53 -Source "10.0.0.0/16" -Description "Allow DNS TCP"
Add-SecurityGroupRule -GroupId $NODE_SG -Protocol "udp" -FromPort 53 -ToPort 53 -Source "10.0.0.0/16" -Description "Allow DNS UDP"

# Step 5: Ensure VPC DNS is enabled
Write-Host "`nStep 5: Ensuring VPC DNS is enabled..." -ForegroundColor Yellow
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames --region $REGION
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support --region $REGION
Write-Host "VPC DNS settings updated" -ForegroundColor Green

# Step 6: Update EKS endpoint access
Write-Host "`nStep 6: Updating EKS endpoint access..." -ForegroundColor Yellow
aws eks update-cluster-config `
    --name $CLUSTER_NAME `
    --resources-vpc-config endpointPrivateAccess=true,endpointPublicAccess=true `
    --region $REGION

Write-Host "Waiting for cluster update to complete (this may take a few minutes)..."
Start-Sleep -Seconds 10

# Step 7: Check node groups
Write-Host "`nStep 7: Getting node group information..." -ForegroundColor Yellow
$NODE_GROUPS = aws eks list-nodegroups --cluster-name $CLUSTER_NAME --region $REGION --query "nodegroups" --output text

if ([string]::IsNullOrEmpty($NODE_GROUPS)) {
    Write-Host "No node groups found. Creating a test node group in PUBLIC subnets..." -ForegroundColor Yellow
    
    # Get public subnets
    $PUBLIC_SUBNETS = aws ec2 describe-subnets `
        --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" `
        --region $REGION `
        --query "Subnets[*].SubnetId" `
        --output text
    
    if ([string]::IsNullOrEmpty($PUBLIC_SUBNETS)) {
        Write-Host "No public subnets found. Please create public subnets first." -ForegroundColor Red
        exit 1
    }
    
    # Get node role ARN
    $NODE_ROLE_ARN = aws iam get-role --role-name $NODE_ROLE_NAME --query "Role.Arn" --output text 2>$null
    
    if ([string]::IsNullOrEmpty($NODE_ROLE_ARN)) {
        Write-Host "Node IAM role not found. Please create it first." -ForegroundColor Red
        exit 1
    }
    
    $subnet_array = $PUBLIC_SUBNETS -split '\s+'
    Write-Host "Creating node group with subnets: $PUBLIC_SUBNETS"
    
    aws eks create-nodegroup `
        --cluster-name $CLUSTER_NAME `
        --nodegroup-name "quick-fix-public-nodes" `
        --node-role $NODE_ROLE_ARN `
        --subnets $subnet_array `
        --instance-types t3.medium `
        --scaling-config minSize=1,maxSize=3,desiredSize=2 `
        --region $REGION
    
    Write-Host "Node group creation initiated. It will take 5-10 minutes to become active."
} else {
    Write-Host "Found existing node groups: $NODE_GROUPS"
    
    foreach ($ng in $NODE_GROUPS -split '\s+') {
        $STATUS = aws eks describe-nodegroup `
            --cluster-name $CLUSTER_NAME `
            --nodegroup-name $ng `
            --region $REGION `
            --query "nodegroup.status" `
            --output text
        
        Write-Host "Node group ${ng} status: $STATUS"
        
        if ($STATUS -eq "CREATE_FAILED" -or $STATUS -eq "DEGRADED") {
            Write-Host "Node group $ng has issues. Consider deleting and recreating it." -ForegroundColor Yellow
            Write-Host "To delete: aws eks delete-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $ng --region $REGION"
        }
    }
}

# Step 8: Configure kubectl
Write-Host "`nStep 8: Configuring kubectl..." -ForegroundColor Yellow
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

# Step 9: Check node status
Write-Host "`nStep 9: Checking node status..." -ForegroundColor Yellow
kubectl get nodes -o wide
if ($LASTEXITCODE -ne 0) {
    Write-Host "kubectl not configured or no nodes ready yet" -ForegroundColor Yellow
}

Write-Host "`n=== Fix Applied ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Wait 2-3 minutes for changes to propagate"
Write-Host "2. Check node status: kubectl get nodes"
Write-Host "3. Check system pods: kubectl get pods -n kube-system"
Write-Host "4. If nodes still not joining, check logs:"
Write-Host "   kubectl get events --all-namespaces | Select-String -Pattern 'node'"
Write-Host ""
Write-Host "If issues persist, check the failed instances directly:" -ForegroundColor Yellow
Write-Host "  Instance IDs: i-08c37d0c522abc6e7, i-0fd5800a679b039c7"
Write-Host "  Use Systems Manager Session Manager to connect and check:"
Write-Host "  sudo journalctl -u kubelet --no-pager | tail -100"