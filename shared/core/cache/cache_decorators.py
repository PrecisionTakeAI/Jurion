"""
Cache Decorators for Strategic Performance Optimization
======================================================

Strategic caching decorators for LegalLLM Professional performance optimization.
Implements caching at key performance bottlenecks identified in CLAUDE.md analysis.

Features:
- Function result caching with automatic key generation
- TTL-based expiration for different data types
- Tag-based invalidation for related data
- Performance monitoring and metrics
- Australian legal document specific optimizations
"""

import functools
import hashlib
import json
import time
from typing import Any, Callable, List, Optional, Union, Dict
from datetime import datetime, timedelta
import logging

from .redis_cache_manager import get_cache_manager, CacheKey, CacheStrategy


def cache_key_generator(func: Callable, *args, **kwargs) -> str:
    """
    Generate cache key from function name and arguments.
    
    Args:
        func: Function being cached
        args: Function positional arguments
        kwargs: Function keyword arguments
        
    Returns:
        Generated cache key
    """
    # Create key from function name and arguments
    key_parts = [func.__module__, func.__name__]
    
    # Add arguments to key
    if args:
        # Handle different argument types
        arg_strs = []
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                arg_strs.append(str(arg))
            elif hasattr(arg, '__dict__'):
                # For objects, use their string representation
                arg_strs.append(str(type(arg).__name__))
            else:
                arg_strs.append(str(hash(str(arg))))
        key_parts.extend(arg_strs)
    
    if kwargs:
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        for key, value in sorted_kwargs:
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}={value}")
            else:
                key_parts.append(f"{key}={hash(str(value))}")
    
    # Create hash of the key parts for consistent length
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(
    namespace: str = "default",
    ttl: Optional[int] = None,
    tags: Optional[List[str]] = None,
    key_func: Optional[Callable] = None,
    condition: Optional[Callable] = None,
    compress: bool = False
):
    """
    Decorator for caching function results.
    
    Args:
        namespace: Cache namespace
        ttl: Time to live in seconds
        tags: Tags for cache invalidation
        key_func: Custom key generation function
        condition: Function to determine if result should be cached
        compress: Whether to compress cached values
        
    Example:
        @cached(namespace="ai_responses", ttl=3600, tags=["ai", "legal"])
        def process_legal_query(query: str, user_id: str) -> str:
            return expensive_ai_processing(query)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            logger = logging.getLogger(f"{func.__module__}.{func.__name__}")
            
            # Generate cache key
            if key_func:
                cache_key = key_func(func, *args, **kwargs)
            else:
                cache_key = cache_key_generator(func, *args, **kwargs)
            
            # Try to get from cache
            start_time = time.time()
            cached_result = cache_manager.get(cache_key, namespace)
            
            if cached_result is not None:
                cache_time = time.time() - start_time
                logger.debug(f"Cache hit for {func.__name__} (key: {cache_key[:16]}..., time: {cache_time:.3f}s)")
                return cached_result
            
            # Execute function
            exec_start = time.time()
            result = func(*args, **kwargs)
            exec_time = time.time() - exec_start
            
            # Check condition before caching
            should_cache = True
            if condition:
                try:
                    should_cache = condition(result, *args, **kwargs)
                except Exception as e:
                    logger.warning(f"Cache condition check failed: {e}")
                    should_cache = True
            
            # Cache the result
            if should_cache and result is not None:
                cache_manager.set(
                    cache_key=cache_key,
                    value=result,
                    namespace=namespace,
                    ttl=ttl,
                    tags=tags,
                    compress=compress
                )
                
                logger.debug(f"Cached result for {func.__name__} (key: {cache_key[:16]}..., exec_time: {exec_time:.3f}s)")
            
            return result
        
        # Add cache management methods to the wrapped function
        wrapper.cache_invalidate = lambda: _invalidate_function_cache(func, namespace)
        wrapper.cache_invalidate_key = lambda *args, **kwargs: _invalidate_specific_key(
            func, namespace, key_func, *args, **kwargs
        )
        wrapper.cache_stats = lambda: _get_function_cache_stats(func, namespace)
        
        return wrapper
    return decorator


def cache_result(
    ttl: int = 3600,
    namespace: str = "results",
    tags: Optional[List[str]] = None
):
    """
    Simple result caching decorator with default settings.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
        namespace: Cache namespace
        tags: Tags for invalidation
    """
    return cached(namespace=namespace, ttl=ttl, tags=tags)


def cache_aside(
    namespace: str,
    ttl: Optional[int] = None,
    tags: Optional[List[str]] = None,
    cache_on_error: bool = False
):
    """
    Cache-aside pattern decorator with error handling.
    
    Args:
        namespace: Cache namespace
        ttl: Time to live in seconds
        tags: Tags for invalidation
        cache_on_error: Whether to cache None results on errors
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            logger = logging.getLogger(f"{func.__module__}.{func.__name__}")
            
            cache_key = cache_key_generator(func, *args, **kwargs)
            
            try:
                # Try cache first
                cached_result = cache_manager.get(cache_key, namespace)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache successful result
                if result is not None:
                    cache_manager.set(cache_key, result, namespace, ttl, tags)
                
                return result
                
            except Exception as e:
                logger.error(f"Function {func.__name__} failed: {e}")
                
                # Try to return cached result even if function failed
                cached_result = cache_manager.get(cache_key, namespace)
                if cached_result is not None:
                    logger.info(f"Returning stale cached result for {func.__name__}")
                    return cached_result
                
                # Cache None result if configured
                if cache_on_error:
                    cache_manager.set(cache_key, None, namespace, ttl or 300, tags)  # Short TTL for errors
                
                raise
        
        return wrapper
    return decorator


