"""
User model with authentication and MFA support
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship, validates
from .base import Base, generate_uuid
from .enums import UserRole, AustralianState
import re
import secrets
import pyotp
from datetime import datetime, timedelta

class User(Base):
    """
    User model with multi-factor authentication and role-based access control
    """
    __tablename__ = 'users'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(ENUM(UserRole), nullable=False, index=True)
    
    # Legal practitioner information
    practitioner_number = Column(String(20))
    practitioner_state = Column(ENUM(AustralianState))
    
    # Account status
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime)
    
    # Multi-factor authentication
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32))  # Base32 encoded TOTP secret
    mfa_backup_codes = Column(JSONB)  # Array of backup codes
    
    # Security tracking
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime)
    password_changed_at = Column(DateTime, default=func.now())
    last_password_reset = Column(DateTime)
    
    # User preferences and settings
    preferences = Column(JSONB, default=dict)
    timezone = Column(String(50), default='Australia/Sydney')
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm", back_populates="users")
    created_cases = relationship("Case", foreign_keys="Case.created_by", back_populates="creator")
    assigned_cases = relationship("Case", foreign_keys="Case.assigned_lawyer", back_populates="lawyer")
    uploaded_documents = relationship("Document", foreign_keys="Document.uploaded_by")
    ai_interactions = relationship("AIInteraction", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role.value}')>"
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format"""
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValueError("Invalid email format")
        return email.lower()
    
    @validates('practitioner_number')
    def validate_practitioner_number(self, key, practitioner_number):
        """Validate Australian legal practitioner number format"""
        if not practitioner_number:
            return practitioner_number
            
        # Basic validation - specific format depends on state
        if not re.match(r'^[A-Z0-9]{3,20}$', practitioner_number.upper()):
            raise ValueError("Invalid practitioner number format")
        return practitioner_number.upper()
    
    def set_password(self, password: str):
        """Set password with PBKDF2 hashing"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        self.password_hash = pwd_context.hash(password)
        self.password_changed_at = datetime.utcnow()
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        return pwd_context.verify(password, self.password_hash)
    
    def setup_mfa(self) -> str:
        """Setup MFA and return QR code data"""
        if not self.mfa_secret:
            self.mfa_secret = pyotp.random_base32()
        
        # Generate backup codes
        self.mfa_backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        totp = pyotp.TOTP(self.mfa_secret)
        qr_data = totp.provisioning_uri(
            name=self.email,
            issuer_name="LegalAI Hub"
        )
        return qr_data
    
    def verify_mfa_token(self, token: str) -> bool:
        """Verify MFA token or backup code"""
        if not self.mfa_enabled or not self.mfa_secret:
            return False
        
        # Check TOTP token
        totp = pyotp.TOTP(self.mfa_secret)
        if totp.verify(token, valid_window=1):
            return True
        
        # Check backup codes
        if self.mfa_backup_codes and token.upper() in self.mfa_backup_codes:
            # Remove used backup code
            self.mfa_backup_codes.remove(token.upper())
            return True
        
        return False
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if not self.account_locked_until:
            return False
        return datetime.utcnow() < self.account_locked_until
    
    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration"""
        self.account_locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0
    
    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
    
    def record_failed_login(self, max_attempts: int = 5):
        """Record failed login attempt and lock if threshold reached"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.lock_account()
    
    def record_successful_login(self):
        """Record successful login and reset counters"""
        self.last_login = datetime.utcnow()
        self.failed_login_attempts = 0
        self.account_locked_until = None
    
    def get_full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission based on role"""
        role_permissions = {
            UserRole.PRINCIPAL: ['*'],  # All permissions
            UserRole.SENIOR_LAWYER: [
                'case.create', 'case.read', 'case.update', 'case.delete',
                'document.create', 'document.read', 'document.update', 'document.delete',
                'ai.query', 'ai.generate', 'analytics.view', 'user.read'
            ],
            UserRole.LAWYER: [
                'case.create', 'case.read', 'case.update',
                'document.create', 'document.read', 'document.update',
                'ai.query', 'ai.generate'
            ],
            UserRole.PARALEGAL: [
                'case.read', 'case.update',
                'document.create', 'document.read', 'document.update',
                'ai.query'
            ],
            UserRole.ADMIN: [
                'user.create', 'user.read', 'user.update', 'user.delete',
                'firm.read', 'firm.update', 'analytics.view'
            ],
            UserRole.CLIENT: [
                'case.read', 'document.read'
            ]
        }
        
        user_permissions = role_permissions.get(self.role, [])
        return '*' in user_permissions or permission in user_permissions