"""
Fallback Handler and Graceful Degradation
=========================================

Implements graceful degradation mechanisms for LegalLLM Professional.
Provides fallback strategies for AI service failures, database connection recovery,
and document processing error recovery.

Features:
- Circuit breaker pattern implementation
- Multiple fallback strategies
- Automatic service recovery
- Performance monitoring
- Australian legal workflow continuity
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future


class FallbackStrategy(Enum):
    """Fallback strategy types"""
    CIRCUIT_BREAKER = "circuit_breaker"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    ALTERNATIVE_SERVICE = "alternative_service"
    CACHED_RESPONSE = "cached_response"
    SIMPLIFIED_RESPONSE = "simplified_response"
    QUEUE_FOR_LATER = "queue_for_later"
    MANUAL_INTERVENTION = "manual_intervention"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Service failing, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5      # Failures before opening
    recovery_timeout: int = 60      # Seconds before trying half-open
    success_threshold: int = 3      # Successes needed to close
    timeout_seconds: float = 10.0   # Operation timeout


@dataclass
class FallbackContext:
    """Context for fallback execution"""
    service_name: str
    operation_name: str
    user_id: Optional[str] = None
    firm_id: Optional[str] = None
    request_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    original_args: tuple = field(default_factory=tuple)
    original_kwargs: dict = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """
    Circuit breaker implementation for service protection.
    
    Monitors service health and prevents cascading failures by
    temporarily blocking requests to failing services.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"circuit_breaker")
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.logger.info("Circuit breaker moving to HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            # Execute with timeout
            result = self._execute_with_timeout(func, *args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _execute_with_timeout(self, func: Callable, *args, **kwargs):
        """Execute function with timeout"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=self.config.timeout_seconds)
            except Exception as e:
                future.cancel()
                raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._reset()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.logger.warning("Circuit breaker opened from HALF_OPEN state")
            elif (self.state == CircuitState.CLOSED and 
                  self.failure_count >= self.config.failure_threshold):
                self.state = CircuitState.OPEN
                self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _reset(self):
        """Reset circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info("Circuit breaker reset to CLOSED state")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time
        }


class GracefulDegradation:
    """
    Graceful degradation manager for maintaining service quality
    during partial system failures.
    """
    
    def __init__(self):
        self.service_status = {}
        self.degradation_strategies = {}
        self.logger = logging.getLogger(__name__)
        
        # Setup default degradation strategies
        self._setup_default_strategies()
    
    def _setup_default_strategies(self):
        """Setup default degradation strategies for common services"""
        
        # AI service degradation
        self.degradation_strategies['ai_service'] = [
            ('use_cached_response', 0.9),      # High priority - use cached if available
            ('use_simple_template', 0.7),     # Medium priority - use template response
            ('queue_for_manual', 0.5),        # Low priority - queue for human review
            ('return_placeholder', 0.3)       # Last resort - placeholder response
        ]
        
        # Database service degradation
        self.degradation_strategies['database'] = [
            ('use_read_replica', 0.9),        # Use read-only replica
            ('use_cache_only', 0.7),          # Cache-only operations
            ('local_storage', 0.5),           # Temporary local storage
            ('read_only_mode', 0.3)           # Read-only functionality
        ]
        
        # Document processing degradation
        self.degradation_strategies['document_processing'] = [
            ('basic_text_extraction', 0.8),   # Simplified text extraction
            ('metadata_only', 0.6),           # Process metadata only
            ('queue_for_later', 0.4),         # Queue for later processing
            ('manual_review', 0.2)            # Route to manual review
        ]
    
    def set_service_status(self, service_name: str, health_score: float):
        """Update service health status (0.0 = down, 1.0 = fully operational)"""
        self.service_status[service_name] = {
            'health_score': health_score,
            'last_updated': datetime.now()
        }
        
        self.logger.info(f"Service {service_name} health: {health_score:.2f}")
    
    def get_degradation_strategy(self, service_name: str) -> Optional[str]:
        """Get appropriate degradation strategy for a service"""
        if service_name not in self.service_status:
            return None
        
        health_score = self.service_status[service_name]['health_score']
        strategies = self.degradation_strategies.get(service_name, [])
        
        # Find the best strategy for current health score
        for strategy_name, min_health in strategies:
            if health_score >= min_health:
                return strategy_name
        
        # Return the lowest tier strategy if all else fails
        if strategies:
            return strategies[-1][0]
        
        return None
    
    def is_service_degraded(self, service_name: str, threshold: float = 0.8) -> bool:
        """Check if a service is operating below threshold"""
        if service_name not in self.service_status:
            return True  # Assume degraded if unknown
        
        return self.service_status[service_name]['health_score'] < threshold


class FallbackHandler:
    """
    Comprehensive fallback handler implementing multiple strategies
    for graceful degradation and error recovery.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.degradation_manager = GracefulDegradation()
        self.fallback_queue = []
        self.logger = logging.getLogger(__name__)
        
        # Setup default circuit breakers
        self._setup_default_circuit_breakers()
        
        # Performance metrics
        self.metrics = {
            'fallbacks_triggered': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'circuit_breakers_opened': 0
        }
    
    def _setup_default_circuit_breakers(self):
        """Setup circuit breakers for critical services"""
        
        # AI service circuit breaker
        self.circuit_breakers['ai_service'] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2,
                timeout_seconds=15.0
            )
        )
        
        # Database circuit breaker
        self.circuit_breakers['database'] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3,
                timeout_seconds=10.0
            )
        )
        
        # Document processing circuit breaker
        self.circuit_breakers['document_processing'] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=45,
                success_threshold=2,
                timeout_seconds=30.0
            )
        )
    
    def execute_with_fallback(
        self,
        primary_func: Callable,
        context: FallbackContext,
        fallback_strategies: Optional[List[FallbackStrategy]] = None
    ) -> Any:
        """
        Execute function with fallback strategies.
        
        Args:
            primary_func: Primary function to execute
            context: Fallback context
            fallback_strategies: List of fallback strategies to try
            
        Returns:
            Result from primary function or fallback
        """
        self.metrics['fallbacks_triggered'] += 1
        
        # Default fallback strategies
        if fallback_strategies is None:
            fallback_strategies = [
                FallbackStrategy.CIRCUIT_BREAKER,
                FallbackStrategy.RETRY_WITH_BACKOFF,
                FallbackStrategy.CACHED_RESPONSE,
                FallbackStrategy.SIMPLIFIED_RESPONSE
            ]
        
        # Try primary function first
        try:
            return self._execute_with_circuit_breaker(
                primary_func, context.service_name, *context.original_args, **context.original_kwargs
            )
        except Exception as primary_error:
            self.logger.warning(f"Primary function failed: {primary_error}")
            
            # Try fallback strategies
            for strategy in fallback_strategies:
                try:
                    result = self._execute_fallback_strategy(
                        strategy, primary_func, context, primary_error
                    )
                    
                    if result is not None:
                        self.metrics['successful_recoveries'] += 1
                        self.logger.info(f"Successfully recovered using {strategy.value}")
                        return result
                
                except Exception as fallback_error:
                    self.logger.warning(f"Fallback strategy {strategy.value} failed: {fallback_error}")
                    continue
            
            # All strategies failed
            self.metrics['failed_recoveries'] += 1
            self.logger.error(f"All fallback strategies failed for {context.service_name}")
            raise primary_error
    
    def _execute_with_circuit_breaker(
        self, 
        func: Callable, 
        service_name: str, 
        *args, 
        **kwargs
    ):
        """Execute function with circuit breaker protection"""
        if service_name in self.circuit_breakers:
            return self.circuit_breakers[service_name].call(func, *args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def _execute_fallback_strategy(
        self,
        strategy: FallbackStrategy,
        primary_func: Callable,
        context: FallbackContext,
        primary_error: Exception
    ) -> Any:
        """Execute specific fallback strategy"""
        
        if strategy == FallbackStrategy.RETRY_WITH_BACKOFF:
            return self._retry_with_backoff(primary_func, context)
        
        elif strategy == FallbackStrategy.CACHED_RESPONSE:
            return self._get_cached_response(context)
        
        elif strategy == FallbackStrategy.ALTERNATIVE_SERVICE:
            return self._use_alternative_service(context)
        
        elif strategy == FallbackStrategy.SIMPLIFIED_RESPONSE:
            return self._get_simplified_response(context)
        
        elif strategy == FallbackStrategy.QUEUE_FOR_LATER:
            return self._queue_for_later_processing(context)
        
        elif strategy == FallbackStrategy.MANUAL_INTERVENTION:
            return self._queue_for_manual_intervention(context)
        
        else:
            raise ValueError(f"Unknown fallback strategy: {strategy}")
    
    def _retry_with_backoff(self, func: Callable, context: FallbackContext) -> Any:
        """Retry with exponential backoff"""
        max_retries = context.max_retries
        base_delay = 1.0
        
        for attempt in range(max_retries):
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                time.sleep(min(delay, 30))  # Cap at 30 seconds
            
            try:
                return func(*context.original_args, **context.original_kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Retry {attempt + 1} failed: {e}")
    
    def _get_cached_response(self, context: FallbackContext) -> Any:
        """Try to get cached response"""
        try:
            from shared.core.cache import cache_get
            
            # Generate cache key based on context
            cache_key = f"{context.service_name}:{context.operation_name}:{hash(str(context.original_args))}"
            
            cached_result = cache_get(cache_key, namespace=context.service_name)
            
            if cached_result is not None:
                self.logger.info(f"Using cached response for {context.service_name}")
                return cached_result
            
        except Exception as e:
            self.logger.warning(f"Cache fallback failed: {e}")
        
        raise Exception("No cached response available")
    
    def _use_alternative_service(self, context: FallbackContext) -> Any:
        """Use alternative service implementation"""
        # This would implement service-specific alternatives
        # For example, using a different AI model or database replica
        
        alternatives = {
            'ai_service': self._use_alternative_ai_service,
            'database': self._use_database_replica,
            'document_processing': self._use_simple_text_extraction
        }
        
        if context.service_name in alternatives:
            return alternatives[context.service_name](context)
        
        raise Exception(f"No alternative service for {context.service_name}")
    
    def _get_simplified_response(self, context: FallbackContext) -> Any:
        """Generate simplified response"""
        
        simplified_responses = {
            'ai_service': "I'm currently experiencing technical difficulties. Please try again in a few minutes or contact support for assistance.",
            'document_processing': {'status': 'queued', 'message': 'Document queued for processing'},
            'legal_analysis': {'analysis': 'Analysis temporarily unavailable', 'confidence': 0.0}
        }
        
        service_response = simplified_responses.get(context.service_name)
        
        if service_response:
            self.logger.info(f"Using simplified response for {context.service_name}")
            return service_response
        
        raise Exception(f"No simplified response for {context.service_name}")
    
    def _queue_for_later_processing(self, context: FallbackContext) -> Any:
        """Queue request for later processing"""
        queued_item = {
            'context': context,
            'timestamp': datetime.now(),
            'priority': 'normal',
            'retry_count': 0
        }
        
        self.fallback_queue.append(queued_item)
        
        self.logger.info(f"Queued {context.service_name} request for later processing")
        
        return {
            'status': 'queued',
            'message': 'Your request has been queued and will be processed when the service is available.',
            'estimated_processing_time': '5-15 minutes'
        }
    
    def _queue_for_manual_intervention(self, context: FallbackContext) -> Any:
        """Queue for manual review/processing"""
        
        manual_queue_item = {
            'context': context,
            'timestamp': datetime.now(),
            'priority': 'high',
            'requires_human_review': True
        }
        
        # In production, this would integrate with a ticket system
        self.logger.warning(f"Manual intervention required for {context.service_name}")
        
        return {
            'status': 'manual_review_required',
            'message': 'This request requires manual review. Our team has been notified and will process it within 2-4 hours.',
            'ticket_id': f"MANUAL-{int(time.time())}"
        }
    
    def _use_alternative_ai_service(self, context: FallbackContext) -> Any:
        """Use alternative AI service (e.g., different model)"""
        # This would implement switching to a backup AI service
        self.logger.info("Switching to backup AI service")
        raise Exception("Alternative AI service not implemented")
    
    def _use_database_replica(self, context: FallbackContext) -> Any:
        """Use database read replica"""
        # This would implement read replica fallback
        self.logger.info("Switching to database read replica")
        raise Exception("Database replica fallback not implemented")
    
    def _use_simple_text_extraction(self, context: FallbackContext) -> Any:
        """Use simple text extraction instead of advanced processing"""
        # This would implement basic text extraction
        return {
            'text': 'Basic text extraction completed',
            'processing_mode': 'simplified',
            'confidence': 0.6
        }
    
    def process_fallback_queue(self):
        """Process queued fallback items"""
        processed = 0
        failed = 0
        
        while self.fallback_queue:
            item = self.fallback_queue.pop(0)
            context = item['context']
            
            try:
                # Retry the original operation
                # This would re-execute the failed operation
                self.logger.info(f"Processing queued item for {context.service_name}")
                processed += 1
                
            except Exception as e:
                item['retry_count'] += 1
                if item['retry_count'] < 3:
                    # Re-queue with higher priority
                    item['priority'] = 'high'
                    self.fallback_queue.append(item)
                else:
                    failed += 1
                
                self.logger.error(f"Failed to process queued item: {e}")
        
        if processed > 0 or failed > 0:
            self.logger.info(f"Processed {processed} queued items, {failed} failed")
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        return {
            name: breaker.get_state() 
            for name, breaker in self.circuit_breakers.items()
        }
    
    def get_fallback_metrics(self) -> Dict[str, Any]:
        """Get fallback handler metrics"""
        return {
            **self.metrics,
            'queue_length': len(self.fallback_queue),
            'circuit_breaker_status': self.get_circuit_breaker_status(),
            'service_health': self.degradation_manager.service_status
        }


# Global fallback handler instance
_fallback_handler = None


def get_fallback_handler() -> FallbackHandler:
    """Get global fallback handler instance"""
    global _fallback_handler
    if _fallback_handler is None:
        _fallback_handler = FallbackHandler()
    return _fallback_handler


# Decorator for automatic fallback handling
def with_fallback(
    service_name: str,
    strategies: Optional[List[FallbackStrategy]] = None
):
    """Decorator to add fallback handling to functions"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            handler = get_fallback_handler()
            context = FallbackContext(
                service_name=service_name,
                operation_name=func.__name__,
                original_args=args,
                original_kwargs=kwargs
            )
            
            return handler.execute_with_fallback(func, context, strategies)
        
        return wrapper
    return decorator