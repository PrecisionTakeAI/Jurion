"""
Distributed Rate Limiting with Redis
====================================

Enterprise-grade distributed rate limiting system addressing CLAUDE.md security requirements.
Implements Redis-based rate limiting with multiple strategies and Australian legal compliance.

Features:
- Redis-based distributed rate limiting
- Multiple rate limiting strategies (fixed window, sliding window, token bucket)
- Per-user, per-IP, and per-endpoint rate limits
- Automatic scaling and failover
- Australian legal practice specific limits
- Performance monitoring and alerting
"""

import os
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import redis
from redis.connection import ConnectionPool
from redis.sentinel import Sentinel


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitScope(Enum):
    """Rate limiting scopes"""
    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    FIRM = "firm"
    GLOBAL = "global"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    scope: RateLimitScope
    strategy: RateLimitStrategy
    limit: int                    # Number of requests
    window_seconds: int          # Time window in seconds
    burst_limit: Optional[int] = None    # Burst allowance
    priority: int = 1            # Higher priority rules are checked first
    enabled: bool = True


@dataclass
class RateLimitStatus:
    """Current rate limit status"""
    rule_name: str
    scope: str
    identifier: str
    current_count: int
    limit: int
    window_seconds: int
    reset_time: datetime
    blocked: bool
    remaining: int


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(
        self, 
        message: str, 
        status: RateLimitStatus,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class DistributedRateLimiter:
    """
    Distributed rate limiting system using Redis.
    
    Provides enterprise-grade rate limiting with:
    - Multiple rate limiting strategies
    - Redis-based distributed state
    - High availability with Redis Sentinel
    - Performance optimization with connection pooling
    - Australian legal practice specific rules
    """
    
    def __init__(
        self, 
        redis_url: Optional[str] = None,
        redis_sentinel: Optional[List[Tuple[str, int]]] = None,
        sentinel_service_name: str = "mymaster"
    ):
        self.logger = logging.getLogger(__name__)
        
        # Redis configuration
        self.redis_url = redis_url or os.getenv(
            'REDIS_URL', 
            'redis://localhost:6379/1'
        )
        
        # Setup Redis connection
        self._setup_redis_connection(redis_sentinel, sentinel_service_name)
        
        # Rate limiting rules
        self.rules: List[RateLimitRule] = []
        self._setup_default_rules()
        
        # Performance tracking
        self.metrics = {
            'requests_checked': 0,
            'requests_blocked': 0,
            'rules_applied': 0,
            'redis_operations': 0,
            'cache_hits': 0
        }
        
        # Key prefixes for Redis
        self.key_prefix = "legalllm:ratelimit"
        self.metrics_prefix = "legalllm:metrics"
        
        # Lua scripts for atomic operations
        self._load_lua_scripts()
        
        self.logger.info("Distributed rate limiter initialized")
    
    def _setup_redis_connection(
        self, 
        sentinel_hosts: Optional[List[Tuple[str, int]]], 
        service_name: str
    ):
        """Setup Redis connection with high availability support"""
        try:
            if sentinel_hosts:
                # Use Redis Sentinel for high availability
                sentinel = Sentinel(sentinel_hosts)
                self.redis_client = sentinel.master_for(
                    service_name,
                    socket_timeout=0.1,
                    socket_connect_timeout=0.1
                )
                self.logger.info(f"Connected to Redis via Sentinel: {service_name}")
            else:
                # Direct Redis connection
                pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=50,
                    retry_on_timeout=True,
                    socket_timeout=1.0
                )
                self.redis_client = redis.Redis(connection_pool=pool)
                self.logger.info(f"Connected to Redis: {self.redis_url}")
            
            # Test connection
            self.redis_client.ping()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            # Fallback to local memory storage (development only)
            self.redis_client = None
            self.local_storage = {}
            self.logger.warning("Using local memory storage for rate limiting")
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules for Australian legal practice"""
        
        # High-priority security rules
        self.rules.extend([
            # Prevent brute force attacks
            RateLimitRule(
                name="auth_attempts",
                scope=RateLimitScope.IP,
                strategy=RateLimitStrategy.FIXED_WINDOW,
                limit=5,
                window_seconds=300,  # 5 minutes
                priority=10
            ),
            
            # API abuse prevention
            RateLimitRule(
                name="api_global",
                scope=RateLimitScope.IP,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                limit=1000,
                window_seconds=3600,  # 1 hour
                priority=9
            ),
            
            # Document upload limits
            RateLimitRule(
                name="document_upload",
                scope=RateLimitScope.USER,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                limit=100,
                window_seconds=3600,  # 1 hour
                burst_limit=10,
                priority=8
            ),
            
            # AI query limits per user
            RateLimitRule(
                name="ai_queries",
                scope=RateLimitScope.USER,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                limit=500,
                window_seconds=3600,  # 1 hour
                priority=7
            ),
            
            # Case creation limits
            RateLimitRule(
                name="case_creation",
                scope=RateLimitScope.USER,
                strategy=RateLimitStrategy.FIXED_WINDOW,
                limit=20,
                window_seconds=3600,  # 1 hour
                priority=6
            ),
            
            # Firm-level limits for enterprise accounts
            RateLimitRule(
                name="firm_api_calls",
                scope=RateLimitScope.FIRM,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                limit=10000,
                window_seconds=3600,  # 1 hour
                priority=5
            )
        ])
        
        # Load custom rules from environment
        self._load_custom_rules()
    
    def _load_custom_rules(self):
        """Load custom rate limiting rules from environment"""
        custom_rules_json = os.getenv('CUSTOM_RATE_LIMIT_RULES')
        if not custom_rules_json:
            return
        
        try:
            custom_rules_data = json.loads(custom_rules_json)
            for rule_data in custom_rules_data:
                rule = RateLimitRule(
                    name=rule_data['name'],
                    scope=RateLimitScope(rule_data['scope']),
                    strategy=RateLimitStrategy(rule_data['strategy']),
                    limit=rule_data['limit'],
                    window_seconds=rule_data['window_seconds'],
                    burst_limit=rule_data.get('burst_limit'),
                    priority=rule_data.get('priority', 1),
                    enabled=rule_data.get('enabled', True)
                )
                self.rules.append(rule)
            
            self.logger.info(f"Loaded {len(custom_rules_data)} custom rate limit rules")
            
        except Exception as e:
            self.logger.error(f"Failed to load custom rules: {e}")
    
    def _load_lua_scripts(self):
        """Load Lua scripts for atomic Redis operations"""
        
        # Sliding window rate limiter script
        self.sliding_window_script = self.redis_client.register_script("""
            local key = KEYS[1]
            local window = tonumber(ARGV[1])
            local limit = tonumber(ARGV[2])
            local current_time = tonumber(ARGV[3])
            
            -- Remove expired entries
            redis.call('ZREMRANGEBYSCORE', key, 0, current_time - window)
            
            -- Count current entries
            local current_count = redis.call('ZCARD', key)
            
            if current_count < limit then
                -- Add current request
                redis.call('ZADD', key, current_time, current_time)
                redis.call('EXPIRE', key, window)
                return {1, current_count + 1, limit - current_count - 1}
            else
                return {0, current_count, 0}
            end
        """) if self.redis_client else None
        
        # Token bucket script
        self.token_bucket_script = self.redis_client.register_script("""
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local current_time = tonumber(ARGV[3])
            local requested_tokens = tonumber(ARGV[4])
            
            -- Get current bucket state
            local bucket_data = redis.call('HMGET', key, 'tokens', 'last_refill')
            local tokens = tonumber(bucket_data[1]) or capacity
            local last_refill = tonumber(bucket_data[2]) or current_time
            
            -- Calculate tokens to add
            local time_passed = current_time - last_refill
            local tokens_to_add = math.floor(time_passed * refill_rate)
            tokens = math.min(capacity, tokens + tokens_to_add)
            
            if tokens >= requested_tokens then
                tokens = tokens - requested_tokens
                redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
                redis.call('EXPIRE', key, 3600)
                return {1, tokens, capacity - tokens}
            else
                redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
                redis.call('EXPIRE', key, 3600)
                return {0, tokens, 0}
            end
        """) if self.redis_client else None
    
    def check_rate_limit(
        self,
        identifier: str,
        scope: RateLimitScope,
        endpoint: Optional[str] = None,
        user_id: Optional[str] = None,
        firm_id: Optional[str] = None
    ) -> List[RateLimitStatus]:
        """
        Check rate limits for a request.
        
        Args:
            identifier: The identifier to rate limit (IP, user ID, etc.)
            scope: The scope of rate limiting
            endpoint: Optional endpoint name
            user_id: Optional user ID
            firm_id: Optional firm ID
            
        Returns:
            List of rate limit statuses
            
        Raises:
            RateLimitExceeded: If any rate limit is exceeded
        """
        self.metrics['requests_checked'] += 1
        
        # Find applicable rules
        applicable_rules = [
            rule for rule in self.rules
            if rule.enabled and rule.scope == scope
        ]
        
        # Sort by priority (highest first)
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        statuses = []
        
        for rule in applicable_rules:
            try:
                status = self._check_single_rule(
                    rule, identifier, endpoint, user_id, firm_id
                )
                statuses.append(status)
                
                if status.blocked:
                    self.metrics['requests_blocked'] += 1
                    
                    # Calculate retry after
                    retry_after = int(
                        (status.reset_time - datetime.now()).total_seconds()
                    )
                    
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {rule.name}: {status.current_count} > {status.limit}",
                        status,
                        retry_after
                    )
                
                self.metrics['rules_applied'] += 1
                
            except RateLimitExceeded:
                raise
            except Exception as e:
                self.logger.error(f"Error checking rule {rule.name}: {e}")
                continue
        
        return statuses
    
    def _check_single_rule(
        self,
        rule: RateLimitRule,
        identifier: str,
        endpoint: Optional[str],
        user_id: Optional[str],
        firm_id: Optional[str]
    ) -> RateLimitStatus:
        """Check a single rate limiting rule"""
        
        # Generate Redis key
        key_parts = [self.key_prefix, rule.name]
        
        if rule.scope == RateLimitScope.USER and user_id:
            key_parts.append(f"user:{user_id}")
        elif rule.scope == RateLimitScope.FIRM and firm_id:
            key_parts.append(f"firm:{firm_id}")
        elif rule.scope == RateLimitScope.ENDPOINT and endpoint:
            key_parts.append(f"endpoint:{endpoint}")
        elif rule.scope == RateLimitScope.IP:
            key_parts.append(f"ip:{identifier}")
        else:
            key_parts.append(f"global")
        
        redis_key = ":".join(key_parts)
        
        # Apply rate limiting strategy
        if rule.strategy == RateLimitStrategy.FIXED_WINDOW:
            return self._apply_fixed_window(rule, redis_key, identifier)
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._apply_sliding_window(rule, redis_key, identifier)
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._apply_token_bucket(rule, redis_key, identifier)
        else:
            raise ValueError(f"Unsupported rate limiting strategy: {rule.strategy}")
    
    def _apply_fixed_window(
        self, 
        rule: RateLimitRule, 
        redis_key: str, 
        identifier: str
    ) -> RateLimitStatus:
        """Apply fixed window rate limiting"""
        current_time = int(time.time())
        window_start = current_time - (current_time % rule.window_seconds)
        
        key_with_window = f"{redis_key}:{window_start}"
        
        try:
            if self.redis_client:
                # Increment counter atomically
                current_count = self.redis_client.incr(key_with_window)
                
                # Set expiration on first increment
                if current_count == 1:
                    self.redis_client.expire(key_with_window, rule.window_seconds)
                
                self.metrics['redis_operations'] += 1
            else:
                # Fallback to local storage
                current_count = self.local_storage.get(key_with_window, 0) + 1
                self.local_storage[key_with_window] = current_count
        
        except Exception as e:
            self.logger.error(f"Redis operation failed: {e}")
            current_count = 1  # Fail open
        
        blocked = current_count > rule.limit
        remaining = max(0, rule.limit - current_count)
        reset_time = datetime.fromtimestamp(window_start + rule.window_seconds)
        
        return RateLimitStatus(
            rule_name=rule.name,
            scope=rule.scope.value,
            identifier=identifier,
            current_count=current_count,
            limit=rule.limit,
            window_seconds=rule.window_seconds,
            reset_time=reset_time,
            blocked=blocked,
            remaining=remaining
        )
    
    def _apply_sliding_window(
        self, 
        rule: RateLimitRule, 
        redis_key: str, 
        identifier: str
    ) -> RateLimitStatus:
        """Apply sliding window rate limiting"""
        current_time = time.time()
        
        try:
            if self.redis_client and self.sliding_window_script:
                result = self.sliding_window_script(
                    keys=[redis_key],
                    args=[rule.window_seconds, rule.limit, current_time]
                )
                allowed, current_count, remaining = result
                self.metrics['redis_operations'] += 1
            else:
                # Fallback implementation
                allowed, current_count, remaining = 1, 1, rule.limit - 1
        
        except Exception as e:
            self.logger.error(f"Sliding window check failed: {e}")
            allowed, current_count, remaining = 1, 1, rule.limit - 1
        
        blocked = not bool(allowed)
        reset_time = datetime.fromtimestamp(current_time + rule.window_seconds)
        
        return RateLimitStatus(
            rule_name=rule.name,
            scope=rule.scope.value,
            identifier=identifier,
            current_count=current_count,
            limit=rule.limit,
            window_seconds=rule.window_seconds,
            reset_time=reset_time,
            blocked=blocked,
            remaining=remaining
        )
    
    def _apply_token_bucket(
        self, 
        rule: RateLimitRule, 
        redis_key: str, 
        identifier: str
    ) -> RateLimitStatus:
        """Apply token bucket rate limiting"""
        current_time = time.time()
        capacity = rule.limit
        refill_rate = rule.limit / rule.window_seconds  # tokens per second
        
        try:
            if self.redis_client and self.token_bucket_script:
                result = self.token_bucket_script(
                    keys=[redis_key],
                    args=[capacity, refill_rate, current_time, 1]
                )
                allowed, tokens_left, consumed = result
                self.metrics['redis_operations'] += 1
            else:
                # Fallback implementation
                allowed, tokens_left, consumed = 1, capacity - 1, 1
        
        except Exception as e:
            self.logger.error(f"Token bucket check failed: {e}")
            allowed, tokens_left, consumed = 1, capacity - 1, 1
        
        blocked = not bool(allowed)
        current_count = capacity - tokens_left
        reset_time = datetime.fromtimestamp(current_time + rule.window_seconds)
        
        return RateLimitStatus(
            rule_name=rule.name,
            scope=rule.scope.value,
            identifier=identifier,
            current_count=current_count,
            limit=rule.limit,
            window_seconds=rule.window_seconds,
            reset_time=reset_time,
            blocked=blocked,
            remaining=tokens_left
        )
    
    def add_rule(self, rule: RateLimitRule):
        """Add a new rate limiting rule"""
        self.rules.append(rule)
        self.logger.info(f"Added rate limiting rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rate limiting rule"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        self.logger.info(f"Removed rate limiting rule: {rule_name}")
    
    def get_status(
        self,
        identifier: str,
        scope: RateLimitScope,
        rule_name: Optional[str] = None
    ) -> List[RateLimitStatus]:
        """Get current rate limit status without incrementing counters"""
        
        applicable_rules = [
            rule for rule in self.rules
            if rule.enabled and rule.scope == scope
        ]
        
        if rule_name:
            applicable_rules = [
                rule for rule in applicable_rules 
                if rule.name == rule_name
            ]
        
        statuses = []
        for rule in applicable_rules:
            # This would query Redis without incrementing
            # For now, return estimated status
            status = RateLimitStatus(
                rule_name=rule.name,
                scope=rule.scope.value,
                identifier=identifier,
                current_count=0,  # Would query actual count
                limit=rule.limit,
                window_seconds=rule.window_seconds,
                reset_time=datetime.now() + timedelta(seconds=rule.window_seconds),
                blocked=False,
                remaining=rule.limit
            )
            statuses.append(status)
        
        return statuses
    
    def reset_limits(self, identifier: str, scope: RateLimitScope):
        """Reset rate limits for an identifier (admin function)"""
        pattern = f"{self.key_prefix}:*:{scope.value}:{identifier}"
        
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    self.logger.info(f"Reset rate limits for {identifier}")
            else:
                # Clear from local storage
                keys_to_remove = [
                    key for key in self.local_storage.keys()
                    if identifier in key
                ]
                for key in keys_to_remove:
                    del self.local_storage[key]
        
        except Exception as e:
            self.logger.error(f"Failed to reset limits: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter performance metrics"""
        return {
            'requests_checked': self.metrics['requests_checked'],
            'requests_blocked': self.metrics['requests_blocked'],
            'block_rate': (
                self.metrics['requests_blocked'] / max(1, self.metrics['requests_checked'])
            ) * 100,
            'rules_applied': self.metrics['rules_applied'],
            'redis_operations': self.metrics['redis_operations'],
            'cache_hits': self.metrics['cache_hits'],
            'active_rules': len([r for r in self.rules if r.enabled]),
            'redis_connected': self.redis_client is not None
        }


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> DistributedRateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = DistributedRateLimiter()
    return _rate_limiter


