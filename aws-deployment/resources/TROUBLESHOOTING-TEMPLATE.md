# Troubleshooting Templates & Common Solutions

**Use these templates to get help quickly and effectively**

---

## ERROR REPORTING TEMPLATE

**Copy and fill out this template when reporting errors:**

```
### ERROR SUMMARY
**What were you trying to do:** 
[Example: Deploy the application to ECS]

**What went wrong:** 
[Example: Container keeps restarting every 30 seconds]

**Error message (exact text):**
```
[Paste the EXACT error message here]
```

### ENVIRONMENT DETAILS
**AWS Service:** [ECS/RDS/S3/etc]
**Region:** ap-southeast-2
**Time it happened:** [Date and time]
**Your AWS Account ID:** [Last 4 digits only for security]

### WHAT I'VE TRIED
1. [First thing you tried]
   - Result: [What happened]
2. [Second thing you tried]
   - Result: [What happened]
3. [Third thing you tried]
   - Result: [What happened]

### SCREENSHOTS
[Attach screenshots of:
- The error message
- Your AWS console
- Any relevant settings]

### IMPACT
**Is production affected?** Yes/No
**How many users affected?** 
**Can users still work?** Yes/No/Partially

### ADDITIONAL CONTEXT
[Any other information that might help]
```

---

## "EXPLAIN LIKE I'M FIVE" REQUEST FORMAT

**Use this when technical explanations are too complex:**

```
### ELI5 REQUEST

**The technical thing I don't understand:**
[Example: What is a VPC and why do I need one?]

**What I'm trying to achieve:**
[Example: I want my application to be secure but accessible from the internet]

**My current understanding:**
[Example: I know it's something about networking but not sure why it matters]

**Specific questions:**
1. [What does this actually do?]
2. [Why is it necessary?]
3. [What happens if I don't use it?]
4. [Is there a simpler alternative?]

**Please explain using:**
- [ ] Real-world analogies
- [ ] Simple diagrams
- [ ] Step-by-step reasoning
- [ ] Common examples
- [ ] What could go wrong stories
```

---

## VIDEO SCRIPT CREATION TEMPLATE

**For creating helpful video tutorials:**

```
### VIDEO TUTORIAL REQUEST

**Video Title:** How to [specific task]
**Target Audience:** [Complete beginners/Law firm IT staff/etc]
**Video Length:** [5-10 minutes preferred]

**INTRODUCTION (30 seconds)**
- Who this video is for
- What we'll accomplish
- What you need before starting

**MAIN CONTENT (3-7 minutes)**
Part 1: [First major step]
- Screen recording needed: Yes/No
- Key points to emphasize:
  • 
  • 
  •

Part 2: [Second major step]
- Screen recording needed: Yes/No
- Key points to emphasize:
  • 
  • 
  •

Part 3: [Third major step]
- Screen recording needed: Yes/No
- Key points to emphasize:
  • 
  • 
  •

**COMMON MISTAKES (1 minute)**
- Mistake 1: [What people often do wrong]
- Mistake 2: [Another common error]
- Mistake 3: [Frequent misunderstanding]

**SUMMARY (30 seconds)**
- What we accomplished
- Next steps
- Where to get help

**SCRIPT NOTES**
- Avoid jargon terms: [List terms to avoid]
- Emphasize: [Important points]
- Go slowly on: [Complex parts]
```

---

## COMMON ERROR SOLUTIONS

### Error: "Container keeps restarting"

**Symptoms:**
- ECS shows task stopping and starting repeatedly
- Health checks failing
- Application never becomes available

**Common Causes & Solutions:**

1. **Memory Issues**
   ```
   Solution: Increase memory in task definition
   - Current: 512 MB
   - Try: 1024 MB or 2048 MB
   ```

2. **Missing Environment Variables**
   ```
   Check: ECS Task Definition → Environment Variables
   Common missing ones:
   - DATABASE_URL
   - REDIS_URL
   - SECRET_KEY
   ```

