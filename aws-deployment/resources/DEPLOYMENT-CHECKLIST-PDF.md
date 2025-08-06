# LegalLLM Professional AWS Deployment Checklist

**Print this document and check off each item as you complete it**

---

## EMERGENCY CONTACTS

**AWS Support:** 1-206-266-4064 (USA - 24/7)  
**AWS Support Portal:** https://console.aws.amazon.com/support/  
**Your AWS Account ID:** ___________________  
**Your Support Case #:** ___________________  
**Emergency Contact:** ___________________  
**Phone:** ___________________  

---

## PRE-DEPLOYMENT (Week 0)

### Accounts & Information
- [ ] Business credit card ready
- [ ] Business email address created
- [ ] Phone number for verification
- [ ] Company ABN/ACN documented
- [ ] Domain name (optional) registered
- [ ] OpenAI API key obtained
- [ ] Strong passwords generated (minimum 4)

**Completed Date:** ___/___/___ **Time:** ___:___

### Software Installation
- [ ] Web browser installed (Chrome/Firefox)
- [ ] Text editor installed (Notepad++/TextEdit)
- [ ] Password manager installed
- [ ] AWS CLI downloaded (not installed yet)

**Completed Date:** ___/___/___ **Time:** ___:___

### Documentation Review
- [ ] Read entire deployment guide
- [ ] Printed this checklist
- [ ] Prepared deployment folder
- [ ] Backed up all passwords

**Completed Date:** ___/___/___ **Time:** ___:___

---

## PHASE 1: AWS ACCOUNT SETUP (Week 1)

### Account Creation
- [ ] Created AWS account with business email
- [ ] Completed phone verification
- [ ] Added payment method
- [ ] Set up billing alerts ($50, $100, $500)
- [ ] Enabled MFA (Multi-Factor Authentication)
- [ ] Downloaded backup codes
- [ ] Stored backup codes securely

**Account Created Date:** ___/___/___ **Time:** ___:___  
**Account ID:** _________________________________

### Initial Security
- [ ] Created IAM admin user
- [ ] Set strong password for IAM user
- [ ] Enabled MFA for IAM user
- [ ] Created access keys
- [ ] Stored access keys securely
- [ ] Tested IAM login
- [ ] Disabled root account access keys

**IAM User Created Date:** ___/___/___ **Time:** ___:___  
**IAM Username:** _________________________________

### Region Configuration
- [ ] Selected Sydney (ap-southeast-2) region
- [ ] Verified all services in Sydney region
- [ ] Set default region in console

**Completed Date:** ___/___/___ **Time:** ___:___

---

## PHASE 2: INFRASTRUCTURE SETUP (Week 2-3)

### Networking
- [ ] Created VPC
- [ ] Created public subnet
- [ ] Created private subnet
- [ ] Configured Internet Gateway
- [ ] Set up NAT Gateway
- [ ] Configured route tables
- [ ] Created security groups

**VPC ID:** _________________________________  
**Completed Date:** ___/___/___ **Time:** ___:___

### Database Setup
- [ ] Created RDS PostgreSQL instance
- [ ] Set master password
- [ ] Configured backup settings
- [ ] Enabled encryption
- [ ] Set maintenance window
- [ ] Created database subnet group
- [ ] Tested connection

**Database Endpoint:** _________________________________  
**Completed Date:** ___/___/___ **Time:** ___:___

### Storage Setup
- [ ] Created S3 bucket for documents
- [ ] Enabled versioning
- [ ] Enabled encryption
- [ ] Set up lifecycle policies
- [ ] Created backup bucket
- [ ] Configured cross-region replication

**S3 Bucket Name:** _________________________________  
**Completed Date:** ___/___/___ **Time:** ___:___

### Compute Setup
- [ ] Created ECS cluster
- [ ] Set up task definitions
- [ ] Configured container registry (ECR)
- [ ] Pushed Docker images
- [ ] Created Application Load Balancer
- [ ] Configured target groups
- [ ] Set up health checks

