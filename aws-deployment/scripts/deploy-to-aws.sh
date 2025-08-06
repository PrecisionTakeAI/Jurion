#!/bin/bash

# LegalLLM Professional - AWS Deployment Script
# Complete deployment automation for production AWS environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-"ap-southeast-2"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
FIRM_NAME=${FIRM_NAME:-"LegalLLM-Professional"}
CLUSTER_NAME="legalllm-cluster"
NAMESPACE="legalllm-production"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/aws-deployment/terraform"
K8S_DIR="$PROJECT_ROOT/aws-deployment/kubernetes"

echo -e "${BLUE}🚀 LegalLLM Professional AWS Deployment${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "AWS Region: ${YELLOW}$AWS_REGION${NC}"
echo -e "Firm Name: ${YELLOW}$FIRM_NAME${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI not found. Please install AWS CLI.${NC}"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}❌ Terraform not found. Please install Terraform.${NC}"
        exit 1
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
        exit 1
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        echo -e "${RED}❌ Helm not found. Please install Helm.${NC}"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure'.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All prerequisites met${NC}"
}

# Function to validate environment variables
validate_environment() {
    echo -e "${BLUE}Validating environment variables...${NC}"
    
    required_vars=(
        "DB_PASSWORD"
        "REDIS_AUTH_TOKEN"
        "OPENAI_API_KEY"
        "GROQ_API_KEY"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        printf '%s\n' "${missing_vars[@]}"
        echo -e "${YELLOW}Please set these variables and try again.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Environment variables validated${NC}"
}

# Function to deploy infrastructure with Terraform
deploy_infrastructure() {
    echo -e "${BLUE}Deploying AWS infrastructure with Terraform...${NC}"
    
    cd "$TERRAFORM_DIR"
    
    # Initialize Terraform
    echo -e "${BLUE}Initializing Terraform...${NC}"
    terraform init
    
    # Create workspace if it doesn't exist
    terraform workspace select "$ENVIRONMENT" 2>/dev/null || terraform workspace new "$ENVIRONMENT"
    
    # Plan deployment
    echo -e "${BLUE}Planning infrastructure deployment...${NC}"
    terraform plan \
        -var="aws_region=$AWS_REGION" \
        -var="environment=$ENVIRONMENT" \
        -var="firm_name=$FIRM_NAME" \
        -var="db_password=$DB_PASSWORD" \
        -var="redis_auth_token=$REDIS_AUTH_TOKEN" \
        -var="openai_api_key=$OPENAI_API_KEY" \
        -var="groq_api_key=$GROQ_API_KEY" \
        -out=tfplan
    
    # Apply deployment
    echo -e "${BLUE}Applying infrastructure deployment...${NC}"
    terraform apply tfplan
    
    # Export outputs
    echo -e "${BLUE}Exporting Terraform outputs...${NC}"
    terraform output -json > "$PROJECT_ROOT/terraform-outputs.json"
    
    echo -e "${GREEN}✅ Infrastructure deployment complete${NC}"
    
    cd "$PROJECT_ROOT"
}

# Function to configure kubectl
configure_kubectl() {
    echo -e "${BLUE}Configuring kubectl for EKS cluster...${NC}"
    
    aws eks update-kubeconfig \
        --region "$AWS_REGION" \
        --name "$CLUSTER_NAME" \
        --alias "$CLUSTER_NAME"
    
    # Test cluster connectivity
    echo -e "${BLUE}Testing cluster connectivity...${NC}"
    kubectl cluster-info
    
    echo -e "${GREEN}✅ kubectl configured successfully${NC}"
}

# Function to install EKS add-ons
install_eks_addons() {
    echo -e "${BLUE}Installing EKS add-ons...${NC}"
    
    # Install AWS Load Balancer Controller
    echo -e "${BLUE}Installing AWS Load Balancer Controller...${NC}"
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName="$CLUSTER_NAME" \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller \
        --wait
    
    # Install Cluster Autoscaler
    echo -e "${BLUE}Installing Cluster Autoscaler...${NC}"
    helm upgrade --install cluster-autoscaler autoscaler/cluster-autoscaler \
        -n kube-system \
        --set autoDiscovery.clusterName="$CLUSTER_NAME" \
        --set awsRegion="$AWS_REGION" \
        --wait
    
    # Install EFS CSI Driver
    echo -e "${BLUE}Installing EFS CSI Driver...${NC}"
    helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
    helm repo update
    
    helm upgrade --install aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
        -n kube-system \
        --wait
    
    echo -e "${GREEN}✅ EKS add-ons installed${NC}"
}

# Function to create EFS file system
create_efs() {
    echo -e "${BLUE}Creating EFS file system...${NC}"
    
    # Get VPC ID and subnet IDs from Terraform outputs
    VPC_ID=$(jq -r '.vpc_id.value' terraform-outputs.json)
    SUBNET_IDS=$(jq -r '.private_subnet_ids.value[]' terraform-outputs.json)
    
    # Create EFS file system
    EFS_ID=$(aws efs create-file-system \
        --region "$AWS_REGION" \
        --performance-mode generalPurpose \
        --throughput-mode provisioned \
        --provisioned-throughput-in-mibps 100 \
        --encrypted \
        --tags Key=Name,Value="legalllm-documents-$ENVIRONMENT" \
        --query 'FileSystemId' \
        --output text)
    
    echo -e "${GREEN}EFS File System created: $EFS_ID${NC}"
    
    # Wait for file system to become available
    echo -e "${BLUE}Waiting for EFS to become available...${NC}"
    aws efs wait file-system-available --file-system-id "$EFS_ID" --region "$AWS_REGION"
    
    # Create mount targets
    for subnet_id in $SUBNET_IDS; do
        echo -e "${BLUE}Creating mount target in subnet: $subnet_id${NC}"
        aws efs create-mount-target \
            --file-system-id "$EFS_ID" \
            --subnet-id "$subnet_id" \
            --security-groups "$(jq -r '.security_group_ids.value.eks_nodes' terraform-outputs.json)" \
            --region "$AWS_REGION" || true
    done
    
    # Update EFS ID in Kubernetes manifests
    sed -i "s/fs-xxxxxxxxx/$EFS_ID/g" "$K8S_DIR/production-deployment.yaml"
    
    echo -e "${GREEN}✅ EFS file system configured${NC}"
}

# Function to build and push Docker images
build_and_push_images() {
    echo -e "${BLUE}Building and pushing Docker images...${NC}"
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # Login to ECR
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
    
    # Create ECR repositories if they don't exist
    repositories=(
        "legalllm/professional"
        "legalllm/agent-orchestrator"
        "legalllm/document-agent"
        "legalllm/financial-agent"
    )
    
    for repo in "${repositories[@]}"; do
        repo_name=$(echo "$repo" | tr '/' '-')
        aws ecr describe-repositories --repository-names "$repo_name" --region "$AWS_REGION" 2>/dev/null || \
        aws ecr create-repository --repository-name "$repo_name" --region "$AWS_REGION"
    done
    
    # Build and push main application
    echo -e "${BLUE}Building main application image...${NC}"
    docker build -f "$PROJECT_ROOT/Dockerfile.production" -t "legalllm/professional:latest" "$PROJECT_ROOT"
    docker tag "legalllm/professional:latest" "$ECR_REGISTRY/legalllm-professional:latest"
    docker push "$ECR_REGISTRY/legalllm-professional:latest"
    
    # Build and push agent images (these would need separate Dockerfiles)
    echo -e "${BLUE}Building agent images...${NC}"
    
    # Agent Orchestrator
    if [[ -f "$PROJECT_ROOT/Dockerfile.agent-orchestrator" ]]; then
        docker build -f "$PROJECT_ROOT/Dockerfile.agent-orchestrator" -t "legalllm/agent-orchestrator:latest" "$PROJECT_ROOT"
        docker tag "legalllm/agent-orchestrator:latest" "$ECR_REGISTRY/legalllm-agent-orchestrator:latest"
        docker push "$ECR_REGISTRY/legalllm-agent-orchestrator:latest"
    fi
    
    # Document Agent
    if [[ -f "$PROJECT_ROOT/Dockerfile.document-agent" ]]; then
        docker build -f "$PROJECT_ROOT/Dockerfile.document-agent" -t "legalllm/document-agent:latest" "$PROJECT_ROOT"
        docker tag "legalllm/document-agent:latest" "$ECR_REGISTRY/legalllm-document-agent:latest"
        docker push "$ECR_REGISTRY/legalllm-document-agent:latest"
    fi
    
    # Financial Agent
    if [[ -f "$PROJECT_ROOT/Dockerfile.financial-agent" ]]; then
        docker build -f "$PROJECT_ROOT/Dockerfile.financial-agent" -t "legalllm/financial-agent:latest" "$PROJECT_ROOT"
        docker tag "legalllm/financial-agent:latest" "$ECR_REGISTRY/legalllm-financial-agent:latest"
        docker push "$ECR_REGISTRY/legalllm-financial-agent:latest"
    fi
    
    # Update image references in Kubernetes manifests
    sed -i "s|legalllm/professional:latest|$ECR_REGISTRY/legalllm-professional:latest|g" "$K8S_DIR/production-deployment.yaml"
    sed -i "s|legalllm/agent-orchestrator:latest|$ECR_REGISTRY/legalllm-agent-orchestrator:latest|g" "$K8S_DIR/production-deployment.yaml"
    sed -i "s|legalllm/document-agent:latest|$ECR_REGISTRY/legalllm-document-agent:latest|g" "$K8S_DIR/production-deployment.yaml"
    sed -i "s|legalllm/financial-agent:latest|$ECR_REGISTRY/legalllm-financial-agent:latest|g" "$K8S_DIR/production-deployment.yaml"
    
    echo -e "${GREEN}✅ Docker images built and pushed${NC}"
}

# Function to update Kubernetes secrets
update_k8s_secrets() {
    echo -e "${BLUE}Updating Kubernetes secrets...${NC}"
    
    # Get database endpoint from Terraform outputs
    DB_ENDPOINT=$(jq -r '.rds_endpoint.value' terraform-outputs.json)
    REDIS_ENDPOINT=$(jq -r '.redis_endpoint.value' terraform-outputs.json)
    
    # Create database URL
    DATABASE_URL="postgresql://legalllm_user:$DB_PASSWORD@$DB_ENDPOINT:5432/legalllm"
    
    # Update secrets in Kubernetes manifest
    sed -i "s|postgresql://user:password@rds-endpoint:5432/legalllm|$DATABASE_URL|g" "$K8S_DIR/production-deployment.yaml"
    sed -i "s|redis-auth-token|$REDIS_AUTH_TOKEN|g" "$K8S_DIR/production-deployment.yaml"
    sed -i "s|openai-api-key|$OPENAI_API_KEY|g" "$K8S_DIR/production-deployment.yaml"
    sed -i "s|groq-api-key|$GROQ_API_KEY|g" "$K8S_DIR/production-deployment.yaml"
    
    # Generate encryption keys
    AES_KEY=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 64)
    
    sed -i "s|32-byte-aes-key|$AES_KEY|g" "$K8S_DIR/production-deployment.yaml"
    sed -i "s|jwt-secret-key|$JWT_SECRET|g" "$K8S_DIR/production-deployment.yaml"
    
    echo -e "${GREEN}✅ Kubernetes secrets updated${NC}"
}

