"""
API routes for LegalAI Hub
"""

from .case_routes import router as case_router
from .document_routes import router as document_router

__all__ = [
    'case_router',
    'document_router'
]