**ECS Cluster Name:** _________________________________  
**Completed Date:** ___/___/___ **Time:** ___:___

---

## PHASE 3: APPLICATION DEPLOYMENT (Week 4-5)

### Environment Configuration
- [ ] Created all environment variables
- [ ] Stored secrets in AWS Secrets Manager
- [ ] Configured API keys
- [ ] Set database connection strings
- [ ] Configured Redis endpoint
- [ ] Set up logging configuration

**Secrets Manager ARN:** _________________________________  
**Completed Date:** ___/___/___ **Time:** ___:___

### Application Deployment
- [ ] Built Docker images
- [ ] Pushed to ECR
- [ ] Created ECS service
- [ ] Configured auto-scaling
- [ ] Set up CloudWatch alarms
- [ ] Deployed application
- [ ] Verified health checks passing

**Service Name:** _________________________________  
**Completed Date:** ___/___/___ **Time:** ___:___

### Domain & SSL (Optional)
- [ ] Created Route 53 hosted zone
- [ ] Updated domain nameservers
- [ ] Created SSL certificate
- [ ] Validated certificate
- [ ] Configured load balancer with SSL
- [ ] Tested HTTPS access

**Domain Name:** _________________________________  
**Completed Date:** ___/___/___ **Time:** ___:___

---

## PHASE 4: SECURITY & TESTING (Week 6)

### Security Hardening
- [ ] Reviewed all security groups
- [ ] Removed unnecessary ports
- [ ] Set up WAF rules
- [ ] Configured CloudTrail
- [ ] Enabled GuardDuty
- [ ] Set up AWS Config
- [ ] Created backup admin user

**Security Review Date:** ___/___/___ **Time:** ___:___

### Testing
- [ ] Created test user account
- [ ] Uploaded test documents
- [ ] Ran AI queries
- [ ] Tested from different locations
- [ ] Verified backup restore
- [ ] Load tested with 10 users
- [ ] Documented all issues

**Testing Completed Date:** ___/___/___ **Time:** ___:___

### User Setup
- [ ] Created production users
- [ ] Set up user permissions
- [ ] Created user guide
- [ ] Scheduled training sessions
- [ ] Set up support process

**Users Created Date:** ___/___/___ **Time:** ___:___

---

## GO-LIVE CHECKLIST

### Final Checks
- [ ] All health checks passing
- [ ] Backups verified working
- [ ] Monitoring alerts configured
- [ ] Cost alerts set up
- [ ] Security scan completed
- [ ] User acceptance testing done
- [ ] Legal compliance verified

**Final Check Date:** ___/___/___ **Time:** ___:___

### Launch
- [ ] Notified all users
- [ ] Support team ready
- [ ] Monitoring dashboard open
- [ ] Backup plan ready
- [ ] Rollback procedure documented
- [ ] **SYSTEM LIVE**

**Go-Live Date:** ___/___/___ **Time:** ___:___

---

## POST-DEPLOYMENT

### Day 1 Monitoring
- [ ] No critical errors
- [ ] All users can login
- [ ] Performance acceptable
- [ ] Costs tracking as expected

**Review Date:** ___/___/___ **Time:** ___:___

### Week 1 Review
- [ ] Gathered user feedback
- [ ] Reviewed error logs
- [ ] Optimized performance
- [ ] Updated documentation
- [ ] Planned improvements

**Review Date:** ___/___/___ **Time:** ___:___

---

## NOTES SECTION

**Issues Encountered:**
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________

**Solutions Applied:**
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________

**Lessons Learned:**
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________

---

**Deployment Team:**

Project Lead: _________________ Signature: _________________  
Technical Lead: _________________ Signature: _________________  
Security Review: _________________ Signature: _________________  

**Deployment Certified Complete:** ___/___/___

---

*This checklist is formatted for A4 printing. Print double-sided to save paper.*