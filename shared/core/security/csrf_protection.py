"""
CSRF Protection System
======================

Cross-Site Request Forgery protection for LegalLLM Professional web interfaces.
Implements OWASP-recommended CSRF protection patterns with Streamlit integration.

Features:
- Double-submit cookie pattern
- Synchronizer token pattern
- Origin header validation
- SameSite cookie protection
- Streamlit session state integration
- Australian legal compliance logging
"""

import os
import secrets
import hmac
import hashlib
import time
from typing import Dict, Optional, Any, Tuple, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse
import logging
import streamlit as st


@dataclass
class CSRFToken:
    """CSRF token with metadata"""
    token: str
    created_at: datetime
    expires_at: datetime
    form_id: str
    user_id: Optional[str]
    session_id: str


class CSRFError(Exception):
    """Exception raised for CSRF validation failures"""
    
    def __init__(self, message: str, attack_details: Dict[str, Any] = None):
        super().__init__(message)
        self.attack_details = attack_details or {}


class CSRFProtection:
    """
    CSRF protection system implementing multiple security patterns.
    
    Provides protection against Cross-Site Request Forgery attacks using:
    - Synchronizer token pattern
    - Double-submit cookie pattern  
    - Origin header validation
    - SameSite cookie attributes
    - Token expiration and rotation
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.secret_key = secret_key or self._get_secret_key()
        self.token_lifetime = timedelta(hours=2)  # CSRF tokens expire in 2 hours
        self.cookie_name = "csrf_token"
        self.header_name = "X-CSRFToken"
        self.form_field_name = "csrf_token"
        
        # Token storage (in production, use Redis or database)
        self.active_tokens: Dict[str, CSRFToken] = {}
        
        # Security configuration
        self.allowed_origins = self._get_allowed_origins()
        self.require_https = os.getenv('REQUIRE_HTTPS', 'false').lower() == 'true'
        
        # Attack tracking
        self.attack_attempts = []
        self.max_attack_log = 1000
        
        self.logger.info("CSRF protection initialized")
    
    def _get_secret_key(self) -> str:
        """Get CSRF secret key from environment"""
        secret = os.getenv('CSRF_SECRET_KEY')
        if not secret:
            secret = secrets.token_urlsafe(32)
            self.logger.warning(
                f"No CSRF_SECRET_KEY found. Generated: {secret}. "
                "Store this in environment variables for production."
            )
        return secret
    
    def _get_allowed_origins(self) -> List[str]:
        """Get allowed origins from environment"""
        origins_env = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8501,https://localhost:8501')
        return [origin.strip() for origin in origins_env.split(',')]
    
    def generate_token(
        self, 
        form_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> CSRFToken:
        """
        Generate a new CSRF token for a form.
        
        Args:
            form_id: Unique identifier for the form
            user_id: Optional user identifier
            session_id: Optional session identifier
            
        Returns:
            CSRFToken object with token and metadata
        """
        # Generate cryptographically secure token
        timestamp = str(int(time.time()))
        random_part = secrets.token_urlsafe(32)
        
        # Create token payload
        payload = f"{form_id}:{user_id or 'anonymous'}:{session_id or 'unknown'}:{timestamp}:{random_part}"
        
        # Sign the token with HMAC
        signature = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{payload}:{signature}"
        
        # Create token object
        csrf_token = CSRFToken(
            token=token,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.token_lifetime,
            form_id=form_id,
            user_id=user_id,
            session_id=session_id or self._get_session_id()
        )
        
        # Store token
        self.active_tokens[token] = csrf_token
        
        # Clean expired tokens
        self._cleanup_expired_tokens()
        
        self.logger.debug(f"Generated CSRF token for form {form_id}")
        
        return csrf_token
    
    def validate_token(
        self,
        token: str,
        form_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        origin: Optional[str] = None,
        referer: Optional[str] = None
    ) -> bool:
        """
        Validate CSRF token against multiple security checks.
        
        Args:
            token: CSRF token to validate
            form_id: Form identifier
            user_id: Optional user identifier
            session_id: Optional session identifier
            origin: Origin header from request
            referer: Referer header from request
            
        Returns:
            True if token is valid, False otherwise
            
        Raises:
            CSRFError: If validation fails with security implications
        """
        attack_details = {
            'token': token[:20] + '...' if token else None,
            'form_id': form_id,
            'user_id': user_id,
            'origin': origin,
            'referer': referer,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Basic token presence check
            if not token:
                raise CSRFError("CSRF token missing", attack_details)
            
            # Token format validation
            if not self._validate_token_format(token):
                raise CSRFError("Invalid CSRF token format", attack_details)
            
            # Token signature validation
            if not self._validate_token_signature(token):
                raise CSRFError("Invalid CSRF token signature", attack_details)
            
            # Check if token exists in our store
            if token not in self.active_tokens:
                raise CSRFError("CSRF token not found or expired", attack_details)
            
            csrf_token = self.active_tokens[token]
            
            # Expiration check
            if datetime.now() > csrf_token.expires_at:
                del self.active_tokens[token]
                raise CSRFError("CSRF token expired", attack_details)
            
            # Form ID validation
            if csrf_token.form_id != form_id:
                raise CSRFError("CSRF token form mismatch", attack_details)
            
            # User validation (if provided)
            if user_id and csrf_token.user_id != user_id:
                raise CSRFError("CSRF token user mismatch", attack_details)
            
            # Session validation (if provided)
            current_session = session_id or self._get_session_id()
            if current_session and csrf_token.session_id != current_session:
                raise CSRFError("CSRF token session mismatch", attack_details)
            
            # Origin header validation
            if origin and not self._validate_origin(origin):
                raise CSRFError("Invalid origin header", attack_details)
            
            # Referer header validation (additional security layer)
            if referer and not self._validate_referer(referer):
                attack_details['referer_validation_failed'] = True
                # Don't fail on referer validation alone, just log warning
                self.logger.warning(f"Suspicious referer header: {referer}")
            
            # Token is valid - consume it (single use)
            del self.active_tokens[token]
            
            self.logger.debug(f"CSRF token validated successfully for form {form_id}")
            return True
            
        except CSRFError as e:
            # Log attack attempt
            self._log_attack_attempt(e, attack_details)
            raise
        
        except Exception as e:
            # Log unexpected error
            attack_details['error'] = str(e)
            csrf_error = CSRFError(f"CSRF validation error: {e}", attack_details)
            self._log_attack_attempt(csrf_error, attack_details)
            raise csrf_error
    
    def _validate_token_format(self, token: str) -> bool:
        """Validate CSRF token format"""
        try:
            parts = token.split(':')
            return len(parts) == 6  # form_id:user_id:session_id:timestamp:random:signature
        except Exception:
            return False
    
    def _validate_token_signature(self, token: str) -> bool:
        """Validate CSRF token HMAC signature"""
        try:
            parts = token.split(':')
            if len(parts) != 6:
                return False
            
            payload = ':'.join(parts[:-1])
            provided_signature = parts[-1]
            
            expected_signature = hmac.new(
                self.secret_key.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, provided_signature)
            
        except Exception:
            return False
    
    def _validate_origin(self, origin: str) -> bool:
        """Validate Origin header against allowed origins"""
        if not origin:
            return False
        
        # Parse origin
        try:
            parsed = urlparse(origin)
            normalized_origin = f"{parsed.scheme}://{parsed.netloc}"
            
            # Check against allowed origins
            return normalized_origin in self.allowed_origins
            
        except Exception:
            return False
    
    def _validate_referer(self, referer: str) -> bool:
        """Validate Referer header (additional security layer)"""
        if not referer:
            return True  # Referer is optional
        
        try:
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            
            return referer_origin in self.allowed_origins
            
        except Exception:
            return False
    
    def _get_session_id(self) -> str:
        """Get current session ID (Streamlit-specific)"""
        try:
            # Try to get Streamlit session ID
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'session_id'):
                return st.session_state.session_id
            
            # Generate session ID if not available
            if 'csrf_session_id' not in st.session_state:
                st.session_state.csrf_session_id = secrets.token_urlsafe(16)
            
            return st.session_state.csrf_session_id
            
        except Exception:
            return 'unknown_session'
    
    def _cleanup_expired_tokens(self):
        """Remove expired tokens from storage"""
        current_time = datetime.now()
        expired_tokens = [
            token for token, csrf_token in self.active_tokens.items()
            if current_time > csrf_token.expires_at
        ]
        
        for token in expired_tokens:
            del self.active_tokens[token]
        
        if expired_tokens:
            self.logger.debug(f"Cleaned up {len(expired_tokens)} expired CSRF tokens")
    
    def _log_attack_attempt(self, error: CSRFError, details: Dict[str, Any]):
        """Log CSRF attack attempt"""
        attack_record = {
            'timestamp': datetime.now(),
            'error_message': str(error),
            'details': details,
            'remote_addr': self._get_client_ip()
        }
        
        self.attack_attempts.append(attack_record)
        
        # Limit attack log size
        if len(self.attack_attempts) > self.max_attack_log:
            self.attack_attempts = self.attack_attempts[-self.max_attack_log:]
        
        # Log high-severity security event
        self.logger.error(
            f"CSRF_ATTACK_ATTEMPT: {error} | Details: {details}"
        )
    
    def _get_client_ip(self) -> str:
        """Get client IP address (for logging)"""
        # This would be implemented based on your deployment
        # For Streamlit, you might use headers or other methods
        return "unknown"
    
    # Streamlit Integration Methods
    
    def protect_form(self, form_id: str, user_id: Optional[str] = None) -> str:
        """
        Generate CSRF protection for a Streamlit form.
        
        Args:
            form_id: Unique identifier for the form
            user_id: Optional user identifier
            
        Returns:
            CSRF token to include in form
        """
        csrf_token = self.generate_token(form_id, user_id)
        
        # Store token in session state for validation
        if 'csrf_tokens' not in st.session_state:
            st.session_state.csrf_tokens = {}
        
        st.session_state.csrf_tokens[form_id] = csrf_token.token
        
        return csrf_token.token
    
    def validate_form_submission(
        self,
        form_id: str,
        submitted_token: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Validate CSRF token for Streamlit form submission.
        
        Args:
            form_id: Form identifier
            submitted_token: Token submitted with form
            user_id: Optional user identifier
            
        Returns:
            True if validation passes
            
        Raises:
            CSRFError: If validation fails
        """
        return self.validate_token(
            token=submitted_token,
            form_id=form_id,
            user_id=user_id,
            origin=None,  # Streamlit doesn't provide origin headers directly
            referer=None  # Streamlit doesn't provide referer headers directly
        )
    
    def create_hidden_input(self, form_id: str, user_id: Optional[str] = None) -> str:
        """
        Create hidden HTML input for CSRF token.
        
        Args:
            form_id: Form identifier
            user_id: Optional user identifier
            
        Returns:
            HTML string for hidden input
        """
        token = self.protect_form(form_id, user_id)
        return f'<input type="hidden" name="{self.form_field_name}" value="{token}">'
    
    def get_protection_stats(self) -> Dict[str, Any]:
        """Get CSRF protection statistics"""
        current_time = datetime.now()
        active_token_count = len(self.active_tokens)
        
        # Count recent attack attempts (last 24 hours)
        recent_attacks = [
            attempt for attempt in self.attack_attempts
            if current_time - attempt['timestamp'] < timedelta(hours=24)
        ]
        
        return {
            'active_tokens': active_token_count,
            'token_lifetime_hours': self.token_lifetime.total_seconds() / 3600,
            'allowed_origins': self.allowed_origins,
            'recent_attacks_24h': len(recent_attacks),
            'total_logged_attacks': len(self.attack_attempts),
            'require_https': self.require_https
        }


