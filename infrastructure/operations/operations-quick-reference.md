# LegalLLM Professional - Operations Quick Reference
## Phase 4: Emergency Response Cards and Command Cheatsheet

---

## 🚨 Emergency Response Cards

### Card 1: System Down - Complete Outage
```bash
# IMMEDIATE ACTIONS (0-5 minutes)
1. Acknowledge incident: slack #legalllm-incidents
2. Check cluster status:
   kubectl get nodes
   kubectl get pods -n legalllm-multiagent

3. Run emergency recovery:
   kubectl create job emergency-recovery-$(date +%s) \
     --from=job/emergency-response-template -n legalllm-multiagent

4. Notify stakeholders:
   - Update status page: https://status.legalllm.com.au
   - Page on-call engineer
   - Alert legal compliance team

5. Monitor recovery:
   kubectl logs -f job/emergency-recovery-* -n legalllm-multiagent
```

### Card 2: A2A Protocol Latency High (>50ms)
```bash
# DIAGNOSIS (0-2 minutes)
kubectl exec -it redis-coordinator-0 -n legalllm-multiagent -- redis-cli ping
kubectl top pods -n legalllm-multiagent --sort-by=cpu

# REMEDIATION (2-10 minutes)  
kubectl scale deployment legalllm-orchestrator --replicas=5 -n legalllm-multiagent
kubectl scale statefulset redis-coordinator --replicas=3 -n legalllm-multiagent

# VALIDATION (10-15 minutes)
python scripts/validate_a2a_latency.py --target-ms 50
```

### Card 3: Document Processing Timeout
```bash
# DIAGNOSIS
kubectl get pods -l app=legalllm-document-agent -n legalllm-multiagent
kubectl exec -it redis-queue-0 -n legalllm-multiagent -- \
  redis-cli llen document_processing_queue

# REMEDIATION
kubectl scale deployment legalllm-document-agent --replicas=10 -n legalllm-multiagent
kubectl exec -it redis-queue-0 -n legalllm-multiagent -- \
  redis-cli del document_processing_queue

# VALIDATION
python scripts/validate_document_processing.py --target-docs 500 --target-time 90
```

### Card 4: Australian Legal Compliance Violation
```bash
# IMMEDIATE ACTIONS (0-1 minute)
1. Run compliance emergency procedure:
   /scripts/emergency-remediation-scripts.sh legal-compliance

2. Preserve audit logs:
   kubectl logs --all-containers=true \
     --selector app.kubernetes.io/name=legalllm-professional \
     -n legalllm-multiagent --tail=10000 > compliance_audit_$(date +%s).log

3. Notify legal team immediately:
   - Phone: +61 4XX XXX XXX (Legal Compliance Officer)
   - Email: legal-compliance@company.com
   - Slack: @legal-compliance-team

4. Review compliance dashboard:
   https://monitoring.legalllm.com.au/d/compliance/australian-legal-compliance
```

### Card 5: Database Connection Issues
```bash
# DIAGNOSIS
kubectl get postgresql -n legalllm-multiagent
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# REMEDIATION
kubectl rollout restart deployment/pgbouncer -n legalllm-multiagent
kubectl patch postgresql postgresql-cluster -n legalllm-multiagent \
  --type='merge' -p='{"spec":{"instances":5}}'

# EMERGENCY: Kill long-running queries
kubectl exec -it postgresql-primary-0 -n legalllm-multiagent -- \
  psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';"
```

---

## 📋 Command Cheatsheet

### System Status Commands
```bash
# Overall system health
kubectl get pods -n legalllm-multiagent | grep -v Running
kubectl get services -n legalllm-multiagent
kubectl top pods -n legalllm-multiagent

# Check alerts
curl -s http://alertmanager:9093/api/v1/alerts | jq '.data[].labels.alertname'

# Performance metrics
curl -s http://prometheus:9090/api/v1/query?query=a2a_protocol_latency_ms | jq '.data.result'
curl -s http://prometheus:9090/api/v1/query?query=document_processing_time_seconds | jq '.data.result'

# Quick health validation
python scripts/emergency_health_check.py
```

### Scaling Commands
```bash
# Emergency scale up critical services
kubectl scale deployment legalllm-orchestrator --replicas=5 -n legalllm-multiagent
kubectl scale deployment legalllm-unified-interface --replicas=8 -n legalllm-multiagent
kubectl scale deployment legalllm-financial-agent --replicas=6 -n legalllm-multiagent
kubectl scale deployment legalllm-document-agent --replicas=10 -n legalllm-multiagent

# Check HPA status
kubectl get hpa -n legalllm-multiagent
kubectl describe hpa legalllm-orchestrator-hpa -n legalllm-multiagent

# Scale database read replicas
kubectl patch postgresql postgresql-cluster -n legalllm-multiagent \
  --type='merge' -p='{"spec":{"instances":5}}'
```

