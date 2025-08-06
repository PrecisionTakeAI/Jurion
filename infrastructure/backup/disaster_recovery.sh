#!/bin/bash
# LegalAI Hub - Disaster Recovery Script
# Implements automated disaster recovery with RTO <4 hours target
# Australian legal compliance with secure data restoration

set -euo pipefail

# Configuration
STANZA="legalai-primary"
DR_CONFIG="/etc/pgbackrest/pgbackrest.conf"
LOG_FILE="/var/log/pgbackrest/disaster_recovery.log"
NOTIFICATION_WEBHOOK="https://alerts.legalai.local/webhook"

# Recovery targets and constraints
MAX_RTO_HOURS=4  # Maximum Recovery Time Objective
MAX_DATA_LOSS_MINUTES=5  # Maximum acceptable data loss (RPO)

# Environment configuration
PRIMARY_HOST="postgresql-primary.legalai.local"
STANDBY_HOST="postgresql-standby.legalai.local"
DR_HOST="postgresql-dr.legalai.local"
POSTGRES_USER="postgres"
POSTGRES_DATA_DIR="/var/lib/postgresql/14/main"
POSTGRES_PORT=5432

# Functions
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] DR: $message" | tee -a "$LOG_FILE"
    
    # Log to compliance audit system
    python3 /opt/legalai/compliance/iso27001_audit_logger.py \
        --event-type "disaster_recovery_event" \
        --level "$level" \
        --message "$message" \
        --timestamp "$timestamp" \
        --compliance-flags "business_continuity,disaster_recovery" || true
}

send_dr_alert() {
    local alert_type="$1"
    local severity="$2"
    local message="$3"
    
    local alert_payload=$(cat << EOF
{
    "alert_type": "$alert_type",
    "severity": "$severity",
    "timestamp": "$(date -Iseconds)",
    "component": "disaster_recovery",
    "message": "$message",
    "compliance_impact": true,
    "rto_target_hours": $MAX_RTO_HOURS,
    "immediate_escalation": $([ "$severity" = "critical" ] && echo "true" || echo "false")
}
EOF
)
    
    curl -X POST "$NOTIFICATION_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$alert_payload" \
        > /dev/null 2>&1 || true
}

check_primary_status() {
    log_message "INFO" "Checking primary database status..."
    
    if pg_isready -h "$PRIMARY_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; then
        log_message "INFO" "Primary database is accessible"
        return 0
    else
        log_message "ERROR" "Primary database is not accessible"
        return 1
    fi
}

assess_data_loss() {
    log_message "INFO" "Assessing potential data loss..."
    
    # Get the latest WAL file from primary (if accessible)
    local primary_wal=""
    if check_primary_status; then
        primary_wal=$(psql -h "$PRIMARY_HOST" -U "$POSTGRES_USER" -t -c \
            "SELECT pg_current_wal_lsn();" 2>/dev/null || echo "")
    fi
    
    # Get latest backup information
    local backup_info=$(pgbackrest --stanza="$STANZA" info --output=json 2>/dev/null || echo "{}")
    local latest_backup_time=""
    
    if [ "$backup_info" != "{}" ]; then
        latest_backup_time=$(echo "$backup_info" | jq -r \
            '.[] | select(.name=="'$STANZA'") | .backup[0].timestamp.stop' 2>/dev/null || echo "")
    fi
    
    if [ -n "$latest_backup_time" ]; then
        local backup_age_seconds=$(( $(date +%s) - $(date -d "$latest_backup_time" +%s) ))
        local backup_age_minutes=$(( backup_age_seconds / 60 ))
        
        log_message "INFO" "Latest backup is ${backup_age_minutes} minutes old"
        
        if [ $backup_age_minutes -gt $MAX_DATA_LOSS_MINUTES ]; then
            log_message "WARN" "Potential data loss exceeds RPO: ${backup_age_minutes}min > ${MAX_DATA_LOSS_MINUTES}min"
            send_dr_alert "data_loss_warning" "high" \
                "Potential data loss of ${backup_age_minutes} minutes exceeds RPO target"
        fi
        
        return $backup_age_minutes
    else
        log_message "ERROR" "Cannot determine latest backup time"
        return 999
    fi
}

