# AWS Deployment Quick Command Reference

**Copy and paste these commands exactly as shown**

---

## PHASE 1: INITIAL SETUP COMMANDS

### Install AWS CLI (Windows)
```bash
# Download installer from: https://awscli.amazonaws.com/AWSCLIV2.msi
# Then run in PowerShell:
msiexec.exe /i AWSCLIV2.msi
```

### Install AWS CLI (Mac)
```bash
# In Terminal:
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

### Configure AWS CLI
```bash
# Sets up your credentials
aws configure

# When prompted, enter:
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: ap-southeast-2
# Default output format: json
```

### Test AWS Connection
```bash
# Should show your account details
aws sts get-caller-identity
```

---

## PHASE 2: INFRASTRUCTURE COMMANDS

### Create S3 Bucket
```bash
# Replace 'my-legallm-bucket' with your unique name
aws s3 mb s3://my-legallm-bucket --region ap-southeast-2

# Enable versioning
aws s3api put-bucket-versioning --bucket my-legallm-bucket --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption --bucket my-legallm-bucket --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'
```

### Create VPC (Basic)
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region ap-southeast-2

# Note the VPC ID that appears, you'll need it
```

### Create ECR Repository
```bash
# Create repository for Docker images
aws ecr create-repository --repository-name legallm-professional --region ap-southeast-2

# Get login token
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin [YOUR-ACCOUNT-ID].dkr.ecr.ap-southeast-2.amazonaws.com
```

---

## PHASE 3: APPLICATION DEPLOYMENT

### Build and Push Docker Image
```bash
# Build Docker image
docker build -t legallm-professional .

# Tag for ECR
docker tag legallm-professional:latest [YOUR-ACCOUNT-ID].dkr.ecr.ap-southeast-2.amazonaws.com/legallm-professional:latest

# Push to ECR
docker push [YOUR-ACCOUNT-ID].dkr.ecr.ap-southeast-2.amazonaws.com/legallm-professional:latest
```

### Create Secrets
```bash
# Store database password
aws secretsmanager create-secret --name prod/legallm/db-password --secret-string "YourStrongPassword123!" --region ap-southeast-2

# Store API keys
aws secretsmanager create-secret --name prod/legallm/openai-key --secret-string "sk-..." --region ap-southeast-2
```

### Deploy ECS Service
```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json --region ap-southeast-2

# Create service
aws ecs create-service --cluster legallm-cluster --service-name legallm-service --task-definition legallm-task:1 --desired-count 2 --region ap-southeast-2
```

---

## MONITORING & TROUBLESHOOTING

### View Logs
```bash
# List log groups
aws logs describe-log-groups --region ap-southeast-2

# View recent logs
aws logs tail /ecs/legallm-professional --follow --region ap-southeast-2
```

### Check Service Status
```bash
# List ECS services
aws ecs list-services --cluster legallm-cluster --region ap-southeast-2

# Describe service
aws ecs describe-services --cluster legallm-cluster --services legallm-service --region ap-southeast-2
```

### Database Commands
```bash
# List databases
aws rds describe-db-instances --region ap-southeast-2

# Create snapshot
aws rds create-db-snapshot --db-instance-identifier legallm-db --db-snapshot-identifier legallm-backup-$(date +%Y%m%d) --region ap-southeast-2
```

### Cost Monitoring
```bash
# Get current month costs
aws ce get-cost-and-usage --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) --granularity DAILY --metrics "UnblendedCost" --region ap-southeast-2

# Set billing alert (via CloudWatch)
aws cloudwatch put-metric-alarm --alarm-name billing-alarm-500 --alarm-description "Alert when billing exceeds $500" --metric-name EstimatedCharges --namespace AWS/Billing --statistic Maximum --period 86400 --threshold 500 --comparison-operator GreaterThanThreshold --region us-east-1
```

---

## BACKUP & RESTORE

### Create Full Backup
```bash
# Database backup
aws rds create-db-snapshot --db-instance-identifier legallm-db --db-snapshot-identifier manual-backup-$(date +%Y%m%d-%H%M%S)

# S3 backup
aws s3 sync s3://my-legallm-bucket s3://my-legallm-backup-bucket --region ap-southeast-2
```

### Restore from Backup
```bash
# Restore database
aws rds restore-db-instance-from-db-snapshot --db-instance-identifier legallm-db-restored --db-snapshot-identifier manual-backup-20240315-120000

# Restore S3
aws s3 sync s3://my-legallm-backup-bucket s3://my-legallm-bucket --region ap-southeast-2
```

---

## SECURITY COMMANDS

### List All Resources
```bash
# Check what's running (and costing money)
aws resourcegroupstaggingapi get-resources --region ap-southeast-2
```

### Security Group Rules
```bash
# List security groups
aws ec2 describe-security-groups --region ap-southeast-2

# Add rule (example: allow HTTPS)
aws ec2 authorize-security-group-ingress --group-id sg-xxxxxx --protocol tcp --port 443 --cidr 0.0.0.0/0 --region ap-southeast-2
```

### IAM User Management
```bash
# Create user
aws iam create-user --user-name john.smith

# Add to group
aws iam add-user-to-group --user-name john.smith --group-name legallm-users

# Create access key
aws iam create-access-key --user-name john.smith
```

---

## EMERGENCY SHUTDOWN

### Stop All Services (Save Money)
```bash
# Scale down ECS to 0
aws ecs update-service --cluster legallm-cluster --service legallm-service --desired-count 0

# Stop RDS instance
aws rds stop-db-instance --db-instance-identifier legallm-db

# Stop NAT Gateway (if using)
aws ec2 delete-nat-gateway --nat-gateway-id nat-xxxxxx
```

### Restart Services
```bash
# Start RDS
aws rds start-db-instance --db-instance-identifier legallm-db

# Scale up ECS
aws ecs update-service --cluster legallm-cluster --service legallm-service --desired-count 2
```

---

## USEFUL SHORTCUTS

### Check Everything at Once
```bash
# Create a status check script
echo "=== ECS Status ===" && aws ecs list-services --cluster legallm-cluster
echo "=== RDS Status ===" && aws rds describe-db-instances --query 'DBInstances[].{ID:DBInstanceIdentifier,Status:DBInstanceStatus}'
echo "=== S3 Buckets ===" && aws s3 ls
echo "=== Current Costs ===" && aws ce get-cost-and-usage --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) --granularity DAILY --metrics "UnblendedCost" --query 'ResultsByTime[-1].Total.UnblendedCost'
```

### Clean Up Test Resources
```bash
# List all resources with 'test' tag
aws resourcegroupstaggingapi get-resources --tag-filters Key=Environment,Values=test

# Delete test S3 bucket (must be empty first)
aws s3 rm s3://test-bucket --recursive
aws s3 rb s3://test-bucket
```

---

**PRO TIPS:**
1. Always add `--region ap-southeast-2` to commands
2. Use `--dry-run` to test dangerous commands first
3. Save command outputs with `> output.txt`
4. Use `aws help` or `aws [service] help` for documentation
5. Set up command aliases for frequently used commands

**NEVER RUN:**
- Commands that delete resources without checking first
- Commands from untrusted sources
- Commands you don't understand

---

*Keep this guide handy during deployment. Update with your specific resource names and IDs.*