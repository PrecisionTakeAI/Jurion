"""
Redis Cache Manager with Connection Pooling
==========================================

Enterprise-grade Redis caching system addressing CLAUDE.md performance requirements.
Implements strategic caching for legal document processing and AI responses.

Features:
- Connection pooling for high performance
- Multiple cache invalidation strategies
- TTL management for different data types
- Compression for large objects
- Performance monitoring and metrics
- Australian legal data compliance
"""

import os
import json
import time
import zlib
import pickle
import hashlib
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import redis
from redis.connection import ConnectionPool
from redis.sentinel import Sentinel


class CacheStrategy(Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"                    # Time-based expiration
    LRU = "lru"                    # Least Recently Used
    WRITE_THROUGH = "write_through" # Update cache on write
    WRITE_BEHIND = "write_behind"   # Async cache update
    REFRESH_AHEAD = "refresh_ahead" # Proactive refresh


@dataclass
class CacheKey:
    """Cache key with metadata"""
    key: str
    namespace: str
    tags: List[str]
    ttl_seconds: Optional[int] = None
    strategy: CacheStrategy = CacheStrategy.TTL
    
    def full_key(self) -> str:
        """Get full Redis key with namespace"""
        return f"legalllm:{self.namespace}:{self.key}"


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    memory_usage_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class CacheError(Exception):
    """Exception raised for cache operations"""
    pass


class RedisCacheManager:
    """
    Enterprise-grade Redis cache manager with advanced features.
    
    Provides high-performance caching with:
    - Connection pooling for scalability
    - Multiple invalidation strategies
    - Automatic compression for large objects
    - Performance monitoring and alerting
    - Legal document specific optimizations
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_sentinel: Optional[List[Tuple[str, int]]] = None,
        sentinel_service_name: str = "mymaster",
        max_connections: int = 50,
        compression_threshold: int = 1024
    ):
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.compression_threshold = compression_threshold
        self.max_connections = max_connections
        
        # Setup Redis connection
        self._setup_redis_connection(redis_sentinel, sentinel_service_name)
        
        # Cache metrics
        self.metrics = CacheMetrics()
        self.namespace_metrics: Dict[str, CacheMetrics] = {}
        
        # Cache configuration
        self.default_ttl = int(os.getenv('CACHE_DEFAULT_TTL', '3600'))  # 1 hour
        self.max_memory_policy = os.getenv('CACHE_MAX_MEMORY_POLICY', 'allkeys-lru')
        
        # Legal-specific cache configurations
        self._setup_legal_cache_configs()
        
        # Lua scripts for atomic operations
        self._load_lua_scripts()
        
        self.logger.info("Redis cache manager initialized")
    
    def _setup_redis_connection(
        self,
        sentinel_hosts: Optional[List[Tuple[str, int]]],
        service_name: str
    ):
        """Setup Redis connection with high availability"""
        try:
            if sentinel_hosts:
                # Redis Sentinel for high availability
                sentinel = Sentinel(sentinel_hosts)
                self.redis_client = sentinel.master_for(
                    service_name,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0,
                    decode_responses=False  # We handle encoding ourselves
                )
                self.logger.info(f"Connected to Redis via Sentinel: {service_name}")
            else:
                # Direct Redis connection with pool
                pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    retry_on_timeout=True,
                    socket_timeout=2.0,
                    decode_responses=False
                )
                self.redis_client = redis.Redis(connection_pool=pool)
                self.logger.info(f"Connected to Redis with pool size: {self.max_connections}")
            
            # Test connection
            self.redis_client.ping()
            
            # Configure Redis memory policy
            try:
                self.redis_client.config_set('maxmemory-policy', self.max_memory_policy)
            except redis.ResponseError:
                self.logger.warning("Could not set maxmemory-policy")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise CacheError(f"Redis connection failed: {e}")
    
    def _setup_legal_cache_configs(self):
        """Setup cache configurations for legal document types"""
        self.cache_configs = {
            # Case data - moderate TTL, high priority
            'cases': {
                'ttl': 7200,  # 2 hours
                'compress': True,
                'strategy': CacheStrategy.WRITE_THROUGH
            },
            
            # Document analysis results - long TTL
            'documents': {
                'ttl': 86400,  # 24 hours
                'compress': True,
                'strategy': CacheStrategy.TTL
            },
            
            # AI responses - medium TTL, compression for large responses
            'ai_responses': {
                'ttl': 3600,  # 1 hour
                'compress': True,
                'strategy': CacheStrategy.LRU
            },
            
            # User sessions - short TTL
            'sessions': {
                'ttl': 1800,  # 30 minutes
                'compress': False,
                'strategy': CacheStrategy.TTL
            },
            
            # Legal research - long TTL (legal precedents don't change often)
            'legal_research': {
                'ttl': 604800,  # 1 week
                'compress': True,
                'strategy': CacheStrategy.TTL
            },
            
            # Financial calculations - medium TTL with write-through
            'financial': {
                'ttl': 14400,  # 4 hours
                'compress': True,
                'strategy': CacheStrategy.WRITE_THROUGH
            },
            
            # Form templates - very long TTL
            'templates': {
                'ttl': 2592000,  # 30 days
                'compress': True,
                'strategy': CacheStrategy.TTL
            }
        }
    
    def _load_lua_scripts(self):
        """Load Lua scripts for atomic cache operations"""
        
        # Get with metadata script
        self.get_with_metadata_script = self.redis_client.register_script("""
            local key = KEYS[1]
            local value = redis.call('GET', key)
            local ttl = redis.call('TTL', key)
            
            if value then
                return {value, ttl}
            else
                return nil
            end
        """)
        
        # Set with tags script
        self.set_with_tags_script = self.redis_client.register_script("""
            local key = KEYS[1]
            local value = ARGV[1]
            local ttl = tonumber(ARGV[2])
            local tags = cjson.decode(ARGV[3])
            
            -- Set the main key
            if ttl > 0 then
                redis.call('SETEX', key, ttl, value)
            else
                redis.call('SET', key, value)
            end
            
            -- Add to tag sets for invalidation
            for i, tag in ipairs(tags) do
                local tag_key = 'tags:' .. tag
                redis.call('SADD', tag_key, key)
                if ttl > 0 then
                    redis.call('EXPIRE', tag_key, ttl + 300)  -- Tag expires 5 min after data
                end
            end
        """)
        
        # Invalidate by tags script
        self.invalidate_by_tags_script = self.redis_client.register_script("""
            local tags = ARGV
            local keys_to_delete = {}
            
            for i, tag in ipairs(tags) do
                local tag_key = 'tags:' .. tag
                local tagged_keys = redis.call('SMEMBERS', tag_key)
                
                for j, key in ipairs(tagged_keys) do
                    table.insert(keys_to_delete, key)
                end
                
                -- Delete the tag set
                redis.call('DEL', tag_key)
            end
            
            -- Delete all tagged keys
            if #keys_to_delete > 0 then
                redis.call('DEL', unpack(keys_to_delete))
            end
            
            return #keys_to_delete
        """)
    
    def get(
        self,
        cache_key: Union[str, CacheKey],
        namespace: str = "default",
        default: Any = None
    ) -> Any:
        """
        Get value from cache.
        
        Args:
            cache_key: Cache key (string or CacheKey object)
            namespace: Cache namespace
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            # Handle both string keys and CacheKey objects
            if isinstance(cache_key, str):
                redis_key = f"legalllm:{namespace}:{cache_key}"
            else:
                redis_key = cache_key.full_key()
                namespace = cache_key.namespace
            
            # Get value from Redis
            result = self.get_with_metadata_script(keys=[redis_key])
            
            if result:
                value_bytes, ttl = result
                
                # Update metrics
                self.metrics.hits += 1
                self._update_namespace_metrics(namespace, 'hit')
                
                # Deserialize value
                value = self._deserialize(value_bytes)
                
                self.logger.debug(f"Cache hit for key: {redis_key} (TTL: {ttl}s)")
                return value
            else:
                # Cache miss
                self.metrics.misses += 1
                self._update_namespace_metrics(namespace, 'miss')
                
                self.logger.debug(f"Cache miss for key: {redis_key}")
                return default
                
        except Exception as e:
            self.logger.error(f"Cache get error for key {cache_key}: {e}")
            self.metrics.misses += 1
            return default
    
    def set(
        self,
        cache_key: Union[str, CacheKey],
        value: Any,
        namespace: str = "default",
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        compress: Optional[bool] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            cache_key: Cache key (string or CacheKey object)
            value: Value to cache
            namespace: Cache namespace
            ttl: Time to live in seconds
            tags: Tags for invalidation
            compress: Whether to compress the value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle both string keys and CacheKey objects
            if isinstance(cache_key, str):
                redis_key = f"legalllm:{namespace}:{cache_key}"
                cache_config = self.cache_configs.get(namespace, {})
                ttl = ttl or cache_config.get('ttl', self.default_ttl)
                tags = tags or []
                compress = compress if compress is not None else cache_config.get('compress', False)
            else:
                redis_key = cache_key.full_key()
                namespace = cache_key.namespace
                ttl = ttl or cache_key.ttl_seconds or self.default_ttl
                tags = tags or cache_key.tags
                cache_config = self.cache_configs.get(namespace, {})
                compress = compress if compress is not None else cache_config.get('compress', False)
            
            # Serialize value
            serialized_value = self._serialize(value, compress)
            
            # Set in Redis with tags
            if tags:
                self.set_with_tags_script(
                    keys=[redis_key],
                    args=[serialized_value, ttl, json.dumps(tags)]
                )
            else:
                # Simple set without tags
                if ttl > 0:
                    self.redis_client.setex(redis_key, ttl, serialized_value)
                else:
                    self.redis_client.set(redis_key, serialized_value)
            
            # Update metrics
            self.metrics.sets += 1
            self._update_namespace_metrics(namespace, 'set')
            
            self.logger.debug(f"Cache set for key: {redis_key} (TTL: {ttl}s, Tags: {tags})")
            return True
            
        except Exception as e:
            self.logger.error(f"Cache set error for key {cache_key}: {e}")
            return False
    
    def delete(
        self,
        cache_key: Union[str, CacheKey],
        namespace: str = "default"
    ) -> bool:
        """
        Delete value from cache.
        
        Args:
            cache_key: Cache key to delete
            namespace: Cache namespace
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            # Handle both string keys and CacheKey objects
            if isinstance(cache_key, str):
                redis_key = f"legalllm:{namespace}:{cache_key}"
            else:
                redis_key = cache_key.full_key()
                namespace = cache_key.namespace
            
            # Delete from Redis
            deleted = self.redis_client.delete(redis_key)
            
            if deleted:
                self.metrics.deletes += 1
                self._update_namespace_metrics(namespace, 'delete')
                self.logger.debug(f"Cache delete for key: {redis_key}")
            
            return deleted > 0
            
        except Exception as e:
            self.logger.error(f"Cache delete error for key {cache_key}: {e}")
            return False
    
    def invalidate_by_tags(self, tags: List[str]) -> int:
        """
        Invalidate all cache entries with given tags.
        
        Args:
            tags: List of tags to invalidate
            
        Returns:
            Number of keys deleted
        """
        try:
            deleted_count = self.invalidate_by_tags_script(args=tags)
            
            self.metrics.deletes += deleted_count
            self.logger.info(f"Invalidated {deleted_count} keys with tags: {tags}")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Tag invalidation error for tags {tags}: {e}")
            return 0
    
    def invalidate_namespace(self, namespace: str) -> int:
        """
        Invalidate all cache entries in a namespace.
        
        Args:
            namespace: Namespace to invalidate
            
        Returns:
            Number of keys deleted
        """
        try:
            pattern = f"legalllm:{namespace}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                self.metrics.deletes += deleted
                self.logger.info(f"Invalidated {deleted} keys in namespace: {namespace}")
                return deleted
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Namespace invalidation error for {namespace}: {e}")
            return 0
    
    def exists(
        self,
        cache_key: Union[str, CacheKey],
        namespace: str = "default"
    ) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            cache_key: Cache key to check
            namespace: Cache namespace
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            if isinstance(cache_key, str):
                redis_key = f"legalllm:{namespace}:{cache_key}"
            else:
                redis_key = cache_key.full_key()
            
            return bool(self.redis_client.exists(redis_key))
            
        except Exception as e:
            self.logger.error(f"Cache exists check error for key {cache_key}: {e}")
            return False
    
    def get_ttl(
        self,
        cache_key: Union[str, CacheKey],
        namespace: str = "default"
    ) -> int:
        """
        Get TTL for cache key.
        
        Args:
            cache_key: Cache key
            namespace: Cache namespace
            
        Returns:
            TTL in seconds (-1 if no TTL, -2 if key doesn't exist)
        """
        try:
            if isinstance(cache_key, str):
                redis_key = f"legalllm:{namespace}:{cache_key}"
            else:
                redis_key = cache_key.full_key()
            
            return self.redis_client.ttl(redis_key)
            
        except Exception as e:
            self.logger.error(f"Cache TTL check error for key {cache_key}: {e}")
            return -2
    
    def extend_ttl(
        self,
        cache_key: Union[str, CacheKey],
        ttl: int,
        namespace: str = "default"
    ) -> bool:
        """
        Extend TTL for cache key.
        
        Args:
            cache_key: Cache key
            ttl: New TTL in seconds
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if isinstance(cache_key, str):
                redis_key = f"legalllm:{namespace}:{cache_key}"
            else:
                redis_key = cache_key.full_key()
            
            return bool(self.redis_client.expire(redis_key, ttl))
            
        except Exception as e:
            self.logger.error(f"Cache TTL extend error for key {cache_key}: {e}")
            return False
    
    def get_or_set(
        self,
        cache_key: Union[str, CacheKey],
        factory_func: Callable[[], Any],
        namespace: str = "default",
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Any:
        """
        Get value from cache or set it using factory function.
        
        Args:
            cache_key: Cache key
            factory_func: Function to generate value if not cached
            namespace: Cache namespace
            ttl: Time to live in seconds
            tags: Tags for invalidation
            
        Returns:
            Cached or generated value
        """
        # Try to get from cache first
        value = self.get(cache_key, namespace)
        
        if value is not None:
            return value
        
        # Generate value and cache it
        try:
            value = factory_func()
            
            if value is not None:
                self.set(cache_key, value, namespace, ttl, tags)
            
            return value
            
        except Exception as e:
            self.logger.error(f"Factory function error for key {cache_key}: {e}")
            return None
    
    def increment(
        self,
        cache_key: Union[str, CacheKey],
        amount: int = 1,
        namespace: str = "default",
        ttl: Optional[int] = None
    ) -> int:
        """
        Increment numeric value in cache.
        
        Args:
            cache_key: Cache key
            amount: Amount to increment by
            namespace: Cache namespace
            ttl: TTL for new keys
            
        Returns:
            New value after increment
        """
        try:
            if isinstance(cache_key, str):
                redis_key = f"legalllm:{namespace}:{cache_key}"
            else:
                redis_key = cache_key.full_key()
            
            # Increment
            new_value = self.redis_client.incrby(redis_key, amount)
            
            # Set TTL if this is a new key
            if ttl and new_value == amount:
                self.redis_client.expire(redis_key, ttl)
            
            return new_value
            
        except Exception as e:
            self.logger.error(f"Cache increment error for key {cache_key}: {e}")
            return 0
    
    def _serialize(self, value: Any, compress: bool = False) -> bytes:
        """Serialize value for storage"""
        try:
            # Use pickle for Python objects
            serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Apply compression if requested and value is large enough
            if compress and len(serialized) > self.compression_threshold:
                compressed = zlib.compress(serialized)
                # Add compression flag
                return b'COMPRESSED:' + compressed
            
            return serialized
            
        except Exception as e:
            self.logger.error(f"Serialization error: {e}")
            raise CacheError(f"Failed to serialize value: {e}")
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            # Check for compression flag
            if data.startswith(b'COMPRESSED:'):
                compressed_data = data[11:]  # Remove 'COMPRESSED:' prefix
                data = zlib.decompress(compressed_data)
            
            # Deserialize with pickle
            return pickle.loads(data)
            
        except Exception as e:
            self.logger.error(f"Deserialization error: {e}")
            raise CacheError(f"Failed to deserialize value: {e}")
    
    def _update_namespace_metrics(self, namespace: str, operation: str):
        """Update metrics for specific namespace"""
        if namespace not in self.namespace_metrics:
            self.namespace_metrics[namespace] = CacheMetrics()
        
        if operation == 'hit':
            self.namespace_metrics[namespace].hits += 1
        elif operation == 'miss':
            self.namespace_metrics[namespace].misses += 1
        elif operation == 'set':
            self.namespace_metrics[namespace].sets += 1
        elif operation == 'delete':
            self.namespace_metrics[namespace].deletes += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            # Redis info
            redis_info = self.redis_client.info('memory')
            
            # Connection pool info
            pool_info = {}
            if hasattr(self.redis_client.connection_pool, 'connection_kwargs'):
                pool_info = {
                    'max_connections': self.redis_client.connection_pool.max_connections,
                    'created_connections': len(self.redis_client.connection_pool._created_connections),
                    'available_connections': len(self.redis_client.connection_pool._available_connections),
                    'in_use_connections': len(self.redis_client.connection_pool._in_use_connections)
                }
            
            return {
                'global_metrics': asdict(self.metrics),
                'namespace_metrics': {
                    ns: asdict(metrics) for ns, metrics in self.namespace_metrics.items()
                },
                'redis_memory': {
                    'used_memory': redis_info.get('used_memory', 0),
                    'used_memory_human': redis_info.get('used_memory_human', '0B'),
                    'used_memory_peak': redis_info.get('used_memory_peak', 0),
                    'used_memory_peak_human': redis_info.get('used_memory_peak_human', '0B')
                },
                'connection_pool': pool_info,
                'cache_configs': self.cache_configs
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform cache health check"""
        try:
            start_time = time.time()
            
            # Test basic operations
            test_key = f"health_check:{int(time.time())}"
            test_value = "health_check_value"
            
            # Set test value
            self.redis_client.set(test_key, test_value, ex=60)
            
            # Get test value
            retrieved = self.redis_client.get(test_key)
            
            # Delete test value
            self.redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'redis_connected': True,
                'operations_test': retrieved.decode() == test_value if retrieved else False,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Cache health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'redis_connected': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def clear_all(self, namespace: Optional[str] = None) -> int:
        """
        Clear all cache entries (use with caution).
        
        Args:
            namespace: Optional namespace to clear (clears all if None)
            
        Returns:
            Number of keys deleted
        """
        try:
            if namespace:
                return self.invalidate_namespace(namespace)
            else:
                # Clear all legalllm keys
                pattern = "legalllm:*"
                keys = self.redis_client.keys(pattern)
                
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    self.logger.warning(f"Cleared all cache: {deleted} keys deleted")
                    return deleted
                
                return 0
                
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
            return 0


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> RedisCacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = RedisCacheManager()
    return _cache_manager


# Helper functions for common cache operations
def cache_get(key: str, namespace: str = "default", default: Any = None) -> Any:
    """Helper function to get from cache"""
    manager = get_cache_manager()
    return manager.get(key, namespace, default)


def cache_set(
    key: str, 
    value: Any, 
    namespace: str = "default", 
    ttl: Optional[int] = None,
    tags: Optional[List[str]] = None
) -> bool:
    """Helper function to set cache value"""
    manager = get_cache_manager()
    return manager.set(key, value, namespace, ttl, tags)


def cache_delete(key: str, namespace: str = "default") -> bool:
    """Helper function to delete from cache"""
    manager = get_cache_manager()
    return manager.delete(key, namespace)


def cache_invalidate_tags(tags: List[str]) -> int:
    """Helper function to invalidate by tags"""
    manager = get_cache_manager()
    return manager.invalidate_by_tags(tags)