3. **Database Connection Failed**
   ```
   Check:
   1. RDS instance is running
   2. Security group allows connection from ECS
   3. Database password is correct in Secrets Manager
   4. Database name exists
   ```

### Error: "Access Denied"

**Symptoms:**
- Can't upload to S3
- Can't read secrets
- Can't write logs

**Common Causes & Solutions:**

1. **IAM Role Missing Permissions**
   ```
   Solution: Add required permissions to task role
   
   For S3:
   - s3:GetObject
   - s3:PutObject
   - s3:ListBucket
   
   For Secrets:
   - secretsmanager:GetSecretValue
   
   For Logs:
   - logs:CreateLogStream
   - logs:PutLogEvents
   ```

2. **Wrong Resource ARN**
   ```
   Check: The exact resource name/path
   Common mistake: Bucket name vs object path
   
   Wrong: arn:aws:s3:::my-bucket
   Right: arn:aws:s3:::my-bucket/*
   ```

### Error: "Health check failed"

**Symptoms:**
- Load balancer shows unhealthy targets
- Application works locally but not on AWS
- 502 Bad Gateway errors

**Common Causes & Solutions:**

1. **Wrong Health Check Path**
   ```
   Check: Load Balancer → Target Groups → Health Check
   Should be: /health or /api/health
   Not: / (unless your app responds there)
   ```

2. **Timeout Too Short**
   ```
   Increase health check settings:
   - Timeout: 30 seconds (was 5)
   - Interval: 60 seconds (was 30)
   - Healthy threshold: 2 (was 5)
   ```

3. **Application Slow to Start**
   ```
   Add startup grace period:
   - ECS Service → Update → Health check grace period: 300 seconds
   ```

### Error: "Database connection refused"

**Symptoms:**
- Can't connect to RDS
- "Connection refused" or "timeout" errors
- Works from local but not from AWS

**Common Causes & Solutions:**

1. **Security Group Issue**
   ```
   Fix: RDS security group must allow:
   - Port: 5432 (PostgreSQL)
   - Source: ECS security group (not IP address)
   ```

2. **Wrong Endpoint**
   ```
   Check: RDS instance → Connectivity → Endpoint
   Format: instance-name.xxxxx.ap-southeast-2.rds.amazonaws.com
   NOT the read replica endpoint
   ```

3. **VPC/Subnet Issue**
   ```
   Ensure:
   - RDS and ECS in same VPC
   - ECS tasks in private subnet with NAT gateway
   - Route tables properly configured
   ```

### Error: "Out of memory"

**Symptoms:**
- Application crashes after running for a while
- "Cannot allocate memory" errors
- Slow performance before crash

**Common Causes & Solutions:**

1. **Memory Leak in Application**
   ```
   Quick fix: Restart containers daily
   - Set up CloudWatch event
   - Restart ECS service at 3 AM
   
   Proper fix: Find and fix memory leak
   ```

2. **Insufficient Memory Allocated**
   ```
   Increase in task definition:
   - Current: 2048 MB
   - Recommended: 4096 MB for production
   ```

3. **Large File Processing**
   ```
   Implement streaming:
   - Don't load entire file into memory
   - Process in chunks
   - Use S3 multipart upload
   ```

---

## GETTING HELP CHECKLIST

### Before Asking for Help:

- [ ] **Check AWS Status Page**
  - https://status.aws.amazon.com/
  - Is the service down?

- [ ] **Search Error Message**
  - Google the EXACT error message
  - Check AWS forums
  - Check Stack Overflow

- [ ] **Review Recent Changes**
  - What changed recently?
  - Check CloudTrail logs
  - Review deployment history

- [ ] **Collect Information**
  - Screenshot errors
  - Copy exact error text
  - Note time of occurrence
  - Check multiple times

