# DEPLOY-IMMEDIATE-EC2-BUILD-FIXED.ps1
# Complete AWS deployment solution that bypasses Docker Desktop issues
# Builds Docker image on EC2 and deploys to EKS

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     LegalLLM Professional - EC2 Build & Deploy Solution      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will:" -ForegroundColor White
Write-Host "  1. Launch a temporary EC2 instance (t3.medium)" -ForegroundColor Gray
Write-Host "  2. Build your Docker image on AWS" -ForegroundColor Gray
Write-Host "  3. Push image to ECR" -ForegroundColor Gray
Write-Host "  4. Deploy to your EKS cluster" -ForegroundColor Gray
Write-Host "  5. Auto-terminate EC2 (cost: ~$0.05)" -ForegroundColor Gray
Write-Host ""

# Get AWS account ID and region
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = "ap-southeast-2"
$ECR_REPO = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/legalllm-app"

Write-Host "AWS Account ID: $ACCOUNT_ID" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host "ECR Repository: $ECR_REPO" -ForegroundColor Yellow
Write-Host ""

# Step 1: Create temporary key pair
Write-Host "STEP 1: Creating temporary key pair..." -ForegroundColor Yellow
Write-Host "──────────────────────────────────────" -ForegroundColor DarkGray

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$KEY_NAME = "legalllm-build-key-$timestamp"
$keyPath = "$env:TEMP\$KEY_NAME.pem"

# Delete key if it exists
aws ec2 delete-key-pair --key-name $KEY_NAME --region $REGION 2>$null

# Create new key pair
$keyMaterial = aws ec2 create-key-pair `
    --key-name $KEY_NAME `
    --region $REGION `
    --query 'KeyMaterial' `
    --output text

$keyMaterial | Out-File -FilePath $keyPath -Encoding ASCII
Write-Host "✓ Key pair created: $KEY_NAME" -ForegroundColor Green
Write-Host "✓ Key saved to: $keyPath" -ForegroundColor Green

# Step 2: Create security group
Write-Host ""
Write-Host "STEP 2: Creating security group..." -ForegroundColor Yellow
Write-Host "──────────────────────────────────────" -ForegroundColor DarkGray

$SG_NAME = "legalllm-build-sg-$timestamp"

# Get VPC ID
$VPC_ID = aws ec2 describe-vpcs `
    --filters "Name=tag:Name,Values=eksctl-legalllm-working-cluster/VPC" `
    --region $REGION `
    --query 'Vpcs[0].VpcId' `
    --output text

if (-not $VPC_ID -or $VPC_ID -eq "None") {
    $VPC_ID = aws ec2 describe-vpcs `
        --filters "Name=isDefault,Values=true" `
        --region $REGION `
        --query 'Vpcs[0].VpcId' `
        --output text
}

Write-Host "Using VPC: $VPC_ID" -ForegroundColor Gray

# Create security group
$SG_ID = aws ec2 create-security-group `
    --group-name $SG_NAME `
    --description "Temporary security group for LegalLLM build" `
    --vpc-id $VPC_ID `
    --region $REGION `
    --query 'GroupId' `
    --output text

# Add SSH rule for your IP
$MY_IP = (Invoke-WebRequest -Uri "http://checkip.amazonaws.com" -UseBasicParsing).Content.Trim()
aws ec2 authorize-security-group-ingress `
    --group-id $SG_ID `
    --protocol tcp `
    --port 22 `
    --cidr "$MY_IP/32" `
    --region $REGION 2>$null

Write-Host "✓ Security group created: $SG_ID" -ForegroundColor Green
Write-Host "✓ SSH access allowed from: $MY_IP" -ForegroundColor Green

# Step 3: Launch EC2 instance
Write-Host ""
Write-Host "STEP 3: Launching EC2 instance..." -ForegroundColor Yellow
Write-Host "──────────────────────────────────────" -ForegroundColor DarkGray

# Get the first public subnet
$SUBNET_ID = aws ec2 describe-subnets `
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" `
    --region $REGION `
    --query 'Subnets[0].SubnetId' `
    --output text

