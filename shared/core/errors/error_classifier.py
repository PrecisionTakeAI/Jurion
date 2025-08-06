"""
Error Classification System
===========================

Intelligent error classification system for LegalLLM Professional.
Categorizes errors into user, system, and external service errors with
appropriate handling strategies and user-friendly messaging.

Features:
- Automatic error classification
- Severity assessment
- Context preservation
- Recovery recommendations
- Australian legal compliance considerations
"""

import re
import traceback
from typing import Dict, List, Any, Optional, Union, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging


class ErrorCategory(Enum):
    """Error categories for classification"""
    USER_ERROR = "user_error"              # User input/behavior errors
    VALIDATION_ERROR = "validation_error"  # Data validation failures
    AUTHENTICATION_ERROR = "auth_error"    # Authentication/authorization issues
    SYSTEM_ERROR = "system_error"          # Internal system failures
    EXTERNAL_SERVICE_ERROR = "external_service_error"  # Third-party service failures
    DATABASE_ERROR = "database_error"      # Database connectivity/query issues
    AI_SERVICE_ERROR = "ai_service_error"  # AI/LLM service issues
    NETWORK_ERROR = "network_error"        # Network connectivity issues
    PERMISSION_ERROR = "permission_error"  # Access permission issues
    RESOURCE_ERROR = "resource_error"      # Resource exhaustion/limits
    CONFIGURATION_ERROR = "config_error"   # Configuration/setup issues
    UNKNOWN_ERROR = "unknown_error"        # Unclassified errors


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Minor issues, system continues normally
    MEDIUM = "medium"     # Moderate issues, some functionality affected
    HIGH = "high"         # Major issues, significant functionality impacted
    CRITICAL = "critical" # System-breaking issues, immediate attention required


@dataclass
class ErrorContext:
    """Context information for error classification"""
    user_id: Optional[str] = None
    firm_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassifiedError:
    """Classified error with metadata and recommendations"""
    original_error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    user_message: str
    technical_message: str
    recovery_actions: List[str]
    context: ErrorContext
    error_code: str
    is_retryable: bool = False
    estimated_fix_time: Optional[str] = None
    related_documentation: Optional[str] = None