- [ ] **Try Basic Fixes**
  - Restart the service
  - Check credentials
  - Verify permissions
  - Review configuration

### Where to Get Help:

1. **AWS Support** (if you have support plan)
   - Use for AWS-specific issues
   - Infrastructure problems
   - Service limits

2. **Stack Overflow**
   - Tag: amazon-web-services
   - Include minimal example
   - Show what you've tried

3. **AWS Forums**
   - https://forums.aws.amazon.com/
   - Search first
   - Be specific

4. **Reddit r/aws**
   - Good for general advice
   - Architecture questions
   - Cost optimization

5. **Local AWS User Groups**
   - Sydney: https://www.meetup.com/aws-sydney/
   - Melbourne: https://www.meetup.com/aws-melbourne/
   - Brisbane: https://www.meetup.com/aws-brisbane/

---

## EMERGENCY COMMUNICATION TEMPLATE

**For critical production issues:**

```
### 🚨 URGENT: Production Issue

**STATUS:** [System Down/Degraded Performance/Data Loss Risk]

**IMPACT:**
- Users affected: [All/Some/Number]
- Features affected: [List features]
- Business impact: [Can't process cases/Can't access documents/etc]

**TIMELINE:**
- Issue started: [Time]
- Discovered: [Time]
- Current time: [Time]

**WHAT'S HAPPENING:**
[Brief description in plain English]

**IMMEDIATE ACTIONS TAKEN:**
1. [What you did first]
2. [What you did second]
3. [Current status]

**HELP NEEDED:**
- [ ] AWS Support case opened: #[number]
- [ ] Need AWS expert immediately
- [ ] Need to restore from backup
- [ ] Need to fail over to disaster recovery

**CONTACT:**
- Primary: [Your phone]
- Secondary: [Backup contact]
- Currently online: [Where you can be reached]

**UPDATES:**
Will update every: 30 minutes
Next update at: [Time]
```

---

## LEARNING RESOURCES

### For Complete Beginners:
1. **AWS Cloud Practitioner Essentials**
   - Free course
   - 6 hours
   - No technical background needed
   - Link: https://aws.amazon.com/training/cloud-practitioner/

2. **AWS for Beginners Videos**
   - YouTube: "AWS with Channy"
   - Start with: "What is Cloud Computing?"
   - Australian presenter

3. **Simple AWS Tutorials**
   - https://aws.amazon.com/getting-started/
   - Hands-on tutorials
   - Step-by-step guides

### For Troubleshooting Skills:
1. **AWS Troubleshooting Guide**
   - https://docs.aws.amazon.com/troubleshooting/
   - Service-specific guides
   - Common issues

2. **CloudWatch Logs Tutorial**
   - Learn to read logs
   - Find errors quickly
   - Set up alerts

3. **AWS Well-Architected Labs**
   - https://wellarchitectedlabs.com/
   - Practical exercises
   - Learn by doing

---

## QUICK REFERENCE: WHAT TO CHECK FIRST

### Application Won't Start
1. Check ECS task logs in CloudWatch
2. Verify environment variables
3. Check task definition memory/CPU
4. Verify IAM role permissions
5. Check security groups

### Can't Access Application
1. Check load balancer target health
2. Verify security group allows HTTPS
3. Check domain name/DNS settings
4. Verify SSL certificate
5. Check WAF rules

### Database Issues
1. Check RDS instance status
2. Verify security groups
3. Check connection string
4. Verify credentials in Secrets Manager
5. Check available storage space

### High Costs
1. Check Cost Explorer
2. Look for unused resources
3. Check data transfer costs
4. Review backup retention
5. Check for forgotten test resources

### Performance Issues
1. Check CloudWatch metrics
2. Review application logs
3. Check database performance insights
4. Verify auto-scaling settings
5. Check for resource limits

---

*Remember: Everyone was a beginner once. Don't hesitate to ask for help, but always try to provide as much relevant information as possible using these templates.*