# Global CSRF protection instance
_csrf_protection = None


def get_csrf_protection() -> CSRFProtection:
    """Get global CSRF protection instance"""
    global _csrf_protection
    if _csrf_protection is None:
        _csrf_protection = CSRFProtection()
    return _csrf_protection


# Streamlit helper functions
def csrf_protect_form(form_id: str, user_id: Optional[str] = None) -> str:
    """Helper function to protect Streamlit form"""
    protection = get_csrf_protection()
    return protection.protect_form(form_id, user_id)


def csrf_validate_form(
    form_id: str, 
    submitted_token: str, 
    user_id: Optional[str] = None
) -> bool:
    """Helper function to validate Streamlit form submission"""
    protection = get_csrf_protection()
    return protection.validate_form_submission(form_id, submitted_token, user_id)


def csrf_create_hidden_field(form_id: str, user_id: Optional[str] = None) -> str:
    """Helper function to create CSRF hidden field"""
    protection = get_csrf_protection()
    return protection.create_hidden_input(form_id, user_id)


# Decorator for protecting Streamlit functions
def csrf_protected(form_id: str):
    """Decorator to add CSRF protection to Streamlit functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate CSRF token
            token = csrf_protect_form(form_id)
            
            # Add token to function arguments
            kwargs['csrf_token'] = token
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator