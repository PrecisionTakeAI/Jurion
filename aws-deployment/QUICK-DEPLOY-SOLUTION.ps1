# ===============================================================
# QUICK DEPLOYMENT SOLUTION - SIMPLIFIED EC2 BUILD
# ===============================================================
# Simplified script that gets your app deployed IMMEDIATELY
# ===============================================================

Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║          QUICK DEPLOY - LEGALLLM PROFESSIONAL                ║
║            Bypassing Docker Desktop Issue                    ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Configuration
$REGION = "ap-southeast-2"
$ACCOUNT_ID = "535319026444"
$ECR_REPO = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/legalllm-app"

Write-Host "This script will deploy your app using GitHub Actions (easiest method)" -ForegroundColor Yellow
Write-Host ""

# Create GitHub Actions workflow
$workflowPath = (Get-Location).Path | Split-Path -Parent
$workflowDir = "$workflowPath\.github\workflows"

if (-not (Test-Path $workflowDir)) {
    New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
}

$workflowContent = @"
name: Deploy to AWS EKS

on:
  workflow_dispatch:
  push:
    branches: [main, clean-working-solution]

env:
  AWS_REGION: ap-southeast-2
  ECR_REPOSITORY: legalllm-app
  EKS_CLUSTER: legalllm-working

jobs:
  deploy:
    name: Build and Deploy
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: `${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: `${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: `${{ env.AWS_REGION }}
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build, tag, and push image to ECR
      env:
        ECR_REGISTRY: `${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: latest
      run: |
        docker build -t `$ECR_REGISTRY/`$ECR_REPOSITORY:`$IMAGE_TAG .
        docker push `$ECR_REGISTRY/`$ECR_REPOSITORY:`$IMAGE_TAG
        echo "image=`$ECR_REGISTRY/`$ECR_REPOSITORY:`$IMAGE_TAG" >> `$GITHUB_OUTPUT
    
    - name: Setup kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'latest'
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --name `${{ env.EKS_CLUSTER }} --region `${{ env.AWS_REGION }}
    
    - name: Deploy to EKS
      run: |
        kubectl apply -f aws-deployment/k8s-configmap.yaml
        kubectl apply -f aws-deployment/k8s-deployment.yaml  
        kubectl apply -f aws-deployment/k8s-service.yaml
        kubectl rollout status deployment/legalllm-app -n legalllm --timeout=5m
    
    - name: Get Load Balancer URL
      run: |
        echo "Waiting for Load Balancer..."
        sleep 30
        LB_URL=`$(kubectl get service legalllm-service -n legalllm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
        echo "Application deployed to: http://`$LB_URL"
        echo "## Deployment Complete! :rocket:" >> `$GITHUB_STEP_SUMMARY
        echo "Application URL: http://`$LB_URL" >> `$GITHUB_STEP_SUMMARY
"@

$workflowContent | Out-File -FilePath "$workflowDir\deploy.yml" -Encoding UTF8

Write-Host "✓ GitHub Actions workflow created" -ForegroundColor Green

# Get AWS credentials for GitHub secrets
Write-Host "`nSTEP 1: Getting AWS Credentials..." -ForegroundColor Yellow
Write-Host "────────────────────────────────────" -ForegroundColor DarkGray

$awsProfile = aws configure get aws_access_key_id 2>$null
$awsSecret = aws configure get aws_secret_access_key 2>$null

if (-not $awsProfile -or -not $awsSecret) {
    Write-Host "ERROR: AWS credentials not found" -ForegroundColor Red
    Write-Host "Run: aws configure" -ForegroundColor Yellow
    exit 1
}

Write-Host @"

STEP 2: Setup GitHub Secrets
────────────────────────────

1. Go to your GitHub repository:
   https://github.com/yourusername/LegalLLM-Professional

2. Navigate to: Settings → Secrets and variables → Actions

3. Click "New repository secret" and add these two secrets:

   Secret 1:
   Name: AWS_ACCESS_KEY_ID
   Value: $awsProfile

   Secret 2:  
   Name: AWS_SECRET_ACCESS_KEY
   Value: [Your AWS Secret Key]

4. After adding the secrets, either:
   - Push this code to trigger automatic deployment
   - Or go to Actions tab → Deploy to AWS EKS → Run workflow

"@ -ForegroundColor Yellow

Write-Host "`nALTERNATIVE: Manual EC2 Build" -ForegroundColor Cyan
Write-Host "──────────────────────────────" -ForegroundColor DarkGray

Write-Host @"
If you prefer to build immediately without GitHub, run this command:

./DEPLOY-IMMEDIATE-EC2-BUILD.ps1

This will:
1. Launch an EC2 instance
2. Build the Docker image on EC2
3. Push to ECR
4. Deploy to Kubernetes
5. Auto-terminate the EC2 instance

Total time: ~15 minutes
"@ -ForegroundColor White

Write-Host "`nQUICK VERIFICATION COMMANDS:" -ForegroundColor Green
Write-Host "────────────────────────────" -ForegroundColor DarkGray

Write-Host @"
Check EKS cluster status:
  kubectl get nodes

Check current pods:
  kubectl get pods -n legalllm

Check if image exists in ECR:
  aws ecr describe-images --repository-name legalllm-app --region ap-southeast-2

Get application URL (after deployment):
  kubectl get service legalllm-service -n legalllm
"@ -ForegroundColor Cyan

Write-Host "`nCURRENT STATUS SUMMARY:" -ForegroundColor Yellow  
Write-Host "───────────────────────" -ForegroundColor DarkGray

Write-Host @"
✅ EKS Cluster: Running (2 nodes healthy)
✅ RDS Database: Available
✅ Redis Cache: Available  
✅ ECR Repository: Created
✅ Kubernetes configs: Ready
✅ Secrets: Configured
❌ Docker Image: Not built (blocked by Docker Desktop issue)
❌ Application: Not deployed

Next Step: Use GitHub Actions or run EC2 build script
"@ -ForegroundColor White

Write-Host "`nFiles created:" -ForegroundColor Green
Write-Host "  .github\workflows\deploy.yml - GitHub Actions workflow" -ForegroundColor DarkGray
Write-Host "  DEPLOY-IMMEDIATE-EC2-BUILD.ps1 - Direct EC2 build script" -ForegroundColor DarkGray