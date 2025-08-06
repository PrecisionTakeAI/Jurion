# Maximum Security Guide for LegalLLM Professional on AWS

**Protecting Your Legal Data and Code During Deployment**

---

## CRITICAL SECURITY QUESTIONS ANSWERED

### "How do I ensure no one can see my code during deployment?"

**Your code is protected through multiple layers:**

1. **During Upload to AWS:**
   - All transfers use TLS 1.3 encryption
   - Your code goes directly from your computer to YOUR private container registry
   - No one at AWS can see your source code
   - ECR (container registry) is private by default

2. **In Storage:**
   - Code is stored in Docker images in YOUR private ECR
   - Images are encrypted at rest using AES-256
   - Access requires YOUR AWS credentials
   - Enable ECR image scanning for vulnerabilities

3. **During Execution:**
   - Code runs in isolated containers
   - Each container has its own secure environment
   - No shared resources with other AWS customers
   - Memory is cleared when containers stop

**Step-by-Step Code Protection:**
```bash
# 1. Build your Docker image locally (code stays on your computer)
docker build -t legallm-professional .

# 2. Create private ECR repository
aws ecr create-repository --repository-name legallm-professional --image-scanning-configuration scanOnPush=true

# 3. Tag image for your private registry
docker tag legallm-professional:latest [YOUR-ACCOUNT].dkr.ecr.ap-southeast-2.amazonaws.com/legallm-professional:latest

# 4. Push to YOUR private registry (encrypted transfer)
docker push [YOUR-ACCOUNT].dkr.ecr.ap-southeast-2.amazonaws.com/legallm-professional:latest
```

### "What security settings are absolutely critical?"

**THE 10 CRITICAL SECURITY SETTINGS:**

1. **Multi-Factor Authentication (MFA)**
   ```
   CRITICAL: Enable MFA on:
   - Root account (IMMEDIATELY)
   - All IAM users
   - Especially users with admin access
   ```

2. **Encryption Everywhere**
   ```
   Database: Enable encryption at rest
   S3: Enable default encryption
   Secrets: Use AWS Secrets Manager
   Network: HTTPS only (no HTTP)
   ```

3. **Network Isolation**
   ```
   Database: Private subnet only
   No direct internet access to database
   Application: Behind load balancer
   Admin access: Via VPN or bastion host only
   ```

4. **Access Logging**
   ```
   CloudTrail: Log ALL API calls
   S3 Access Logs: Track document access
   Application Logs: User activity tracking
   Database Logs: Query logging for compliance
   ```

5. **Principle of Least Privilege**
   ```
   Each user: Minimum required permissions
   Each service: Specific role with limited access
   No use of root account for daily operations
   Regular permission audits
   ```

6. **Security Groups (Firewalls)**
   ```
   Database: Only accept from app servers
   App servers: Only accept from load balancer
   Load balancer: Only accept HTTPS (443)
   SSH/Admin: Only from your office IP
   ```

7. **Backup Encryption**
   ```
   RDS automated backups: Encrypted
   S3 backup bucket: Encrypted
   Snapshot copies: Encrypted
   Cross-region backups: Encrypted
   ```

8. **Secrets Management**
   ```
   NO passwords in code
   NO API keys in environment variables
   ALL secrets in AWS Secrets Manager
   Automatic rotation enabled
   ```

9. **Update Management**
   ```
   Enable automatic security patches
   Weekly vulnerability scans
   Monthly security reviews
   Immediate critical patch deployment
   ```

10. **Deletion Protection**
    ```
    RDS: Enable deletion protection
    S3: Enable versioning and MFA delete
    CloudTrail: Protect logs from deletion
    Backups: Separate account if possible
    ```

### "How do I set up secure access for my team only?"

**TEAM ACCESS SETUP - STEP BY STEP:**

#### Step 1: Create User Groups
```bash
# Create groups for different roles
aws iam create-group --group-name LegalLLM-Admins
aws iam create-group --group-name LegalLLM-Developers  
aws iam create-group --group-name LegalLLM-ReadOnly

# Attach appropriate policies
aws iam attach-group-policy --group-name LegalLLM-Admins --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam attach-group-policy --group-name LegalLLM-ReadOnly --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
```

#### Step 2: Create Individual Users
```bash
# Create user for each team member
aws iam create-user --user-name john.smith

# Force password change on first login
aws iam create-login-profile --user-name john.smith --password TempPass123! --password-reset-required

# Add to appropriate group
aws iam add-user-to-group --user-name john.smith --group-name LegalLLM-ReadOnly
```

