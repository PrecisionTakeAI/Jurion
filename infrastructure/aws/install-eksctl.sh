#!/bin/bash
# Install eksctl - The official CLI for Amazon EKS
# Much easier than Terraform for beginners

set -e

echo "=== Installing eksctl ==="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing eksctl on Linux..."
    
    # Download and install eksctl
    curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz" | tar xz -C /tmp
    sudo mv /tmp/eksctl /usr/local/bin
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Installing eksctl on macOS..."
    
    # Install using Homebrew
    if command -v brew &> /dev/null; then
        brew tap weaveworks/tap
        brew install weaveworks/tap/eksctl
    else
        echo "Please install Homebrew first: https://brew.sh"
        exit 1
    fi
    
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "For Windows, please download eksctl from:"
    echo "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Windows_amd64.zip"
    echo "Extract and add to your PATH"
    exit 0
fi

# Verify installation
eksctl version

echo "eksctl installed successfully!"