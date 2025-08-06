# FIXED EKS Configuration - Resolves Node Join Issues
# Use this instead of eks.tf if nodes are failing to join

# CRITICAL: Import existing resources first
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# EKS Cluster with FIXED endpoint configuration
resource "aws_eks_cluster" "legalllm_cluster_fixed" {
  name     = "legalllm-cluster"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.28"
  
  vpc_config {
    # CRITICAL: Use PUBLIC subnets for immediate fix
    # Change back to private after fixing security groups
    subnet_ids = concat(
      aws_subnet.public_subnets[*].id,
      aws_subnet.private_subnets[*].id
    )
    
    # CRITICAL: Both must be true for nodes in private subnets
    endpoint_private_access = true
    endpoint_public_access  = true
    
    # Security: Restrict after testing
    public_access_cidrs = ["0.0.0.0/0"]  # TODO: Restrict to your IP
    
    # Let EKS manage its own security group
    # Don't specify security_group_ids here
  }
  
  encryption_config {
    provider {
      key_arn = aws_kms_key.legalllm_kms.arn
    }
    resources = ["secrets"]
  }
  
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_cloudwatch_log_group.eks_cluster_logs
  ]
  
  tags = {
    Name = "LegalLLM EKS Cluster"
    Environment = var.environment
  }
}

# SIMPLIFIED Node Group for Testing - PUBLIC SUBNETS
resource "aws_eks_node_group" "public_test_nodes" {
  cluster_name    = aws_eks_cluster.legalllm_cluster_fixed.name
  node_group_name = "legalllm-public-test-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  
  # USE PUBLIC SUBNETS FOR IMMEDIATE FIX
  subnet_ids = aws_subnet.public_subnets[*].id
  
  capacity_type  = "ON_DEMAND"
  instance_types = ["t3.medium"]  # Cheaper for testing
  
  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }
  
  update_config {
    max_unavailable = 1
  }
  
  # Let EKS handle the launch template
  # Remove custom launch template for testing
  
  labels = {
    role = "test"
    subnet = "public"
  }
  
  # No taints for test nodes
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
  
  tags = {
    Name = "LegalLLM Test Node Group - Public"
    Purpose = "Testing node join issues"
  }
}

# After nodes join successfully, create private node group
resource "aws_eks_node_group" "private_production_nodes" {
  count = 0  # Set to 1 after public nodes work
  
  cluster_name    = aws_eks_cluster.legalllm_cluster_fixed.name
  node_group_name = "legalllm-private-production-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  
  # Use private subnets for production
  subnet_ids = aws_subnet.private_subnets[*].id
  
  capacity_type  = "ON_DEMAND"
  instance_types = ["m5.large"]
  
  scaling_config {
    desired_size = 3
    max_size     = 6
    min_size     = 2
  }
  
  update_config {
    max_unavailable = 1
  }
  
  labels = {
    role = "production"
    subnet = "private"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
    # Add security group rules as dependency
    aws_security_group_rule.nodes_ingress_cluster_api,
    aws_security_group_rule.nodes_ingress_kubelet,
    aws_security_group_rule.cluster_ingress_node_https,
    aws_security_group_rule.cluster_ingress_node_kubelet,
  ]
  
  tags = {
    Name = "LegalLLM Production Node Group - Private"
  }
}

# Critical: VPC CNI addon configuration for private networking
resource "aws_eks_addon" "vpc_cni_fixed" {
  cluster_name = aws_eks_cluster.legalllm_cluster_fixed.name
  addon_name   = "vpc-cni"
  
  # Use latest version
  addon_version = "v1.15.4-eksbuild.1"
  
  # Preserve settings on delete
  preserve = true
  
  # Custom configuration for private subnets
  configuration_values = jsonencode({
    env = {
      # Enable private IP for pods
      AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG = "true"
      ENI_CONFIG_LABEL_DEF = "topology.kubernetes.io/zone"
      
      # Increase IP addresses per node
      WARM_IP_TARGET = "5"
      MINIMUM_IP_TARGET = "2"
    }
  })
}

# CoreDNS addon - critical for node registration
resource "aws_eks_addon" "coredns_fixed" {
  cluster_name = aws_eks_cluster.legalllm_cluster_fixed.name
  addon_name   = "coredns"
  
  # Wait for at least one node to be ready
  depends_on = [
    aws_eks_node_group.public_test_nodes
  ]
}

# Kube-proxy addon
resource "aws_eks_addon" "kube_proxy_fixed" {
  cluster_name = aws_eks_cluster.legalllm_cluster_fixed.name
  addon_name   = "kube-proxy"
}

# Output for kubectl configuration
output "update_kubeconfig_command" {
  value = "aws eks update-kubeconfig --name ${aws_eks_cluster.legalllm_cluster_fixed.name} --region ${var.aws_region}"
}

output "test_nodes_command" {
  value = "kubectl get nodes -o wide"
}

output "check_system_pods_command" {
  value = "kubectl get pods -n kube-system"
}