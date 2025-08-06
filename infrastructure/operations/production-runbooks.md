# LegalLLM Professional Multi-Agent System - Production Runbooks
## Phase 4: Operations Team Documentation

### Table of Contents
1. [System Overview](#system-overview)
2. [Incident Response Procedures](#incident-response-procedures)
3. [Scaling Procedures](#scaling-procedures)
4. [Maintenance Workflows](#maintenance-workflows)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Australian Legal Compliance Operations](#australian-legal-compliance-operations)
8. [Emergency Contacts](#emergency-contacts)

---

## System Overview

### Architecture Summary
- **10-Agent Multi-Agent System** with A2A Protocol communication
- **Unified Interface** serving all user interactions
- **PostgreSQL Cluster** with automatic failover
- **Redis Coordinator & Queue** for agent communication and caching
- **Blue-Green Deployment** strategy for zero-downtime updates
- **Australian Legal Compliance** monitoring and enforcement

### Performance Targets
- **99.9% System Uptime** (8.76 hours downtime/year maximum)
- **A2A Protocol Latency**: <50ms between agents
- **Document Processing**: 500+ documents in <90 seconds
- **Recovery Time Objective (RTO)**: <5 minutes
- **Recovery Point Objective (RPO)**: <1 minute data loss

### Key Services
```
Namespace: legalllm-multiagent

Core Services:
- legalllm-orchestrator-svc (Agent coordination)
- legalllm-unified-interface-svc (User interface)
- postgresql-primary-svc (Database)
- redis-coordinator-svc (Agent coordination)
- redis-queue-svc (Message queuing)

Monitoring Services:  
- prometheus-svc (Metrics collection)
- grafana-svc (Monitoring dashboards)
- alertmanager-svc (Alert routing)
```

---

## Incident Response Procedures

### Incident Classification

#### Severity 1 - Critical (Response: Immediate)
- Complete system outage
- Data breach or security incident
- Australian legal compliance violation
- A2A Protocol latency >200ms sustained
- Document processing failure affecting >50% of requests

#### Severity 2 - High (Response: <15 minutes)
- Single service degradation
- Performance degradation affecting users
- Backup failure
- A2A Protocol latency 50-200ms sustained
- Minor compliance alerts

#### Severity 3 - Medium (Response: <1 hour)
- Non-critical service issues
- Monitoring alerts
- Capacity warnings
- Performance optimization needed

#### Severity 4 - Low (Response: <4 hours)
- Documentation updates needed
- Non-urgent improvements
- Scheduled maintenance planning

### Incident Response Workflow

#### 1. Detection and Alerting
```bash
# Check system status
kubectl get pods -n legalllm-multiagent
kubectl get services -n legalllm-multiagent

# Check monitoring dashboards
# Navigate to: https://monitoring.legalllm.com.au/grafana
# Default login: admin / [see secrets]

# Check alert status
curl -s http://alertmanager:9093/api/v1/alerts | jq '.'
```

#### 2. Initial Assessment
```bash
# Quick health check script
python scripts/emergency_health_check.py

# Check resource utilization
kubectl top pods -n legalllm-multiagent
kubectl top nodes

# Check recent events
kubectl get events -n legalllm-multiagent --sort-by='.lastTimestamp'
```

#### 3. Escalation Process
1. **On-Call Engineer** (0-15 minutes)
   - Initial assessment and immediate response
   - Execute automatic remediation if available
   - Escalate if not resolved within 15 minutes

2. **Senior DevOps Engineer** (15-30 minutes)
   - Advanced troubleshooting
   - Manual intervention and system recovery
   - Coordinate with development team if needed

3. **Technical Lead** (30-60 minutes)
   - Strategic decision making
   - Approve emergency procedures
   - Coordinate major incident response

4. **Legal Technology Director** (60+ minutes)
   - Executive oversight
   - Client communication authorization
   - Legal compliance review

#### 4. Communication Templates

**Slack Incident Alert:**
```
🚨 INCIDENT ALERT - SEV[1-4]
Service: [Service Name]
Issue: [Brief Description]
Impact: [User Impact Description]
Status: INVESTIGATING
Assigned: @[engineer]
Time: [Timestamp]
Incident ID: INC-YYYY-MMDD-HHMMSS
```

**Client Communication Template:**
```
Subject: LegalLLM Service Update - [Date/Time]

Dear [Client/Practice Name],

We are currently experiencing [brief description] with our LegalLLM 
Professional service. 

Impact: [Specific impact on their usage]
Expected Resolution: [Timeline]
Current Status: [What we're doing]

We will provide updates every [frequency] until resolved.

Australian legal compliance and data security remain fully maintained.

For urgent matters, please contact: [emergency contact]

LegalLLM Operations Team
```

---

## Scaling Procedures

### Horizontal Pod Autoscaling (HPA)

#### Monitor Current Scaling Status
```bash
# Check HPA status
kubectl get hpa -n legalllm-multiagent

# View detailed HPA metrics
kubectl describe hpa legalllm-orchestrator-hpa -n legalllm-multiagent
kubectl describe hpa legalllm-unified-interface-hpa -n legalllm-multiagent
```

#### Manual Scaling Procedures

**Scale Unified Interface:**
```bash
# Scale up for high user load
kubectl scale deployment legalllm-unified-interface \
  --replicas=10 -n legalllm-multiagent

# Monitor scaling progress
kubectl rollout status deployment/legalllm-unified-interface \
  -n legalllm-multiagent --timeout=300s
```

**Scale Agent Services:**
```bash
# Scale financial agent for heavy Form 13 processing
kubectl scale deployment legalllm-financial-agent \
  --replicas=8 -n legalllm-multiagent

# Scale document agent for bulk document processing
kubectl scale deployment legalllm-document-agent \
  --replicas=12 -n legalllm-multiagent

# Scale cross-examination agent for trial preparation
kubectl scale deployment legalllm-crossexam-agent \
  --replicas=6 -n legalllm-multiagent
```

**Scale Database (PostgreSQL):**
```bash
# Scale read replicas (read-only queries)
kubectl patch postgresql postgresql-cluster \
  --type='merge' \
  -p='{"spec":{"instances":5}}' -n legalllm-multiagent

# Monitor scaling
kubectl get postgresql -n legalllm-multiagent -w
```

#### Cluster Scaling (Node Management)

**Add Nodes to Cluster:**
```bash
# Check current node capacity
kubectl get nodes
kubectl describe nodes

# Check cluster autoscaler status
kubectl get pods -n kube-system | grep cluster-autoscaler

# Manually trigger node scaling (if autoscaler disabled)
aws eks update-nodegroup \
  --cluster-name legalllm-production \
  --nodegroup-name worker-nodes \
  --scaling-config minSize=3,maxSize=20,desiredSize=8
```

#### Load Testing and Validation

**Pre-Scaling Load Test:**
```bash
# Test current capacity
python scripts/load_test.py \
  --concurrent-users 50 \
  --duration 300 \
  --ramp-up 30

# Monitor during load test
watch kubectl top pods -n legalllm-multiagent
```

**Post-Scaling Validation:**
```bash
# Validate A2A Protocol performance
python scripts/validate_a2a_latency.py --target-ms 50

# Validate document processing performance
python scripts/validate_document_processing.py \
  --target-docs 500 --target-time 90

# End-to-end workflow test
pytest tests/e2e/test_complete_user_workflows.py -v
```

---

## Maintenance Workflows

### Scheduled Maintenance Windows

**Monthly Maintenance (First Sunday 2-4 AM AEST):**
- Database maintenance and optimization
- Security patches application
- Performance optimization
- Backup validation

**Quarterly Maintenance (First Sunday 1-5 AM AEST):**
- Major version updates
- Infrastructure improvements
- Comprehensive security audit
- Disaster recovery testing

### Pre-Maintenance Checklist

```bash
# 1. Create maintenance announcement
python scripts/create_maintenance_announcement.py \
  --start "2024-01-07 02:00 AEST" \
  --duration 120 \
  --description "Monthly database optimization"

# 2. Backup current state
kubectl create job manual-backup-$(date +%s) \
  --from=cronjob/postgresql-backup -n legalllm-multiagent

# 3. Scale down non-essential services
kubectl scale deployment legalllm-document-agent --replicas=2 -n legalllm-multiagent
kubectl scale deployment legalllm-crossexam-agent --replicas=1 -n legalllm-multiagent

# 4. Verify monitoring is active
curl -s http://alertmanager:9093/api/v1/status | jq '.data.uptime'
```

### Database Maintenance

**Monthly Database Optimization:**
```sql
-- Connect to primary database
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- psql -U postgres legalllm_multiagent

-- Analyze and vacuum
ANALYZE;
VACUUM (ANALYZE, VERBOSE);

-- Reindex critical tables
REINDEX TABLE cases;
REINDEX TABLE documents;
REINDEX TABLE compliance_violations;

-- Update statistics
SELECT schemaname, tablename, last_analyze, last_autoanalyze 
FROM pg_stat_user_tables;
```

**Database Health Check:**
```bash
# Check database performance metrics
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres -c "
    SELECT 
      schemaname,
      tablename,
      n_tup_ins as inserts,
      n_tup_upd as updates,
      n_tup_del as deletes,
      n_live_tup as live_tuples,
      n_dead_tup as dead_tuples
    FROM pg_stat_user_tables 
    ORDER BY n_live_tup DESC;"

# Check connection health
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

### Application Updates

**Blue-Green Deployment Process:**
```bash
# 1. Determine current active slot
CURRENT_SLOT=$(kubectl get service legalllm-unified-interface-svc \
  -n legalllm-multiagent -o jsonpath='{.spec.selector.deployment-slot}')

# 2. Set target slot
if [ "$CURRENT_SLOT" = "blue" ]; then
  TARGET_SLOT="green"
else  
  TARGET_SLOT="blue"
fi

echo "Deploying to $TARGET_SLOT (current: $CURRENT_SLOT)"

# 3. Deploy to target slot
kubectl apply -f kubernetes/multiagent-unified-interface.yaml -n legalllm-multiagent
kubectl apply -f kubernetes/multiagent-orchestrator.yaml -n legalllm-multiagent
kubectl apply -f kubernetes/multiagent-agents.yaml -n legalllm-multiagent

# 4. Wait for deployment ready
kubectl rollout status deployment/legalllm-unified-interface-$TARGET_SLOT \
  -n legalllm-multiagent --timeout=600s

# 5. Run validation tests
python scripts/deployment_validation.py --slot $TARGET_SLOT

# 6. Switch traffic (if validation passes)
kubectl patch service legalllm-unified-interface-svc -n legalllm-multiagent \
  -p '{"spec":{"selector":{"deployment-slot":"'$TARGET_SLOT'"}}}'

echo "Traffic switched to $TARGET_SLOT"
```

---

## Monitoring and Alerting

### Dashboard Access

**Primary Monitoring Dashboard:**
- URL: https://monitoring.legalllm.com.au/grafana
- Credentials: Stored in `monitoring-credentials` secret

**Key Dashboards:**
1. **Multi-Agent System Overview** - Overall system health
2. **A2A Protocol Performance** - Inter-agent communication metrics
3. **Document Processing Pipeline** - Document workflow performance
4. **Australian Legal Compliance** - Compliance monitoring
5. **Infrastructure Health** - Kubernetes cluster metrics

### Critical Alert Definitions

**System Down (Severity 1):**
```yaml
Alert: SystemDown
Expression: up{job="legalllm-unified-interface"} == 0
Duration: 30s
Action: Immediate page to on-call
```

**A2A Latency Violation (Severity 2):**
```yaml
Alert: A2ALatencyHigh  
Expression: a2a_protocol_latency_ms > 50
Duration: 2m
Action: Slack notification + email
```

**Document Processing SLA Breach (Severity 2):**
```yaml
Alert: DocumentProcessingSLABreach
Expression: document_processing_time_seconds > 90 AND document_batch_size >= 500
Duration: 1m
Action: Slack notification + escalation
```

**Australian Legal Compliance Violation (Severity 1):**
```yaml
Alert: AustralianLegalViolation
Expression: australian_legal_violations_total > 0
Duration: 0s
Action: Immediate page + legal team notification
```

### Monitoring Commands

**Real-time System Status:**
```bash
# Quick health overview
kubectl get pods -n legalllm-multiagent | grep -v Running

# Check resource usage
kubectl top pods -n legalllm-multiagent --sort-by=cpu
kubectl top pods -n legalllm-multiagent --sort-by=memory

# View recent logs
kubectl logs -f deployment/legalllm-orchestrator -n legalllm-multiagent --tail=100
```

**Performance Metrics:**
```bash
# A2A Protocol latency check
curl -s http://prometheus:9090/api/v1/query?query=a2a_protocol_latency_ms | jq '.data.result'

# Document processing metrics
curl -s http://prometheus:9090/api/v1/query?query=document_processing_time_seconds | jq '.data.result'

# System availability
curl -s http://prometheus:9090/api/v1/query?query=up | jq '.data.result'
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: High A2A Protocol Latency (>50ms)

**Symptoms:**
- Slow agent responses
- User interface delays
- Performance alerts

**Diagnosis:**
```bash
# Check Redis coordinator health
kubectl exec -it redis-coordinator-0 -n legalllm-multiagent -- redis-cli ping

# Check network latency between pods
kubectl exec -it legalllm-orchestrator-xxx -n legalllm-multiagent -- \
  ping redis-coordinator-svc

# Check Redis coordinator load
kubectl exec -it redis-coordinator-0 -n legalllm-multiagent -- \
  redis-cli --latency-history -i 1
```

**Resolution:**
```bash
# Scale Redis coordinator
kubectl scale statefulset redis-coordinator --replicas=3 -n legalllm-multiagent

# Restart slow agents
kubectl rollout restart deployment/legalllm-financial-agent -n legalllm-multiagent

# Clear Redis cache if corrupted
kubectl exec -it redis-coordinator-0 -n legalllm-multiagent -- redis-cli flushdb
```

#### Issue: Document Processing Timeout

**Symptoms:**
- Documents not processed within 90 seconds
- 500+ document batch failures
- User complaints about slow processing

**Diagnosis:**
```bash
# Check document agent status
kubectl get pods -l app=legalllm-document-agent -n legalllm-multiagent

# Check processing queue
kubectl exec -it redis-queue-0 -n legalllm-multiagent -- \
  redis-cli llen document_processing_queue

# Check resource limits
kubectl describe pod legalllm-document-agent-xxx -n legalllm-multiagent
```

**Resolution:**
```bash
# Scale document agents
kubectl scale deployment legalllm-document-agent --replicas=8 -n legalllm-multiagent

# Increase resource limits
kubectl patch deployment legalllm-document-agent -n legalllm-multiagent \
  -p='{"spec":{"template":{"spec":{"containers":[{"name":"document-agent","resources":{"limits":{"memory":"4Gi","cpu":"2000m"}}}]}}}}'

# Clear stuck processing jobs
kubectl exec -it redis-queue-0 -n legalllm-multiagent -- \
  redis-cli del document_processing_queue
```

#### Issue: Database Connection Issues

**Symptoms:**
- Connection timeouts
- Database queries failing
- High connection count

**Diagnosis:**
```bash
# Check PostgreSQL status
kubectl get postgresql -n legalllm-multiagent

# Check connection count
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Check for locks
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

**Resolution:**
```bash
# Restart connection pooler
kubectl rollout restart deployment/pgbouncer -n legalllm-multiagent

# Kill long-running queries
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';"

# Scale read replicas
kubectl patch postgresql postgresql-cluster -n legalllm-multiagent \
  --type='merge' -p='{"spec":{"instances":5}}'
```

### Emergency Procedures

#### Complete System Recovery

**Scenario: All services down**
```bash
# 1. Check cluster health
kubectl get nodes
kubectl get pods --all-namespaces

# 2. Restart core services in order
kubectl apply -f kubernetes/multiagent-namespace.yaml
kubectl apply -f kubernetes/postgresql-cluster.yaml -n legalllm-multiagent
kubectl apply -f kubernetes/redis-cluster.yaml -n legalllm-multiagent

# Wait for database ready
kubectl wait --for=condition=Ready pod/postgresql-primary-0 -n legalllm-multiagent --timeout=300s

# 3. Restart application services
kubectl apply -f kubernetes/multiagent-orchestrator.yaml -n legalllm-multiagent
kubectl apply -f kubernetes/multiagent-agents.yaml -n legalllm-multiagent  
kubectl apply -f kubernetes/multiagent-unified-interface.yaml -n legalllm-multiagent

# 4. Validate recovery
python scripts/emergency_recovery_validation.py
```

#### Disaster Recovery Activation

**Scenario: Regional failure**
```bash
# 1. Switch to disaster recovery region
export AWS_REGION=ap-southeast-2
kubectl config use-context sydney-dr-cluster

# 2. Restore from backup
kubectl create job disaster-recovery-$(date +%s) \
  --from=cronjob/postgresql-disaster-restore -n legalllm-multiagent

# 3. Deploy application stack
./scripts/dr-deploy.sh --region sydney --priority emergency

# 4. Update DNS for failover
./scripts/dns-failover.sh --target-region sydney

# 5. Notify stakeholders
python scripts/send_dr_notification.py --region sydney
```

---

## Australian Legal Compliance Operations

### Compliance Monitoring

**Daily Compliance Check:**
```bash
# Run comprehensive compliance validation
python scripts/daily_compliance_check.py

# Check for privacy violations
kubectl logs -l app=australian-legal-compliance-monitor -n legalllm-multiagent | grep VIOLATION

# Review compliance dashboard
curl -s http://compliance-monitor:8080/api/compliance/dashboard | jq '.'
```

**Privacy Act 1988 Compliance:**
```bash
# Check consent management
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres legalllm_multiagent -c "
    SELECT consent_type, COUNT(*) as total, 
           COUNT(*) FILTER (WHERE withdrawn_at IS NULL) as active
    FROM privacy_consents 
    GROUP BY consent_type;"

# Check data retention compliance
python scripts/check_data_retention_compliance.py
```

**Family Law Act 1975 Compliance:**
```bash
# Validate Form 13 processing
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres legalllm_multiagent -c "
    SELECT case_type, COUNT(*) as cases,
           AVG(CASE WHEN form13_data IS NOT NULL THEN 1 ELSE 0 END) as form13_completion_rate
    FROM cases 
    WHERE case_type = 'property_settlement'
    GROUP BY case_type;"

# Check financial analysis compliance
python scripts/validate_financial_compliance.py
```

### Audit Logging

**Access Audit Logs:**
```bash
# View compliance audit logs
kubectl logs -l app=filebeat -n legalllm-multiagent | grep compliance

# Search specific compliance events
kubectl exec -it elasticsearch-0 -n legalllm-multiagent -- \
  curl -X GET "localhost:9200/legalllm-compliance-*/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"match":{"compliance_framework":"family_law_act_1975"}}}'
```

**Generate Compliance Reports:**
```bash
# Monthly compliance report
python scripts/generate_monthly_compliance_report.py \
  --month $(date +%Y-%m) \
  --output /tmp/compliance_report_$(date +%Y%m).pdf

# Upload to compliance storage
aws s3 cp /tmp/compliance_report_$(date +%Y%m).pdf \
  s3://legalllm-compliance-reports/monthly/ \
  --server-side-encryption AES256
```

---

## Emergency Contacts

### On-Call Rotation
- **Primary On-Call**: DevOps Engineer
  - Phone: +61 4XX XXX XXX
  - Slack: @devops-oncall
  - Escalation: 15 minutes

- **Secondary On-Call**: Senior DevOps Engineer  
  - Phone: +61 4XX XXX XXX
  - Slack: @senior-devops
  - Escalation: 30 minutes

### Escalation Contacts
- **Technical Lead**: +61 4XX XXX XXX
- **Legal Compliance Officer**: +61 4XX XXX XXX  
- **Legal Technology Director**: +61 4XX XXX XXX
- **AWS Enterprise Support**: Case via console

### External Contacts
- **Australian Privacy Commissioner**: 1300 363 992
- **Law Institute of Victoria**: (03) 9607 9311
- **NSW Law Society**: (02) 9926 0333

### Communication Channels
- **Incident Response**: #legalllm-incidents
- **Deployments**: #legalllm-deployments  
- **Compliance**: #legalllm-compliance
- **General Operations**: #legalllm-ops

### Status Pages
- **Internal Status**: https://status-internal.legalllm.com.au
- **Client Status**: https://status.legalllm.com.au
- **Monitoring**: https://monitoring.legalllm.com.au

---

## Quick Reference Commands

### Emergency Commands
```bash
# Emergency system shutdown
kubectl scale deployment --all --replicas=0 -n legalllm-multiagent

# Emergency system startup
kubectl apply -f kubernetes/ -n legalllm-multiagent

# Quick health check
kubectl get pods -n legalllm-multiagent | grep -v Running | wc -l

# View all alerts
curl -s http://alertmanager:9093/api/v1/alerts | jq '.data[].labels.alertname'

# Emergency log aggregation
kubectl logs --all-containers=true --selector app.kubernetes.io/name=legalllm-professional -n legalllm-multiagent --tail=1000 > emergency_logs_$(date +%s).txt
```

### Performance Validation
```bash
# A2A latency test
python scripts/validate_a2a_latency.py --target-ms 50

# Document processing test  
python scripts/validate_document_processing.py --target-docs 500 --target-time 90

# End-to-end test
pytest tests/e2e/test_complete_user_workflows.py -v --tb=short

# Load test
python scripts/load_test.py --concurrent-users 100 --duration 300
```

---

**Document Version**: v2.0.0  
**Last Updated**: 2024-01-07  
**Next Review**: 2024-04-07  
**Document Owner**: DevOps Team  
**Approved By**: Legal Technology Director