# Fix for EKS Node Group Metadata Service Issue

## Problem
Nodes in private subnets cannot reach EC2 metadata service (169.254.169.254), preventing them from joining the EKS cluster.

## Solution Steps

### Step 1: Fix Security Group Rules

1. **Go to EC2 Console → Security Groups**
2. **Find the security group attached to your failed nodes** (check the node group details)
3. **Edit Inbound Rules - Add these:**
   ```
   Type: All traffic
   Source: Self (security group ID)
   Description: Allow all traffic within security group
   ```

4. **Edit Outbound Rules - Ensure you have:**
   ```
   Type: All traffic
   Destination: 0.0.0.0/0
   Description: Allow all outbound traffic
   ```

### Step 2: Create Additional VPC Endpoints (if using private subnets)

Go to VPC Console → Endpoints → Create endpoint for each:

1. **com.amazonaws.ap-southeast-2.eks** (Interface endpoint)
   - Select your VPC
   - Select private subnets
   - Select security group that allows HTTPS (443)

2. **com.amazonaws.ap-southeast-2.ecr.api** (Interface endpoint)
3. **com.amazonaws.ap-southeast-2.ecr.dkr** (Interface endpoint)
4. **com.amazonaws.ap-southeast-2.logs** (Interface endpoint)
5. **com.amazonaws.ap-southeast-2.sts** (Interface endpoint)

### Step 3: Update Route Tables

1. **Go to VPC Console → Route Tables**
2. **Select the route table for your private subnets**
3. **Verify these routes exist:**
   ```
   Destination: 0.0.0.0/0 → Target: nat-xxxxx (your NAT Gateway)
   Destination: 10.0.0.0/16 → Target: local
   ```

### Step 4: Create New Node Group with Correct Configuration

Delete the failed node group and create a new one:

```bash
# First, create a launch template with user data
cat > user-data.sh << 'EOF'
#!/bin/bash
# Ensure metadata service is accessible
/usr/bin/imds-compat-disable-v1
# Join the cluster
/etc/eks/bootstrap.sh legalllm-cluster
EOF
```

In AWS Console:
1. **EC2 → Launch Templates → Create launch template**
   - Name: `legalllm-node-template`
   - AMI: Don't specify (let EKS choose)
   - Instance type: Don't specify
   - User data: Paste the script above

2. **Create Node Group with Launch Template:**
   - Go to EKS → Your cluster → Compute → Add node group
   - Name: `legalllm-nodes-fixed`
   - Node IAM role: `legalllm-eks-node-role`
   - **Use launch template:** Select `legalllm-node-template`
   - Subnets: Select private subnets
   - Create

## Alternative Quick Fix: Use Managed Node Groups with Public IP

If still having issues, create a node group with this configuration:

1. **Use PUBLIC subnets** (temporary for testing)
2. **Enable "Configure remote access"**
3. **Set "Remote access source security groups" to allow your IP**

This ensures nodes can definitely reach all required services.

## Verification Commands

After node group creation, verify:

```bash
# Check nodes joined cluster
kubectl get nodes

# Check node logs if issues persist
kubectl describe node <node-name>

# SSH to node (if remote access enabled)
ssh -i your-key.pem ec2-user@<node-public-ip>

# On the node, test metadata service
curl http://169.254.169.254/latest/meta-data/instance-id
```

## Why This Happens

1. **Network isolation:** Private subnets require careful configuration
2. **Security groups:** Default rules may be too restrictive
3. **VPC endpoints:** Required for private subnet communication with AWS services
4. **IMDS v2:** New instances may require IMDSv2 which has stricter requirements

## Best Practice for Production

Use private subnets with:
- Properly configured NAT Gateway
- All required VPC endpoints
- Security groups that allow internal communication
- Launch templates with correct bootstrap configuration