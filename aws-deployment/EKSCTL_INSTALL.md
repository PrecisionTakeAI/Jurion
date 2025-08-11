# eksctl Installation Guide

## Important Note
The `eksctl.exe` file (140MB) was removed from this repository because it exceeds GitHub's 100MB file size limit. This does NOT affect the application's functionality - eksctl is only needed for AWS EKS cluster management.

## Installing eksctl

### Windows
```bash
# Option 1: Using Chocolatey (Recommended)
choco install eksctl

# Option 2: Direct Download
# Download from: https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Windows_amd64.zip
# Extract and add to PATH
```

### macOS
```bash
# Using Homebrew
brew install eksctl
```

### Linux
```bash
# Download and install
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

## Verify Installation
```bash
eksctl version
```

## Usage
Once installed, you can use all the eksctl commands in the deployment scripts:
```bash
# Create cluster
eksctl create cluster -f eksctl-simple-deploy.yaml

# Delete cluster
eksctl delete cluster --name legallm-cluster --region ap-southeast-2
```

## Alternative: Use AWS CLI
If you prefer not to install eksctl, you can manage EKS clusters using AWS CLI:
```bash
aws eks create-cluster --name legallm-cluster --region ap-southeast-2 ...
```

## No Impact on Application
- The Jurion application runs perfectly without eksctl
- eksctl is only needed by DevOps team for cluster management
- Developers can run the application locally without eksctl
- Production deployments can use existing EKS clusters