### Log and Debug Commands
```bash
# View recent logs
kubectl logs -f deployment/legalllm-orchestrator -n legalllm-multiagent --tail=100
kubectl logs -f deployment/legalllm-unified-interface -n legalllm-multiagent --tail=100

# Get all logs for incident
kubectl logs --all-containers=true \
  --selector app.kubernetes.io/name=legalllm-professional \
  -n legalllm-multiagent --since=1h > incident_logs_$(date +%s).txt

# Check events
kubectl get events -n legalllm-multiagent --sort-by='.lastTimestamp' | tail -20

# Debug pod issues
kubectl describe pod <pod-name> -n legalllm-multiagent
kubectl exec -it <pod-name> -n legalllm-multiagent -- /bin/bash
```

### Backup and Recovery Commands
```bash
# Manual backup
kubectl create job manual-backup-$(date +%s) \
  --from=cronjob/postgresql-backup -n legalllm-multiagent

# Check backup status
kubectl get cronjobs -n legalllm-multiagent | grep backup
kubectl get jobs -n legalllm-multiagent | grep backup

# Disaster recovery
kubectl create job disaster-recovery-$(date +%s) \
  --from=cronjob/postgresql-disaster-restore -n legalllm-multiagent

# Switch to DR cluster
kubectl config use-context sydney-dr-cluster
./scripts/dr-deploy.sh --region sydney --priority emergency
```

### Compliance and Audit Commands
```bash
# Check compliance status
python scripts/daily_compliance_check.py
curl -s http://compliance-monitor:8080/api/compliance/dashboard | jq '.'

# Australian legal compliance validation
python scripts/validate_family_law_compliance.py
python scripts/validate_privacy_act_compliance.py

# Generate compliance report
python scripts/generate_monthly_compliance_report.py \
  --month $(date +%Y-%m) --output /tmp/compliance_report.pdf

# Check audit logs
kubectl logs -l app=filebeat -n legalllm-multiagent | grep compliance
```

---

## 🎯 Performance Targets Quick Reference

### Critical SLAs
- **System Uptime**: 99.9% (≤8.76 hours downtime/year)
- **A2A Protocol Latency**: <50ms average
- **Document Processing**: 500+ docs in <90 seconds
- **Recovery Time Objective (RTO)**: <5 minutes
- **Recovery Point Objective (RPO)**: <1 minute data loss

### Performance Validation Commands
```bash
# A2A Protocol latency test
python scripts/validate_a2a_latency.py --target-ms 50

# Document processing performance test  
python scripts/validate_document_processing.py \
  --target-docs 500 --target-time 90

# End-to-end user workflow test
pytest tests/e2e/test_complete_user_workflows.py -v

# Load testing
python scripts/load_test.py --concurrent-users 100 --duration 300

# System capacity test
python scripts/capacity_test.py --target-uptime 99.9
```

---

## 🔄 Blue-Green Deployment Quick Reference

### Check Current Deployment Slot
```bash
CURRENT_SLOT=$(kubectl get service legalllm-unified-interface-svc \
  -n legalllm-multiagent -o jsonpath='{.spec.selector.deployment-slot}')
echo "Current active slot: $CURRENT_SLOT"
```

### Deploy to Inactive Slot
```bash
# Determine target slot
if [ "$CURRENT_SLOT" = "blue" ]; then
  TARGET_SLOT="green"
else
  TARGET_SLOT="blue"
fi

# Deploy to target slot with new image
kubectl set image deployment/legalllm-unified-interface-$TARGET_SLOT \
  unified-interface=legalllm-unified-interface:v2.0.1 -n legalllm-multiagent

# Wait for deployment
kubectl rollout status deployment/legalllm-unified-interface-$TARGET_SLOT \
  -n legalllm-multiagent --timeout=600s
```

### Switch Traffic to New Deployment
```bash
# Validate new deployment
python scripts/deployment_validation.py --slot $TARGET_SLOT

# Switch traffic
kubectl patch service legalllm-unified-interface-svc -n legalllm-multiagent \
  -p '{"spec":{"selector":{"deployment-slot":"'$TARGET_SLOT'"}}}'

echo "Traffic switched to $TARGET_SLOT slot"
```

