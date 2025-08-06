# Alternative Solutions for Docker/WSL Issue

## 🚀 OPTION 1: Build on EC2 Instance (No Docker Desktop Needed!)

If Docker Desktop won't work on your machine, we can build the image directly on AWS:

### Script to Build on EC2:

```powershell
# This script creates an EC2 instance, builds the Docker image, and pushes to ECR
# Save as: BUILD-ON-EC2.ps1

Write-Host "=== Building Docker Image on EC2 (No Docker Desktop Needed!) ===" -ForegroundColor Green

# Configuration
$REGION = "ap-southeast-2"
$KEY_NAME = "legalllm-build-key"
$INSTANCE_TYPE = "t3.medium"
$AMI_ID = "ami-0d6560f3176dc9ec0"  # Amazon Linux 2023 in Sydney

# Step 1: Create a key pair
Write-Host "Creating EC2 key pair..." -ForegroundColor Yellow
aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text --region $REGION > $KEY_NAME.pem

# Step 2: Create security group
Write-Host "Creating security group..." -ForegroundColor Yellow
$SG_ID = aws ec2 create-security-group `
    --group-name legalllm-build-sg `
    --description "Temporary SG for Docker build" `
    --region $REGION `
    --query 'GroupId' `
    --output text

# Allow SSH
aws ec2 authorize-security-group-ingress `
    --group-id $SG_ID `
    --protocol tcp `
    --port 22 `
    --cidr 0.0.0.0/0 `
    --region $REGION

# Step 3: Launch EC2 instance
Write-Host "Launching EC2 instance..." -ForegroundColor Yellow
$INSTANCE_ID = aws ec2 run-instances `
    --image-id $AMI_ID `
    --instance-type $INSTANCE_TYPE `
    --key-name $KEY_NAME `
    --security-group-ids $SG_ID `
    --region $REGION `
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=legalllm-docker-build}]' `
    --user-data file://ec2-build-script.sh `
    --query 'Instances[0].InstanceId' `
    --output text

Write-Host "Instance launched: $INSTANCE_ID" -ForegroundColor Green
Write-Host "Waiting for instance to be ready..." -ForegroundColor Yellow

# Wait for instance
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get public IP
$PUBLIC_IP = aws ec2 describe-instances `
    --instance-ids $INSTANCE_ID `
    --region $REGION `
    --query 'Reservations[0].Instances[0].PublicIpAddress' `
    --output text

Write-Host "Instance ready at: $PUBLIC_IP" -ForegroundColor Green
Write-Host ""
Write-Host "The EC2 instance is now building your Docker image automatically!" -ForegroundColor Cyan
Write-Host "This will take about 10-15 minutes." -ForegroundColor Yellow
Write-Host ""
Write-Host "To check progress:" -ForegroundColor Yellow
Write-Host "  ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP" -ForegroundColor Cyan
Write-Host "  tail -f /var/log/cloud-init-output.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "When complete, the instance will terminate automatically." -ForegroundColor Green
```

### EC2 Build Script (ec2-build-script.sh):

```bash
#!/bin/bash
# This script runs on the EC2 instance to build and push the Docker image

# Install Docker
yum update -y
yum install -y docker git
service docker start

# Install AWS CLI
yum install -y aws-cli

# Clone the repository
cd /home/ec2-user
git clone https://github.com/yourusername/LegalLLM-Professional.git
cd LegalLLM-Professional

# Login to ECR
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 535319026444.dkr.ecr.ap-southeast-2.amazonaws.com

# Build the Docker image
docker build -t legalllm-app:latest .

# Tag and push to ECR
docker tag legalllm-app:latest 535319026444.dkr.ecr.ap-southeast-2.amazonaws.com/legalllm-app:latest
docker push 535319026444.dkr.ecr.ap-southeast-2.amazonaws.com/legalllm-app:latest

# Terminate instance after build
aws ec2 terminate-instances --instance-ids $(ec2-metadata --instance-id | cut -d " " -f 2) --region ap-southeast-2
```

---

## 🚀 OPTION 2: Use GitHub Actions (Completely Automated)

Create `.github/workflows/deploy.yml`:

```yaml
name: Build and Deploy to EKS

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-southeast-2
    
    - name: Login to Amazon ECR
      run: |
        aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 535319026444.dkr.ecr.ap-southeast-2.amazonaws.com
    
    - name: Build and push Docker image
      run: |
        docker build -t legalllm-app:latest .
        docker tag legalllm-app:latest 535319026444.dkr.ecr.ap-southeast-2.amazonaws.com/legalllm-app:latest
        docker push 535319026444.dkr.ecr.ap-southeast-2.amazonaws.com/legalllm-app:latest
    
    - name: Deploy to EKS
      run: |
        aws eks update-kubeconfig --name legalllm-working --region ap-southeast-2
        kubectl apply -f aws-deployment/k8s-configmap.yaml
        kubectl apply -f aws-deployment/k8s-deployment.yaml
        kubectl apply -f aws-deployment/k8s-service.yaml
        kubectl rollout status deployment/legalllm-app -n legalllm
```

To use this:
1. Go to your GitHub repository
2. Settings → Secrets → Actions
3. Add secrets:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
4. Push code or manually trigger the workflow

---

## 🚀 OPTION 3: Use AWS CodeBuild

Create a buildspec.yml file and use AWS CodeBuild to build the image without local Docker.

---

## 🚀 OPTION 4: Fix WSL/Docker Desktop

### Quick WSL Reset:
```powershell
# Run as Administrator
wsl --shutdown
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data
# Then reinstall Docker Desktop
```

### Use Older Docker Desktop Version:
Download Docker Desktop 4.20.0 or earlier which doesn't require the latest Windows build:
https://docs.docker.com/desktop/release-notes/

---

## Which Option Should You Choose?

1. **If you can update Windows:** Update Windows and use Docker Desktop normally
2. **If you can't update Windows:** Use Option 1 (EC2 build) - it's the fastest
3. **If you have GitHub:** Use Option 2 (GitHub Actions) - it's the most automated
4. **If you want to fix Docker locally:** Try Option 4 with an older version

The EC2 option (Option 1) is probably the quickest way to get your application deployed without dealing with local Docker issues!