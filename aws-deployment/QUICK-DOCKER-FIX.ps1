# Quick Docker Fix and Deployment Script
Write-Host "=== Docker Fix and Deployment Script ===" -ForegroundColor Green
Write-Host ""

# Step 1: Check Docker Desktop
Write-Host "Step 1: Checking Docker Desktop..." -ForegroundColor Yellow

$dockerRunning = $false
try {
    docker version > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerRunning = $true
    }
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-Host "Docker Desktop is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "PLEASE DO THE FOLLOWING:" -ForegroundColor Yellow
    Write-Host "1. Open Docker Desktop from your Start Menu or Desktop" -ForegroundColor Cyan
    Write-Host "2. Wait for Docker Desktop to show 'Docker Desktop is running'" -ForegroundColor Cyan
    Write-Host "3. Then run this script again" -ForegroundColor Cyan
    Write-Host ""
    
    # Try to start Docker Desktop
    Write-Host "Attempting to start Docker Desktop..." -ForegroundColor Yellow
    $dockerDesktopPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    
    if (Test-Path $dockerDesktopPath) {
        Start-Process "$dockerDesktopPath"
        Write-Host "Docker Desktop is starting. Please wait 30-60 seconds..." -ForegroundColor Yellow
        Write-Host "Look for the Docker icon in your system tray (bottom right)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Once Docker is running (whale icon is steady), press Enter to continue..." -ForegroundColor Green
        Read-Host
    } else {
        Write-Host "Could not find Docker Desktop. Please start it manually." -ForegroundColor Red
        Write-Host "After starting Docker Desktop, run this script again." -ForegroundColor Yellow
        exit 1
    }
}

# Test Docker again
Write-Host "Testing Docker connection..." -ForegroundColor Yellow
docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is still not responding. Please ensure Docker Desktop is fully started." -ForegroundColor Red
    Write-Host "The Docker whale icon in your system tray should be steady (not animated)." -ForegroundColor Yellow
    exit 1
}

Write-Host "Docker is running!" -ForegroundColor Green

# Step 2: Login to ECR
Write-Host "`nStep 2: Logging into Amazon ECR..." -ForegroundColor Yellow
$REGION = "ap-southeast-2"
$ACCOUNT_ID = "535319026444"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to login to ECR" -ForegroundColor Red
    exit 1
}

Write-Host "Successfully logged into ECR!" -ForegroundColor Green

# Step 3: Build Docker Image
Write-Host "`nStep 3: Building Docker image..." -ForegroundColor Yellow
Write-Host "This will take 5-10 minutes. You'll see progress below:" -ForegroundColor Cyan

# Change to parent directory where Dockerfile is
cd ..

# Build the image
docker build -t legalllm-app:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Missing requirements.txt" -ForegroundColor White
    Write-Host "  - Missing start_railway.sh" -ForegroundColor White
    Write-Host "  - Syntax errors in Dockerfile" -ForegroundColor White
    exit 1
}

Write-Host "Docker image built successfully!" -ForegroundColor Green

# Step 4: Tag and Push
Write-Host "`nStep 4: Pushing image to ECR..." -ForegroundColor Yellow
$ECR_REPO = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/legalllm-app"

docker tag legalllm-app:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "Image pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "Failed to push image" -ForegroundColor Red
    exit 1
}

# Step 5: Deploy to Kubernetes
Write-Host "`nStep 5: Deploying to Kubernetes..." -ForegroundColor Yellow

cd aws-deployment

# Create namespace
kubectl create namespace legalllm 2>$null

# Apply configurations
kubectl apply -f k8s-configmap.yaml
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-service.yaml

# Check deployment
Write-Host "`nChecking deployment status..." -ForegroundColor Yellow
kubectl get pods -n legalllm

Write-Host "`nWaiting for pods to be ready (this takes 2-3 minutes)..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=legalllm -n legalllm --timeout=300s

# Get Load Balancer URL
Write-Host "`nGetting application URL..." -ForegroundColor Yellow
$LB_URL = kubectl get service legalllm-service -n legalllm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

if ([string]::IsNullOrEmpty($LB_URL)) {
    Write-Host "Load balancer is being created. Check in 2-3 minutes with:" -ForegroundColor Yellow
    Write-Host "  kubectl get service legalllm-service -n legalllm" -ForegroundColor Cyan
} else {
    Write-Host "`n=== DEPLOYMENT SUCCESSFUL! ===" -ForegroundColor Green
    Write-Host "Your application is available at:" -ForegroundColor Green
    Write-Host "  http://$LB_URL" -ForegroundColor Cyan
}

Write-Host "`nDeployment complete!" -ForegroundColor Green