### Emergency Rollback
```bash
# Switch back to previous slot
kubectl patch service legalllm-unified-interface-svc -n legalllm-multiagent \
  -p '{"spec":{"selector":{"deployment-slot":"'$CURRENT_SLOT'"}}}'

echo "Emergency rollback completed - traffic restored to $CURRENT_SLOT"
```

---

## 📞 Emergency Contacts Quick Reference

### Immediate Response Team
- **Primary On-Call**: +61 4XX XXX XXX
- **Secondary On-Call**: +61 4XX XXX XXX  
- **Technical Lead**: +61 4XX XXX XXX
- **Legal Compliance Officer**: +61 4XX XXX XXX

### External Contacts
- **AWS Enterprise Support**: Create case via console
- **Australian Privacy Commissioner**: 1300 363 992
- **Law Institute of Victoria**: (03) 9607 9311

### Communication Channels
- **Incidents**: #legalllm-incidents
- **Deployments**: #legalllm-deployments
- **Compliance**: #legalllm-compliance

### Status Pages
- **Internal**: https://status-internal.legalllm.com.au
- **Public**: https://status.legalllm.com.au
- **Monitoring**: https://monitoring.legalllm.com.au

---

## 🛡️ Security Incident Response

### Data Breach Response
```bash
# IMMEDIATE (0-5 minutes)
1. Isolate affected systems:
   kubectl scale deployment --all --replicas=0 -n legalllm-multiagent

2. Preserve evidence:
   kubectl logs --all-containers=true \
     --selector app.kubernetes.io/name=legalllm-professional \
     -n legalllm-multiagent > security_incident_$(date +%s).log

3. Notify security team:
   - Phone: +61 4XX XXX XXX
   - Email: security-incident@company.com
   - Slack: @security-team

4. Legal notifications (if personal data affected):
   - Australian Privacy Commissioner: 1300 363 992
   - Affected clients within 72 hours (GDPR/Privacy Act)
```

### Unauthorized Access Response
```bash
# IMMEDIATE
1. Revoke all authentication tokens:
   kubectl delete secrets -l type=auth-token -n legalllm-multiagent

2. Check access logs:
   kubectl logs -l app=australian-legal-compliance-monitor \
     -n legalllm-multiagent | grep "VIOLATION"

3. Reset all service account credentials:
   kubectl rollout restart deployment --all -n legalllm-multiagent

4. Enable enhanced monitoring:
   kubectl patch configmap prometheus-config -n legalllm-multiagent \
     -p '{"data":{"security-enhanced.yml":"rules enabled"}}'
```

---

## ✅ Health Check Automation

### Automated Health Check Script
```bash
#!/bin/bash
# Save as: /usr/local/bin/legalllm-health-check

# Check all critical components
echo "=== LegalLLM Professional Health Check ==="
echo "Time: $(date)"
echo ""

# System status
echo "🔍 System Status:"
kubectl get pods -n legalllm-multiagent | grep -v Running | wc -l | \
  awk '{if($1==0) print "✅ All pods running"; else print "❌ " $1 " pods not running"}'

# Performance validation
echo ""
echo "⚡ Performance Check:"
A2A_LATENCY=$(curl -s http://prometheus:9090/api/v1/query?query=a2a_protocol_latency_ms | \
              jq -r '.data.result[0].value[1]' 2>/dev/null || echo "unknown")
if (( $(echo "$A2A_LATENCY < 50" | bc -l) )); then
  echo "✅ A2A Protocol latency: ${A2A_LATENCY}ms"
else
  echo "❌ A2A Protocol latency: ${A2A_LATENCY}ms (target: <50ms)"
fi

# Compliance status
echo ""
echo "🇦🇺 Australian Legal Compliance:"
COMPLIANCE_SCORE=$(curl -s http://compliance-monitor:8080/api/compliance/dashboard | \
                   jq -r '.compliance_scores.family_law_act_1975' 2>/dev/null || echo "unknown")
if (( $(echo "$COMPLIANCE_SCORE >= 0.9" | bc -l) )); then
  echo "✅ Family Law Act compliance: ${COMPLIANCE_SCORE}"
else
  echo "❌ Family Law Act compliance: ${COMPLIANCE_SCORE} (target: ≥0.9)"
fi

echo ""
echo "=== Health Check Complete ==="
```

### Cron Job for Regular Health Checks
```bash
# Add to crontab: crontab -e
*/15 * * * * /usr/local/bin/legalllm-health-check >> /var/log/legalllm-health.log 2>&1
```

---

**Document Version**: v2.0.0  
**Last Updated**: 2024-01-07  
**Emergency Hotline**: +61 4XX XXX XXX  
**Status Page**: https://status.legalllm.com.au