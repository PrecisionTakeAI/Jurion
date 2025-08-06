# EKS Node Join Issue - Immediate Fix Guide

## CRITICAL ISSUE IDENTIFIED
Your nodes are failing to join because they're launching in **PRIVATE subnets** but the configuration isn't complete for private subnet node communication!

## 1. IMMEDIATE DEBUGGING COMMANDS

Run these commands RIGHT NOW to check your current state:

```bash
# 1. Check if your nodes can reach the EKS API endpoint
aws ec2 describe-instances \
  --filters "Name=tag:kubernetes.io/cluster/legalllm-cluster,Values=owned" \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,PrivateIpAddress,PublicIpAddress]" \
  --region ap-southeast-2

# 2. Check EKS cluster endpoint access configuration
aws eks describe-cluster --name legalllm-cluster \
  --query "cluster.resourcesVpcConfig" \
  --region ap-southeast-2

# 3. Check security group rules
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=legalllm-eks-*" \
  --query "SecurityGroups[*].[GroupId,GroupName,IpPermissions]" \
  --region ap-southeast-2

# 4. Get the failed node system logs (replace instance-id with yours)
aws ssm get-command-invocation \
  --command-id $(aws ssm send-command \
    --instance-ids "i-08c37d0c522abc6e7" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["sudo journalctl -u kubelet -n 100"]' \
    --query "Command.CommandId" \
    --output text \
    --region ap-southeast-2) \
  --instance-id "i-08c37d0c522abc6e7" \
  --region ap-southeast-2
```

## 2. MOST LIKELY CAUSES & FIXES

### CAUSE #1: Missing Security Group Rules (90% Probability)
**Problem:** The security groups are missing critical ingress rules for EKS communication.

**IMMEDIATE FIX - Add these rules manually in AWS Console:**

1. Go to EC2 > Security Groups
2. Find `legalllm-eks-cluster-sg`
3. Add these INBOUND rules:
   - **Port 443** from `legalllm-eks-nodes-sg` (HTTPS)
   - **Port 10250** from `legalllm-eks-nodes-sg` (Kubelet API)

4. Find `legalllm-eks-nodes-sg`
5. Add these INBOUND rules:
   - **Port 443** from `legalllm-eks-cluster-sg` (API Server to Kubelet)
   - **Port 10250** from `legalllm-eks-cluster-sg` (Metrics)
   - **Ports 1-65535** from SELF (inter-node communication)
   - **Port 53 (TCP & UDP)** from VPC CIDR (10.0.0.0/16) for DNS

### CAUSE #2: VPC DNS Configuration Issue
**Problem:** CoreDNS can't resolve cluster endpoint.

**IMMEDIATE FIX:**
```bash
# Check VPC DNS settings
aws ec2 describe-vpcs --vpc-ids <your-vpc-id> \
  --query "Vpcs[0].[EnableDnsHostnames,EnableDnsSupport]" \
  --region ap-southeast-2

# If either is false, enable them:
aws ec2 modify-vpc-attribute --vpc-id <your-vpc-id> \
  --enable-dns-hostnames --region ap-southeast-2

aws ec2 modify-vpc-attribute --vpc-id <your-vpc-id> \
  --enable-dns-support --region ap-southeast-2
```

### CAUSE #3: Nodes in Private Subnets Can't Reach EKS API
**Problem:** Your nodes are in private subnets but can't reach the public EKS endpoint.

**IMMEDIATE FIX - Update EKS endpoint access:**
```bash
aws eks update-cluster-config \
  --name legalllm-cluster \
  --resources-vpc-config endpointPrivateAccess=true,endpointPublicAccess=true \
  --region ap-southeast-2
```

## 3. TERRAFORM CONFIGURATION FIXES

Update your `eks.tf` file with these CRITICAL changes:

