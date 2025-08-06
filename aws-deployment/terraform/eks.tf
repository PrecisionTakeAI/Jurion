# Amazon EKS Configuration for LegalLLM Professional
# Multi-agent capable Kubernetes cluster with node groups

# EKS Cluster IAM Role
resource "aws_iam_role" "eks_cluster_role" {
  name = "legalllm-eks-cluster-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster_role.name
}

# EKS Node Group IAM Role
resource "aws_iam_role" "eks_node_role" {
  name = "legalllm-eks-node-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_role.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_role.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_role.name
}

# Additional IAM policy for EFS access
resource "aws_iam_policy" "eks_efs_policy" {
  name        = "legalllm-eks-efs-policy"
  description = "Policy for EKS nodes to access EFS"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:CreateFileSystem",
          "elasticfilesystem:CreateMountTarget",
          "elasticfilesystem:CreateTags",
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeMountTargetSecurityGroups",
          "elasticfilesystem:ModifyMountTargetSecurityGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_efs_policy_attachment" {
  policy_arn = aws_iam_policy.eks_efs_policy.arn
  role       = aws_iam_role.eks_node_role.name
}

# EKS Cluster
resource "aws_eks_cluster" "legalllm_cluster" {
  name     = "legalllm-cluster"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.28"
  
  vpc_config {
    subnet_ids              = aws_subnet.private_subnets[*].id
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs    = ["0.0.0.0/0"]  # Restrict this in production
    security_group_ids     = [aws_security_group.eks_cluster_sg.id]
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

# CloudWatch Log Group for EKS
resource "aws_cloudwatch_log_group" "eks_cluster_logs" {
  name              = "/aws/eks/legalllm-cluster/cluster"
  retention_in_days = 30
  kms_key_id       = aws_kms_key.legalllm_kms.arn
}

# Launch Template for EKS Node Groups
resource "aws_launch_template" "eks_node_template" {
  name_prefix   = "legalllm-eks-node-"
  image_id      = data.aws_ami.eks_worker.id
  instance_type = "m5.xlarge"
  
  vpc_security_group_ids = [aws_security_group.eks_nodes_sg.id]
  
  user_data = base64encode(templatefile("${path.module}/eks-node-userdata.sh", {
    cluster_name = aws_eks_cluster.legalllm_cluster.name
    endpoint     = aws_eks_cluster.legalllm_cluster.endpoint
    ca_data      = aws_eks_cluster.legalllm_cluster.certificate_authority[0].data
  }))
  
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 50
      volume_type = "gp3"
      encrypted   = true
      kms_key_id  = aws_kms_key.legalllm_kms.arn
    }
  }
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 2
  }
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "legalllm-eks-node"
      "kubernetes.io/cluster/legalllm-cluster" = "owned"
    }
  }
}

# Primary Node Group for core services
resource "aws_eks_node_group" "primary_nodes" {
  cluster_name    = aws_eks_cluster.legalllm_cluster.name
  node_group_name = "legalllm-primary-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_subnet.private_subnets[*].id
  
  capacity_type  = "ON_DEMAND"
  instance_types = ["m5.xlarge"]
  
  scaling_config {
    desired_size = 3
    max_size     = 6
    min_size     = 2
  }
  
  update_config {
    max_unavailable = 1
  }
  
  launch_template {
    id      = aws_launch_template.eks_node_template.id
    version = aws_launch_template.eks_node_template.latest_version
  }
  
  labels = {
    role = "primary"
    workload = "core"
  }
  
  taint {
    key    = "workload"
    value  = "core"
    effect = "NO_SCHEDULE"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
  
  tags = {
    Name = "LegalLLM Primary Node Group"
  }
}

# Agent Node Group for multi-agent workloads
resource "aws_eks_node_group" "agent_nodes" {
  cluster_name    = aws_eks_cluster.legalllm_cluster.name
  node_group_name = "legalllm-agent-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_subnet.private_subnets[*].id
  
  capacity_type  = "ON_DEMAND"
  instance_types = ["c5.2xlarge"]  # CPU optimized for AI workloads
  
  scaling_config {
    desired_size = 2
    max_size     = 5
    min_size     = 1
  }
  
  update_config {
    max_unavailable = 1
  }
  
  launch_template {
    id      = aws_launch_template.eks_node_template.id
    version = aws_launch_template.eks_node_template.latest_version
  }
  
  labels = {
    role = "agent"
    workload = "ai-processing"
  }
  
  taint {
    key    = "workload"
    value  = "ai-processing"
    effect = "NO_SCHEDULE"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
  
  tags = {
    Name = "LegalLLM Agent Node Group"
    Purpose = "Multi-Agent AI Processing"
  }
}

# Spot Node Group for cost optimization
resource "aws_eks_node_group" "spot_nodes" {
  cluster_name    = aws_eks_cluster.legalllm_cluster.name
  node_group_name = "legalllm-spot-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_subnet.private_subnets[*].id
  
  capacity_type  = "SPOT"
  instance_types = ["m5.large", "m5.xlarge", "c5.large", "c5.xlarge"]
  
  scaling_config {
    desired_size = 1
    max_size     = 3
    min_size     = 0
  }
  
  update_config {
    max_unavailable = 1
  }
  
  launch_template {
    id      = aws_launch_template.eks_node_template.id
    version = aws_launch_template.eks_node_template.latest_version
  }
  
  labels = {
    role = "spot"
    workload = "batch-processing"
  }
  
  taint {
    key    = "workload"
    value  = "batch-processing"
    effect = "NO_SCHEDULE"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
  
  tags = {
    Name = "LegalLLM Spot Node Group"
    Purpose = "Cost-Optimized Batch Processing"
  }
}

# Data source for EKS worker AMI
data "aws_ami" "eks_worker" {
  filter {
    name   = "name"
    values = ["amazon-eks-node-1.28-v*"]
  }
  
  most_recent = true
  owners      = ["602401143452"]
}

# EKS Add-ons
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.legalllm_cluster.name
  addon_name   = "vpc-cni"
}

resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.legalllm_cluster.name
  addon_name   = "coredns"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.legalllm_cluster.name
  addon_name   = "kube-proxy"
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name = aws_eks_cluster.legalllm_cluster.name
  addon_name   = "aws-ebs-csi-driver"
}

resource "aws_eks_addon" "efs_csi_driver" {
  cluster_name = aws_eks_cluster.legalllm_cluster.name
  addon_name   = "aws-efs-csi-driver"
}

# Outputs
output "cluster_endpoint" {
  value = aws_eks_cluster.legalllm_cluster.endpoint
}

output "cluster_security_group_id" {
  value = aws_eks_cluster.legalllm_cluster.vpc_config[0].cluster_security_group_id
}

output "cluster_name" {
  value = aws_eks_cluster.legalllm_cluster.name
}

output "cluster_certificate_authority_data" {
  value = aws_eks_cluster.legalllm_cluster.certificate_authority[0].data
}