# Complete LegalLLM Professional Deployment Script
# This script will deploy your application to the working EKS cluster

Write-Host "=== LegalLLM Professional - Complete Deployment Script ===" -ForegroundColor Green
Write-Host "This will deploy your application to your working EKS cluster" -ForegroundColor Cyan
Write-Host ""

# Configuration
$REGION = "ap-southeast-2"
$ACCOUNT_ID = "535319026444"
$CLUSTER_NAME = "legalllm-working"
$APP_NAME = "legalllm-app"
$ECR_REPO = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME"

# Step 1: Create ECR Repository
Write-Host "Step 1: Creating ECR Repository..." -ForegroundColor Yellow
$ecrExists = aws ecr describe-repositories --repository-names $APP_NAME --region $REGION 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating new ECR repository..."
    aws ecr create-repository `
        --repository-name $APP_NAME `
        --region $REGION `
        --image-scanning-configuration scanOnPush=true `
        --encryption-configuration encryptionType=AES256
    Write-Host "ECR repository created!" -ForegroundColor Green
} else {
    Write-Host "ECR repository already exists" -ForegroundColor Yellow
}

# Step 2: Docker Login to ECR
Write-Host "`nStep 2: Logging into ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully logged into ECR!" -ForegroundColor Green
} else {
    Write-Host "Failed to login to ECR. Please check Docker is running." -ForegroundColor Red
    exit 1
}

# Step 3: Build Docker Image
Write-Host "`nStep 3: Building Docker Image..." -ForegroundColor Yellow
Write-Host "Looking for Dockerfile..."

# Check for different Dockerfile locations
$dockerfilePath = ""
if (Test-Path ".\Dockerfile") {
    $dockerfilePath = "."
    Write-Host "Found Dockerfile in current directory"
} elseif (Test-Path "..\Dockerfile") {
    $dockerfilePath = ".."
    Write-Host "Found Dockerfile in parent directory"
} elseif (Test-Path "..\docker-deployment\Dockerfile") {
    $dockerfilePath = ".."
    $dockerfileFlag = "-f docker-deployment/Dockerfile"
    Write-Host "Found Dockerfile in docker-deployment directory"
} else {
    Write-Host "No Dockerfile found. Creating a basic one..." -ForegroundColor Yellow
    # We'll create this file next
    $dockerfilePath = ".."
    $dockerfileFlag = "-f aws-deployment/Dockerfile"
}

# Build the image
Write-Host "Building Docker image (this may take 5-10 minutes)..."
if ($dockerfileFlag) {
    docker build $dockerfileFlag -t ${APP_NAME}:latest $dockerfilePath
} else {
    docker build -t ${APP_NAME}:latest $dockerfilePath
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed. Please check the error messages above." -ForegroundColor Red
    exit 1
}

Write-Host "Docker image built successfully!" -ForegroundColor Green

# Step 4: Tag and Push Image
Write-Host "`nStep 4: Pushing image to ECR..." -ForegroundColor Yellow
docker tag ${APP_NAME}:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "Image pushed to ECR successfully!" -ForegroundColor Green
} else {
    Write-Host "Failed to push image to ECR" -ForegroundColor Red
    exit 1
}

# Step 5: Get Database and Redis Information
Write-Host "`nStep 5: Gathering resource information..." -ForegroundColor Yellow

# Get RDS endpoint
$RDS_ENDPOINT = aws rds describe-db-instances `
    --region $REGION `
    --query "DBInstances[?DBName=='legalllm'].Endpoint.Address" `
    --output text

if ([string]::IsNullOrEmpty($RDS_ENDPOINT)) {
    Write-Host "Warning: No RDS database found. You may need to create one." -ForegroundColor Yellow
    $RDS_ENDPOINT = "your-rds-endpoint-here"
}

Write-Host "RDS Endpoint: $RDS_ENDPOINT"

# Get Redis endpoint
$REDIS_ENDPOINT = aws elasticache describe-cache-clusters `
    --region $REGION `
    --show-cache-node-info `
    --query "CacheClusters[?contains(CacheClusterId, 'legalllm')].CacheNodes[0].Endpoint.Address" `
    --output text

if ([string]::IsNullOrEmpty($REDIS_ENDPOINT)) {
    Write-Host "Warning: No Redis cluster found. You may need to create one." -ForegroundColor Yellow
    $REDIS_ENDPOINT = "your-redis-endpoint-here"
}

Write-Host "Redis Endpoint: $REDIS_ENDPOINT"

# Step 6: Create Kubernetes namespace
Write-Host "`nStep 6: Creating Kubernetes namespace..." -ForegroundColor Yellow
kubectl create namespace legalllm 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Namespace 'legalllm' created" -ForegroundColor Green
} else {
    Write-Host "Namespace 'legalllm' already exists or creation failed" -ForegroundColor Yellow
}

# Step 7: Apply Kubernetes configurations
Write-Host "`nStep 7: Deploying application to Kubernetes..." -ForegroundColor Yellow
Write-Host "Applying configuration files..."

# Apply ConfigMap
if (Test-Path ".\k8s-configmap.yaml") {
    kubectl apply -f k8s-configmap.yaml -n legalllm
}

# Apply Secret
if (Test-Path ".\k8s-secret.yaml") {
    kubectl apply -f k8s-secret.yaml -n legalllm
}

# Apply Deployment
if (Test-Path ".\k8s-deployment.yaml") {
    kubectl apply -f k8s-deployment.yaml -n legalllm
}

# Apply Service
if (Test-Path ".\k8s-service.yaml") {
    kubectl apply -f k8s-service.yaml -n legalllm
}

# Apply Ingress
if (Test-Path ".\k8s-ingress.yaml") {
    kubectl apply -f k8s-ingress.yaml -n legalllm
}

# Step 8: Wait for deployment
Write-Host "`nStep 8: Waiting for deployment to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=available --timeout=300s deployment/legalllm-app -n legalllm 2>$null

# Step 9: Check deployment status
Write-Host "`nStep 9: Checking deployment status..." -ForegroundColor Yellow
kubectl get all -n legalllm

# Step 10: Get Load Balancer URL
Write-Host "`nStep 10: Getting application URL..." -ForegroundColor Yellow
$LB_URL = kubectl get service legalllm-service -n legalllm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>$null

if ([string]::IsNullOrEmpty($LB_URL)) {
    Write-Host "Load balancer is still being created. This can take 2-5 minutes." -ForegroundColor Yellow
    Write-Host "Run this command to check: kubectl get service legalllm-service -n legalllm" -ForegroundColor Cyan
} else {
    Write-Host "`n=== DEPLOYMENT COMPLETE ===" -ForegroundColor Green
    Write-Host "Your application is available at: http://$LB_URL" -ForegroundColor Green
}

Write-Host "`nUseful commands:" -ForegroundColor Cyan
Write-Host "  View pods:        kubectl get pods -n legalllm" -ForegroundColor White
Write-Host "  View logs:        kubectl logs -n legalllm deployment/legalllm-app" -ForegroundColor White
Write-Host "  Get URL:          kubectl get service legalllm-service -n legalllm" -ForegroundColor White
Write-Host "  Scale deployment: kubectl scale deployment legalllm-app --replicas=3 -n legalllm" -ForegroundColor White

Write-Host "`nDeployment script complete!" -ForegroundColor Green