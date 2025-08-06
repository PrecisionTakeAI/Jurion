"""
Services for LegalAI Hub
Business logic and external integrations
"""

from .ai_service import AIService
from .case_service import CaseService
from .document_service import DocumentService
from .conflict_service import ConflictCheckService

__all__ = [
    'AIService',
    'CaseService', 
    'DocumentService',
    'ConflictCheckService'
]