#### Step 3: Set Up IP Restrictions
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "NotIpAddress": {
        "aws:SourceIp": [
          "203.1.2.3/32",     // Your office IP
          "203.1.2.4/32"      // Backup office IP
        ]
      }
    }
  }]
}
```

#### Step 4: Application-Level Access Control
```python
# In your application settings
ALLOWED_EMAIL_DOMAINS = ['yourlawfirm.com.au']
REQUIRE_EMAIL_VERIFICATION = True
SESSION_TIMEOUT = 30  # minutes
REQUIRE_2FA = True
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = 15  # minutes
```

---

## STEP-BY-STEP SECURITY HARDENING

### Phase 1: AWS Account Security (Day 1)

1. **Secure Root Account**
   ```
   [ ] Log into root account
   [ ] Enable MFA using authenticator app
   [ ] Create strong password (20+ characters)
   [ ] Store root credentials in physical safe
   [ ] NEVER use root account again except emergencies
   ```

2. **Create Admin User**
   ```
   [ ] Create IAM user for yourself
   [ ] Attach AdministratorAccess policy
   [ ] Enable MFA
   [ ] Create access keys
   [ ] Store securely in password manager
   ```

3. **Enable Security Services**
   ```
   [ ] Enable CloudTrail in all regions
   [ ] Enable GuardDuty for threat detection
   [ ] Enable AWS Config for compliance
   [ ] Enable Security Hub for overview
   ```

### Phase 2: Network Security (Before Deployment)

1. **VPC Configuration**
   ```
   Create VPC with:
   - Private subnets for database/app
   - Public subnets for load balancer only
   - No default security group rules
   - Enable VPC Flow Logs
   ```

2. **Security Groups Setup**
   ```
   # Load Balancer Security Group
   Inbound: 
   - HTTPS (443) from 0.0.0.0/0
   - HTTP (80) from 0.0.0.0/0 (redirect to HTTPS)
   Outbound:
   - HTTPS (443) to App Security Group

   # Application Security Group  
   Inbound:
   - Custom port from Load Balancer SG only
   Outbound:
   - HTTPS (443) to 0.0.0.0/0 (for APIs)
   - PostgreSQL (5432) to Database SG
   - Redis (6379) to Cache SG

   # Database Security Group
   Inbound:
   - PostgreSQL (5432) from App SG only
   Outbound:
   - None (database doesn't need internet)

   # Admin Access Security Group
   Inbound:
   - SSH (22) from YOUR office IP only
   Outbound:
   - All (for updates)
   ```

3. **WAF Configuration**
   ```
   Enable these WAF rules:
   [ ] SQL injection protection
   [ ] XSS (Cross-site scripting) protection  
   [ ] Known bad IPs blocking
   [ ] Geographic restrictions (Australia only?)
   [ ] Rate limiting (100 requests/minute)
   ```

### Phase 3: Data Security (During Deployment)

1. **Encryption Setup**
   ```bash
   # RDS Encryption
   --storage-encrypted \
   --kms-key-id alias/aws/rds

   # S3 Default Encryption
   aws s3api put-bucket-encryption \
     --bucket legallm-documents \
     --server-side-encryption-configuration \
     '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"}}]}'

   # EBS Volume Encryption
   --encrypted \
   --kms-key-id alias/aws/ebs
   ```

2. **Secrets Manager Setup**
   ```bash
   # Store database password
   aws secretsmanager create-secret \
     --name prod/legallm/db-password \
     --secret-string '{"password":"GeneratedPassword123!@#"}'

   # Store API keys
   aws secretsmanager create-secret \
     --name prod/legallm/openai-key \
     --secret-string '{"api_key":"sk-..."}'

   # Enable automatic rotation
   aws secretsmanager rotate-secret \
     --secret-id prod/legallm/db-password \
     --rotation-lambda-arn arn:aws:lambda:ap-southeast-2:xxx:function:SecretsManagerRotation
   ```

3. **Backup Security**
   ```bash
   # Enable backup encryption
   --backup-retention-period 30 \
   --preferred-backup-window "14:00-14:30" \
   --copy-tags-to-snapshot

   # Create separate backup account (optional but recommended)
   # Use AWS Organizations for account isolation
   ```

### Phase 4: Access Control (Before Going Live)

1. **IAM Roles for Services**
   ```json
   // ECS Task Role
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject"
         ],
         "Resource": "arn:aws:s3:::legallm-documents/*"
       },
       {
         "Effect": "Allow",
         "Action": [
           "secretsmanager:GetSecretValue"
         ],
         "Resource": "arn:aws:secretsmanager:ap-southeast-2:*:secret:prod/legallm/*"
       }
     ]
   }
   ```

2. **S3 Bucket Policies**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "DenyUnencryptedObjectUploads",
         "Effect": "Deny",
         "Principal": "*",
         "Action": "s3:PutObject",
         "Resource": "arn:aws:s3:::legallm-documents/*",
         "Condition": {
           "StringNotEquals": {
             "s3:x-amz-server-side-encryption": "aws:kms"
           }
         }
       }
     ]
   }
   ```

