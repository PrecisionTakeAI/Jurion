"""
Adaptive Legal Document Processing Engine
Handles document parsing, text extraction, OCR functionality, and database storage.
Automatically uses PostgreSQL database when available, falls back to legacy processing.
Maintains full backward compatibility with existing interfaces.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union

# Import the new database-based document processor
try:
    from core.document_processor_db import (
        DatabaseDocumentProcessor, ProcessingResult as DBProcessingResult,
        DocumentMetadata as DBDocumentMetadata, AustralianDocumentCategory,
        AustralianDocumentSubcategory, DocumentType, ProcessingStatus
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    logging.warning(f"Database document processor not available: {e}")

# Import legacy document processor as fallback
from core.document_processor_legacy import (
    LegacyDocumentProcessor, ProcessingResult as LegacyProcessingResult,
    DocumentMetadata as LegacyDocumentMetadata, DocumentType as LegacyDocumentType
)

# Export the appropriate classes based on availability
if DATABASE_AVAILABLE:
    # Use database classes when available
    ProcessingResult = DBProcessingResult
    DocumentMetadata = DBDocumentMetadata
else:
    # Use legacy classes as fallback
    ProcessingResult = LegacyProcessingResult
    DocumentMetadata = LegacyDocumentMetadata
    DocumentType = LegacyDocumentType

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Adaptive document processor for legal professionals.
    Automatically uses PostgreSQL database when available, falls back to legacy processing.
    Maintains full backward compatibility with existing interfaces.
    """
    
    def __init__(self, firm_id: str = None, user_id: str = None, storage_path: str = "data/documents"):
        """
        Initialize document processor with automatic backend selection
        
        Args:
            firm_id: Law firm ID for multi-tenant database mode
            user_id: Current user ID for audit trails in database mode
            storage_path: Directory for document storage
        """
        self.firm_id = firm_id
        self.user_id = user_id
        self.storage_path = storage_path
        
        # Determine which backend to use
        if DATABASE_AVAILABLE and self._should_use_database():
            logger.info("Using PostgreSQL database backend for document processing")
            self.backend = DatabaseDocumentProcessor(
                firm_id=firm_id, 
                user_id=user_id, 
                storage_path=storage_path
            )
            self.is_database_mode = True
        else:
            logger.info("Using legacy file-based backend for document processing")
            self.backend = LegacyDocumentProcessor()
            self.is_database_mode = False
    
    def _should_use_database(self) -> bool:
        """Determine if database should be used based on environment and context"""
        # Use database if explicitly requested via environment variable
        if os.getenv('USE_DATABASE', '').lower() in ['true', '1', 'yes']:
            return True
        
        # Use database if firm_id is provided (multi-tenant context)
        if self.firm_id:
            return True
        
        # Use database if DATABASE_URL is configured
        if os.getenv('DATABASE_URL') or (
            os.getenv('DB_HOST') and os.getenv('DB_NAME') and os.getenv('DB_USER')
        ):
            return True
        
        # Default to legacy mode for backward compatibility
        return False
    
    # ==========================================
    # PROXY METHODS - Forward all calls to backend
    # ==========================================
    
    def process_document(self, file_content: bytes, filename: str, **kwargs) -> ProcessingResult:
        """
        Process a document and extract text content
        Enhanced version supports additional parameters for database mode
        """
        # For database mode, pass through additional parameters
        if self.is_database_mode:
            return self.backend.process_document(file_content, filename, **kwargs)
        else:
            # Legacy mode only accepts file_content and filename
            return self.backend.process_document(file_content, filename)
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return self.backend.get_supported_formats()
    
    def get_processing_capabilities(self) -> Dict[str, Any]:
        """Get detailed processing capabilities"""
        return self.backend.get_processing_capabilities()
    
    # ==========================================
    # DATABASE-SPECIFIC METHODS (Available only in database mode)
    # ==========================================
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata from database (database mode only)"""
        if self.is_database_mode:
            return self.backend.get_document_by_id(document_id)
        else:
            logger.warning("get_document_by_id() not available in legacy mode")
            return None
    
    def list_documents_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        """List all documents for a specific case (database mode only)"""
        if self.is_database_mode:
            return self.backend.list_documents_for_case(case_id)
        else:
            logger.warning("list_documents_for_case() not available in legacy mode")
            return []
    
    def process_document_for_case(self, 
                                 file_content: bytes, 
                                 filename: str,
                                 case_id: str,
                                 category: Union[str, 'AustralianDocumentCategory'] = None,
                                 subcategory: Union[str, 'AustralianDocumentSubcategory'] = None,
                                 is_privileged: bool = False,
                                 confidentiality_level: int = 1,
                                 title: str = None) -> ProcessingResult:
        """
        Process and store a document for a specific case (database mode preferred)
        Falls back to basic processing in legacy mode
        """
        if self.is_database_mode:
            return self.backend.process_document(
                file_content=file_content,
                filename=filename,
                case_id=case_id,
                category=category,
                subcategory=subcategory,
                is_privileged=is_privileged,
                confidentiality_level=confidentiality_level,
                title=title
            )
        else:
            logger.warning("Enhanced document processing with case linking not available in legacy mode")
            return self.backend.process_document(file_content, filename)
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the current backend being used"""
        return {
            'backend_type': 'database' if self.is_database_mode else 'legacy',
            'database_available': DATABASE_AVAILABLE,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'storage_path': self.storage_path,
            'supported_formats': self.get_supported_formats(),
            'enhanced_features_available': self.is_database_mode
        }
    
    def get_australian_categories(self) -> List[str]:
        """Get available Australian family law document categories"""
        if DATABASE_AVAILABLE:
            return [cat.value for cat in AustralianDocumentCategory]
        else:
            return []
    
    def get_australian_subcategories(self) -> List[str]:
        """Get available Australian family law document subcategories"""
        if DATABASE_AVAILABLE:
            return [subcat.value for subcat in AustralianDocumentSubcategory]
        else:
            return []
    
    def migrate_to_database(self, firm_id: str, user_id: str, storage_path: str = None) -> bool:
        """
        Migrate from legacy mode to database mode
        
        Args:
            firm_id: Target firm ID for migration
            user_id: User performing the migration
            storage_path: Optional new storage path
            
        Returns:
            bool: True if migration successful or already using database
        """
        if self.is_database_mode:
            logger.info("Already using database backend")
            return True
        
        if not DATABASE_AVAILABLE:
            logger.error("Database backend not available for migration")
            return False
        
        try:
            # Switch to database backend
            self.backend = DatabaseDocumentProcessor(
                firm_id=firm_id, 
                user_id=user_id, 
                storage_path=storage_path or self.storage_path
            )
            self.is_database_mode = True
            self.firm_id = firm_id
            self.user_id = user_id
            
            logger.info("Successfully migrated to database backend")
            return True
            
        except Exception as e:
            logger.error(f"Migration to database failed: {e}")
            return False

# Export main classes with backward compatibility
if DATABASE_AVAILABLE:
    __all__ = [
        'DocumentProcessor', 'ProcessingResult', 'DocumentMetadata', 
        'AustralianDocumentCategory', 'AustralianDocumentSubcategory',
        'DocumentType', 'ProcessingStatus'
    ]
else:
    __all__ = ['DocumentProcessor', 'ProcessingResult', 'DocumentMetadata']

