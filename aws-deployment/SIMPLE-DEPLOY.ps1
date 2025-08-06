# SIMPLE-DEPLOY.ps1 - Simplified EC2 Build & Deploy
# Builds Docker image on EC2 and deploys to EKS

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  LegalLLM EC2 Build & Deploy" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$REGION = "ap-southeast-2"
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ECR_REPO = "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/legalllm-app"
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$KEY_NAME = "legalllm-key-$timestamp"

Write-Host "Account: $ACCOUNT_ID" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host ""

# Create key pair
Write-Host "Creating key pair..." -ForegroundColor Yellow
$keyPath = "$env:TEMP\$KEY_NAME.pem"
aws ec2 delete-key-pair --key-name $KEY_NAME --region $REGION 2>$null
$keyMaterial = aws ec2 create-key-pair --key-name $KEY_NAME --region $REGION --query KeyMaterial --output text
$keyMaterial | Out-File -FilePath $keyPath -Encoding ASCII
Write-Host "Key saved: $keyPath" -ForegroundColor Green

# Get VPC
Write-Host "Getting VPC..." -ForegroundColor Yellow
$VPC_ID = aws ec2 describe-vpcs --filters "Name=tag:Name,Values=eksctl-legalllm-working-cluster/VPC" --region $REGION --query "Vpcs[0].VpcId" --output text
if ($VPC_ID -eq "None") {
    $VPC_ID = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --region $REGION --query "Vpcs[0].VpcId" --output text
}
Write-Host "VPC: $VPC_ID" -ForegroundColor Green

# Create security group
Write-Host "Creating security group..." -ForegroundColor Yellow
$SG_NAME = "legalllm-sg-$timestamp"
$SG_ID = aws ec2 create-security-group --group-name $SG_NAME --description "LegalLLM build SG" --vpc-id $VPC_ID --region $REGION --query GroupId --output text

# Add SSH access
$MY_IP = (Invoke-WebRequest -Uri "http://checkip.amazonaws.com" -UseBasicParsing).Content.Trim()
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr "${MY_IP}/32" --region $REGION 2>$null
Write-Host "Security group: $SG_ID" -ForegroundColor Green

# Get subnet
Write-Host "Getting subnet..." -ForegroundColor Yellow
$SUBNET_ID = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" --region $REGION --query "Subnets[0].SubnetId" --output text
if ($SUBNET_ID -eq "None") {
    $SUBNET_ID = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --region $REGION --query "Subnets[0].SubnetId" --output text
}
Write-Host "Subnet: $SUBNET_ID" -ForegroundColor Green

# Create user data script
Write-Host "Preparing user data..." -ForegroundColor Yellow
$userDataFile = "$env:TEMP\userdata-$timestamp.txt"
@'
#!/bin/bash
exec > /var/log/legalllm-build.log 2>&1
set -x

# Update and install Docker
yum update -y
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user

# Install git
yum install git -y

# Configure AWS ECR
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-southeast-2
ECR_REPO=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/legalllm-app

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

# Clone and build
cd /home/ec2-user
git clone https://github.com/luqmanzulfiqarAhmed/LegalLLM-Professional.git || echo "Using local files"

# Check for uploaded files
if [ -f /tmp/app.tar.gz ]; then
    mkdir -p /home/ec2-user/LegalLLM-Professional
    tar -xzf /tmp/app.tar.gz -C /home/ec2-user/LegalLLM-Professional/
fi

cd /home/ec2-user/LegalLLM-Professional

# Create simple Dockerfile if not exists
if [ ! -f Dockerfile ]; then
    cat > Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "web_interface/enhanced_app_authenticated.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF
fi

# Build and push
docker build -t legalllm-app:latest .
docker tag legalllm-app:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest

echo "Build complete!"
'@ | Out-File -FilePath $userDataFile -Encoding ASCII

