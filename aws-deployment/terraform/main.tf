# LegalLLM Professional - AWS Infrastructure as Code
# Terraform configuration for enterprise deployment in Australia

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
  
  backend "s3" {
    bucket = "legalllm-terraform-state"
    key    = "production/terraform.tfstate"
    region = "ap-southeast-2"
    encrypt = true
  }
}

# AWS Provider - Australia region for legal compliance
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "LegalLLM Professional"
      Environment = var.environment
      Compliance  = "Privacy Act 1988"
      DataClass   = "Legal Confidential"
      Owner       = var.firm_name
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-southeast-2"  # Sydney for Australian legal compliance
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "firm_name" {
  description = "Law firm name for resource tagging"
  type        = string
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key"
  type        = string
  sensitive   = true
}

# VPC Configuration
resource "aws_vpc" "legalllm_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "legalllm-vpc-${var.environment}"
    "kubernetes.io/cluster/legalllm-cluster" = "shared"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "legalllm_igw" {
  vpc_id = aws_vpc.legalllm_vpc.id
  
  tags = {
    Name = "legalllm-igw-${var.environment}"
  }
}

# Public Subnets for Load Balancers and NAT Gateways
resource "aws_subnet" "public_subnets" {
  count = 2
  
  vpc_id                  = aws_vpc.legalllm_vpc.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "legalllm-public-subnet-${count.index + 1}"
    Type = "Public"
    "kubernetes.io/role/elb" = "1"
  }
}

# Private Subnets for Application and Database
resource "aws_subnet" "private_subnets" {
  count = 3
  
  vpc_id            = aws_vpc.legalllm_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index % length(data.aws_availability_zones.available.names)]
  
  tags = {
    Name = "legalllm-private-subnet-${count.index + 1}"
    Type = "Private"
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/legalllm-cluster" = "owned"
  }
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat_gateway_eips" {
  count = 2
  domain = "vpc"
  
  tags = {
    Name = "legalllm-nat-eip-${count.index + 1}"
  }
}

# NAT Gateways
resource "aws_nat_gateway" "nat_gateways" {
  count = 2
  
  allocation_id = aws_eip.nat_gateway_eips[count.index].id
  subnet_id     = aws_subnet.public_subnets[count.index].id
  
  tags = {
    Name = "legalllm-nat-gateway-${count.index + 1}"
  }
  
  depends_on = [aws_internet_gateway.legalllm_igw]
}

# Route Tables
resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.legalllm_vpc.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.legalllm_igw.id
  }
  
  tags = {
    Name = "legalllm-public-route-table"
  }
}

resource "aws_route_table" "private_route_tables" {
  count = 2
  
  vpc_id = aws_vpc.legalllm_vpc.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gateways[count.index].id
  }
  
  tags = {
    Name = "legalllm-private-route-table-${count.index + 1}"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public_route_table_associations" {
  count = 2
  
  subnet_id      = aws_subnet.public_subnets[count.index].id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "private_route_table_associations" {
  count = 3
  
  subnet_id      = aws_subnet.private_subnets[count.index].id
  route_table_id = aws_route_table.private_route_tables[count.index % 2].id
}

# Security Groups
resource "aws_security_group" "eks_cluster_sg" {
  name_prefix = "legalllm-eks-cluster-"
  vpc_id      = aws_vpc.legalllm_vpc.id
  
  ingress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
    cidr_blocks = [aws_vpc.legalllm_vpc.cidr_block]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "legalllm-eks-cluster-sg"
  }
}

resource "aws_security_group" "rds_sg" {
  name_prefix = "legalllm-rds-"
  vpc_id      = aws_vpc.legalllm_vpc.id
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes_sg.id]
  }
  
  tags = {
    Name = "legalllm-rds-sg"
  }
}

resource "aws_security_group" "redis_sg" {
  name_prefix = "legalllm-redis-"
  vpc_id      = aws_vpc.legalllm_vpc.id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes_sg.id]
  }
  
  tags = {
    Name = "legalllm-redis-sg"
  }
}

resource "aws_security_group" "eks_nodes_sg" {
  name_prefix = "legalllm-eks-nodes-"
  vpc_id      = aws_vpc.legalllm_vpc.id
  
  ingress {
    from_port = 0
    to_port   = 65535
    protocol  = "tcp"
    self      = true
  }
  
  ingress {
    from_port       = 1025
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_cluster_sg.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "legalllm-eks-nodes-sg"
    "kubernetes.io/cluster/legalllm-cluster" = "owned"
  }
}

# KMS Key for encryption
resource "aws_kms_key" "legalllm_kms" {
  description             = "LegalLLM Professional encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  tags = {
    Name = "legalllm-kms-key"
  }
}

resource "aws_kms_alias" "legalllm_kms_alias" {
  name          = "alias/legalllm-${var.environment}"
  target_key_id = aws_kms_key.legalllm_kms.key_id
}

# Outputs
output "vpc_id" {
  value = aws_vpc.legalllm_vpc.id
}

output "private_subnet_ids" {
  value = aws_subnet.private_subnets[*].id
}

output "public_subnet_ids" {
  value = aws_subnet.public_subnets[*].id
}

output "security_group_ids" {
  value = {
    eks_cluster = aws_security_group.eks_cluster_sg.id
    eks_nodes   = aws_security_group.eks_nodes_sg.id
    rds         = aws_security_group.rds_sg.id
    redis       = aws_security_group.redis_sg.id
  }
}

output "kms_key_id" {
  value = aws_kms_key.legalllm_kms.key_id
}