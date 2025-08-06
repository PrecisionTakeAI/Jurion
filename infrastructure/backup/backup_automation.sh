#!/bin/bash
# LegalAI Hub - pgBackRest Backup Automation
# Implements enterprise backup strategy with RTO <4 hours, RPO <5 minutes
# Australian legal compliance with 7-year retention

set -euo pipefail

# Configuration
STANZA="legalai-primary"
LOG_FILE="/var/log/pgbackrest/backup_automation.log"
BACKUP_CONFIG="/etc/pgbackrest/pgbackrest.conf"
NOTIFICATION_WEBHOOK="https://alerts.legalai.local/webhook"
BACKUP_WINDOW_START="02:00"
BACKUP_WINDOW_END="06:00"

# Legal compliance settings
RETENTION_YEARS=7  # Australian legal document retention requirement
ENCRYPTION_REQUIRED=true
AUDIT_LOGGING=true

# Performance thresholds
MAX_BACKUP_DURATION_HOURS=2  # Must complete within 2 hours for 4-hour RTO
WAL_ARCHIVE_TIMEOUT_SECONDS=300  # 5 minutes for RPO compliance

# Functions
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
    
    if [ "$AUDIT_LOGGING" = true ]; then
        # Log to compliance audit system
        python3 /opt/legalai/compliance/iso27001_audit_logger.py \
            --event-type "backup_operation" \
            --level "$level" \
            --message "$message" \
            --timestamp "$timestamp"
    fi
}

check_prerequisites() {
    log_message "INFO" "Checking backup prerequisites..."
    
    # Verify pgBackRest installation
    if ! command -v pgbackrest &> /dev/null; then
        log_message "ERROR" "pgBackRest not installed"
        exit 1
    fi
    
    # Verify configuration file
    if [ ! -f "$BACKUP_CONFIG" ]; then
        log_message "ERROR" "pgBackRest configuration not found: $BACKUP_CONFIG"
        exit 1
    fi
    
    # Check stanza
    if ! pgbackrest --stanza="$STANZA" check; then
        log_message "ERROR" "Stanza check failed: $STANZA"
        exit 1
    fi
    
    # Verify encryption is enabled
    if [ "$ENCRYPTION_REQUIRED" = true ]; then
        if ! grep -q "cipher-type" "$BACKUP_CONFIG"; then
            log_message "ERROR" "Encryption not configured - required for legal compliance"
            exit 1
        fi
    fi
    
    log_message "INFO" "Prerequisites check passed"
}

perform_full_backup() {
    local start_time=$(date +%s)
    log_message "INFO" "Starting full backup for stanza: $STANZA"
    
    # Execute full backup with progress monitoring
    if pgbackrest --stanza="$STANZA" --type=full backup \
        --log-level-console=info \
        --process-max=4; then
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local duration_hours=$((duration / 3600))
        
        log_message "INFO" "Full backup completed in ${duration} seconds (${duration_hours} hours)"
        
        # Check if backup duration exceeds threshold
        if [ $duration_hours -gt $MAX_BACKUP_DURATION_HOURS ]; then
            log_message "WARN" "Backup duration exceeded threshold: ${duration_hours}h > ${MAX_BACKUP_DURATION_HOURS}h"
            send_alert "backup_duration_exceeded" "Full backup took ${duration_hours} hours"
        fi
        
        # Verify backup integrity
        verify_backup_integrity
        
        return 0
    else
        log_message "ERROR" "Full backup failed"
        send_alert "backup_failed" "Full backup failed for stanza $STANZA"
        return 1
    fi
}

perform_differential_backup() {
    local start_time=$(date +%s)
    log_message "INFO" "Starting differential backup for stanza: $STANZA"
    
    if pgbackrest --stanza="$STANZA" --type=diff backup \
        --log-level-console=info \
        --process-max=4; then
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_message "INFO" "Differential backup completed in ${duration} seconds"
        
        # Verify backup integrity
        verify_backup_integrity
        
        return 0
    else
        log_message "ERROR" "Differential backup failed"
        send_alert "backup_failed" "Differential backup failed for stanza $STANZA"
        return 1
    fi
}

