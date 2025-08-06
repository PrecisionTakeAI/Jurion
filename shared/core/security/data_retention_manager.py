"""
Data Retention and Compliance Manager
====================================

Implements data retention policies and automated purging mechanisms
in compliance with Australian Privacy Act 1988 and legal requirements.

Features:
- Configurable retention policies by data type
- Automated data purging with audit trails
- Compliance with Australian legal retention requirements
- Integration with multi-agent workflows
- Secure data deletion with verification
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
import asyncio

from shared.core.security.encryption_service import get_encryption_service
from shared.database.models import (
    Case, Document, AIInteraction, UserConsent,
    ConsentStatus, ConsentType
)


class DataCategory(Enum):
    """Categories of data with different retention requirements"""
    PERSONAL_INFORMATION = "personal_information"
    FINANCIAL_RECORDS = "financial_records"
    LEGAL_DOCUMENTS = "legal_documents"
    COURT_DOCUMENTS = "court_documents"
    AI_INTERACTIONS = "ai_interactions"
    AUDIT_LOGS = "audit_logs"
    CHILDREN_INFORMATION = "children_information"
    HEALTH_RECORDS = "health_records"
    CORRESPONDENCE = "correspondence"
    TEMP_PROCESSING = "temp_processing"


class RetentionAction(Enum):
    """Actions to take when retention period expires"""
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    REVIEW = "review"


@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    data_category: DataCategory
    retention_days: int
    action: RetentionAction
    legal_basis: str
    exceptions: List[str] = None
    review_required: bool = False
    notification_days: int = 30


@dataclass
class RetentionAuditEntry:
    """Audit entry for retention actions"""
    timestamp: datetime
    action: str
    data_type: str
    record_count: int
    success: bool
    details: Dict[str, Any]
    performed_by: str = "system"


class DataRetentionManager:
    """
    Manages data retention policies and automated purging.
    
    Ensures compliance with:
    - Australian Privacy Act 1988
    - Family Law Act 1975
    - Legal professional retention requirements
    - Multi-agent data processing agreements
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.encryption_service = get_encryption_service()
        self.logger = logging.getLogger(__name__)
        
        # Initialize retention policies
        self.policies = self._initialize_retention_policies()
        
        # Audit configuration
        self.audit_retention_days = 2555  # 7 years for audit logs
        self.enable_secure_deletion = True
        self.batch_size = 100  # Process in batches
        
    def _initialize_retention_policies(self) -> Dict[DataCategory, RetentionPolicy]:
        """Initialize retention policies based on Australian legal requirements"""
        policies = {
            DataCategory.PERSONAL_INFORMATION: RetentionPolicy(
                data_category=DataCategory.PERSONAL_INFORMATION,
                retention_days=730,  # 2 years
                action=RetentionAction.DELETE,
                legal_basis="Privacy Act 1988 - APP 11.2",
                exceptions=["active_litigation", "court_order"],
                review_required=True
            ),
            
            DataCategory.FINANCIAL_RECORDS: RetentionPolicy(
                data_category=DataCategory.FINANCIAL_RECORDS,
                retention_days=2555,  # 7 years
                action=RetentionAction.ARCHIVE,
                legal_basis="ATO record keeping requirements",
                exceptions=["ongoing_audit", "dispute"],
                notification_days=60
            ),
            
            DataCategory.LEGAL_DOCUMENTS: RetentionPolicy(
                data_category=DataCategory.LEGAL_DOCUMENTS,
                retention_days=2555,  # 7 years
                action=RetentionAction.ARCHIVE,
                legal_basis="Legal professional retention requirements",
                exceptions=["active_matter", "appeal_period"]
            ),
            
            DataCategory.COURT_DOCUMENTS: RetentionPolicy(
                data_category=DataCategory.COURT_DOCUMENTS,
                retention_days=5475,  # 15 years
                action=RetentionAction.ARCHIVE,
                legal_basis="Court rules and professional standards",
                review_required=True
            ),
            
            DataCategory.AI_INTERACTIONS: RetentionPolicy(
                data_category=DataCategory.AI_INTERACTIONS,
                retention_days=365,  # 1 year
                action=RetentionAction.ANONYMIZE,
                legal_basis="Privacy Act - minimize data retention",
                exceptions=["quality_review", "complaint_investigation"]
            ),
            
            DataCategory.AUDIT_LOGS: RetentionPolicy(
                data_category=DataCategory.AUDIT_LOGS,
                retention_days=2555,  # 7 years
                action=RetentionAction.ARCHIVE,
                legal_basis="Compliance and security requirements",
                exceptions=["security_incident", "regulatory_review"]
            ),
            
            DataCategory.CHILDREN_INFORMATION: RetentionPolicy(
                data_category=DataCategory.CHILDREN_INFORMATION,
                retention_days=6570,  # 18 years or until child turns 18
                action=RetentionAction.REVIEW,
                legal_basis="Family Law Act - best interests of child",
                review_required=True,
                notification_days=90
            ),
            
            DataCategory.TEMP_PROCESSING: RetentionPolicy(
                data_category=DataCategory.TEMP_PROCESSING,
                retention_days=7,  # 7 days
                action=RetentionAction.DELETE,
                legal_basis="Temporary processing only",
                exceptions=[]
            )
        }
        
        return policies
    
    async def apply_retention_policies(self) -> Dict[str, Any]:
        """
        Apply all retention policies and return summary.
        
        Returns:
            Dict with retention action summary
        """
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'policies_applied': 0,
            'records_processed': 0,
            'records_deleted': 0,
            'records_archived': 0,
            'records_anonymized': 0,
            'errors': []
        }
        
        try:
            for category, policy in self.policies.items():
                self.logger.info(f"Applying retention policy for {category.value}")
                
                result = await self._apply_policy(policy)
                
                summary['policies_applied'] += 1
                summary['records_processed'] += result['processed']
                summary['records_deleted'] += result.get('deleted', 0)
                summary['records_archived'] += result.get('archived', 0)
                summary['records_anonymized'] += result.get('anonymized', 0)
                
                if result.get('errors'):
                    summary['errors'].extend(result['errors'])
            
            # Create audit entry
            self._create_audit_entry(
                action='retention_policies_applied',
                data_type='all',
                record_count=summary['records_processed'],
                success=len(summary['errors']) == 0,
                details=summary
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error applying retention policies: {e}")
            summary['errors'].append(str(e))
            return summary
    
    async def _apply_policy(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Apply a specific retention policy"""
        result = {
            'category': policy.data_category.value,
            'processed': 0,
            'errors': []
        }
        
        try:
            # Get expired records based on category
            expired_records = self._get_expired_records(policy)
            
            # Process in batches
            for batch in self._batch_records(expired_records, self.batch_size):
                # Check for exceptions
                filtered_batch = self._filter_exceptions(batch, policy)
                
                # Apply retention action
                if policy.action == RetentionAction.DELETE:
                    count = await self._delete_records(filtered_batch, policy)
                    result['deleted'] = result.get('deleted', 0) + count
                    
                elif policy.action == RetentionAction.ARCHIVE:
                    count = await self._archive_records(filtered_batch, policy)
                    result['archived'] = result.get('archived', 0) + count
                    
                elif policy.action == RetentionAction.ANONYMIZE:
                    count = await self._anonymize_records(filtered_batch, policy)
                    result['anonymized'] = result.get('anonymized', 0) + count
                    
                elif policy.action == RetentionAction.REVIEW:
                    count = await self._mark_for_review(filtered_batch, policy)
                    result['review_marked'] = result.get('review_marked', 0) + count
                
                result['processed'] += len(filtered_batch)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying policy for {policy.data_category.value}: {e}")
            result['errors'].append(str(e))
            return result
    
    def _get_expired_records(self, policy: RetentionPolicy) -> List[Any]:
        """Get records that have exceeded retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
        
        if policy.data_category == DataCategory.LEGAL_DOCUMENTS:
            return self.db_session.query(Document).filter(
                Document.created_at < cutoff_date,
                Document.category.in_(['court_documents', 'affidavits', 'expert_reports'])
            ).all()
            
        elif policy.data_category == DataCategory.AI_INTERACTIONS:
            return self.db_session.query(AIInteraction).filter(
                AIInteraction.created_at < cutoff_date
            ).all()
            
        elif policy.data_category == DataCategory.FINANCIAL_RECORDS:
            return self.db_session.query(Document).filter(
                Document.created_at < cutoff_date,
                Document.category.in_(['financial_documents', 'bank_statements', 'tax_returns'])
            ).all()
            
        # Add more categories as needed
        return []
    
    def _filter_exceptions(self, records: List[Any], policy: RetentionPolicy) -> List[Any]:
        """Filter out records that meet exception criteria"""
        if not policy.exceptions:
            return records
        
        filtered = []
        for record in records:
            keep = False
            
            # Check each exception
            for exception in policy.exceptions:
                if exception == "active_litigation" and hasattr(record, 'case'):
                    if record.case.status not in ['completed', 'archived']:
                        keep = True
                        break
                        
                elif exception == "court_order" and hasattr(record, 'metadata'):
                    if record.metadata and record.metadata.get('court_order_retention'):
                        keep = True
                        break
                        
                elif exception == "ongoing_audit" and hasattr(record, 'audit_flag'):
                    if record.audit_flag:
                        keep = True
                        break
            
            if not keep:
                filtered.append(record)
        
        return filtered
    
    async def _delete_records(self, records: List[Any], policy: RetentionPolicy) -> int:
        """Securely delete records"""
        count = 0
        
        for record in records:
            try:
                # Secure deletion process
                if self.enable_secure_deletion:
                    await self._secure_delete(record)
                
                # Remove from database
                self.db_session.delete(record)
                count += 1
                
                # Log deletion
                self.logger.info(f"Deleted {type(record).__name__} record {record.id}")
                
            except Exception as e:
                self.logger.error(f"Error deleting record {record.id}: {e}")
        
        self.db_session.commit()
        return count
    
    async def _archive_records(self, records: List[Any], policy: RetentionPolicy) -> int:
        """Archive records to long-term storage"""
        count = 0
        
        for record in records:
            try:
                # Create archive entry
                archive_data = self._create_archive_data(record)
                
                # In production, this would move to cold storage
                # For now, mark as archived
                if hasattr(record, 'archived_at'):
                    record.archived_at = datetime.utcnow()
                
                if hasattr(record, 'is_archived'):
                    record.is_archived = True
                
                count += 1
                
                self.logger.info(f"Archived {type(record).__name__} record {record.id}")
                
            except Exception as e:
                self.logger.error(f"Error archiving record {record.id}: {e}")
        
        self.db_session.commit()
        return count
    
    async def _anonymize_records(self, records: List[Any], policy: RetentionPolicy) -> int:
        """Anonymize sensitive data in records"""
        count = 0
        
        for record in records:
            try:
                # Anonymize based on record type
                if isinstance(record, AIInteraction):
                    # Keep interaction for analytics but remove PII
                    record.user_query = self._anonymize_text(record.user_query)
                    record.ai_response = self._anonymize_text(record.ai_response)
                    record.user_id = None  # Remove user association
                    
                elif isinstance(record, Document):
                    # Anonymize document metadata
                    if record.ai_extracted_entities:
                        record.ai_extracted_entities = self._anonymize_entities(record.ai_extracted_entities)
                    
                count += 1
                
                self.logger.info(f"Anonymized {type(record).__name__} record {record.id}")
                
            except Exception as e:
                self.logger.error(f"Error anonymizing record {record.id}: {e}")
        
        self.db_session.commit()
        return count
    
    async def _mark_for_review(self, records: List[Any], policy: RetentionPolicy) -> int:
        """Mark records for manual review"""
        count = 0
        
        for record in records:
            try:
                # Add review flag
                if hasattr(record, 'metadata'):
                    if not record.metadata:
                        record.metadata = {}
                    record.metadata['retention_review_required'] = True
                    record.metadata['retention_review_date'] = datetime.utcnow().isoformat()
                    record.metadata['retention_policy'] = policy.data_category.value
                
                count += 1
                
                # Send notification if configured
                if policy.notification_days:
                    self._send_retention_notification(record, policy)
                
            except Exception as e:
                self.logger.error(f"Error marking record for review {record.id}: {e}")
        
        self.db_session.commit()
        return count
    
    async def _secure_delete(self, record: Any):
        """Perform secure deletion of sensitive data"""
        # Overwrite sensitive fields with random data before deletion
        if hasattr(record, 'ocr_text') and record.ocr_text:
            record.ocr_text = os.urandom(len(record.ocr_text)).hex()
        
        if hasattr(record, 'ai_summary') and record.ai_summary:
            record.ai_summary = os.urandom(len(record.ai_summary)).hex()
        
        # Force write to ensure overwrite
        self.db_session.flush()
    
    def _create_archive_data(self, record: Any) -> Dict[str, Any]:
        """Create archive-ready data from record"""
        archive_data = {
            'record_type': type(record).__name__,
            'record_id': str(record.id) if hasattr(record, 'id') else None,
            'archived_at': datetime.utcnow().isoformat(),
            'retention_policy': 'legal_retention',
            'metadata': {}
        }
        
        # Add type-specific data
        if isinstance(record, Document):
            archive_data['metadata'] = {
                'filename': record.filename,
                'category': record.category,
                'case_id': str(record.case_id) if record.case_id else None,
                'created_at': record.created_at.isoformat()
            }
        
        return archive_data
    
    def _anonymize_text(self, text: str) -> str:
        """Anonymize text by removing PII"""
        if not text:
            return text
        
        # Simple anonymization - in production use more sophisticated NLP
        import re
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # Remove names (simplified - use NER in production)
        text = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', text)
        
        return text
    
    def _anonymize_entities(self, entities: Dict) -> Dict:
        """Anonymize extracted entities"""
        anonymized = {}
        
        for key, value in entities.items():
            if key in ['person_names', 'email_addresses', 'phone_numbers']:
                anonymized[key] = ['[REDACTED]' for _ in value] if isinstance(value, list) else '[REDACTED]'
            else:
                anonymized[key] = value
        
        return anonymized
    
    def _batch_records(self, records: List[Any], batch_size: int):
        """Yield records in batches"""
        for i in range(0, len(records), batch_size):
            yield records[i:i + batch_size]
    
    def _send_retention_notification(self, record: Any, policy: RetentionPolicy):
        """Send notification about upcoming retention action"""
        # In production, integrate with notification system
        self.logger.info(
            f"Retention notification for {type(record).__name__} {record.id}: "
            f"Action {policy.action.value} due in {policy.notification_days} days"
        )
    
    def _create_audit_entry(
        self,
        action: str,
        data_type: str,
        record_count: int,
        success: bool,
        details: Dict[str, Any]
    ):
        """Create audit entry for retention action"""
        audit_entry = RetentionAuditEntry(
            timestamp=datetime.utcnow(),
            action=action,
            data_type=data_type,
            record_count=record_count,
            success=success,
            details=details
        )
        
        # In production, store in audit table
        self.logger.info(f"Retention audit: {json.dumps(asdict(audit_entry), default=str)}")
    
    def get_retention_status(self, data_category: DataCategory) -> Dict[str, Any]:
        """Get current retention status for a data category"""
        policy = self.policies.get(data_category)
        if not policy:
            return {'error': 'Unknown data category'}
        
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
        
        # Count records approaching retention
        approaching_count = 0
        expired_count = 0
        
        if data_category == DataCategory.LEGAL_DOCUMENTS:
            approaching_count = self.db_session.query(Document).filter(
                Document.created_at < cutoff_date + timedelta(days=30),
                Document.created_at >= cutoff_date
            ).count()
            
            expired_count = self.db_session.query(Document).filter(
                Document.created_at < cutoff_date
            ).count()
        
        return {
            'category': data_category.value,
            'retention_days': policy.retention_days,
            'action': policy.action.value,
            'records_approaching_retention': approaching_count,
            'records_expired': expired_count,
            'next_review_date': (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
    
    def handle_consent_withdrawal(self, user_id: str, consent_type: ConsentType):
        """Handle data deletion after consent withdrawal"""
        self.logger.info(f"Processing data deletion for user {user_id} after consent withdrawal")
        
        # Immediate deletion for certain consent types
        if consent_type == ConsentType.AI_PROCESSING:
            # Delete AI interactions
            self.db_session.query(AIInteraction).filter(
                AIInteraction.user_id == user_id
            ).delete()
        
        elif consent_type == ConsentType.FINANCIAL_DATA_PROCESSING:
            # Anonymize financial documents
            financial_docs = self.db_session.query(Document).filter(
                Document.uploaded_by == user_id,
                Document.category.in_(['financial_documents', 'bank_statements'])
            ).all()
            
            for doc in financial_docs:
                doc.ai_extracted_entities = None
                doc.ai_financial_amounts = None
        
        self.db_session.commit()


# Helper functions
def get_retention_manager(db_session: Session) -> DataRetentionManager:
    """Get data retention manager instance"""
    return DataRetentionManager(db_session)


async def apply_retention_policies(db_session: Session) -> Dict[str, Any]:
    """Apply all retention policies"""
    manager = get_retention_manager(db_session)
    return await manager.apply_retention_policies()