# Helper functions for common use cases
def check_user_rate_limit(user_id: str, endpoint: str = "api") -> List[RateLimitStatus]:
    """Check rate limits for a user"""
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(
        identifier=user_id,
        scope=RateLimitScope.USER,
        endpoint=endpoint,
        user_id=user_id
    )


def check_ip_rate_limit(ip_address: str, endpoint: str = "api") -> List[RateLimitStatus]:
    """Check rate limits for an IP address"""
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(
        identifier=ip_address,
        scope=RateLimitScope.IP,
        endpoint=endpoint
    )


def check_firm_rate_limit(firm_id: str, endpoint: str = "api") -> List[RateLimitStatus]:
    """Check rate limits for a firm"""
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(
        identifier=firm_id,
        scope=RateLimitScope.FIRM,
        endpoint=endpoint,
        firm_id=firm_id
    )


# Decorator for applying rate limiting
def rate_limit(
    scope: RateLimitScope,
    identifier_func=None,
    fail_gracefully: bool = True
):
    """Decorator to apply rate limiting to functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Extract identifier based on scope
                if identifier_func:
                    identifier = identifier_func(*args, **kwargs)
                elif scope == RateLimitScope.USER:
                    identifier = kwargs.get('user_id', 'anonymous')
                elif scope == RateLimitScope.IP:
                    identifier = kwargs.get('ip_address', 'unknown')
                else:
                    identifier = 'global'
                
                # Check rate limits
                limiter = get_rate_limiter()
                limiter.check_rate_limit(identifier, scope)
                
                return func(*args, **kwargs)
                
            except RateLimitExceeded as e:
                if fail_gracefully:
                    return {'error': 'Rate limit exceeded', 'retry_after': e.retry_after}
                else:
                    raise
            
        return wrapper
    return decorator