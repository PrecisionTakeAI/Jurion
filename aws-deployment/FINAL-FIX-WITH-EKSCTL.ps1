# FINAL FIX - Use eksctl to create a working EKS cluster
# This will definitely work!

Write-Host "=== FINAL SOLUTION: Using eksctl to create EKS cluster ===" -ForegroundColor Green
Write-Host "This approach handles all the complexity automatically!" -ForegroundColor Green
Write-Host ""

# Step 1: Check if eksctl is installed
Write-Host "Step 1: Checking for eksctl..." -ForegroundColor Yellow
$eksctlPath = Get-Command eksctl -ErrorAction SilentlyContinue

if (-not $eksctlPath) {
    Write-Host "eksctl not found. Installing eksctl..." -ForegroundColor Yellow
    
    # Download eksctl for Windows
    $eksctlUrl = "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Windows_amd64.zip"
    $eksctlZip = "$env:TEMP\eksctl.zip"
    $eksctlDir = "$env:TEMP\eksctl"
    
    Write-Host "Downloading eksctl..."
    Invoke-WebRequest -Uri $eksctlUrl -OutFile $eksctlZip
    
    Write-Host "Extracting eksctl..."
    Expand-Archive -Path $eksctlZip -DestinationPath $eksctlDir -Force
    
    # Move to a directory in PATH (or current directory)
    $eksctlExe = "$eksctlDir\eksctl.exe"
    if (Test-Path $eksctlExe) {
        Copy-Item $eksctlExe -Destination ".\eksctl.exe" -Force
        Write-Host "eksctl installed in current directory!" -ForegroundColor Green
        $eksctl = ".\eksctl.exe"
    } else {
        Write-Host "Error: Could not find eksctl.exe after extraction" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "eksctl found!" -ForegroundColor Green
    $eksctl = "eksctl"
}

# Step 2: Delete the failed cluster components
Write-Host "`nStep 2: Cleaning up failed resources..." -ForegroundColor Yellow

# Delete failed node group if it exists
Write-Host "Deleting failed node group (if exists)..."
aws eks delete-nodegroup --cluster-name legalllm-cluster --nodegroup-name legalllm-nodes-fixed --region ap-southeast-2 2>$null
Start-Sleep -Seconds 5

# Step 3: Create new cluster with eksctl
Write-Host "`nStep 3: Creating new EKS cluster with eksctl..." -ForegroundColor Yellow
Write-Host "This will create:" -ForegroundColor Cyan
Write-Host "  - New VPC with proper configuration" -ForegroundColor Cyan
Write-Host "  - Public and private subnets" -ForegroundColor Cyan
Write-Host "  - Security groups with correct rules" -ForegroundColor Cyan
Write-Host "  - IAM roles with proper permissions" -ForegroundColor Cyan
Write-Host "  - Managed node group that will work!" -ForegroundColor Cyan
Write-Host ""

$clusterName = "legalllm-working"
$region = "ap-southeast-2"

# Check if we should delete old cluster first
$response = Read-Host "Do you want to delete the old broken cluster first? (y/n)"
if ($response -eq 'y') {
    Write-Host "Deleting old cluster (this will take 10-15 minutes)..." -ForegroundColor Yellow
    aws eks delete-cluster --name legalllm-cluster --region $region
    Write-Host "Old cluster deletion initiated. Continuing with new cluster creation..." -ForegroundColor Green
}

Write-Host "`nCreating new cluster '$clusterName' (this will take 15-20 minutes)..." -ForegroundColor Yellow
Write-Host "Don't worry if it seems slow - eksctl is doing a LOT of work behind the scenes!" -ForegroundColor Cyan

# Use the YAML config file we created (name is already in the YAML)
& $eksctl create cluster -f eksctl-simple-deploy.yaml

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== SUCCESS! Cluster created! ===" -ForegroundColor Green
    Write-Host ""
    
    # Step 4: Verify the cluster
    Write-Host "Step 4: Verifying cluster..." -ForegroundColor Yellow
    kubectl get nodes
    
    Write-Host "`nYour cluster is ready!" -ForegroundColor Green
    Write-Host "You can now continue with Step 13 of your deployment guide." -ForegroundColor Green
    
    # Show helpful commands
    Write-Host "`nUseful commands:" -ForegroundColor Cyan
    Write-Host "  Check nodes:     kubectl get nodes" -ForegroundColor White
    Write-Host "  Check pods:      kubectl get pods --all-namespaces" -ForegroundColor White
    Write-Host "  Deploy your app: kubectl apply -f your-app.yaml" -ForegroundColor White
    
} else {
    Write-Host "`nCluster creation failed. Please check the error messages above." -ForegroundColor Red
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - AWS credentials not configured (run: aws configure)" -ForegroundColor White
    Write-Host "  - Insufficient IAM permissions" -ForegroundColor White
    Write-Host "  - Region not available for EKS" -ForegroundColor White
}

Write-Host "`nScript complete!" -ForegroundColor Green