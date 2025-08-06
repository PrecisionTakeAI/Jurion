"""
Law Firm model for multi-tenant architecture
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship, validates
from .base import Base, generate_uuid
from .enums import AustralianState, SubscriptionTier, ComplianceStatus
import re

class LawFirm(Base):
    """
    Law Firm entity for multi-tenant architecture
    Each firm has isolated data with row-level security
    """
    __tablename__ = 'law_firms'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    abn = Column(String(11), unique=True)  # Australian Business Number
    
    # Contact information
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    state = Column(ENUM(AustralianState), nullable=True)
    postal_code = Column(String(10))
    country = Column(String(3), default='AUS')
    
    # Subscription and limits
    subscription_tier = Column(ENUM(SubscriptionTier), default=SubscriptionTier.PROFESSIONAL)
    max_users = Column(Integer, default=15)
    storage_limit_gb = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    
    # Compliance tracking
    compliance_status = Column(ENUM(ComplianceStatus), default=ComplianceStatus.PENDING)
    last_audit_date = Column(DateTime)
    next_audit_date = Column(DateTime)
    
    # Legal practitioner verification
    principal_practitioner_number = Column(String(20))
    practitioner_state = Column(ENUM(AustralianState))
    
    # Financial information
    billing_email = Column(String(255))
    billing_address = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="firm", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="firm", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="firm", cascade="all, delete-orphan")
    ai_interactions = relationship("AIInteraction", back_populates="firm", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="firm", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LawFirm(name='{self.name}', abn='{self.abn}')>"
    
    @validates('abn')
    def validate_abn(self, key, abn):
        """Validate Australian Business Number format"""
        if abn and not re.match(r'^\d{11}$', abn):
            raise ValueError("ABN must be 11 digits")
        return abn
    
    @validates('email')
    def validate_email(self, key, email):
        """Basic email validation"""
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValueError("Invalid email format")
        return email
    
    @validates('phone')
    def validate_phone(self, key, phone):
        """Basic phone validation"""
        if phone and not re.match(r'^[\+]?[\d\s\-\(\)]{8,20}$', phone):
            raise ValueError("Invalid phone format")
        return phone
    
    def get_user_count(self):
        """Get current active user count"""
        return len([user for user in self.users if user.is_active])
    
    def can_add_user(self):
        """Check if firm can add more users based on subscription"""
        return self.get_user_count() < self.max_users
    
    def get_storage_usage_mb(self):
        """Calculate current storage usage in MB"""
        total_size = sum(doc.file_size for doc in self.documents)
        return total_size / (1024 * 1024)  # Convert bytes to MB
    
    def can_upload_file(self, file_size_bytes):
        """Check if file upload is within storage limits"""
        current_usage_gb = self.get_storage_usage_mb() / 1024
        file_size_gb = file_size_bytes / (1024 * 1024 * 1024)
        return (current_usage_gb + file_size_gb) <= self.storage_limit_gb