# Function to deploy application to Kubernetes
deploy_to_kubernetes() {
    echo -e "${BLUE}Deploying application to Kubernetes...${NC}"
    
    # Apply the deployment
    kubectl apply -f "$K8S_DIR/production-deployment.yaml"
    
    # Wait for deployments to be ready
    echo -e "${BLUE}Waiting for deployments to be ready...${NC}"
    kubectl wait --for=condition=available --timeout=600s deployment/legalllm-app -n "$NAMESPACE"
    kubectl wait --for=condition=available --timeout=300s deployment/legalllm-agent-orchestrator -n "$NAMESPACE"
    kubectl wait --for=condition=available --timeout=300s deployment/legalllm-document-agent -n "$NAMESPACE"
    kubectl wait --for=condition=available --timeout=300s deployment/legalllm-financial-agent -n "$NAMESPACE"
    
    echo -e "${GREEN}✅ Application deployed to Kubernetes${NC}"
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "${BLUE}Setting up monitoring and logging...${NC}"
    
    # Install Prometheus and Grafana
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        -n monitoring \
        --create-namespace \
        --set prometheus.prometheusSpec.retention=30d \
        --set grafana.adminPassword="$GRAFANA_PASSWORD" \
        --wait
    
    # Install AWS for Fluent Bit for log collection
    helm repo add aws https://aws.github.io/eks-charts
    helm upgrade --install aws-for-fluent-bit aws/aws-for-fluent-bit \
        -n kube-system \
        --set cloudWatchLogs.region="$AWS_REGION" \
        --wait
    
    echo -e "${GREEN}✅ Monitoring setup complete${NC}"
}