# Launch EC2 instance
Write-Host "Launching EC2 instance..." -ForegroundColor Yellow
$INSTANCE_ID = aws ec2 run-instances `
    --image-id ami-0d147324c76e8210a `
    --instance-type t3.medium `
    --key-name $KEY_NAME `
    --security-group-ids $SG_ID `
    --subnet-id $SUBNET_ID `
    --user-data file://$userDataFile `
    --associate-public-ip-address `
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=legalllm-build}]" `
    --instance-initiated-shutdown-behavior terminate `
    --region $REGION `
    --query "Instances[0].InstanceId" `
    --output text

Write-Host "Instance: $INSTANCE_ID" -ForegroundColor Green

# Wait for instance
Write-Host "Waiting for instance..." -ForegroundColor Yellow
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get public IP
$PUBLIC_IP = aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Write-Host "Public IP: $PUBLIC_IP" -ForegroundColor Green

# Optional: Upload local files
Write-Host ""
Write-Host "Preparing local files for upload..." -ForegroundColor Yellow
$sourcePath = Split-Path -Parent $PSScriptRoot
$tarPath = "$env:TEMP\app-$timestamp.tar.gz"

Push-Location $sourcePath
tar -czf $tarPath . --exclude .git --exclude __pycache__ 2>$null
Pop-Location

if (Test-Path $tarPath) {
    Write-Host "Archive created. Attempting upload..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Set key permissions
    icacls $keyPath /inheritancelevel:r /grant:r "${env:USERNAME}:R" 2>$null
    
    # Try SCP
    scp -o StrictHostKeyChecking=no -i $keyPath $tarPath ec2-user@${PUBLIC_IP}:/tmp/app.tar.gz 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Files uploaded!" -ForegroundColor Green
    } else {
        Write-Host "Upload failed, will use git clone" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "     BUILD IN PROGRESS" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Instance: $INSTANCE_ID" -ForegroundColor Yellow
Write-Host "IP: $PUBLIC_IP" -ForegroundColor Yellow
Write-Host ""
Write-Host "To monitor build:" -ForegroundColor White
Write-Host "  ssh -i $keyPath ec2-user@$PUBLIC_IP" -ForegroundColor Cyan
Write-Host "  tail -f /var/log/legalllm-build.log" -ForegroundColor Cyan
Write-Host ""

# Monitor ECR for image
Write-Host "Waiting for Docker image (max 15 minutes)..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 30
    $waited++
    
    $imageCheck = aws ecr describe-images --repository-name legalllm-app --region $REGION --query "imageDetails[0]" --output json 2>$null
    if ($imageCheck) {
        Write-Host ""
        Write-Host "Image found in ECR!" -ForegroundColor Green
        break
    }
    Write-Host "." -NoNewline
}

# Deploy to Kubernetes
Write-Host ""
Write-Host "Deploying to Kubernetes..." -ForegroundColor Yellow

# Update kubeconfig
aws eks update-kubeconfig --name legalllm-working --region $REGION

# Check if namespace exists
kubectl get namespace legalllm 2>$null
if ($LASTEXITCODE -ne 0) {
    kubectl create namespace legalllm
}

# Apply manifests
if (Test-Path "$PSScriptRoot\k8s-deployment.yaml") {
    kubectl apply -f "$PSScriptRoot\k8s-configmap.yaml" 2>$null
    kubectl apply -f "$PSScriptRoot\k8s-deployment.yaml"
    kubectl apply -f "$PSScriptRoot\k8s-service.yaml"
} else {
    Write-Host "Creating minimal deployment..." -ForegroundColor Yellow
    
    # Create deployment
    kubectl create deployment legalllm-app --image="${ECR_REPO}:latest" -n legalllm --dry-run=client -o yaml | kubectl apply -f -
    
    # Expose service
    kubectl expose deployment legalllm-app --type=LoadBalancer --port=80 --target-port=8501 -n legalllm --dry-run=client -o yaml | kubectl apply -f -
}

# Wait for deployment
Write-Host "Waiting for pods..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
kubectl get pods -n legalllm

# Get service URL
$LB_URL = kubectl get service -n legalllm -o jsonpath="{.items[0].status.loadBalancer.ingress[0].hostname}" 2>$null

Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Write-Host "    DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

if ($LB_URL) {
    Write-Host "Application URL:" -ForegroundColor Yellow
    Write-Host "http://$LB_URL" -ForegroundColor Cyan
} else {
    Write-Host "Getting Load Balancer URL..." -ForegroundColor Yellow
    Write-Host "Run: kubectl get service -n legalllm" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  kubectl get pods -n legalllm" -ForegroundColor White
Write-Host "  kubectl logs -n legalllm -l app=legalllm-app" -ForegroundColor White
Write-Host "  kubectl get service -n legalllm" -ForegroundColor White
Write-Host ""
Write-Host "EC2 will auto-terminate. Key: $keyPath" -ForegroundColor Gray
Write-Host ""
Write-Host "Done!" -ForegroundColor Green

# Cleanup temp files
Remove-Item $userDataFile -Force -ErrorAction SilentlyContinue
Remove-Item $tarPath -Force -ErrorAction SilentlyContinue