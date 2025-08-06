"""
Enhanced Error Handling System for LegalLLM Professional
========================================================

Comprehensive error handling and classification system addressing CLAUDE.md requirements:
- Error classification (user, system, external service)
- User-friendly error messages
- Graceful degradation mechanisms
- Recovery suggestions and fallback strategies
- Australian legal compliance error handling

This module provides enterprise-grade error management for legal AI applications.
"""

from .error_classifier import (
    ErrorClassifier,
    ErrorCategory,
    ErrorSeverity,
    ClassifiedError,
    ErrorContext
)
from .fallback_handler import (
    FallbackHandler,
    FallbackStrategy,
    CircuitBreaker,
    GracefulDegradation
)
from .user_friendly_errors import (
    UserFriendlyErrorHandler,
    ErrorMessage,
    RecoveryAction,
    format_user_error
)

__all__ = [
    'ErrorClassifier',
    'ErrorCategory',
    'ErrorSeverity', 
    'ClassifiedError',
    'ErrorContext',
    'FallbackHandler',
    'FallbackStrategy',
    'CircuitBreaker',
    'GracefulDegradation',
    'UserFriendlyErrorHandler',
    'ErrorMessage',
    'RecoveryAction',
    'format_user_error'
]