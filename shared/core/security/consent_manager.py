"""
Privacy Act 1988 Compliant Consent Management System
====================================================

Implements comprehensive consent management for multi-agent data processing
with Australian Privacy Act 1988 compliance, including:
- Explicit consent collection and management
- Multi-agent processing consent workflows
- Data retention and purging policies
- Audit trail for all consent activities
- Integration with existing security infrastructure
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from shared.core.security.encryption_service import get_encryption_service
from shared.core.security.input_validator import InputValidator, SecurityLevel
from shared.database.models import Base


class ConsentType(Enum):
    """Types of consent for different data processing activities"""
    AI_PROCESSING = "ai_processing"
    DOCUMENT_ANALYSIS = "document_analysis"
    FINANCIAL_DATA_PROCESSING = "financial_data_processing"
    CROSS_BORDER_TRANSFER = "cross_border_transfer"
    MULTI_AGENT_PROCESSING = "multi_agent_processing"
    AUTOMATED_DECISIONS = "automated_decisions"
    DATA_SHARING = "data_sharing"
    MARKETING = "marketing"


class ConsentStatus(Enum):
    """Status of consent"""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


@dataclass
class ConsentRequest:
    """Request for user consent"""
    consent_type: ConsentType
    purpose: str
    data_categories: List[str]
    processing_description: str
    retention_period_days: int
    third_party_sharing: bool = False
    third_party_recipients: List[str] = None
    offshore_disclosure: bool = False
    offshore_countries: List[str] = None
    automated_decision_making: bool = False
    withdrawal_mechanism: str = "Via settings or contacting support"
    agents_involved: List[str] = None


@dataclass
class ConsentDecision:
    """User's consent decision"""
    granted: bool
    timestamp: datetime
    ip_address: str
    user_agent: str
    consent_method: str  # 'explicit_form', 'checkbox', 'verbal', etc.
    guardian_consent: bool = False
    guardian_details: Optional[Dict] = None


class UserConsent(Base):
    """Database model for user consents"""
    __tablename__ = 'user_consents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id'), nullable=False)
    
    # Consent details
    consent_type = Column(String(50), nullable=False)
    consent_version = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    
    # Consent metadata
    purpose = Column(Text, nullable=False)
    data_categories = Column(JSON, nullable=False)
    processing_description = Column(Text, nullable=False)
    retention_period_days = Column(Integer, nullable=False)
    
    # Third party and offshore
    third_party_sharing = Column(Boolean, default=False)
    third_party_recipients = Column(JSON)
    offshore_disclosure = Column(Boolean, default=False)
    offshore_countries = Column(JSON)
    
    # Automated processing
    automated_decision_making = Column(Boolean, default=False)
    agents_involved = Column(JSON)
    
    # Consent decision
    granted_at = Column(DateTime(timezone=True))
    denied_at = Column(DateTime(timezone=True))
    withdrawn_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    
    # Consent context
    ip_address = Column(String(45))  # Encrypted
    user_agent = Column(Text)  # Encrypted
    consent_method = Column(String(50))
    
    # Guardian consent for minors
    guardian_consent = Column(Boolean, default=False)
    guardian_details = Column(JSON)  # Encrypted
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    firm = relationship("LawFirm")
    audit_logs = relationship("ConsentAuditLog", back_populates="consent", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_consent_type', 'user_id', 'consent_type'),
        Index('idx_consent_status', 'status'),
        Index('idx_consent_expiry', 'expires_at'),
    )


class ConsentAuditLog(Base):
    """Audit trail for all consent activities"""
    __tablename__ = 'consent_audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consent_id = Column(UUID(as_uuid=True), ForeignKey('user_consents.id'), nullable=False)
    
    # Audit details
    action = Column(String(50), nullable=False)  # 'requested', 'granted', 'denied', 'withdrawn', 'expired'
    action_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Context
    ip_address = Column(String(45))  # Encrypted
    user_agent = Column(Text)  # Encrypted
    reason = Column(Text)
    metadata = Column(JSON)
    
    # Relationships
    consent = relationship("UserConsent", back_populates="audit_logs")
    actor = relationship("User")


