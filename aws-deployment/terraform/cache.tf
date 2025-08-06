# ElastiCache Redis Configuration for LegalLLM Professional
# Optimized for A2A Protocol messaging and multi-agent communication

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "legalllm_cache_subnet_group" {
  name       = "legalllm-cache-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id
  
  tags = {
    Name = "LegalLLM Cache Subnet Group"
  }
}

# ElastiCache Parameter Group for Redis optimization
resource "aws_elasticache_parameter_group" "legalllm_redis_params" {
  name   = "legalllm-redis-params"
  family = "redis7.x"
  
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  
  parameter {
    name  = "timeout"
    value = "300"
  }
  
  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }
  
  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"  # Enable keyspace notifications for expiration events
  }
  
  # Redis configuration for A2A Protocol
  parameter {
    name  = "list-max-ziplist-entries"
    value = "512"
  }
  
  parameter {
    name  = "hash-max-ziplist-entries"
    value = "512"
  }
  
  parameter {
    name  = "set-max-intset-entries"
    value = "512"
  }
  
  tags = {
    Name = "LegalLLM Redis Parameters"
  }
}

# ElastiCache Replication Group (Redis Cluster)
resource "aws_elasticache_replication_group" "legalllm_redis" {
  replication_group_id       = "legalllm-redis"
  description                = "Redis cluster for LegalLLM Professional multi-agent system"
  
  # Node Configuration
  node_type               = "cache.r6g.large"  # 16GB memory, optimized for memory workloads
  port                    = 6379
  parameter_group_name    = aws_elasticache_parameter_group.legalllm_redis_params.name
  
  # Cluster Configuration
  num_cache_clusters      = 3  # 1 primary + 2 replicas
  automatic_failover_enabled = true
  multi_az_enabled        = true
  
  # Network Configuration
  subnet_group_name       = aws_elasticache_subnet_group.legalllm_cache_subnet_group.name
  security_group_ids      = [aws_security_group.redis_sg.id]
  
  # Data Protection
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.legalllm_kms.arn
  auth_token                 = var.redis_auth_token
  
  # Backup Configuration
  snapshot_retention_limit   = 7
  snapshot_window           = "03:00-05:00"  # UTC
  maintenance_window        = "sun:05:00-sun:07:00"  # UTC
  
  # Performance and Monitoring
  notification_topic_arn    = aws_sns_topic.legalllm_alerts.arn
  auto_minor_version_upgrade = true
  
  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }
  
  tags = {
    Name = "LegalLLM Redis Cluster"
    Purpose = "Multi-Agent Communication & Caching"
    Compliance = "Privacy Act 1988"
  }
}

# CloudWatch Log Group for Redis
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/legalllm-redis/slow-log"
  retention_in_days = 14
  kms_key_id       = aws_kms_key.legalllm_kms.arn
  
  tags = {
    Name = "LegalLLM Redis Slow Log"
  }
}

# Redis AUTH token variable
variable "redis_auth_token" {
  description = "Redis authentication token"
  type        = string
  sensitive   = true
}

# SNS Topic for ElastiCache notifications
resource "aws_sns_topic" "legalllm_alerts" {
  name              = "legalllm-alerts"
  kms_master_key_id = aws_kms_key.legalllm_kms.id
  
  tags = {
    Name = "LegalLLM Alert Notifications"
  }
}

# CloudWatch Alarms for Redis monitoring
resource "aws_cloudwatch_metric_alarm" "redis_cpu_utilization" {
  alarm_name          = "legalllm-redis-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors redis cpu utilization"
  alarm_actions       = [aws_sns_topic.legalllm_alerts.arn]
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.legalllm_redis.id
  }
  
  tags = {
    Name = "LegalLLM Redis CPU Alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory_utilization" {
  alarm_name          = "legalllm-redis-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors redis memory utilization"
  alarm_actions       = [aws_sns_topic.legalllm_alerts.arn]
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.legalllm_redis.id
  }
  
  tags = {
    Name = "LegalLLM Redis Memory Alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_connection_count" {
  alarm_name          = "legalllm-redis-connection-count"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "500"  # Adjust based on expected load
  alarm_description   = "This metric monitors redis connection count"
  alarm_actions       = [aws_sns_topic.legalllm_alerts.arn]
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.legalllm_redis.id
  }
  
  tags = {
    Name = "LegalLLM Redis Connection Alarm"
  }
}

# Additional Redis instance for session storage (separate from cache)
resource "aws_elasticache_replication_group" "legalllm_redis_sessions" {
  replication_group_id       = "legalllm-redis-sessions"
  description                = "Redis cluster for session storage and authentication"
  
  # Smaller configuration for sessions
  node_type               = "cache.r6g.medium"  # 8GB memory
  port                    = 6379
  parameter_group_name    = aws_elasticache_parameter_group.legalllm_redis_params.name
  
  # Cluster Configuration
  num_cache_clusters      = 2  # 1 primary + 1 replica
  automatic_failover_enabled = true
  multi_az_enabled        = true
  
  # Network Configuration
  subnet_group_name       = aws_elasticache_subnet_group.legalllm_cache_subnet_group.name
  security_group_ids      = [aws_security_group.redis_sg.id]
  
  # Data Protection
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.legalllm_kms.arn
  auth_token                 = var.redis_auth_token
  
  # Backup Configuration
  snapshot_retention_limit   = 5
  snapshot_window           = "04:00-05:00"  # UTC
  maintenance_window        = "sun:06:00-sun:07:00"  # UTC
  
  tags = {
    Name = "LegalLLM Redis Sessions"
    Purpose = "Session Storage & Authentication"
  }
}

# Outputs
output "redis_endpoint" {
  value = aws_elasticache_replication_group.legalllm_redis.configuration_endpoint_address
  description = "Redis cluster endpoint"
}

output "redis_port" {
  value = aws_elasticache_replication_group.legalllm_redis.port
  description = "Redis port"
}

output "redis_sessions_endpoint" {
  value = aws_elasticache_replication_group.legalllm_redis_sessions.configuration_endpoint_address
  description = "Redis sessions endpoint"
}

output "redis_auth_token_required" {
  value = true
  description = "Redis requires authentication token"
}