class ErrorClassifier:
    """
    Intelligent error classification system.
    
    Analyzes exceptions and classifies them into appropriate categories
    with severity assessment and recovery recommendations.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Error pattern matching rules
        self._setup_classification_rules()
        
        # Error statistics for pattern learning
        self.error_stats = {}
        
        # Known error patterns
        self.known_patterns = {}
        
        self.logger.info("Error classifier initialized")
    
    def _setup_classification_rules(self):
        """Setup error classification rules and patterns"""
        
        # Database error patterns
        self.db_error_patterns = [
            (r"connection.*refused", ErrorCategory.DATABASE_ERROR, ErrorSeverity.HIGH),
            (r"timeout.*database", ErrorCategory.DATABASE_ERROR, ErrorSeverity.MEDIUM),
            (r"constraint.*violation", ErrorCategory.DATABASE_ERROR, ErrorSeverity.MEDIUM),
            (r"duplicate.*key", ErrorCategory.DATABASE_ERROR, ErrorSeverity.LOW),
            (r"table.*not.*found", ErrorCategory.CONFIGURATION_ERROR, ErrorSeverity.HIGH),
            (r"column.*not.*found", ErrorCategory.CONFIGURATION_ERROR, ErrorSeverity.HIGH),
        ]
        
        # Network error patterns
        self.network_error_patterns = [
            (r"connection.*timed.*out", ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            (r"name.*resolution.*failed", ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            (r"connection.*reset", ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            (r"no.*route.*to.*host", ErrorCategory.NETWORK_ERROR, ErrorSeverity.HIGH),
            (r"ssl.*handshake.*failed", ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
        ]
        
        # Authentication error patterns
        self.auth_error_patterns = [
            (r"invalid.*credentials", ErrorCategory.AUTHENTICATION_ERROR, ErrorSeverity.LOW),
            (r"access.*denied", ErrorCategory.PERMISSION_ERROR, ErrorSeverity.MEDIUM),
            (r"unauthorized", ErrorCategory.AUTHENTICATION_ERROR, ErrorSeverity.MEDIUM),
            (r"forbidden", ErrorCategory.PERMISSION_ERROR, ErrorSeverity.MEDIUM),
            (r"token.*expired", ErrorCategory.AUTHENTICATION_ERROR, ErrorSeverity.LOW),
            (r"session.*expired", ErrorCategory.AUTHENTICATION_ERROR, ErrorSeverity.LOW),
        ]
        
        # Validation error patterns
        self.validation_error_patterns = [
            (r"validation.*failed", ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW),
            (r"invalid.*input", ErrorCategory.USER_ERROR, ErrorSeverity.LOW),
            (r"required.*field", ErrorCategory.USER_ERROR, ErrorSeverity.LOW),
            (r"format.*invalid", ErrorCategory.USER_ERROR, ErrorSeverity.LOW),
            (r"value.*out.*of.*range", ErrorCategory.USER_ERROR, ErrorSeverity.LOW),
        ]
        
        # AI service error patterns
        self.ai_error_patterns = [
            (r"openai.*api.*error", ErrorCategory.AI_SERVICE_ERROR, ErrorSeverity.MEDIUM),
            (r"rate.*limit.*exceeded", ErrorCategory.EXTERNAL_SERVICE_ERROR, ErrorSeverity.MEDIUM),
            (r"model.*not.*found", ErrorCategory.CONFIGURATION_ERROR, ErrorSeverity.HIGH),
            (r"context.*length.*exceeded", ErrorCategory.USER_ERROR, ErrorSeverity.MEDIUM),
            (r"api.*key.*invalid", ErrorCategory.CONFIGURATION_ERROR, ErrorSeverity.HIGH),
        ]
        
        # Resource error patterns
        self.resource_error_patterns = [
            (r"memory.*error", ErrorCategory.RESOURCE_ERROR, ErrorSeverity.HIGH),
            (r"disk.*space", ErrorCategory.RESOURCE_ERROR, ErrorSeverity.HIGH),
            (r"file.*not.*found", ErrorCategory.USER_ERROR, ErrorSeverity.LOW),
            (r"permission.*denied", ErrorCategory.PERMISSION_ERROR, ErrorSeverity.MEDIUM),
            (r"too.*many.*files", ErrorCategory.RESOURCE_ERROR, ErrorSeverity.MEDIUM),
        ]
        
        # System error patterns
        self.system_error_patterns = [
            (r"internal.*server.*error", ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH),
            (r"service.*unavailable", ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH),
            (r"null.*pointer", ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
            (r"index.*out.*of.*bounds", ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
            (r"stack.*overflow", ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH),
        ]
        
        # Combine all patterns
        self.all_patterns = [
            *self.db_error_patterns,
            *self.network_error_patterns,
            *self.auth_error_patterns,
            *self.validation_error_patterns,
            *self.ai_error_patterns,
            *self.resource_error_patterns,
            *self.system_error_patterns
        ]
        
        # Exception type mappings
        self.exception_type_mappings = {
            'ConnectionError': (ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            'TimeoutError': (ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            'PermissionError': (ErrorCategory.PERMISSION_ERROR, ErrorSeverity.MEDIUM),
            'FileNotFoundError': (ErrorCategory.USER_ERROR, ErrorSeverity.LOW),
            'ValueError': (ErrorCategory.USER_ERROR, ErrorSeverity.LOW),
            'TypeError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
            'AttributeError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
            'KeyError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
            'IndexError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
            'MemoryError': (ErrorCategory.RESOURCE_ERROR, ErrorSeverity.CRITICAL),
            'IOError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
            'OSError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.MEDIUM),
        }
    
    def classify_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None
    ) -> ClassifiedError:
        """
        Classify an error and generate appropriate response.
        
        Args:
            error: Exception to classify
            context: Optional context information
            
        Returns:
            ClassifiedError with classification and recommendations
        """
        if context is None:
            context = ErrorContext()
        
        # Get error details
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Classify using multiple methods
        category, severity = self._classify_by_patterns(error_message, error_type)
        
        # Generate error code
        error_code = self._generate_error_code(category, error_type)
        
        # Generate user-friendly message
        user_message = self._generate_user_message(category, error, context)
        
        # Generate technical message
        technical_message = self._generate_technical_message(error)
        
        # Generate recovery actions
        recovery_actions = self._generate_recovery_actions(category, error, context)
        
        # Determine if retryable
        is_retryable = self._is_retryable(category, error)
        
        # Estimate fix time
        estimated_fix_time = self._estimate_fix_time(category, severity)
        
        # Get related documentation
        related_docs = self._get_related_documentation(category)
        
        classified_error = ClassifiedError(
            original_error=error,
            category=category,
            severity=severity,
            user_message=user_message,
            technical_message=technical_message,
            recovery_actions=recovery_actions,
            context=context,
            error_code=error_code,
            is_retryable=is_retryable,
            estimated_fix_time=estimated_fix_time,
            related_documentation=related_docs
        )
        
        # Update statistics
        self._update_error_stats(classified_error)
        
        # Log classified error
        self._log_classified_error(classified_error)
        
        return classified_error
    
    def _classify_by_patterns(self, error_message: str, error_type: str) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error using pattern matching"""
        
        # First, try exception type mapping
        if error_type in self.exception_type_mappings:
            category, severity = self.exception_type_mappings[error_type]
            
            # Fine-tune based on message patterns
            for pattern, pattern_category, pattern_severity in self.all_patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return pattern_category, pattern_severity
            
            return category, severity
        
        # Pattern-based classification
        for pattern, category, severity in self.all_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return category, severity
        
        # Default classification
        return ErrorCategory.UNKNOWN_ERROR, ErrorSeverity.MEDIUM
    
    def _generate_error_code(self, category: ErrorCategory, error_type: str) -> str:
        """Generate unique error code"""
        category_codes = {
            ErrorCategory.USER_ERROR: "USR",
            ErrorCategory.VALIDATION_ERROR: "VAL", 
            ErrorCategory.AUTHENTICATION_ERROR: "AUTH",
            ErrorCategory.SYSTEM_ERROR: "SYS",
            ErrorCategory.EXTERNAL_SERVICE_ERROR: "EXT",
            ErrorCategory.DATABASE_ERROR: "DB",
            ErrorCategory.AI_SERVICE_ERROR: "AI",
            ErrorCategory.NETWORK_ERROR: "NET",
            ErrorCategory.PERMISSION_ERROR: "PERM",
            ErrorCategory.RESOURCE_ERROR: "RES",
            ErrorCategory.CONFIGURATION_ERROR: "CFG",
            ErrorCategory.UNKNOWN_ERROR: "UNK"
        }
        
        code_prefix = category_codes.get(category, "UNK")
        type_hash = hash(error_type) % 1000
        
        return f"{code_prefix}{type_hash:03d}"
    
    def _generate_user_message(
        self,
        category: ErrorCategory,
        error: Exception,
        context: ErrorContext
    ) -> str:
        """Generate user-friendly error message"""
        
        user_messages = {
            ErrorCategory.USER_ERROR: "There was an issue with the information provided. Please check your input and try again.",
            ErrorCategory.VALIDATION_ERROR: "The data you entered doesn't meet the required format. Please review and correct the highlighted fields.",
            ErrorCategory.AUTHENTICATION_ERROR: "We couldn't verify your identity. Please check your login credentials and try again.",
            ErrorCategory.PERMISSION_ERROR: "You don't have permission to perform this action. Please contact your administrator if you believe this is an error.",
            ErrorCategory.SYSTEM_ERROR: "We're experiencing a technical issue. Our team has been notified and is working to resolve it.",
            ErrorCategory.EXTERNAL_SERVICE_ERROR: "One of our external services is temporarily unavailable. Please try again in a few minutes.",
            ErrorCategory.DATABASE_ERROR: "We're having trouble accessing your data. Please try again shortly.",
            ErrorCategory.AI_SERVICE_ERROR: "Our AI service is temporarily unavailable. Please try again in a few minutes.",
            ErrorCategory.NETWORK_ERROR: "There's a connection issue. Please check your internet connection and try again.",
            ErrorCategory.RESOURCE_ERROR: "The system is currently at capacity. Please try again in a few minutes.",
            ErrorCategory.CONFIGURATION_ERROR: "There's a configuration issue. Our technical team has been notified.",
            ErrorCategory.UNKNOWN_ERROR: "An unexpected error occurred. We've logged the issue and our team will investigate."
        }
        
        base_message = user_messages.get(category, user_messages[ErrorCategory.UNKNOWN_ERROR])
        
        # Add context-specific information for legal users
        if context.firm_id:
            base_message += " If this issue persists, please contact your firm's IT administrator."
        
        return base_message
    
    def _generate_technical_message(self, error: Exception) -> str:
        """Generate technical error message for logging"""
        return f"{type(error).__name__}: {str(error)}\n{traceback.format_exc()}"
    
    def _generate_recovery_actions(
        self,
        category: ErrorCategory,
        error: Exception,
        context: ErrorContext
    ) -> List[str]:
        """Generate recovery action suggestions"""
        
        recovery_actions = {
            ErrorCategory.USER_ERROR: [
                "Verify the input data format",
                "Check required fields are filled",
                "Try with different input values"
            ],
            ErrorCategory.VALIDATION_ERROR: [
                "Review the validation requirements",
                "Correct any highlighted errors",
                "Ensure all required fields are completed"
            ],
            ErrorCategory.AUTHENTICATION_ERROR: [
                "Check your username and password",
                "Clear browser cache and cookies",
                "Reset your password if needed",
                "Contact your administrator"
            ],
            ErrorCategory.PERMISSION_ERROR: [
                "Contact your firm administrator",
                "Verify your user role and permissions",
                "Ensure you're logged into the correct account"
            ],
            ErrorCategory.SYSTEM_ERROR: [
                "Try refreshing the page",
                "Wait a few minutes and try again",
                "Contact technical support if the issue persists"
            ],
            ErrorCategory.EXTERNAL_SERVICE_ERROR: [
                "Wait 2-3 minutes and try again",
                "Check if the service is experiencing known issues",
                "Use alternative features if available"
            ],
            ErrorCategory.DATABASE_ERROR: [
                "Try again in a few minutes",
                "Check your internet connection",
                "Contact support if data appears corrupted"
            ],
            ErrorCategory.AI_SERVICE_ERROR: [
                "Reduce the size of your request",
                "Try again in a few minutes",
                "Use simpler queries",
                "Check if you've reached usage limits"
            ],
            ErrorCategory.NETWORK_ERROR: [
                "Check your internet connection",
                "Try refreshing the page",
                "Disable VPN if using one",
                "Contact your network administrator"
            ],
            ErrorCategory.RESOURCE_ERROR: [
                "Try again during off-peak hours",
                "Reduce the size of your request",
                "Contact support to increase limits"
            ],
            ErrorCategory.CONFIGURATION_ERROR: [
                "Contact your system administrator",
                "Check system configuration",
                "Verify environment setup"
            ],
            ErrorCategory.UNKNOWN_ERROR: [
                "Try refreshing the page",
                "Clear browser cache",
                "Try again in a few minutes",
                "Contact technical support with error details"
            ]
        }
        
        return recovery_actions.get(category, recovery_actions[ErrorCategory.UNKNOWN_ERROR])
    
    def _is_retryable(self, category: ErrorCategory, error: Exception) -> bool:
        """Determine if error is retryable"""
        retryable_categories = {
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.EXTERNAL_SERVICE_ERROR,
            ErrorCategory.AI_SERVICE_ERROR,
            ErrorCategory.RESOURCE_ERROR,
            ErrorCategory.DATABASE_ERROR
        }
        
        non_retryable_errors = {
            'PermissionError',
            'AuthenticationError',
            'ValidationError',
            'ValueError',
            'TypeError'
        }
        
        if category in retryable_categories:
            return type(error).__name__ not in non_retryable_errors
        
        return False
    
    def _estimate_fix_time(self, category: ErrorCategory, severity: ErrorSeverity) -> str:
        """Estimate time to resolution"""
        fix_times = {
            (ErrorCategory.USER_ERROR, ErrorSeverity.LOW): "Immediate (fix your input)",
            (ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW): "Immediate (correct input)",
            (ErrorCategory.AUTHENTICATION_ERROR, ErrorSeverity.LOW): "1-2 minutes",
            (ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM): "2-5 minutes",
            (ErrorCategory.EXTERNAL_SERVICE_ERROR, ErrorSeverity.MEDIUM): "5-15 minutes",
            (ErrorCategory.AI_SERVICE_ERROR, ErrorSeverity.MEDIUM): "5-10 minutes",
            (ErrorCategory.DATABASE_ERROR, ErrorSeverity.MEDIUM): "10-30 minutes",
            (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH): "30 minutes - 2 hours",
            (ErrorCategory.CONFIGURATION_ERROR, ErrorSeverity.HIGH): "1-4 hours",
            (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.CRITICAL): "2-8 hours"
        }
        
        return fix_times.get((category, severity), "Unknown - contact support")
    
    def _get_related_documentation(self, category: ErrorCategory) -> Optional[str]:
        """Get links to related documentation"""
        docs = {
            ErrorCategory.USER_ERROR: "/docs/user-guide",
            ErrorCategory.VALIDATION_ERROR: "/docs/data-formats",
            ErrorCategory.AUTHENTICATION_ERROR: "/docs/authentication",
            ErrorCategory.PERMISSION_ERROR: "/docs/user-roles",
            ErrorCategory.AI_SERVICE_ERROR: "/docs/ai-services",
            ErrorCategory.DATABASE_ERROR: "/docs/troubleshooting",
            ErrorCategory.NETWORK_ERROR: "/docs/connectivity"
        }
        
        return docs.get(category)
    
    def _update_error_stats(self, classified_error: ClassifiedError):
        """Update error statistics for pattern learning"""
        key = f"{classified_error.category.value}:{classified_error.severity.value}"
        
        if key not in self.error_stats:
            self.error_stats[key] = {
                'count': 0,
                'first_seen': datetime.now(),
                'last_seen': datetime.now()
            }
        
        self.error_stats[key]['count'] += 1
        self.error_stats[key]['last_seen'] = datetime.now()
    
    def _log_classified_error(self, classified_error: ClassifiedError):
        """Log classified error with appropriate level"""
        log_levels = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        
        log_level = log_levels.get(classified_error.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"Classified Error [{classified_error.error_code}]: "
            f"{classified_error.category.value} | {classified_error.severity.value} | "
            f"{classified_error.user_message}"
        )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error classification statistics"""
        return {
            'total_errors_classified': sum(stats['count'] for stats in self.error_stats.values()),
            'error_breakdown': self.error_stats,
            'most_common_errors': sorted(
                self.error_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]
        }


# Global error classifier instance
_error_classifier = None


def get_error_classifier() -> ErrorClassifier:
    """Get global error classifier instance"""
    global _error_classifier
    if _error_classifier is None:
        _error_classifier = ErrorClassifier()
    return _error_classifier


def classify_error(error: Exception, context: Optional[ErrorContext] = None) -> ClassifiedError:
    """Helper function to classify an error"""
    classifier = get_error_classifier()
    return classifier.classify_error(error, context)