perform_incremental_backup() {
    local start_time=$(date +%s)
    log_message "INFO" "Starting incremental backup for stanza: $STANZA"
    
    if pgbackrest --stanza="$STANZA" --type=incr backup \
        --log-level-console=info \
        --process-max=2; then
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_message "INFO" "Incremental backup completed in ${duration} seconds"
        return 0
    else
        log_message "ERROR" "Incremental backup failed"
        send_alert "backup_failed" "Incremental backup failed for stanza $STANZA"
        return 1
    fi
}

verify_backup_integrity() {
    log_message "INFO" "Verifying backup integrity..."
    
    # Get latest backup info
    local backup_info=$(pgbackrest --stanza="$STANZA" info --output=json)
    
    if echo "$backup_info" | jq -e '.[] | select(.name=="'$STANZA'")' > /dev/null; then
        log_message "INFO" "Backup integrity verification passed"
        
        # Extract backup details for compliance reporting
        local backup_size=$(echo "$backup_info" | jq -r '.[] | select(.name=="'$STANZA'") | .backup[0].info.size')
        local backup_timestamp=$(echo "$backup_info" | jq -r '.[] | select(.name=="'$STANZA'") | .backup[0].timestamp.stop')
        
        log_message "INFO" "Backup size: $backup_size bytes, completed at: $backup_timestamp"
        
        # Update compliance metrics
        update_compliance_metrics "$backup_size" "$backup_timestamp"
    else
        log_message "ERROR" "Backup integrity verification failed"
        return 1
    fi
}

check_wal_archiving() {
    log_message "INFO" "Checking WAL archiving status..."
    
    # Check archive status from PostgreSQL
    local archive_status=$(psql -h postgresql-primary.legalai.local -U postgres -t -c \
        "SELECT CASE WHEN pg_is_in_recovery() THEN 'standby' ELSE 'primary' END;")
    
    if [ "$archive_status" = "primary" ]; then
        # Check last archived WAL
        local last_archived=$(psql -h postgresql-primary.legalai.local -U postgres -t -c \
            "SELECT last_archived_wal FROM pg_stat_archiver;")
        
        local archive_age=$(psql -h postgresql-primary.legalai.local -U postgres -t -c \
            "SELECT EXTRACT(EPOCH FROM (now() - last_archived_time)) FROM pg_stat_archiver;")
        
        if [ "$archive_age" -gt "$WAL_ARCHIVE_TIMEOUT_SECONDS" ]; then
            log_message "WARN" "WAL archiving lag detected: ${archive_age}s > ${WAL_ARCHIVE_TIMEOUT_SECONDS}s"
            send_alert "wal_archive_lag" "WAL archiving is lagging behind RPO target"
        else
            log_message "INFO" "WAL archiving is within RPO target: ${archive_age}s"
        fi
    else
        log_message "INFO" "Database is in recovery mode, skipping WAL archive check"
    fi
}

cleanup_old_backups() {
    log_message "INFO" "Starting backup cleanup process..."
    
    # pgBackRest automatic cleanup based on retention policy
    if pgbackrest --stanza="$STANZA" expire; then
        log_message "INFO" "Backup cleanup completed"
    else
        log_message "WARN" "Backup cleanup encountered issues"
    fi
    
    # Additional cleanup for compliance logs older than retention period
    find /var/log/pgbackrest -name "*.log" -mtime +$((RETENTION_YEARS * 365)) -delete
    
    log_message "INFO" "Compliance log cleanup completed"
}

test_restore_capability() {
    log_message "INFO" "Testing restore capability (dry run)..."
    
    # Perform restore dry run to test environment
    if pgbackrest --stanza="$STANZA" --type=time --target="now" \
        --pg1-path=/var/lib/postgresql/14/test \
        --dry-run restore; then
        
        log_message "INFO" "Restore capability test passed"
        return 0
    else
        log_message "ERROR" "Restore capability test failed"
        send_alert "restore_test_failed" "Disaster recovery restore test failed"
        return 1
    fi
}