if (-not $SUBNET_ID -or $SUBNET_ID -eq "None") {
    $SUBNET_ID = aws ec2 describe-subnets `
        --filters "Name=vpc-id,Values=$VPC_ID" `
        --region $REGION `
        --query 'Subnets[0].SubnetId' `
        --output text
}

Write-Host "Using subnet: $SUBNET_ID" -ForegroundColor Gray

# User data script for EC2
$userData = @'
#!/bin/bash
exec > /var/log/legalllm-build.log 2>&1
set -x

echo "=== Starting LegalLLM Docker Build ==="
echo "Time: $(date)"

# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install git
yum install git -y

# Configure AWS ECR
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-southeast-2
ECR_REPO=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/legalllm-app

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

# Clone repository or use uploaded files
if [ -f /tmp/legalllm-app.tar.gz ]; then
    echo "Using uploaded application files..."
    cd /tmp
    mkdir -p LegalLLM-Professional
    tar -xzf legalllm-app.tar.gz -C LegalLLM-Professional/
    cd LegalLLM-Professional
else
    echo "Cloning repository..."
    cd /home/ec2-user
    git clone https://github.com/YourUsername/LegalLLM-Professional.git
    cd LegalLLM-Professional
fi

# Build Docker image
echo "Building Docker image..."
docker build -t legalllm-app:latest .

# Tag and push to ECR
docker tag legalllm-app:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest

echo "=== Build Complete! ==="
echo "Image pushed to: ${ECR_REPO}:latest"

# Signal completion
aws sns publish --topic-arn arn:aws:sns:${REGION}:${ACCOUNT_ID}:legalllm-build-complete --message "Docker build complete" 2>/dev/null || true

# Terminate instance after 5 minutes
echo "Instance will terminate in 5 minutes..."
sleep 300
shutdown -h now
'@

$userDataBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($userData))

# Launch instance
$instanceInfo = aws ec2 run-instances `
    --image-id ami-0d147324c76e8210a `
    --instance-type t3.medium `
    --key-name $KEY_NAME `
    --security-group-ids $SG_ID `
    --subnet-id $SUBNET_ID `
    --user-data $userDataBase64 `
    --associate-public-ip-address `
    --block-device-mappings "[{\"DeviceName\":\"/dev/xvda\",\"Ebs\":{\"VolumeSize\":30,\"VolumeType\":\"gp3\"}}]" `
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=legalllm-build-temp},{Key=Purpose,Value=docker-build},{Key=AutoTerminate,Value=true}]" `
    --instance-initiated-shutdown-behavior terminate `
    --region $REGION `
    --output json | ConvertFrom-Json

$INSTANCE_ID = $instanceInfo.Instances[0].InstanceId

Write-Host "✓ Instance launched: $INSTANCE_ID" -ForegroundColor Green
Write-Host "  Instance type: t3.medium" -ForegroundColor Gray
Write-Host "  Storage: 30 GB gp3" -ForegroundColor Gray
Write-Host "  Auto-terminate: Enabled" -ForegroundColor Gray

# Step 4: Wait for instance to be running
Write-Host ""
Write-Host "STEP 4: Waiting for instance to be ready..." -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────" -ForegroundColor DarkGray

aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get public IP
$PUBLIC_IP = aws ec2 describe-instances `
    --instance-ids $INSTANCE_ID `
    --region $REGION `
    --query 'Reservations[0].Instances[0].PublicIpAddress' `
    --output text

Write-Host "✓ Instance is running!" -ForegroundColor Green
Write-Host "✓ Public IP: $PUBLIC_IP" -ForegroundColor Green

# Step 5: Wait for instance to be ready for SSH
Write-Host ""
Write-Host "STEP 5: Waiting for SSH to be ready..." -ForegroundColor Yellow
Write-Host "──────────────────────────────────────" -ForegroundColor DarkGray

