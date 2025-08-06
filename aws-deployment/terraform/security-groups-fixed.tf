# FIXED Security Groups for EKS - Resolves Node Join Issues
# This file contains the corrected security group configurations

# Additional security group rules for EKS Cluster
resource "aws_security_group_rule" "cluster_ingress_node_https" {
  description              = "Allow nodes to communicate with cluster API"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_cluster_sg.id
  source_security_group_id = aws_security_group.eks_nodes_sg.id
  to_port                  = 443
  type                     = "ingress"
}

resource "aws_security_group_rule" "cluster_ingress_node_kubelet" {
  description              = "Allow cluster to receive kubelet communication"
  from_port                = 10250
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_cluster_sg.id
  source_security_group_id = aws_security_group.eks_nodes_sg.id
  to_port                  = 10250
  type                     = "ingress"
}

# Additional security group rules for EKS Nodes
resource "aws_security_group_rule" "nodes_ingress_cluster_api" {
  description              = "Allow cluster API to communicate with nodes"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_nodes_sg.id
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  to_port                  = 443
  type                     = "ingress"
}

resource "aws_security_group_rule" "nodes_ingress_kubelet" {
  description              = "Allow cluster to access kubelet API"
  from_port                = 10250
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_nodes_sg.id
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  to_port                  = 10250
  type                     = "ingress"
}

resource "aws_security_group_rule" "nodes_ingress_self_all" {
  description              = "Allow nodes to communicate with each other - all traffic"
  from_port                = 0
  protocol                 = "-1"
  security_group_id        = aws_security_group.eks_nodes_sg.id
  source_security_group_id = aws_security_group.eks_nodes_sg.id
  to_port                  = 0
  type                     = "ingress"
}

resource "aws_security_group_rule" "nodes_ingress_coredns_tcp" {
  description       = "Allow nodes to communicate with CoreDNS TCP"
  from_port         = 53
  protocol          = "tcp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = [aws_vpc.legalllm_vpc.cidr_block]
  to_port           = 53
  type              = "ingress"
}

resource "aws_security_group_rule" "nodes_ingress_coredns_udp" {
  description       = "Allow nodes to communicate with CoreDNS UDP"
  from_port         = 53
  protocol          = "udp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = [aws_vpc.legalllm_vpc.cidr_block]
  to_port           = 53
  type              = "ingress"
}

# Additional ingress for webhook admission controllers
resource "aws_security_group_rule" "nodes_ingress_webhook" {
  description              = "Allow webhook admission controller"
  from_port                = 8443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_nodes_sg.id
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  to_port                  = 8443
  type                     = "ingress"
}

# Allow nodes to pull images from ECR
resource "aws_security_group_rule" "nodes_egress_https" {
  description       = "Allow nodes to pull images from ECR and communicate with AWS services"
  from_port         = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  to_port           = 443
  type              = "egress"
}

resource "aws_security_group_rule" "nodes_egress_http" {
  description       = "Allow nodes HTTP for package updates"
  from_port         = 80
  protocol          = "tcp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  to_port           = 80
  type              = "egress"
}

resource "aws_security_group_rule" "nodes_egress_dns_tcp" {
  description       = "Allow nodes DNS TCP"
  from_port         = 53
  protocol          = "tcp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  to_port           = 53
  type              = "egress"
}

resource "aws_security_group_rule" "nodes_egress_dns_udp" {
  description       = "Allow nodes DNS UDP"
  from_port         = 53
  protocol          = "udp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  to_port           = 53
  type              = "egress"
}

resource "aws_security_group_rule" "nodes_egress_ntp" {
  description       = "Allow nodes NTP"
  from_port         = 123
  protocol          = "udp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  to_port           = 123
  type              = "egress"
}