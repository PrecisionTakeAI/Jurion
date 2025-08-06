"""
Audit Log model for compliance tracking
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, validates
from .base import Base, generate_uuid

class AuditLog(Base):
    """
    Comprehensive audit logging for compliance and security
    """
    __tablename__ = 'audit_logs'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50))  # user, case, document, etc.
    entity_id = Column(UUID(as_uuid=True))
    action = Column(String(50), nullable=False)  # create, read, update, delete
    
    # Event description
    description = Column(Text, nullable=False)
    
    # Before/after data for changes
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    
    # Additional context
    metadata = Column(JSONB, default=dict)
    
    # Request context
    ip_address = Column(INET)
    user_agent = Column(Text)
    request_id = Column(String(100))
    
    # Severity and status
    severity = Column(String(20), default='info')  # info, warning, error, critical
    status = Column(String(20), default='success')  # success, failure, partial
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relationships
    firm = relationship("LawFirm", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(event='{self.event_type}', action='{self.action}')>"
    
    @validates('action')
    def validate_action(self, key, action):
        """Validate action type"""
        allowed_actions = ['create', 'read', 'update', 'delete', 'login', 'logout', 'access_denied', 'password_change']
        if action.lower() not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return action.lower()
    
    @validates('severity')
    def validate_severity(self, key, severity):
        """Validate severity level"""
        allowed_severities = ['debug', 'info', 'warning', 'error', 'critical']
        if severity.lower() not in allowed_severities:
            raise ValueError(f"Severity must be one of: {allowed_severities}")
        return severity.lower()
    
    @classmethod
    def log_user_action(cls, firm_id: str, user_id: str, action: str, description: str, 
                       entity_type: str = None, entity_id: str = None, 
                       metadata: dict = None, ip_address: str = None, user_agent: str = None):
        """Create a new audit log entry for user action"""
        return cls(
            firm_id=firm_id,
            user_id=user_id,
            event_type='user_action',
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_security_event(cls, firm_id: str, user_id: str, event: str, description: str,
                          severity: str = 'warning', metadata: dict = None, 
                          ip_address: str = None, user_agent: str = None):
        """Create a new audit log entry for security event"""
        return cls(
            firm_id=firm_id,
            user_id=user_id,
            event_type='security_event',
            action=event,
            description=description,
            severity=severity,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_data_change(cls, firm_id: str, user_id: str, entity_type: str, entity_id: str,
                       action: str, description: str, old_values: dict = None, 
                       new_values: dict = None, metadata: dict = None):
        """Create a new audit log entry for data changes"""
        return cls(
            firm_id=firm_id,
            user_id=user_id,
            event_type='data_change',
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            description=description,
            old_values=old_values,
            new_values=new_values,
            metadata=metadata or {}
        )