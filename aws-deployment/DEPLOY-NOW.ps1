# MASTER DEPLOYMENT SCRIPT FOR LEGALLLM PROFESSIONAL
# This script will deploy your entire application

Write-Host @"
================================================================================
     _                    _ _    _     __  __   ____             
    | |    ___  __ _  __ | | |  | |   |  \/  | |  _ \ _ __ ___  
    | |   / _ \/ _` |/ _` | |  | |   | |\/| | | |_) | '__/ _ \ 
    | |__|  __/ (_| | (_| | |  | |___| |  | | |  __/| | | (_) |
    |_____\___|\__, |\__,_|_|  |_____|_|  |_| |_|   |_|  \___/ 
               |___/                                            
    
    COMPLETE AWS DEPLOYMENT SCRIPT
================================================================================
"@ -ForegroundColor Cyan

Write-Host "`nThis script will:" -ForegroundColor Yellow
Write-Host "  1. Create your Kubernetes secrets" -ForegroundColor White
Write-Host "  2. Build and push your Docker image" -ForegroundColor White
Write-Host "  3. Deploy your application to EKS" -ForegroundColor White
Write-Host "  4. Set up load balancer and monitoring" -ForegroundColor White
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check kubectl
$kubectl = Get-Command kubectl -ErrorAction SilentlyContinue
if (-not $kubectl) {
    Write-Host "ERROR: kubectl not found. Please install it first." -ForegroundColor Red
    exit 1
}

# Check docker
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "ERROR: Docker not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check AWS CLI
$aws = Get-Command aws -ErrorAction SilentlyContinue
if (-not $aws) {
    Write-Host "ERROR: AWS CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

Write-Host "All prerequisites found!" -ForegroundColor Green

# Configuration
$REGION = "ap-southeast-2"
$ACCOUNT_ID = "535319026444"
$CLUSTER_NAME = "legalllm-working"

# Verify cluster connection
Write-Host "`nVerifying EKS cluster connection..." -ForegroundColor Yellow
kubectl get nodes > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cannot connect to EKS cluster. Updating kubeconfig..." -ForegroundColor Yellow
    aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION
}

kubectl get nodes
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cannot connect to EKS cluster" -ForegroundColor Red
    exit 1
}

Write-Host "Connected to EKS cluster!" -ForegroundColor Green

# STEP 1: Create Secrets
Write-Host "`n" -NoNewline
Write-Host "================================================================================`n" -ForegroundColor Cyan
Write-Host "STEP 1: CREATING KUBERNETES SECRETS" -ForegroundColor Yellow
Write-Host "================================================================================`n" -ForegroundColor Cyan

Write-Host "I need your passwords to create secure Kubernetes secrets." -ForegroundColor Yellow
Write-Host "These will be encrypted and stored securely in Kubernetes.`n" -ForegroundColor White

# Get passwords from .env.production if they exist
$envFile = "..\env.production"
$dbPassword = ""
$redisPassword = ""
$openaiKey = ""

if (Test-Path $envFile) {
    Write-Host "Reading from .env.production file..." -ForegroundColor Green
    $envContent = Get-Content $envFile
    foreach ($line in $envContent) {
        if ($line -match "^DB_PASSWORD=(.+)$") {
            $dbPassword = $matches[1]
        }
        if ($line -match "^REDIS_PASSWORD=(.+)$") {
            $redisPassword = $matches[1]
        }
        if ($line -match "^OPENAI_API_KEY=(.+)$") {
            $openaiKey = $matches[1]
        }
    }
}

# Get RDS password
if ($dbPassword) {
    Write-Host "Found RDS password in .env.production" -ForegroundColor Green
} else {
    $dbPasswordSecure = Read-Host "Enter your RDS Database Password" -AsSecureString
    $dbPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPasswordSecure))
}

# Get Redis password
if ($redisPassword) {
    Write-Host "Found Redis password in .env.production" -ForegroundColor Green
} else {
    $redisPasswordSecure = Read-Host "Enter your Redis Password" -AsSecureString
    $redisPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($redisPasswordSecure))
}

