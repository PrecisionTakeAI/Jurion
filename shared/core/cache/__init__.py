"""
Enhanced Caching Infrastructure for LegalLLM Professional
========================================================

Comprehensive Redis-based caching system addressing CLAUDE.md performance requirements:
- Connection pooling for Redis
- Strategic caching points for performance optimization
- Cache invalidation strategies
- TTL management for different data types
- Performance monitoring and metrics

This module provides enterprise-grade caching capabilities for Australian legal AI applications.
"""

from .redis_cache_manager import (
    RedisCacheManager, 
    CacheStrategy,
    CacheKey,
    CacheMetrics,
    CacheError
)
from .cache_decorators import (
    cached,
    cache_result,
    invalidate_cache,
    cache_aside
)

__all__ = [
    'RedisCacheManager',
    'CacheStrategy',
    'CacheKey', 
    'CacheMetrics',
    'CacheError',
    'cached',
    'cache_result',
    'invalidate_cache',
    'cache_aside'
]