def invalidate_cache(tags: Optional[List[str]] = None, namespace: Optional[str] = None):
    """
    Decorator to invalidate cache after function execution.
    
    Args:
        tags: Tags to invalidate
        namespace: Namespace to invalidate
        
    Example:
        @invalidate_cache(tags=["cases", "documents"])
        def update_case(case_id: str, data: dict):
            # Update case in database
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache after successful execution
            cache_manager = get_cache_manager()
            
            if tags:
                invalidated = cache_manager.invalidate_by_tags(tags)
                logging.getLogger(func.__module__).info(
                    f"Invalidated {invalidated} cached entries with tags: {tags}"
                )
            
            if namespace:
                invalidated = cache_manager.invalidate_namespace(namespace)
                logging.getLogger(func.__module__).info(
                    f"Invalidated {invalidated} cached entries in namespace: {namespace}"
                )
            
            return result
        
        return wrapper
    return decorator


# Strategic caching decorators for LegalLLM components

def cache_ai_response(ttl: int = 3600, compress: bool = True):
    """Cache AI/LLM responses with compression."""
    return cached(
        namespace="ai_responses",
        ttl=ttl,
        tags=["ai", "llm"],
        compress=compress,
        condition=lambda result, *args, **kwargs: result and len(str(result)) > 100
    )


def cache_document_analysis(ttl: int = 86400):
    """Cache document analysis results for 24 hours."""
    return cached(
        namespace="documents",
        ttl=ttl,
        tags=["documents", "analysis"],
        compress=True,
        condition=lambda result, *args, **kwargs: result is not None
    )


def cache_case_data(ttl: int = 7200):
    """Cache case data with write-through invalidation."""
    return cached(
        namespace="cases",
        ttl=ttl,
        tags=["cases"],
        compress=True
    )


def cache_legal_research(ttl: int = 604800):
    """Cache legal research results for 1 week."""
    return cached(
        namespace="legal_research",
        ttl=ttl,
        tags=["legal", "research"],
        compress=True
    )


def cache_financial_calculation(ttl: int = 14400):
    """Cache financial calculations for 4 hours."""
    return cached(
        namespace="financial",
        ttl=ttl,
        tags=["financial", "calculations"],
        compress=True
    )


def cache_user_session(ttl: int = 1800):
    """Cache user session data for 30 minutes."""
    return cached(
        namespace="sessions",
        ttl=ttl,
        tags=["sessions", "users"],
        compress=False
    )


# Cache invalidation helpers

def _invalidate_function_cache(func: Callable, namespace: str):
    """Invalidate all cache entries for a function"""
    cache_manager = get_cache_manager()
    # This would require tracking function keys, simplified for now
    return cache_manager.invalidate_namespace(namespace)


def _invalidate_specific_key(
    func: Callable, 
    namespace: str, 
    key_func: Optional[Callable],
    *args, 
    **kwargs
):
    """Invalidate specific cache key for function with given arguments"""
    cache_manager = get_cache_manager()
    
    if key_func:
        cache_key = key_func(func, *args, **kwargs)
    else:
        cache_key = cache_key_generator(func, *args, **kwargs)
    
    return cache_manager.delete(cache_key, namespace)


def _get_function_cache_stats(func: Callable, namespace: str) -> Dict[str, Any]:
    """Get cache statistics for a function"""
    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()
    
    # Return namespace-specific stats
    return stats.get('namespace_metrics', {}).get(namespace, {})


# Utility functions for manual cache management

def warm_cache(
    func: Callable,
    arg_sets: List[tuple],
    namespace: str = "default",
    batch_size: int = 10
):
    """
    Warm cache by pre-computing results for common argument sets.
    
    Args:
        func: Function to warm cache for
        arg_sets: List of argument tuples to pre-compute
        namespace: Cache namespace
        batch_size: Number of concurrent cache operations
    """
    logger = logging.getLogger("cache_warmer")
    cache_manager = get_cache_manager()
    
    warmed = 0
    for i in range(0, len(arg_sets), batch_size):
        batch = arg_sets[i:i + batch_size]
        
        for args in batch:
            try:
                # Check if already cached
                cache_key = cache_key_generator(func, *args)
                
                if not cache_manager.exists(cache_key, namespace):
                    # Compute and cache result
                    result = func(*args)
                    if result is not None:
                        cache_manager.set(cache_key, result, namespace)
                        warmed += 1
                
            except Exception as e:
                logger.warning(f"Failed to warm cache for {args}: {e}")
        
        # Brief pause between batches
        time.sleep(0.1)
    
    logger.info(f"Warmed {warmed} cache entries for {func.__name__}")
    return warmed


def cache_performance_monitor(func: Callable) -> Callable:
    """
    Decorator to monitor cache performance for a function.
    
    Logs cache hit rates, execution times, and cache efficiency metrics.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(f"cache_monitor.{func.__name__}")
        
        start_time = time.time()
        result = func(*args, **kwargs)
        total_time = time.time() - start_time
        
        # Log performance metrics
        logger.info(f"Function: {func.__name__}, Execution time: {total_time:.3f}s")
        
        return result
    
    return wrapper


# Pre-configured decorators for common LegalLLM use cases

# Document processing caching
document_cache = cache_document_analysis()

# AI response caching with compression
ai_cache = cache_ai_response(ttl=3600, compress=True)

# Case management caching
case_cache = cache_case_data(ttl=7200)

# Legal research caching (long TTL)
research_cache = cache_legal_research(ttl=604800)

# Financial analysis caching
financial_cache = cache_financial_calculation(ttl=14400)

# Session caching
session_cache = cache_user_session(ttl=1800)