# Get OpenAI key
if ($openaiKey) {
    Write-Host "Found OpenAI API key in .env.production" -ForegroundColor Green
} else {
    $openaiKeySecure = Read-Host "Enter your OpenAI API Key" -AsSecureString
    $openaiKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($openaiKeySecure))
}

# Run the secret creation script
Write-Host "`nCreating Kubernetes secrets..." -ForegroundColor Yellow
& .\CREATE-K8S-SECRET.ps1

# STEP 2: Build and Deploy
Write-Host "`n" -NoNewline
Write-Host "================================================================================`n" -ForegroundColor Cyan
Write-Host "STEP 2: BUILDING AND DEPLOYING APPLICATION" -ForegroundColor Yellow
Write-Host "================================================================================`n" -ForegroundColor Cyan

# Run the complete deployment script
& .\COMPLETE-DEPLOYMENT.ps1

# STEP 3: Verify Deployment
Write-Host "`n" -NoNewline
Write-Host "================================================================================`n" -ForegroundColor Cyan
Write-Host "STEP 3: VERIFYING DEPLOYMENT" -ForegroundColor Yellow
Write-Host "================================================================================`n" -ForegroundColor Cyan

Write-Host "Checking deployment status..." -ForegroundColor Yellow
kubectl get all -n legalllm

# Wait for load balancer
Write-Host "`nWaiting for load balancer (this can take 2-5 minutes)..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $LB_URL = kubectl get service legalllm-service -n legalllm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>$null
    
    if (-not [string]::IsNullOrEmpty($LB_URL)) {
        Write-Host "`n" -NoNewline
        Write-Host "================================================================================`n" -ForegroundColor Green
        Write-Host "🎉 DEPLOYMENT SUCCESSFUL! 🎉" -ForegroundColor Green
        Write-Host "================================================================================`n" -ForegroundColor Green
        
        Write-Host "Your LegalLLM Professional application is now live!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Access your application at:" -ForegroundColor Yellow
        Write-Host "  http://$LB_URL" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "It may take 2-3 minutes for the application to be fully accessible." -ForegroundColor Yellow
        Write-Host ""
        
        Write-Host "NEXT STEPS:" -ForegroundColor Yellow
        Write-Host "  1. Open the URL in your browser" -ForegroundColor White
        Write-Host "  2. Create your admin account" -ForegroundColor White
        Write-Host "  3. Configure your law firm settings" -ForegroundColor White
        Write-Host "  4. Start using LegalLLM Professional!" -ForegroundColor White
        
        break
    }
    
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 10
    $attempt++
}

if ($attempt -eq $maxAttempts) {
    Write-Host "`nLoad balancer is taking longer than expected." -ForegroundColor Yellow
    Write-Host "Run this command to check status:" -ForegroundColor White
    Write-Host "  kubectl get service legalllm-service -n legalllm" -ForegroundColor Cyan
}

Write-Host "`n" -NoNewline
Write-Host "================================================================================`n" -ForegroundColor Cyan
Write-Host "USEFUL COMMANDS FOR MANAGEMENT:" -ForegroundColor Yellow
Write-Host "================================================================================`n" -ForegroundColor Cyan

Write-Host "View application logs:" -ForegroundColor White
Write-Host "  kubectl logs -n legalllm deployment/legalllm-app --follow" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check pod status:" -ForegroundColor White
Write-Host "  kubectl get pods -n legalllm" -ForegroundColor Cyan
Write-Host ""
Write-Host "Scale application:" -ForegroundColor White
Write-Host "  kubectl scale deployment legalllm-app --replicas=3 -n legalllm" -ForegroundColor Cyan
Write-Host ""
Write-Host "Update application:" -ForegroundColor White
Write-Host "  kubectl rollout restart deployment/legalllm-app -n legalllm" -ForegroundColor Cyan
Write-Host ""

Write-Host "Deployment complete!" -ForegroundColor Green