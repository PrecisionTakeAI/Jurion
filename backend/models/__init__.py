"""
LegalAI Hub Backend Models
SQLAlchemy models for multi-tenant legal practice management
"""

from .base import Base
from .enums import *
from .law_firm import LawFirm
from .user import User
from .case import Case
from .document import Document
from .financial_information import FinancialInformation
from .children_information import ChildrenInformation
from .ai_interaction import AIInteraction
from .audit_log import AuditLog

__all__ = [
    'Base',
    'UserRole',
    'AustralianState',
    'SubscriptionTier',
    'ComplianceStatus',
    'CaseStatus',
    'CasePriority',
    'AustralianFamilyCaseType',
    'CourtSystem',
    'DocumentType',
    'ProcessingStatus',
    'AIInteractionType',
    'PartyType',
    'LawFirm',
    'User', 
    'Case',
    'Document',
    'FinancialInformation',
    'ChildrenInformation',
    'AIInteraction',
    'AuditLog'
]