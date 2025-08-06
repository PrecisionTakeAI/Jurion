"""
Enhanced Security Module for LegalLLM Professional
====================================================

Comprehensive security enhancements addressing CLAUDE.md identified vulnerabilities:
- OWASP-compliant input validation
- AES-256-GCM encryption (replacing weak PBKDF2)  
- CSRF protection for all forms
- Distributed rate limiting with Redis
- Enhanced error handling and recovery

This module provides enterprise-grade security hardening for Australian legal AI applications.
"""

from .input_validator import InputValidator, ValidationError, SecurityLevel
from .encryption_service import EncryptionService, EncryptionError
from .csrf_protection import CSRFProtection, CSRFError
from .distributed_rate_limiter import DistributedRateLimiter, RateLimitExceeded

__all__ = [
    'InputValidator',
    'ValidationError', 
    'SecurityLevel',
    'EncryptionService',
    'EncryptionError',
    'CSRFProtection',
    'CSRFError',
    'DistributedRateLimiter',
    'RateLimitExceeded'
]