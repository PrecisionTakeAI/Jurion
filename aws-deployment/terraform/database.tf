# RDS PostgreSQL Configuration for LegalLLM Professional
# Multi-AZ deployment with encryption and compliance features

# DB Subnet Group
resource "aws_db_subnet_group" "legalllm_db_subnet_group" {
  name       = "legalllm-db-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id
  
  tags = {
    Name = "LegalLLM DB Subnet Group"
  }
}

# RDS Parameter Group for PostgreSQL optimization
resource "aws_db_parameter_group" "legalllm_db_params" {
  name   = "legalllm-postgres15-params"
  family = "postgres15"
  
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
  
  parameter {
    name  = "log_statement"
    value = "all"
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries taking more than 1 second
  }
  
  parameter {
    name  = "max_connections"
    value = "200"
  }
  
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4}"
  }
  
  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory*3/4}"
  }
  
  parameter {
    name  = "maintenance_work_mem"
    value = "2097152"  # 2GB
  }
  
  parameter {
    name  = "checkpoint_completion_target"
    value = "0.9"
  }
  
  parameter {
    name  = "wal_buffers"
    value = "16384"  # 16MB
  }
  
  parameter {
    name  = "default_statistics_target"
    value = "100"
  }
  
  parameter {
    name  = "random_page_cost"
    value = "1.1"
  }
  
  parameter {
    name  = "effective_io_concurrency"
    value = "200"
  }
  
  tags = {
    Name = "LegalLLM PostgreSQL Parameters"
  }
}

# RDS Instance - Multi-AZ PostgreSQL
resource "aws_db_instance" "legalllm_postgres" {
  # Basic Configuration
  identifier             = "legalllm-postgres-${var.environment}"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.r6g.xlarge"  # 4 vCPU, 32GB RAM
  allocated_storage      = 500
  max_allocated_storage  = 2000
  storage_type           = "gp3"
  storage_encrypted      = true
  kms_key_id            = aws_kms_key.legalllm_kms.arn
  
  # Database Configuration
  db_name  = "legalllm"
  username = "legalllm_user"
  password = var.db_password
  port     = 5432
  
  # Network Configuration
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.legalllm_db_subnet_group.name
  parameter_group_name   = aws_db_parameter_group.legalllm_db_params.name
  
  # High Availability & Backup
  multi_az               = true
  backup_retention_period = 30
  backup_window          = "03:00-04:00"  # UTC
  maintenance_window     = "sun:04:00-sun:05:00"  # UTC
  copy_tags_to_snapshot  = true
  delete_automated_backups = false
  deletion_protection    = true
  
  # Performance & Monitoring
  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.legalllm_kms.arn
  performance_insights_retention_period = 7
  monitoring_interval    = 60
  monitoring_role_arn   = aws_iam_role.rds_monitoring_role.arn
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  # Security
  auto_minor_version_upgrade = true
  ca_cert_identifier        = "rds-ca-2019"
  
  # Maintenance
  apply_immediately = false
  
  # Snapshot Configuration
  final_snapshot_identifier = "legalllm-postgres-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  skip_final_snapshot       = false
  
  tags = {
    Name = "LegalLLM PostgreSQL Database"
    BackupSchedule = "Daily"
    Compliance = "Privacy Act 1988"
  }
  
  depends_on = [aws_cloudwatch_log_group.rds_logs]
}

# CloudWatch Log Groups for RDS
resource "aws_cloudwatch_log_group" "rds_logs" {
  name              = "/aws/rds/instance/legalllm-postgres/postgresql"
  retention_in_days = 30
  kms_key_id       = aws_kms_key.legalllm_kms.arn
}

# IAM Role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring_role" {
  name = "legalllm-rds-monitoring-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring_policy" {
  role       = aws_iam_role.rds_monitoring_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Read Replica for reporting and analytics (optional)
resource "aws_db_instance" "legalllm_postgres_replica" {
  count = var.enable_read_replica ? 1 : 0
  
  identifier              = "legalllm-postgres-replica-${var.environment}"
  replicate_source_db     = aws_db_instance.legalllm_postgres.identifier
  instance_class          = "db.r6g.large"  # Smaller instance for read replica
  auto_minor_version_upgrade = true
  
  # Network
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  
  # Monitoring
  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.legalllm_kms.arn
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring_role.arn
  
  tags = {
    Name = "LegalLLM PostgreSQL Read Replica"
    Purpose = "Analytics and Reporting"
  }
}

# Database Migration Service Subnet Group (for data migration)
resource "aws_dms_subnet_group" "legalllm_dms_subnet_group" {
  subnet_group_id  = "legalllm-dms-subnet-group"
  subnet_group_description = "DMS subnet group for LegalLLM migration"
  subnet_ids       = aws_subnet.private_subnets[*].id
  
  tags = {
    Name = "LegalLLM DMS Subnet Group"
  }
}

# Variable for read replica
variable "enable_read_replica" {
  description = "Enable read replica for analytics"
  type        = bool
  default     = false
}

# Outputs
output "rds_endpoint" {
  value = aws_db_instance.legalllm_postgres.endpoint
  description = "RDS instance endpoint"
}

output "rds_port" {
  value = aws_db_instance.legalllm_postgres.port
  description = "RDS instance port"
}

output "database_name" {
  value = aws_db_instance.legalllm_postgres.db_name
  description = "Database name"
}

output "rds_replica_endpoint" {
  value = var.enable_read_replica ? aws_db_instance.legalllm_postgres_replica[0].endpoint : null
  description = "RDS read replica endpoint"
}