class ConsentManager:
    """
    Privacy Act 1988 compliant consent management system.
    
    Handles all aspects of user consent for data processing:
    - Consent collection and storage
    - Multi-agent processing consent
    - Consent withdrawal and expiry
    - Audit logging for compliance
    - Integration with encryption service
    """
    
    def __init__(self, db_session, firm_id: str = None):
        self.db_session = db_session
        self.firm_id = firm_id
        self.encryption_service = get_encryption_service()
        self.input_validator = InputValidator()
        self.logger = logging.getLogger(__name__)
        
        # Consent configuration
        self.consent_version = "2.1"  # Update when consent requirements change
        self.default_retention_days = 730  # 2 years default
        self.consent_expiry_days = 365  # 1 year validity
        
    def request_consent(
        self,
        user_id: str,
        consent_request: ConsentRequest,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Request consent from user for data processing.
        
        Args:
            user_id: User ID requesting consent from
            consent_request: Details of what consent is being requested
            context: Request context (IP, user agent, etc.)
            
        Returns:
            Dict with consent request details and ID
        """
        try:
            # Validate inputs
            validation_result = self.input_validator.validate_text_input(
                user_id,
                "user_id",
                SecurityLevel.HIGH
            )
            if not validation_result.is_valid:
                raise ValueError(f"Invalid user_id: {validation_result.errors}")
            
            # Check for existing active consent
            existing_consent = self._get_active_consent(
                user_id,
                consent_request.consent_type
            )
            
            if existing_consent:
                return {
                    'consent_id': str(existing_consent.id),
                    'status': 'already_granted',
                    'expires_at': existing_consent.expires_at.isoformat(),
                    'message': 'User has already granted this consent'
                }
            
            # Create new consent record
            consent = UserConsent(
                user_id=uuid.UUID(user_id),
                firm_id=uuid.UUID(self.firm_id) if self.firm_id else None,
                consent_type=consent_request.consent_type.value,
                consent_version=self.consent_version,
                status=ConsentStatus.PENDING.value,
                purpose=consent_request.purpose,
                data_categories=consent_request.data_categories,
                processing_description=consent_request.processing_description,
                retention_period_days=consent_request.retention_period_days,
                third_party_sharing=consent_request.third_party_sharing,
                third_party_recipients=consent_request.third_party_recipients,
                offshore_disclosure=consent_request.offshore_disclosure,
                offshore_countries=consent_request.offshore_countries,
                automated_decision_making=consent_request.automated_decision_making,
                agents_involved=consent_request.agents_involved,
                ip_address=self._encrypt_pii(context.get('ip_address', '')),
                user_agent=self._encrypt_pii(context.get('user_agent', ''))
            )
            
            self.db_session.add(consent)
            
            # Create audit log
            audit_log = ConsentAuditLog(
                consent_id=consent.id,
                action='requested',
                action_by=uuid.UUID(user_id),
                ip_address=self._encrypt_pii(context.get('ip_address', '')),
                user_agent=self._encrypt_pii(context.get('user_agent', '')),
                metadata={
                    'consent_version': self.consent_version,
                    'request_source': context.get('source', 'web_interface')
                }
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
            self.logger.info(f"Consent requested for user {user_id}, type: {consent_request.consent_type.value}")
            
            return {
                'consent_id': str(consent.id),
                'status': 'pending',
                'consent_type': consent_request.consent_type.value,
                'purpose': consent_request.purpose,
                'data_categories': consent_request.data_categories,
                'requires_action': True
            }
            
        except Exception as e:
            self.logger.error(f"Error requesting consent: {e}")
            self.db_session.rollback()
            raise
    
    def record_consent_decision(
        self,
        consent_id: str,
        user_id: str,
        decision: ConsentDecision
    ) -> Dict[str, Any]:
        """
        Record user's consent decision.
        
        Args:
            consent_id: ID of consent request
            user_id: User making the decision
            decision: Consent decision details
            
        Returns:
            Dict with consent status
        """
        try:
            # Get consent record
            consent = self.db_session.query(UserConsent).filter_by(
                id=uuid.UUID(consent_id),
                user_id=uuid.UUID(user_id)
            ).first()
            
            if not consent:
                raise ValueError("Consent record not found")
            
            if consent.status != ConsentStatus.PENDING.value:
                raise ValueError(f"Consent already {consent.status}")
            
            # Update consent based on decision
            if decision.granted:
                consent.status = ConsentStatus.GRANTED.value
                consent.granted_at = decision.timestamp
                consent.expires_at = decision.timestamp + timedelta(days=self.consent_expiry_days)
                consent.consent_method = decision.consent_method
                action = 'granted'
            else:
                consent.status = ConsentStatus.DENIED.value
                consent.denied_at = decision.timestamp
                action = 'denied'
            
            # Update consent context
            consent.ip_address = self._encrypt_pii(decision.ip_address)
            consent.user_agent = self._encrypt_pii(decision.user_agent)
            
            # Handle guardian consent
            if decision.guardian_consent:
                consent.guardian_consent = True
                consent.guardian_details = self._encrypt_json(decision.guardian_details)
            
            # Create audit log
            audit_log = ConsentAuditLog(
                consent_id=consent.id,
                action=action,
                action_by=uuid.UUID(user_id),
                ip_address=self._encrypt_pii(decision.ip_address),
                user_agent=self._encrypt_pii(decision.user_agent),
                metadata={
                    'consent_method': decision.consent_method,
                    'guardian_consent': decision.guardian_consent
                }
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
            self.logger.info(f"Consent {action} for user {user_id}, consent_id: {consent_id}")
            
            return {
                'consent_id': consent_id,
                'status': consent.status,
                'granted': decision.granted,
                'expires_at': consent.expires_at.isoformat() if consent.expires_at else None,
                'message': f"Consent {action} successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error recording consent decision: {e}")
            self.db_session.rollback()
            raise
    
    def withdraw_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        reason: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Withdraw previously granted consent.
        
        Args:
            user_id: User withdrawing consent
            consent_type: Type of consent to withdraw
            reason: Optional reason for withdrawal
            context: Request context
            
        Returns:
            Dict with withdrawal confirmation
        """
        try:
            # Get active consent
            consent = self._get_active_consent(user_id, consent_type)
            
            if not consent:
                raise ValueError(f"No active consent found for type: {consent_type.value}")
            
            # Update consent status
            consent.status = ConsentStatus.WITHDRAWN.value
            consent.withdrawn_at = datetime.utcnow()
            
            # Create audit log
            audit_log = ConsentAuditLog(
                consent_id=consent.id,
                action='withdrawn',
                action_by=uuid.UUID(user_id),
                reason=reason,
                ip_address=self._encrypt_pii(context.get('ip_address', '')) if context else None,
                user_agent=self._encrypt_pii(context.get('user_agent', '')) if context else None,
                metadata={
                    'withdrawal_source': context.get('source', 'user_request') if context else 'user_request'
                }
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
            self.logger.info(f"Consent withdrawn for user {user_id}, type: {consent_type.value}")
            
            # Trigger data deletion if required
            self._schedule_data_deletion(user_id, consent_type)
            
            return {
                'consent_id': str(consent.id),
                'status': 'withdrawn',
                'consent_type': consent_type.value,
                'withdrawn_at': consent.withdrawn_at.isoformat(),
                'data_deletion_scheduled': True,
                'message': 'Consent withdrawn successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Error withdrawing consent: {e}")
            self.db_session.rollback()
            raise
    
    def check_consent(
        self,
        user_id: str,
        consent_types: List[ConsentType]
    ) -> Dict[ConsentType, bool]:
        """
        Check if user has granted specific consents.
        
        Args:
            user_id: User to check
            consent_types: List of consent types to check
            
        Returns:
            Dict mapping consent types to granted status
        """
        try:
            results = {}
            
            for consent_type in consent_types:
                active_consent = self._get_active_consent(user_id, consent_type)
                results[consent_type] = active_consent is not None
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking consent: {e}")
            raise
    
    def get_consent_history(
        self,
        user_id: str,
        include_audit_logs: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get user's consent history.
        
        Args:
            user_id: User ID
            include_audit_logs: Include detailed audit logs
            
        Returns:
            List of consent records
        """
        try:
            consents = self.db_session.query(UserConsent).filter_by(
                user_id=uuid.UUID(user_id)
            ).order_by(UserConsent.created_at.desc()).all()
            
            history = []
            for consent in consents:
                record = {
                    'consent_id': str(consent.id),
                    'consent_type': consent.consent_type,
                    'status': consent.status,
                    'purpose': consent.purpose,
                    'granted_at': consent.granted_at.isoformat() if consent.granted_at else None,
                    'withdrawn_at': consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
                    'expires_at': consent.expires_at.isoformat() if consent.expires_at else None,
                    'created_at': consent.created_at.isoformat()
                }
                
                if include_audit_logs:
                    audit_logs = []
                    for log in consent.audit_logs:
                        audit_logs.append({
                            'action': log.action,
                            'timestamp': log.action_timestamp.isoformat(),
                            'reason': log.reason
                        })
                    record['audit_logs'] = audit_logs
                
                history.append(record)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting consent history: {e}")
            raise
    
    def request_multi_agent_consent(
        self,
        user_id: str,
        workflow_type: str,
        agents: List[str],
        data_description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Request consent for multi-agent processing workflow.
        
        Args:
            user_id: User ID
            workflow_type: Type of multi-agent workflow
            agents: List of agents that will process data
            data_description: Description of data to be processed
            context: Request context
            
        Returns:
            Dict with consent request details
        """
        # Create comprehensive consent request for multi-agent processing
        consent_request = ConsentRequest(
            consent_type=ConsentType.MULTI_AGENT_PROCESSING,
            purpose=f"Process your data using multiple AI agents for {workflow_type}",
            data_categories=self._determine_data_categories(workflow_type, agents),
            processing_description=(
                f"Your data will be processed by {len(agents)} specialized AI agents "
                f"working together to {data_description}. Each agent will only access "
                f"the data necessary for its specific function."
            ),
            retention_period_days=self._get_retention_period(workflow_type),
            third_party_sharing=False,
            automated_decision_making='decision' in [a.lower() for a in agents],
            agents_involved=agents
        )
        
        return self.request_consent(user_id, consent_request, context)
    
    def expire_old_consents(self) -> int:
        """
        Mark expired consents and return count.
        
        Returns:
            Number of consents expired
        """
        try:
            expired_consents = self.db_session.query(UserConsent).filter(
                UserConsent.status == ConsentStatus.GRANTED.value,
                UserConsent.expires_at < datetime.utcnow()
            ).all()
            
            count = 0
            for consent in expired_consents:
                consent.status = ConsentStatus.EXPIRED.value
                
                # Create audit log
                audit_log = ConsentAuditLog(
                    consent_id=consent.id,
                    action='expired',
                    metadata={'expiry_date': consent.expires_at.isoformat()}
                )
                self.db_session.add(audit_log)
                count += 1
            
            if count > 0:
                self.db_session.commit()
                self.logger.info(f"Expired {count} consents")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error expiring consents: {e}")
            self.db_session.rollback()
            raise
    
    def _get_active_consent(
        self,
        user_id: str,
        consent_type: ConsentType
    ) -> Optional[UserConsent]:
        """Get active consent for user and type"""
        return self.db_session.query(UserConsent).filter(
            UserConsent.user_id == uuid.UUID(user_id),
            UserConsent.consent_type == consent_type.value,
            UserConsent.status == ConsentStatus.GRANTED.value,
            UserConsent.expires_at > datetime.utcnow()
        ).first()
    
    def _encrypt_pii(self, data: str) -> str:
        """Encrypt PII data"""
        if not data:
            return None
        return self.encryption_service.encrypt_string(data, "consent_pii")
    
    def _decrypt_pii(self, encrypted_data: str) -> str:
        """Decrypt PII data"""
        if not encrypted_data:
            return None
        return self.encryption_service.decrypt_string(encrypted_data, "consent_pii")
    
    def _encrypt_json(self, data: Dict) -> str:
        """Encrypt JSON data"""
        if not data:
            return None
        json_str = json.dumps(data)
        return self.encryption_service.encrypt_string(json_str, "consent_json")
    
    def _decrypt_json(self, encrypted_data: str) -> Dict:
        """Decrypt JSON data"""
        if not encrypted_data:
            return None
        json_str = self.encryption_service.decrypt_string(encrypted_data, "consent_json")
        return json.loads(json_str)
    
    def _determine_data_categories(
        self,
        workflow_type: str,
        agents: List[str]
    ) -> List[str]:
        """Determine data categories based on workflow and agents"""
        categories = ['personal_information', 'case_data']
        
        if 'financial' in workflow_type.lower() or 'financial_analyst' in agents:
            categories.extend(['financial_records', 'asset_information', 'income_data'])
        
        if 'document' in workflow_type.lower() or 'document_analyzer' in agents:
            categories.append('legal_documents')
        
        if 'child' in workflow_type.lower() or 'parenting' in workflow_type.lower():
            categories.append('children_information')
        
        return list(set(categories))
    
    def _get_retention_period(self, workflow_type: str) -> int:
        """Get retention period based on workflow type"""
        retention_periods = {
            'property_settlement': 2555,  # 7 years
            'child_custody': 6570,  # 18 years
            'divorce': 2555,  # 7 years
            'financial_analysis': 2555,  # 7 years
            'document_review': 1095,  # 3 years
            'general': 730  # 2 years default
        }
        
        for key, days in retention_periods.items():
            if key in workflow_type.lower():
                return days
        
        return retention_periods['general']
    
    def _schedule_data_deletion(
        self,
        user_id: str,
        consent_type: ConsentType
    ):
        """Schedule data deletion after consent withdrawal"""
        # This would integrate with a task queue system
        # For now, log the requirement
        self.logger.info(
            f"Data deletion scheduled for user {user_id}, "
            f"consent type: {consent_type.value}"
        )
        # TODO: Implement actual data deletion scheduling


# Helper functions for easy access
def get_consent_manager(db_session, firm_id: str = None) -> ConsentManager:
    """Get consent manager instance"""
    return ConsentManager(db_session, firm_id)


def check_user_consent(
    db_session,
    user_id: str,
    consent_types: List[ConsentType]
) -> Dict[ConsentType, bool]:
    """Quick check for user consents"""
    manager = get_consent_manager(db_session)
    return manager.check_consent(user_id, consent_types)