```hcl
# FIXED Security Group for EKS Cluster
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

# FIXED Security Group Rules for Nodes
resource "aws_security_group_rule" "nodes_ingress_cluster" {
  description              = "Allow cluster API to communicate with nodes"
  from_port                = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_nodes_sg.id
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  to_port                  = 443
  type                     = "ingress"
}

resource "aws_security_group_rule" "nodes_ingress_kubelet" {
  description              = "Allow cluster to access kubelet"
  from_port                = 10250
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_nodes_sg.id
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  to_port                  = 10250
  type                     = "ingress"
}

resource "aws_security_group_rule" "nodes_ingress_coredns_tcp" {
  description       = "Allow nodes CoreDNS TCP"
  from_port         = 53
  protocol          = "tcp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = [aws_vpc.legalllm_vpc.cidr_block]
  to_port           = 53
  type              = "ingress"
}

resource "aws_security_group_rule" "nodes_ingress_coredns_udp" {
  description       = "Allow nodes CoreDNS UDP"
  from_port         = 53
  protocol          = "udp"
  security_group_id = aws_security_group.eks_nodes_sg.id
  cidr_blocks       = [aws_vpc.legalllm_vpc.cidr_block]
  to_port           = 53
  type              = "ingress"
}
```

## 4. QUICK WORKAROUND - Launch Nodes in PUBLIC Subnets

If you need this working IMMEDIATELY, here's a quick workaround:

### Option A: Modify Node Group to Use Public Subnets (Fastest)
```bash
# Delete the failing node group
aws eks delete-nodegroup \
  --cluster-name legalllm-cluster \
  --nodegroup-name legalllm-primary-nodes \
  --region ap-southeast-2

# Wait for deletion
aws eks wait nodegroup-deleted \
  --cluster-name legalllm-cluster \
  --nodegroup-name legalllm-primary-nodes \
  --region ap-southeast-2

# Create new node group in PUBLIC subnets
aws eks create-nodegroup \
  --cluster-name legalllm-cluster \
  --nodegroup-name legalllm-primary-nodes-public \
  --node-role <your-node-role-arn> \
  --subnets <public-subnet-1> <public-subnet-2> \
  --instance-types m5.large \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --region ap-southeast-2
```

### Option B: Create Managed Node Group via Console
1. Go to EKS Console > Your Cluster > Compute tab
2. Click "Add Node Group"
3. **IMPORTANT:** Select PUBLIC subnets
4. Use these settings:
   - Instance type: m5.large (cheaper for testing)
   - Desired size: 2
   - Min: 1, Max: 3

## 5. VERIFICATION COMMANDS

After applying fixes, verify nodes are joining:

```bash
# 1. Check node status
kubectl get nodes

# 2. If kubectl not configured, configure it first:
aws eks update-kubeconfig --name legalllm-cluster --region ap-southeast-2

# 3. Check node logs
kubectl get events --all-namespaces | grep -i node

# 4. Check system pods
kubectl get pods -n kube-system

# 5. Detailed node description
kubectl describe nodes
```

## 6. AWS SUPPORT ESCALATION

If nodes still won't join after these fixes:

1. **Check AWS Systems Manager (SSM) access to nodes:**
```bash
aws ssm describe-instance-information \
  --filters "Key=tag:kubernetes.io/cluster/legalllm-cluster,Values=owned" \
  --region ap-southeast-2
```

2. **Get kubelet logs directly:**
```bash
# SSH to the node (if you have key pair)
ssh ec2-user@<node-public-ip>
sudo journalctl -u kubelet --no-pager | tail -100
```

3. **Check IAM role trust relationships:**
```bash
aws iam get-role --role-name legalllm-eks-node-role \
  --query "Role.AssumeRolePolicyDocument" \
  --region ap-southeast-2
```

## EMERGENCY CONTACT

If you're still stuck, these are the EXACT details to provide AWS Support:
- Cluster Name: legalllm-cluster
- Region: ap-southeast-2
- Node Instance IDs: i-08c37d0c522abc6e7, i-0fd5800a679b039c7
- Error: "NodeCreationFailure - Instances failed to join the kubernetes cluster"
- What you've tried: This guide's fixes

## PREVENTION FOR FUTURE

Add these to your Terraform to prevent this issue:

```hcl
# In eks.tf - Add explicit security group rules
# In main.tf - Ensure VPC has DNS enabled
# Consider using eks module: terraform-aws-modules/eks/aws
```

---

**This guide should get your nodes joining within 10-15 minutes. Start with Section 2, CAUSE #1 - it's the most common issue!**