3. **API Security**
   ```python
   # In your application
   from functools import wraps
   import jwt

   def require_auth(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           token = request.headers.get('Authorization')
           if not token:
               return jsonify({'message': 'No token provided'}), 401
           
           try:
               payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
               request.user_id = payload['user_id']
               request.firm_id = payload['firm_id']
           except jwt.InvalidTokenError:
               return jsonify({'message': 'Invalid token'}), 401
           
           return f(*args, **kwargs)
       return decorated_function
   ```

### Phase 5: Monitoring & Alerting

1. **CloudWatch Alarms**
   ```
   Set up alarms for:
   [ ] Failed login attempts > 5 in 5 minutes
   [ ] Database connection failures
   [ ] Unusual API activity
   [ ] High error rates
   [ ] Unauthorized access attempts
   ```

2. **Log Analysis**
   ```
   Enable these logs:
   [ ] VPC Flow Logs → S3
   [ ] CloudTrail → S3 with encryption
   [ ] Application logs → CloudWatch
   [ ] Database query logs → CloudWatch
   [ ] WAF logs → S3
   ```

3. **Security Notifications**
   ```
   Create SNS topic for security alerts:
   [ ] Root account usage
   [ ] IAM policy changes
   [ ] Security group modifications
   [ ] Failed authentication spikes
   [ ] Data exfiltration attempts
   ```

---

## IP PROTECTION DURING DEPLOYMENT

### Protecting Your Intellectual Property

1. **Code Obfuscation (Optional)**
   ```python
   # Consider obfuscating sensitive algorithms
   pip install pyarmor
   pyarmor obfuscate --recursive src/
   ```

2. **License Enforcement**
   ```python
   # Add license checking
   def verify_license():
       license_key = os.environ.get('LICENSE_KEY')
       if not validate_license(license_key):
           sys.exit("Invalid license")
   ```

3. **Deployment Artifacts**
   ```
   Never include in Docker image:
   [ ] Source code comments
   [ ] Development files
   [ ] Test data
   [ ] Internal documentation
   [ ] Git history (.git folder)
   ```

4. **Access Audit Trail**
   ```python
   # Log all code access
   logger.info(f"Code accessed by {user_id} from {ip_address} at {timestamp}")
   ```

---

## TEAM ACCESS MANAGEMENT

### Setting Up Least Privilege Access

#### For Lawyers (Application Users)
```
Can:
- Log into application
- View their firm's data
- Upload documents
- Run queries

Cannot:
- Access AWS Console
- View other firms' data
- Modify system settings
- Access raw database
```

#### For IT Support
```
Can:
- View CloudWatch logs
- Restart services
- View monitoring dashboards
- Create support tickets

Cannot:
- Modify infrastructure
- Access sensitive data
- Change security settings
- Delete resources
```

#### For Developers
```
Can:
- Deploy new versions
- View application logs
- Modify code
- Run tests

Cannot:
- Access production data
- Modify security groups
- Delete backups
- Access billing
```

#### For Administrators
```
Can:
- Everything except root account
- Manage users
- Modify infrastructure
- Set security policies

Should:
- Use MFA always
- Log all actions
- Follow change process
- Regular access review
```

---

## SECURITY CHECKLIST SUMMARY

### Before Deployment
- [ ] Root account secured with MFA
- [ ] Admin user created with MFA
- [ ] CloudTrail enabled
- [ ] GuardDuty enabled
- [ ] All passwords in Secrets Manager
- [ ] VPC properly configured
- [ ] Security groups minimally permissive

### During Deployment
- [ ] All transfers over TLS
- [ ] Encryption enabled everywhere
- [ ] No secrets in code
- [ ] IP restrictions configured
- [ ] WAF rules active
- [ ] Backup encryption verified

### After Deployment
- [ ] All monitoring active
- [ ] Alerts configured
- [ ] Team access properly restricted
- [ ] Security scan completed
- [ ] Compliance documented
- [ ] Incident response plan ready

---

## EMERGENCY SECURITY PROCEDURES

### If You Suspect a Breach

1. **Immediate Actions (First 5 minutes)**
   ```bash
   # Isolate affected resources
   aws ec2 modify-instance-attribute --instance-id i-xxx --no-source-dest-check

   # Revoke potentially compromised credentials
   aws iam delete-access-key --access-key-id AKIA...

   # Take forensic snapshot
   aws ec2 create-snapshot --volume-id vol-xxx --description "Security incident $(date)"
   ```

2. **Investigation (First hour)**
   - Check CloudTrail for unauthorized API calls
   - Review VPC Flow Logs for unusual traffic
   - Analyze application logs for suspicious activity
   - Check for new or modified resources

3. **Containment**
   - Change all passwords
   - Rotate all API keys
   - Review and tighten security groups
   - Enable additional monitoring

4. **Communication**
   - Notify senior management
   - Contact AWS Support if needed
   - Document all actions taken
   - Prepare incident report

---

*Remember: Security is not a one-time task. Schedule monthly security reviews and stay updated on AWS security best practices.*