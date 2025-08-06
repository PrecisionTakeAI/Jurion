# AWS Cost Calculator for LegalLLM Professional

**Sydney Region (ap-southeast-2) Pricing - January 2025**  
**All prices in AUD including GST**

---

## QUICK COST ESTIMATE

### Small Firm (1-5 lawyers)
- **Monthly Cost:** $350-500
- **Annual Cost:** $4,200-6,000

### Medium Firm (6-20 lawyers)
- **Monthly Cost:** $800-1,500
- **Annual Cost:** $9,600-18,000

### Large Firm (21-50 lawyers)
- **Monthly Cost:** $2,000-3,500
- **Annual Cost:** $24,000-42,000

---

## DETAILED SERVICE PRICING

### 1. Compute (ECS Fargate)

**Container Costs:**
- vCPU: $0.05740 per vCPU per hour
- Memory: $0.00628 per GB per hour

**Typical Configuration:**
```
Small Firm (2 containers):
- 2 vCPU, 4GB RAM each
- Cost: 2 × (2 × $0.05740 + 4 × $0.00628) × 730 hours
- Monthly: $202.68

Medium Firm (4 containers):
- 2 vCPU, 8GB RAM each
- Cost: 4 × (2 × $0.05740 + 8 × $0.00628) × 730 hours
- Monthly: $481.78

Large Firm (8 containers):
- 4 vCPU, 16GB RAM each
- Cost: 8 × (4 × $0.05740 + 16 × $0.00628) × 730 hours
- Monthly: $1,926.72
```

### 2. Database (RDS PostgreSQL)

**Instance Pricing:**
```
db.t3.medium (2 vCPU, 4GB RAM):
- On-Demand: $0.113 per hour
- Monthly: $82.49

db.t3.large (2 vCPU, 8GB RAM):
- On-Demand: $0.226 per hour
- Monthly: $164.98

db.m5.xlarge (4 vCPU, 16GB RAM):
- On-Demand: $0.407 per hour
- Monthly: $297.11
```

**Storage Pricing:**
- General Purpose SSD (gp3): $0.138 per GB per month
- Provisioned IOPS: $0.138 per IOPS per month
- Backup storage: $0.116 per GB per month

**Typical Database Costs:**
```
Small Firm:
- db.t3.medium + 100GB storage + 50GB backups
- Monthly: $82.49 + $13.80 + $5.80 = $102.09

Medium Firm:
- db.t3.large + 500GB storage + 250GB backups
- Monthly: $164.98 + $69.00 + $29.00 = $262.98

Large Firm:
- db.m5.xlarge + 1TB storage + 500GB backups
- Monthly: $297.11 + $141.31 + $58.00 = $496.42
```

### 3. Storage (S3)

**Storage Classes:**
- Standard: $0.025 per GB per month
- Infrequent Access: $0.0138 per GB per month
- Glacier Instant: $0.005 per GB per month

**Request Pricing:**
- PUT/COPY/POST: $0.0055 per 1,000 requests
- GET: $0.00044 per 1,000 requests

**Data Transfer:**
- To Internet: $0.114 per GB (first 10TB)
- Between regions: $0.02 per GB
- Within region: Free

**Typical S3 Costs:**
```
Small Firm (100GB docs, 10GB monthly upload):
- Storage: 100GB × $0.025 = $2.50
- Upload: 10GB × $0.114 = $1.14
- Requests: ~$2.00
- Monthly: $5.64

Medium Firm (1TB docs, 100GB monthly upload):
- Storage: 1000GB × $0.025 = $25.00
- Upload: 100GB × $0.114 = $11.40
- Requests: ~$10.00
- Monthly: $46.40

Large Firm (5TB docs, 500GB monthly upload):
- Storage: 5000GB × $0.025 = $125.00
- Upload: 500GB × $0.114 = $57.00
- Requests: ~$25.00
- Monthly: $207.00
```

### 4. Load Balancer (ALB)

**Pricing:**
- ALB hour: $0.0315 per hour
- LCU hour: $0.0105 per LCU hour

**LCU Dimensions:**
- New connections: 25 per second
- Active connections: 3,000 per minute
- Processed bytes: 1 GB per hour
- Rule evaluations: 1,000 per second

**Typical ALB Costs:**
```
All Firms:
- Base: $0.0315 × 730 = $23.00
- LCUs: ~10 LCUs × $0.0105 × 730 = $76.65
- Monthly: $99.65
```

### 5. Data Transfer

**Pricing Structure:**
- First 10GB/month: Free
- Up to 10TB/month: $0.114 per GB
- Next 40TB/month: $0.098 per GB

**Typical Transfer Costs:**
```
Small Firm (50GB/month out):
- First 10GB: Free
- Next 40GB: 40 × $0.114 = $4.56
- Monthly: $4.56

Medium Firm (200GB/month out):
- First 10GB: Free
- Next 190GB: 190 × $0.114 = $21.66
- Monthly: $21.66

Large Firm (1TB/month out):
- First 10GB: Free
- Next 990GB: 990 × $0.114 = $112.86
- Monthly: $112.86
```

### 6. Additional Services

**CloudWatch (Monitoring):**
- Metrics: $0.38 per metric per month
- Logs: $0.76 per GB ingested
- Dashboards: $3.80 per dashboard per month

**Secrets Manager:**
- Secret: $0.50 per secret per month
- API calls: $0.065 per 10,000 API calls

**WAF (Web Application Firewall):**
- Web ACL: $6.30 per month
- Rule: $1.26 per rule per month
- Requests: $0.74 per million requests

**Backup:**
- EFS backup: $0.065 per GB per month
- RDS backup: Included (up to DB size)
- Additional: $0.116 per GB per month

---

## COST CALCULATION WORKSHEET

### Your Firm Size: _____________

**1. Compute (ECS)**
- Number of containers: _____ × $_____ = $_____
- Container size: [ ] Small [ ] Medium [ ] Large

**2. Database (RDS)**
- Instance type: _____________ = $_____
- Storage size: _____ GB × $0.138 = $_____
- Backup size: _____ GB × $0.116 = $_____
- Subtotal: $_____

**3. Storage (S3)**
- Document storage: _____ GB × $0.025 = $_____
- Monthly uploads: _____ GB × $0.114 = $_____
- Requests estimate: $_____
- Subtotal: $_____

**4. Load Balancer**
- Fixed cost: $99.65

**5. Data Transfer**
- Monthly outbound: _____ GB
- Transfer cost: $_____

**6. Monitoring & Security**
- CloudWatch: $50 (estimate)
- Secrets Manager: $5 (10 secrets)
- WAF: $15 (basic rules)
- Subtotal: $70

**MONTHLY TOTAL: $_____**
**ANNUAL TOTAL: $_____ × 12 = $_____**

---

## COST OPTIMIZATION TIPS

### 1. Use Reserved Instances (Save 30-50%)
```
1-year term: ~30% discount
3-year term: ~50% discount

Example: db.t3.large
- On-Demand: $164.98/month
- 1-year Reserved: $115.49/month (30% savings)
- 3-year Reserved: $82.49/month (50% savings)
```

### 2. Use Spot Instances for Non-Critical Workloads
- Up to 90% discount
- Good for batch processing
- Not recommended for production web servers

### 3. Implement Auto-Scaling
```python
# Scale down during off-hours
Business hours (7am-7pm): 4 containers
After hours: 2 containers
Savings: ~40% on compute costs
```

### 4. S3 Lifecycle Policies
```
Documents > 90 days: Move to Infrequent Access (save 45%)
Documents > 180 days: Move to Glacier (save 80%)
```

### 5. Data Transfer Optimization
- Use CloudFront CDN for static assets
- Compress data before transfer
- Batch API calls

---

## HIDDEN COSTS TO WATCH

1. **NAT Gateway**
   - $0.059 per hour = $43.07/month
   - $0.059 per GB processed
   - Alternative: Use NAT instance (cheaper but less reliable)

2. **Elastic IPs**
   - Free when attached to running instance
   - $0.005 per hour when not attached = $3.65/month

3. **Snapshots**
   - $0.065 per GB per month
   - Accumulate over time
   - Set retention policies

4. **CloudTrail**
   - First trail free
   - Additional: $2.30 per 100,000 events

5. **Support Plans**
   - Business Support: $150/month minimum
   - Can be 3-10% of total AWS bill

---

## EXAMPLE DETAILED CALCULATIONS

### Small Law Firm (3 lawyers, 2 paralegals)
```
Compute (ECS):
- 2 containers (1 vCPU, 2GB each)
- 2 × (1 × $0.05740 + 2 × $0.00628) × 730 = $102.12

Database (RDS):
- db.t3.small (2 vCPU, 2GB)
- Instance: $41.24
- 50GB storage: $6.90
- 25GB backups: $2.90
- Subtotal: $51.04

Storage (S3):
- 50GB documents: $1.25
- 5GB monthly upload: $0.57
- Requests: $1.00
- Subtotal: $2.82

Load Balancer: $99.65
Data Transfer (25GB): $1.71
Monitoring/Security: $70.00

MONTHLY TOTAL: $327.34
ANNUAL TOTAL: $3,928.08
```

### Medium Law Firm (15 lawyers, 10 support staff)
```
Compute (ECS):
- 4 containers (2 vCPU, 4GB each)
- 4 × (2 × $0.05740 + 4 × $0.00628) × 730 = $408.48

Database (RDS):
- db.t3.large (2 vCPU, 8GB)
- Instance: $164.98
- 250GB storage: $34.50
- 125GB backups: $14.50
- Subtotal: $213.98

Storage (S3):
- 500GB documents: $12.50
- 50GB monthly upload: $5.70
- Requests: $5.00
- Subtotal: $23.20

Load Balancer: $99.65
Data Transfer (150GB): $15.96
Monitoring/Security: $100.00

MONTHLY TOTAL: $861.27
ANNUAL TOTAL: $10,335.24
```

---

## BILLING ALERTS SETUP

**Set these alerts in AWS Billing Console:**

1. **50% of expected budget**
   - Alert when bill reaches $_____

2. **100% of expected budget**
   - Alert when bill reaches $_____

3. **Anomaly detection**
   - Alert on 20% increase from normal

4. **Service-specific alerts**
   - RDS: > $_____
   - ECS: > $_____
   - S3: > $_____

---

## ROI CALCULATION

**Cost Savings from LegalLLM:**
- Manual document review: 10 hours/week saved
- At $200/hour: $2,000/week = $8,000/month
- AWS costs: -$861/month (medium firm)
- **Net savings: $7,139/month**

**Break-even Timeline:**
- Initial setup cost: ~$5,000
- Monthly savings: $7,139
- **Break-even: < 1 month**

---

*Note: All prices are estimates based on AWS Sydney region pricing as of January 2025. Actual costs may vary based on usage patterns. Always check current AWS pricing at https://aws.amazon.com/pricing/*