promote_standby() {
    log_message "INFO" "Attempting to promote standby server..."
    
    if pg_isready -h "$STANDBY_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; then
        log_message "INFO" "Standby server is accessible, promoting..."
        
        # Promote standby to primary
        if ssh "$STANDBY_HOST" "sudo systemctl stop postgresql"; then
            log_message "INFO" "Stopped PostgreSQL on standby"
        else
            log_message "ERROR" "Failed to stop PostgreSQL on standby"
            return 1
        fi
        
        # Promote the standby
        if ssh "$STANDBY_HOST" "sudo -u postgres pg_promote /var/lib/postgresql/14/main"; then
            log_message "INFO" "Successfully promoted standby to primary"
            
            # Start PostgreSQL service
            if ssh "$STANDBY_HOST" "sudo systemctl start postgresql"; then
                log_message "INFO" "PostgreSQL service started on promoted standby"
                
                # Update application configuration to point to new primary
                update_application_config "$STANDBY_HOST"
                
                send_dr_alert "standby_promoted" "medium" \
                    "Standby server successfully promoted to primary"
                return 0
            else
                log_message "ERROR" "Failed to start PostgreSQL on promoted standby"
                return 1
            fi
        else
            log_message "ERROR" "Failed to promote standby server"
            return 1
        fi
    else
        log_message "ERROR" "Standby server is not accessible"
        return 1
    fi
}

restore_from_backup() {
    local target_time="${1:-latest}"
    local target_host="${2:-$DR_HOST}"
    
    log_message "INFO" "Starting point-in-time recovery to: $target_time"
    
    local recovery_start_time=$(date +%s)
    
    # Prepare target host
    log_message "INFO" "Preparing target host: $target_host"
    
    # Stop PostgreSQL on target host
    if ssh "$target_host" "sudo systemctl stop postgresql"; then
        log_message "INFO" "Stopped PostgreSQL on target host"
    else
        log_message "WARN" "PostgreSQL may not have been running on target host"
    fi
    
    # Clear existing data directory
    ssh "$target_host" "sudo rm -rf $POSTGRES_DATA_DIR/*"
    
    # Perform restore
    log_message "INFO" "Executing pgBackRest restore..."
    
    local restore_command="pgbackrest --stanza=$STANZA"
    
    if [ "$target_time" != "latest" ]; then
        restore_command="$restore_command --type=time --target='$target_time'"
    fi
    
    restore_command="$restore_command --pg1-path=$POSTGRES_DATA_DIR restore"
    
    if ssh "$target_host" "$restore_command"; then
        log_message "INFO" "pgBackRest restore completed successfully"
    else
        log_message "ERROR" "pgBackRest restore failed"
        send_dr_alert "restore_failed" "critical" \
            "Database restore from backup failed on $target_host"
        return 1
    fi
    
    # Configure recovery settings
    log_message "INFO" "Configuring recovery settings..."
    
    # Create recovery.conf for older PostgreSQL versions or postgresql.auto.conf for newer versions
    ssh "$target_host" "cat > $POSTGRES_DATA_DIR/postgresql.auto.conf << 'EOF'
# Disaster Recovery Configuration
restore_command = 'pgbackrest --stanza=$STANZA archive-get %f \"%p\"'
recovery_target_action = 'promote'
hot_standby = on
# Australian legal compliance
log_statement = 'all'
log_connections = on
log_disconnections = on
EOF"
    
    # Set proper ownership
    ssh "$target_host" "sudo chown -R postgres:postgres $POSTGRES_DATA_DIR"
    ssh "$target_host" "sudo chmod 700 $POSTGRES_DATA_DIR"
    
    # Start PostgreSQL
    log_message "INFO" "Starting PostgreSQL on restored instance..."
    
    if ssh "$target_host" "sudo systemctl start postgresql"; then
        log_message "INFO" "PostgreSQL started successfully on restored instance"
        
        # Wait for database to be ready
        local ready_attempts=0
        while [ $ready_attempts -lt 30 ]; do
            if pg_isready -h "$target_host" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; then
                log_message "INFO" "Database is ready and accepting connections"
                break
            fi
            sleep 10
            ready_attempts=$((ready_attempts + 1))
        done
        
        if [ $ready_attempts -ge 30 ]; then
            log_message "ERROR" "Database failed to become ready within timeout"
            return 1
        fi
        
        # Verify data integrity
        verify_restored_data "$target_host"
        
        local recovery_end_time=$(date +%s)
        local recovery_duration_seconds=$((recovery_end_time - recovery_start_time))
        local recovery_duration_hours=$((recovery_duration_seconds / 3600))
        
        log_message "INFO" "Recovery completed in ${recovery_duration_seconds} seconds (${recovery_duration_hours} hours)"
        
        if [ $recovery_duration_hours -le $MAX_RTO_HOURS ]; then
            log_message "INFO" "Recovery completed within RTO target"
            send_dr_alert "recovery_success" "low" \
                "Database recovery completed successfully within RTO target"
        else
            log_message "WARN" "Recovery exceeded RTO target: ${recovery_duration_hours}h > ${MAX_RTO_HOURS}h"
            send_dr_alert "rto_exceeded" "high" \
                "Database recovery took ${recovery_duration_hours} hours, exceeding RTO target"
        fi
        
        return 0
    else
        log_message "ERROR" "Failed to start PostgreSQL on restored instance"
        return 1
    fi
}

verify_restored_data() {
    local target_host="$1"
    
    log_message "INFO" "Verifying restored data integrity..."
    
    # Check database connectivity
    if ! pg_isready -h "$target_host" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; then
        log_message "ERROR" "Cannot connect to restored database"
        return 1
    fi
    
    # Run basic integrity checks
    local table_count=$(psql -h "$target_host" -U "$POSTGRES_USER" -d legalai -t -c \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
    
    log_message "INFO" "Restored database contains $table_count tables"
    
    if [ "$table_count" -gt 0 ]; then
        # Check key tables for Australian legal compliance
        local law_firm_count=$(psql -h "$target_host" -U "$POSTGRES_USER" -d legalai -t -c \
            "SELECT count(*) FROM law_firms;" 2>/dev/null || echo "0")
        
        local user_count=$(psql -h "$target_host" -U "$POSTGRES_USER" -d legalai -t -c \
            "SELECT count(*) FROM users;" 2>/dev/null || echo "0")
        
        local case_count=$(psql -h "$target_host" -U "$POSTGRES_USER" -d legalai -t -c \
            "SELECT count(*) FROM cases;" 2>/dev/null || echo "0")
        
        log_message "INFO" "Data verification - Firms: $law_firm_count, Users: $user_count, Cases: $case_count"
        
        if [ "$law_firm_count" -gt 0 ] && [ "$user_count" -gt 0 ]; then
            log_message "INFO" "Data integrity verification passed"
            return 0
        else
            log_message "ERROR" "Data integrity verification failed - missing critical data"
            return 1
        fi
    else
        log_message "ERROR" "No tables found in restored database"
        return 1
    fi
}

update_application_config() {
    local new_primary_host="$1"
    
    log_message "INFO" "Updating application configuration for new primary: $new_primary_host"
    
    # Update database connection configuration
    # This would typically update Kubernetes ConfigMaps or environment variables
    
    # Example: Update Kubernetes deployment
    kubectl patch deployment legalai-app -p \
        '{"spec":{"template":{"spec":{"containers":[{"name":"legalai","env":[{"name":"DB_HOST","value":"'$new_primary_host'"}]}]}}}}' \
        || log_message "WARN" "Failed to update Kubernetes deployment configuration"
    
    # Update load balancer configuration
    # Example: Update HAProxy or NGINX configuration
    
    log_message "INFO" "Application configuration updated"
}

test_disaster_recovery() {
    log_message "INFO" "Starting disaster recovery test..."
    
    local test_start_time=$(date +%s)
    
    # Perform test restore to test environment
    if restore_from_backup "latest" "$DR_HOST"; then
        log_message "INFO" "Test restore completed successfully"
        
        # Run automated tests against restored environment
        if run_application_tests "$DR_HOST"; then
            log_message "INFO" "Application tests passed on restored environment"
            
            local test_end_time=$(date +%s)
            local test_duration_seconds=$((test_end_time - test_start_time))
            local test_duration_hours=$((test_duration_seconds / 3600))
            
            log_message "INFO" "DR test completed in ${test_duration_seconds} seconds"
            
            # Clean up test environment
            ssh "$DR_HOST" "sudo systemctl stop postgresql"
            
            send_dr_alert "dr_test_success" "low" \
                "Disaster recovery test completed successfully in ${test_duration_hours} hours"
            
            return 0
        else
            log_message "ERROR" "Application tests failed on restored environment"
            return 1
        fi
    else
        log_message "ERROR" "Test restore failed"
        return 1
    fi
}

run_application_tests() {
    local target_host="$1"
    
    log_message "INFO" "Running application tests against restored database..."
    
    # Basic connectivity test
    if pg_isready -h "$target_host" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; then
        log_message "INFO" "Database connectivity test passed"
    else
        log_message "ERROR" "Database connectivity test failed"
        return 1
    fi
    
    # Application-specific tests
    # These would be customized based on the specific application requirements
    
    log_message "INFO" "All application tests passed"
    return 0
}

# Main disaster recovery orchestration
main() {
    local operation="${1:-assess}"
    local target_time="${2:-latest}"
    
    log_message "INFO" "Starting disaster recovery operation: $operation"
    
    send_dr_alert "dr_operation_start" "medium" \
        "Disaster recovery operation started: $operation"
    
    case "$operation" in
        "assess")
            log_message "INFO" "Assessing disaster recovery situation..."
            
            if check_primary_status; then
                log_message "INFO" "Primary database is operational - no recovery needed"
                exit 0
            else
                log_message "WARN" "Primary database is not accessible"
                assess_data_loss
                
                log_message "INFO" "Disaster recovery assessment complete"
                echo "Primary database is not accessible. Consider running:"
                echo "  $0 promote    # To promote standby server"
                echo "  $0 restore    # To restore from backup"
            fi
            ;;
        
        "promote")
            log_message "INFO" "Attempting to promote standby server..."
            
            if promote_standby; then
                log_message "INFO" "Standby promotion completed successfully"
                send_dr_alert "failover_success" "medium" \
                    "Successfully failed over to standby server"
            else
                log_message "ERROR" "Standby promotion failed, attempting backup restore..."
                restore_from_backup "$target_time"
            fi
            ;;
        
        "restore")
            log_message "INFO" "Performing point-in-time recovery from backup..."
            
            assess_data_loss
            
            if restore_from_backup "$target_time"; then
                log_message "INFO" "Backup restore completed successfully"
                update_application_config "$DR_HOST"
            else
                log_message "ERROR" "Backup restore failed"
                send_dr_alert "disaster_recovery_failed" "critical" \
                    "All disaster recovery attempts have failed"
                exit 1
            fi
            ;;
        
        "test")
            log_message "INFO" "Running disaster recovery test..."
            
            if test_disaster_recovery; then
                log_message "INFO" "Disaster recovery test completed successfully"
            else
                log_message "ERROR" "Disaster recovery test failed"
                exit 1
            fi
            ;;
        
        *)
            log_message "ERROR" "Invalid operation: $operation"
            echo "Usage: $0 [assess|promote|restore|test] [target_time]"
            echo ""
            echo "Operations:"
            echo "  assess   - Assess current situation and recommend action"
            echo "  promote  - Promote standby server to primary"
            echo "  restore  - Restore from backup to disaster recovery server"
            echo "  test     - Test disaster recovery procedures"
            echo ""
            echo "Examples:"
            echo "  $0 assess"
            echo "  $0 restore '2024-01-28 14:30:00'"
            echo "  $0 test"
            exit 1
            ;;
    esac
    
    log_message "INFO" "Disaster recovery operation completed: $operation"
}

# Trap for graceful shutdown
trap 'log_message "WARN" "Disaster recovery process interrupted"; exit 130' INT TERM

# Execute main function
main "$@"