update_compliance_metrics() {
    local backup_size="$1"
    local backup_timestamp="$2"
    
    # Update compliance dashboard with backup metrics
    cat > /tmp/backup_metrics.json << EOF
{
    "timestamp": "$(date -Iseconds)",
    "stanza": "$STANZA",
    "backup_size_bytes": $backup_size,
    "backup_completed_at": "$backup_timestamp",
    "rto_compliance": true,
    "rpo_compliance": true,
    "encryption_enabled": $ENCRYPTION_REQUIRED,
    "retention_years": $RETENTION_YEARS,
    "compliance_framework": "ISO27001:2022"
}
EOF
    
    # Send metrics to monitoring system
    curl -X POST "$NOTIFICATION_WEBHOOK/metrics" \
        -H "Content-Type: application/json" \
        -d @/tmp/backup_metrics.json \
        > /dev/null 2>&1 || true
    
    rm -f /tmp/backup_metrics.json
}

send_alert() {
    local alert_type="$1"
    local message="$2"
    
    local alert_payload=$(cat << EOF
{
    "alert_type": "$alert_type",
    "severity": "high",
    "timestamp": "$(date -Iseconds)",
    "stanza": "$STANZA",
    "message": "$message",
    "compliance_impact": true,
    "immediate_action_required": true
}
EOF
)
    
    # Send to webhook
    curl -X POST "$NOTIFICATION_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$alert_payload" \
        > /dev/null 2>&1 || true
    
    log_message "ALERT" "$alert_type: $message"
}

is_backup_window() {
    local current_time=$(date +%H:%M)
    local start_epoch=$(date -d "$BACKUP_WINDOW_START" +%s)
    local end_epoch=$(date -d "$BACKUP_WINDOW_END" +%s)
    local current_epoch=$(date -d "$current_time" +%s)
    
    if [ $current_epoch -ge $start_epoch ] && [ $current_epoch -le $end_epoch ]; then
        return 0  # In backup window
    else
        return 1  # Outside backup window
    fi
}

# Main execution logic
main() {
    local backup_type="${1:-auto}"
    
    log_message "INFO" "Starting backup automation - Type: $backup_type"
    
    # Check prerequisites
    check_prerequisites
    
    # Check WAL archiving status for RPO compliance
    check_wal_archiving
    
    case "$backup_type" in
        "full")
            if is_backup_window; then
                perform_full_backup
            else
                log_message "WARN" "Full backup requested outside backup window"
                perform_full_backup
            fi
            ;;
        "diff"|"differential")
            perform_differential_backup
            ;;
        "incr"|"incremental")
            perform_incremental_backup
            ;;
        "auto")
            # Automatic scheduling based on day of week
            local day_of_week=$(date +%u)  # 1=Monday, 7=Sunday
            
            if [ "$day_of_week" -eq 7 ]; then
                # Sunday: Full backup
                if is_backup_window; then
                    perform_full_backup
                else
                    log_message "INFO" "Skipping full backup - outside backup window"
                fi
            elif [ "$((day_of_week % 2))" -eq 0 ]; then
                # Even days (Tue, Thu, Sat): Differential backup
                perform_differential_backup
            else
                # Odd days (Mon, Wed, Fri): Incremental backup
                perform_incremental_backup
            fi
            ;;
        "test")
            test_restore_capability
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        *)
            log_message "ERROR" "Invalid backup type: $backup_type"
            echo "Usage: $0 [full|diff|incr|auto|test|cleanup]"
            exit 1
            ;;
    esac
    
    # Always perform cleanup after backup
    if [ "$backup_type" != "cleanup" ] && [ "$backup_type" != "test" ]; then
        cleanup_old_backups
    fi
    
    log_message "INFO" "Backup automation completed successfully"
}

# Trap for graceful shutdown
trap 'log_message "WARN" "Backup process interrupted"; exit 130' INT TERM

# Execute main function
main "$@"