Start-Sleep -Seconds 30

Write-Host "✓ Instance should be ready for connections" -ForegroundColor Green

# Step 6: Copy Dockerfile to instance
Write-Host ""
Write-Host "STEP 6: Preparing application files..." -ForegroundColor Yellow
Write-Host "──────────────────────────────────────" -ForegroundColor DarkGray

# Create a tarball of the application
$sourcePath = Split-Path -Parent $PSScriptRoot
$tarPath = "$env:TEMP\legalllm-app.tar.gz"

Write-Host "Creating application archive..." -ForegroundColor Gray
Push-Location $sourcePath
tar -czf $tarPath --exclude=".git" --exclude="node_modules" --exclude="*.pyc" --exclude="__pycache__" .
Pop-Location

Write-Host "✓ Application archive created: $tarPath" -ForegroundColor Green

# Step 7: Upload to EC2
Write-Host ""
Write-Host "STEP 7: Uploading application to EC2..." -ForegroundColor Yellow
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray

# Fix permissions on key file (Windows-specific)
icacls $keyPath /inheritancelevel:r /grant:r "${env:USERNAME}:R"

# Upload via SCP
$scpCommand = "scp -o StrictHostKeyChecking=no -i `"$keyPath`" `"$tarPath`" ec2-user@${PUBLIC_IP}:/tmp/legalllm-app.tar.gz"

Write-Host "Uploading application files to EC2..." -ForegroundColor DarkGray
Write-Host "Command: $scpCommand" -ForegroundColor DarkGray

# Try to upload
$uploadSuccess = $false
for ($i = 0; $i -lt 3; $i++) {
    try {
        Invoke-Expression $scpCommand 2>$null
        if ($LASTEXITCODE -eq 0) {
            $uploadSuccess = $true
            break
        }
    } catch {}
    Write-Host "Retry $($i+1)/3..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 10
}