# Function to run post-deployment tests
run_post_deployment_tests() {
    echo -e "${BLUE}Running post-deployment tests...${NC}"
    
    # Get the load balancer endpoint
    echo -e "${BLUE}Waiting for load balancer to be ready...${NC}"
    sleep 60
    
    LB_HOSTNAME=$(kubectl get ingress legalllm-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    if [[ -n "$LB_HOSTNAME" ]]; then
        echo -e "${GREEN}Load Balancer Endpoint: https://$LB_HOSTNAME${NC}"
        
        # Test health endpoint
        echo -e "${BLUE}Testing health endpoint...${NC}"
        if curl -f "https://$LB_HOSTNAME/_stcore/health" --connect-timeout 30; then
            echo -e "${GREEN}✅ Health check passed${NC}"
        else
            echo -e "${YELLOW}⚠️  Health check failed, but deployment may still be initializing${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Load balancer endpoint not ready yet${NC}"
    fi
    
    # Show pod status
    echo -e "${BLUE}Pod status:${NC}"
    kubectl get pods -n "$NAMESPACE"
    
    echo -e "${GREEN}✅ Post-deployment tests complete${NC}"
}

# Function to display deployment summary
display_summary() {
    echo -e "${GREEN}🎉 Deployment Summary${NC}"
    echo -e "${GREEN}===================${NC}"
    
    # Get outputs from Terraform
    if [[ -f "$PROJECT_ROOT/terraform-outputs.json" ]]; then
        echo -e "${BLUE}Infrastructure:${NC}"
        echo -e "  VPC ID: $(jq -r '.vpc_id.value' terraform-outputs.json)"
        echo -e "  RDS Endpoint: $(jq -r '.rds_endpoint.value' terraform-outputs.json)"
        echo -e "  Redis Endpoint: $(jq -r '.redis_endpoint.value' terraform-outputs.json)"
        echo -e "  EKS Cluster: $CLUSTER_NAME"
    fi
    
    # Get load balancer endpoint
    LB_HOSTNAME=$(kubectl get ingress legalllm-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Not ready")
    
    echo -e "${BLUE}Application:${NC}"
    echo -e "  Namespace: $NAMESPACE"
    echo -e "  Load Balancer: $LB_HOSTNAME"
    echo -e "  Application URL: https://$LB_HOSTNAME"
    
    echo -e "${BLUE}Monitoring:${NC}"
    echo -e "  Prometheus: Port-forward with 'kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090'"
    echo -e "  Grafana: Port-forward with 'kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80'"
    
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "  1. Configure DNS to point to the load balancer"
    echo -e "  2. Setup SSL certificate in AWS Certificate Manager"
    echo -e "  3. Configure backup schedules"
    echo -e "  4. Setup monitoring alerts"
    echo -e "  5. Run security audit"
}

# Main deployment flow
main() {
    check_prerequisites
    validate_environment
    deploy_infrastructure
    configure_kubectl
    install_eks_addons
    create_efs
    build_and_push_images
    update_k8s_secrets
    deploy_to_kubernetes
    setup_monitoring
    run_post_deployment_tests
    display_summary
    
    echo -e "${GREEN}🎉 LegalLLM Professional deployment complete!${NC}"
}

# Handle command line arguments
case "${1:-deploy}" in
    "infrastructure")
        check_prerequisites
        validate_environment
        deploy_infrastructure
        ;;
    "app")
        check_prerequisites
        configure_kubectl
        build_and_push_images
        update_k8s_secrets
        deploy_to_kubernetes
        run_post_deployment_tests
        ;;
    "monitoring")
        check_prerequisites
        configure_kubectl
        setup_monitoring
        ;;
    "deploy"|"")
        main
        ;;
    *)
        echo "Usage: $0 [infrastructure|app|monitoring|deploy]"
        exit 1
        ;;
esac