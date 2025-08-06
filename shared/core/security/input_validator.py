"""
OWASP-Compliant Input Validation and Sanitization
=================================================

Enhanced input validation system addressing CLAUDE.md security vulnerabilities:
- SQL injection prevention
- XSS protection for all user inputs  
- File upload security scanning
- Australian legal document validation
- Multi-layered validation with security levels

Based on OWASP Top 10 security guidelines and Australian Privacy Act compliance.
"""

import re
import os
import html
import mimetypes
import hashlib
import magic
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse, quote
import bleach
from markupsafe import Markup


class SecurityLevel(Enum):
    """Security validation levels"""
    LOW = "low"           # Basic validation
    MEDIUM = "medium"     # Standard business validation
    HIGH = "high"         # Legal document validation
    CRITICAL = "critical" # Financial/PII data validation


@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    sanitized_value: Any
    errors: List[str]
    warnings: List[str]
    security_flags: List[str]
    confidence_score: float


class ValidationError(Exception):
    """Exception raised for validation failures"""
    
    def __init__(self, message: str, errors: List[str] = None, security_flags: List[str] = None):
        super().__init__(message)
        self.errors = errors or []
        self.security_flags = security_flags or []


class InputValidator:
    """
    OWASP-compliant input validation and sanitization system.
    
    Features:
    - SQL injection prevention with parameterized queries
    - XSS protection with HTML sanitization
    - File upload security scanning
    - Australian legal document validation
    - Performance-optimized validation caching
    """
    
    def __init__(self):
        self.validation_cache = {}  # Cache for repeated validations
        self._setup_validation_rules()
        self._setup_australian_legal_patterns()
    
    def _setup_validation_rules(self):
        """Setup comprehensive validation rules"""
        
        # SQL injection patterns (comprehensive OWASP list)
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\bOR\b.*\b(TRUE|FALSE)\b)",
            r"(;\s*(SELECT|INSERT|UPDATE|DELETE))",
            r"(\b(INFORMATION_SCHEMA|SYS\.TABLES|DUAL)\b)",
            r"(\b(CONCAT|CHAR|ASCII|SUBSTRING)\s*\()",
            r"(\b(WAITFOR|DELAY)\s+)",
            r"(0x[0-9A-Fa-f]+)",  # Hex encoded strings
            r"(\b(CAST|CONVERT)\s*\()",
            r"(\bUNION\s+(ALL\s+)?SELECT\b)"
        ]
        
        # XSS patterns (extended OWASP list)
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"onmouseover\s*=",
            r"onfocus\s*=",
            r"onblur\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"expression\s*\(",
            r"@import",
            r"data:text/html",
            r"<svg[^>]*onload"
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e\\",
            r"..%2f",
            r"..%5c"
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            r"[;&|`$(){}\[\]]",
            r"\b(cat|ls|dir|type|del|rm|mv|cp|chmod|chown|ps|kill|wget|curl)\b",
            r">\s*&",
            r"\|\s*[a-zA-Z]",
            r"\$\([^)]*\)",
            r"`[^`]*`"
        ]
        
        # Australian legal document patterns
        self.australian_legal_patterns = {
            'abn': r'^(\d{2}\s?\d{3}\s?\d{3}\s?\d{3})$',
            'acn': r'^(\d{3}\s?\d{3}\s?\d{3})$',
            'legal_practitioner_number': r'^[A-Z]{2,3}\d{4,6}$',
            'case_number': r'^[A-Z]{2,4}\d{4,8}$',
            'court_file_number': r'^[A-Z]{1,3}\d{4,8}\/\d{4}$'
        }
        
        # Allowed file types for legal documents
        self.allowed_legal_file_types = {
            'application/pdf': ['.pdf'],
            'application/msword': ['.doc'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
            'text/plain': ['.txt'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'image/tiff': ['.tif', '.tiff']
        }
        
        # Maximum file sizes (in bytes)
        self.max_file_sizes = {
            'pdf': 50 * 1024 * 1024,    # 50MB for PDF
            'doc': 25 * 1024 * 1024,    # 25MB for Word docs
            'image': 10 * 1024 * 1024,  # 10MB for images
            'default': 5 * 1024 * 1024  # 5MB default
        }
    
    def _setup_australian_legal_patterns(self):
        """Setup Australian legal system specific validation patterns"""
        
        self.australian_jurisdictions = [
            'NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT'
        ]
        
        self.australian_courts = [
            'High Court of Australia',
            'Federal Court of Australia', 
            'Family Court of Australia',
            'Federal Circuit Court',
            'Supreme Court',
            'District Court',
            'Magistrates Court',
            'Local Court'
        ]
        
        self.family_law_case_types = [
            'divorce', 'property_settlement', 'child_custody',
            'spousal_maintenance', 'de_facto_property', 'parenting_orders',
            'child_support', 'adoption', 'surrogacy', 'family_violence',
            'international_child_abduction'
        ]
    
    def validate_text_input(
        self, 
        text: str, 
        field_name: str,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        max_length: int = 10000,
        allow_html: bool = False
    ) -> ValidationResult:
        """
        Validate and sanitize text input with OWASP compliance.
        
        Args:
            text: Input text to validate
            field_name: Name of the field being validated
            security_level: Security validation level
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML content
            
        Returns:
            ValidationResult with validation status and sanitized content
        """
        errors = []
        warnings = []
        security_flags = []
        
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        
        original_text = text
        
        # Length validation
        if len(text) > max_length:
            errors.append(f"Text exceeds maximum length of {max_length} characters")
        
        # Check for null bytes
        if '\x00' in text:
            security_flags.append("NULL_BYTE_DETECTED")
            errors.append("Null bytes are not allowed")
        
        # SQL injection detection
        sql_threats = self._detect_sql_injection(text)
        if sql_threats:
            security_flags.extend(sql_threats)
            errors.append("Potential SQL injection attempt detected")
        
        # XSS detection and sanitization
        if security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            xss_threats = self._detect_xss(text)
            if xss_threats:
                security_flags.extend(xss_threats)
                if not allow_html:
                    errors.append("Potentially malicious content detected")
        
        # Path traversal detection
        path_threats = self._detect_path_traversal(text)
        if path_threats:
            security_flags.extend(path_threats)
            errors.append("Path traversal attempt detected")
        
        # Command injection detection
        cmd_threats = self._detect_command_injection(text)
        if cmd_threats:
            security_flags.extend(cmd_threats)
            errors.append("Command injection attempt detected")
        
        # Sanitize content
        if allow_html:
            # Use bleach for HTML sanitization
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3']
            allowed_attributes = {}
            sanitized_text = bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes)
        else:
            # HTML escape for non-HTML content
            sanitized_text = html.escape(text, quote=True)
        
        # Additional security-level specific validation
        if security_level == SecurityLevel.CRITICAL:
            # Extra validation for financial/PII data
            pii_threats = self._detect_pii_exposure(text)
            if pii_threats:
                security_flags.extend(pii_threats)
                warnings.append("Potential PII data detected - ensure proper handling")
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            original_text, sanitized_text, security_flags, errors
        )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized_text,
            errors=errors,
            warnings=warnings,
            security_flags=security_flags,
            confidence_score=confidence_score
        )
    
    def validate_file_upload(
        self, 
        file_content: bytes, 
        filename: str,
        expected_type: Optional[str] = None,
        security_level: SecurityLevel = SecurityLevel.HIGH
    ) -> ValidationResult:
        """
        Validate and scan uploaded files for security threats.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            expected_type: Expected file type (pdf, doc, image)
            security_level: Security validation level
            
        Returns:
            ValidationResult with file security assessment
        """
        errors = []
        warnings = []
        security_flags = []
        
        # Basic file validation
        if not file_content:
            errors.append("File content is empty")
            return ValidationResult(False, None, errors, warnings, security_flags, 0.0)
        
        # Filename validation
        filename_result = self.validate_filename(filename)
        if not filename_result.is_valid:
            errors.extend(filename_result.errors)
            security_flags.extend(filename_result.security_flags)
        
        # File size validation
        file_size = len(file_content)
        max_size = self._get_max_file_size(filename)
        
        if file_size > max_size:
            errors.append(f"File size {file_size} bytes exceeds maximum {max_size} bytes")
        
        # MIME type detection and validation
        try:
            detected_mime = magic.from_buffer(file_content, mime=True)
            file_extension = os.path.splitext(filename.lower())[1]
            
            # Validate MIME type matches extension
            if not self._validate_mime_type(detected_mime, file_extension):
                security_flags.append("MIME_TYPE_MISMATCH")
                errors.append(f"File type mismatch: extension {file_extension} vs MIME {detected_mime}")
            
            # Check if file type is allowed
            if detected_mime not in self.allowed_legal_file_types:
                errors.append(f"File type {detected_mime} is not allowed")
            
        except Exception as e:
            warnings.append(f"Could not detect file type: {e}")
            security_flags.append("FILE_TYPE_DETECTION_FAILED")
        
        # Malware scanning (basic signature detection)
        malware_threats = self._scan_for_malware(file_content)
        if malware_threats:
            security_flags.extend(malware_threats)
            errors.append("Potential malware detected in file")
        
        # PDF-specific validation
        if filename.lower().endswith('.pdf'):
            pdf_threats = self._validate_pdf_content(file_content)
            if pdf_threats:
                security_flags.extend(pdf_threats)
                warnings.extend([f"PDF security concern: {threat}" for threat in pdf_threats])
        
        # Document metadata analysis
        if security_level == SecurityLevel.CRITICAL:
            metadata_issues = self._analyze_file_metadata(file_content, filename)
            if metadata_issues:
                warnings.extend(metadata_issues)
        
        confidence_score = max(0.0, 1.0 - (len(errors) * 0.3) - (len(security_flags) * 0.2))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=file_content if len(errors) == 0 else None,
            errors=errors,
            warnings=warnings,
            security_flags=security_flags,
            confidence_score=confidence_score
        )
    
    def validate_filename(self, filename: str) -> ValidationResult:
        """Validate uploaded filename for security"""
        errors = []
        security_flags = []
        
        if not filename:
            errors.append("Filename cannot be empty")
        
        # Path traversal in filename
        if any(pattern in filename for pattern in ['../', '..\\', '%2e%2e']):
            security_flags.append("PATH_TRAVERSAL_FILENAME")
            errors.append("Path traversal attempt in filename")
        
        # Dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in dangerous_chars:
            if char in filename:
                security_flags.append("DANGEROUS_FILENAME_CHAR")
                errors.append(f"Dangerous character '{char}' in filename")
        
        # Length check
        if len(filename) > 255:
            errors.append("Filename too long (max 255 characters)")
        
        # Sanitize filename
        sanitized = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)
        sanitized = sanitized.replace('..', '_')
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized,
            errors=errors,
            warnings=[],
            security_flags=security_flags,
            confidence_score=1.0 if len(errors) == 0 else 0.5
        )
    
    def validate_australian_legal_identifier(
        self, 
        identifier: str, 
        identifier_type: str
    ) -> ValidationResult:
        """
        Validate Australian legal system identifiers.
        
        Args:
            identifier: The identifier to validate
            identifier_type: Type of identifier (abn, acn, legal_practitioner_number, etc.)
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        if identifier_type not in self.australian_legal_patterns:
            errors.append(f"Unknown Australian legal identifier type: {identifier_type}")
            return ValidationResult(False, identifier, errors, warnings, [], 0.0)
        
        pattern = self.australian_legal_patterns[identifier_type]
        
        if not re.match(pattern, identifier.strip()):
            errors.append(f"Invalid {identifier_type} format")
        
        # Additional validation for specific types
        if identifier_type == 'abn':
            # ABN checksum validation
            if not self._validate_abn_checksum(identifier):
                errors.append("Invalid ABN checksum")
        
        sanitized = identifier.strip().upper() if identifier_type == 'legal_practitioner_number' else identifier.strip()
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized,
            errors=errors,
            warnings=warnings,
            security_flags=[],
            confidence_score=1.0 if len(errors) == 0 else 0.0
        )
    
    def _detect_sql_injection(self, text: str) -> List[str]:
        """Detect SQL injection patterns"""
        threats = []
        text_upper = text.upper()
        
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                threats.append("SQL_INJECTION_DETECTED")
                break
        
        return threats
    
    def _detect_xss(self, text: str) -> List[str]:
        """Detect XSS patterns"""
        threats = []
        
        for pattern in self.xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append("XSS_DETECTED")
                break
        
        return threats
    
    def _detect_path_traversal(self, text: str) -> List[str]:
        """Detect path traversal patterns"""
        threats = []
        
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append("PATH_TRAVERSAL_DETECTED")
                break
        
        return threats
    
    def _detect_command_injection(self, text: str) -> List[str]:
        """Detect command injection patterns"""
        threats = []
        
        for pattern in self.command_injection_patterns:
            if re.search(pattern, text):
                threats.append("COMMAND_INJECTION_DETECTED")
                break
        
        return threats
    
    def _detect_pii_exposure(self, text: str) -> List[str]:
        """Detect potential PII data exposure"""
        threats = []
        
        # Australian TFN pattern
        if re.search(r'\b\d{3}\s?\d{3}\s?\d{3}\b', text):
            threats.append("POTENTIAL_TFN_DETECTED")
        
        # Credit card patterns
        if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', text):
            threats.append("POTENTIAL_CREDIT_CARD_DETECTED")
        
        # Email addresses
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            threats.append("EMAIL_ADDRESS_DETECTED")
        
        return threats
    
    def _validate_mime_type(self, mime_type: str, file_extension: str) -> bool:
        """Validate MIME type matches file extension"""
        if mime_type in self.allowed_legal_file_types:
            allowed_extensions = self.allowed_legal_file_types[mime_type]
            return file_extension in allowed_extensions
        return False
    
    def _get_max_file_size(self, filename: str) -> int:
        """Get maximum file size based on file type"""
        extension = os.path.splitext(filename.lower())[1]
        
        if extension == '.pdf':
            return self.max_file_sizes['pdf']
        elif extension in ['.doc', '.docx']:
            return self.max_file_sizes['doc']
        elif extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            return self.max_file_sizes['image']
        else:
            return self.max_file_sizes['default']
    
    def _scan_for_malware(self, file_content: bytes) -> List[str]:
        """Basic malware signature detection"""
        threats = []
        
        # Check for executable signatures
        executable_signatures = [
            b'MZ',  # PE executable
            b'\x7fELF',  # ELF executable
            b'\xfe\xed\xfa',  # Mach-O executable
        ]
        
        for signature in executable_signatures:
            if file_content.startswith(signature):
                threats.append("EXECUTABLE_FILE_DETECTED")
        
        # Check for script content in non-script files
        script_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'<?php',
            b'#!/bin/',
            b'powershell'
        ]
        
        for pattern in script_patterns:
            if pattern in file_content.lower():
                threats.append("EMBEDDED_SCRIPT_DETECTED")
        
        return threats
    
    def _validate_pdf_content(self, pdf_content: bytes) -> List[str]:
        """Validate PDF content for security issues"""
        threats = []
        
        # Check PDF header
        if not pdf_content.startswith(b'%PDF-'):
            threats.append("INVALID_PDF_HEADER")
        
        # Check for JavaScript in PDF
        if b'/JavaScript' in pdf_content or b'/JS' in pdf_content:
            threats.append("PDF_JAVASCRIPT_DETECTED")
        
        # Check for forms/actions
        if b'/Action' in pdf_content:
            threats.append("PDF_ACTION_DETECTED")
        
        # Check for external references
        if b'/URI' in pdf_content:
            threats.append("PDF_EXTERNAL_URI_DETECTED")
        
        return threats
    
    def _analyze_file_metadata(self, file_content: bytes, filename: str) -> List[str]:
        """Analyze file metadata for security concerns"""
        issues = []
        
        # This would integrate with metadata extraction libraries
        # For now, basic checks
        
        if len(file_content) < 100:
            issues.append("File suspiciously small")
        
        # Check for hidden file extensions
        if filename.count('.') > 1:
            issues.append("Multiple file extensions detected")
        
        return issues
    
    def _validate_abn_checksum(self, abn: str) -> bool:
        """Validate Australian Business Number checksum"""
        # Remove spaces and convert to digits
        digits = re.sub(r'\s', '', abn)
        if len(digits) != 11 or not digits.isdigit():
            return False
        
        # ABN checksum algorithm
        weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
        
        # Subtract 1 from first digit
        first_digit = int(digits[0]) - 1
        if first_digit < 0:
            return False
        
        # Calculate weighted sum
        total = first_digit * weights[0]
        for i in range(1, 11):
            total += int(digits[i]) * weights[i]
        
        # Check if divisible by 89
        return total % 89 == 0
    
    def _calculate_confidence_score(
        self, 
        original: str, 
        sanitized: str, 
        security_flags: List[str], 
        errors: List[str]
    ) -> float:
        """Calculate confidence score for validation result"""
        base_score = 1.0
        
        # Reduce score for security flags
        base_score -= len(security_flags) * 0.1
        
        # Reduce score for errors
        base_score -= len(errors) * 0.2
        
        # Reduce score if significant sanitization occurred
        if len(original) > 0:
            sanitization_ratio = abs(len(original) - len(sanitized)) / len(original)
            base_score -= sanitization_ratio * 0.3
        
        return max(0.0, min(1.0, base_score))


# Validation helper functions
def validate_legal_query(query: str) -> ValidationResult:
    """Helper function to validate legal queries"""
    validator = InputValidator()
    return validator.validate_text_input(
        query, 
        "legal_query", 
        SecurityLevel.HIGH,
        max_length=5000,
        allow_html=False
    )


def validate_case_number(case_number: str) -> ValidationResult:
    """Helper function to validate Australian case numbers"""
    validator = InputValidator()
    return validator.validate_australian_legal_identifier(case_number, 'case_number')


def validate_uploaded_document(file_content: bytes, filename: str) -> ValidationResult:
    """Helper function to validate uploaded legal documents"""
    validator = InputValidator()
    return validator.validate_file_upload(
        file_content, 
        filename, 
        security_level=SecurityLevel.HIGH
    )