if ($uploadSuccess) {
    Write-Host "✓ Files uploaded successfully" -ForegroundColor Green
    
    # Extract files on EC2
    $sshCommand = "ssh -o StrictHostKeyChecking=no -i `"$keyPath`" ec2-user@$PUBLIC_IP"
    $extractCommand = "$sshCommand `"cd /tmp && mkdir -p LegalLLM-Professional && tar -xzf legalllm-app.tar.gz -C LegalLLM-Professional && docker build -t legalllm-app:latest LegalLLM-Professional/`""
    
    Write-Host "Extracting and building on EC2..." -ForegroundColor DarkGray
    Invoke-Expression $extractCommand
} else {
    Write-Host "WARNING: Could not upload files via SCP. Build will proceed with git clone." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    BUILD IN PROGRESS                         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "The EC2 instance is now building your Docker image!" -ForegroundColor White
Write-Host ""
Write-Host "Instance ID: $INSTANCE_ID" -ForegroundColor Yellow
Write-Host "Public IP: $PUBLIC_IP" -ForegroundColor Yellow
Write-Host ""
Write-Host "The build process will:" -ForegroundColor White
Write-Host "1. Install Docker and dependencies" -ForegroundColor Gray
Write-Host "2. Clone/upload your application code" -ForegroundColor Gray
Write-Host "3. Build the Docker image" -ForegroundColor Gray
Write-Host "4. Push to ECR: $ECR_REPO`:latest" -ForegroundColor Gray
Write-Host "5. Auto-terminate after completion" -ForegroundColor Gray
Write-Host ""
Write-Host "Estimated time: 10-15 minutes" -ForegroundColor Yellow
Write-Host ""

Write-Host "STEP 9: Monitoring Build Progress..." -ForegroundColor Yellow
Write-Host "──────────────────────────────────────" -ForegroundColor DarkGray

Write-Host "You can monitor the build in several ways:" -ForegroundColor White
Write-Host ""
Write-Host "Option 1: SSH into the instance:" -ForegroundColor Yellow
Write-Host "  ssh -i `"$keyPath`" ec2-user@$PUBLIC_IP" -ForegroundColor Cyan
Write-Host "  tail -f /var/log/legalllm-build.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option 2: Check CloudWatch logs (if configured)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 3: Wait and check ECR for the image:" -ForegroundColor Yellow
Write-Host "  aws ecr describe-images --repository-name legalllm-app --region $REGION" -ForegroundColor Cyan

# Monitor for completion
Write-Host ""
Write-Host "Waiting for build to complete (checking every 30 seconds)..." -ForegroundColor Yellow

$maxWaitMinutes = 20
$waitedMinutes = 0

while ($waitedMinutes -lt $maxWaitMinutes) {
    Start-Sleep -Seconds 30
    $waitedMinutes += 0.5
    
    # Check if image exists in ECR
    $imageExists = aws ecr describe-images `
        --repository-name legalllm-app `
        --region $REGION `
        --query "imageDetails[?imageTags[?contains(@, 'latest')]]" `
        --output json 2>$null | ConvertFrom-Json
    
    if ($imageExists -and $imageExists.Count -gt 0) {
        Write-Host ""
        Write-Host "✓ Docker image successfully pushed to ECR!" -ForegroundColor Green
        break
    }
    
    Write-Host "." -NoNewline
}

if ($waitedMinutes -ge $maxWaitMinutes) {
    Write-Host ""
    Write-Host "Build is taking longer than expected. Please check the EC2 instance logs." -ForegroundColor Yellow
}

# Deploy to Kubernetes
Write-Host ""
Write-Host "STEP 10: Deploying to Kubernetes..." -ForegroundColor Yellow
Write-Host "─────────────────────────────────────" -ForegroundColor DarkGray

# Update kubeconfig
aws eks update-kubeconfig --name legalllm-working --region $REGION

# Apply Kubernetes manifests
kubectl apply -f "$PSScriptRoot\k8s-configmap.yaml"
kubectl apply -f "$PSScriptRoot\k8s-deployment.yaml"
kubectl apply -f "$PSScriptRoot\k8s-service.yaml"

# Wait for deployment
Write-Host "Waiting for pods to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=legalllm -n legalllm --timeout=300s 2>$null

# Get Load Balancer URL
$LB_URL = kubectl get service legalllm-service -n legalllm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>$null

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                   DEPLOYMENT COMPLETE!                       ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

if ($LB_URL) {
    Write-Host "Your application is now available at:" -ForegroundColor Yellow
    Write-Host "http://$LB_URL" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: It may take 2-3 minutes for the DNS to propagate." -ForegroundColor Gray
} else {
    Write-Host "Load Balancer is being provisioned. Check status with:" -ForegroundColor Yellow
    Write-Host "kubectl get service legalllm-service -n legalllm" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "USEFUL COMMANDS:" -ForegroundColor Yellow
Write-Host "────────────────" -ForegroundColor DarkGray
Write-Host "Check pods:        kubectl get pods -n legalllm" -ForegroundColor White
Write-Host "View logs:         kubectl logs -n legalllm deployment/legalllm-app" -ForegroundColor White
Write-Host "Get service URL:   kubectl get service legalllm-service -n legalllm" -ForegroundColor White
Write-Host "Scale deployment:  kubectl scale deployment legalllm-app -n legalllm --replicas=3" -ForegroundColor White
Write-Host ""
Write-Host "CLEANUP:" -ForegroundColor Yellow
Write-Host "────────" -ForegroundColor DarkGray
Write-Host "The EC2 instance will auto-terminate after the build." -ForegroundColor White
Write-Host "To manually terminate: aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION" -ForegroundColor White
Write-Host ""
Write-Host "Key pair saved at: $keyPath" -ForegroundColor Gray
Write-Host "Security group: $SG_ID" -ForegroundColor Gray
Write-Host ""

Write-Host "Deployment script completed successfully!" -ForegroundColor Green