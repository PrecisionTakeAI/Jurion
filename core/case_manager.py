"""
Legal Case Management System
Core case lifecycle management with CRUD operations, metadata tracking, and data persistence.
Now supports both PostgreSQL database and legacy JSON storage with automatic fallback.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union

# Import the new database-based case manager
try:
    from core.case_manager_db import (
        DatabaseCaseManager, CaseStatus, CasePriority, NoteType, 
        CaseNote, LegalCase
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    logging.warning(f"Database case manager not available: {e}")

# Import legacy case manager as fallback
from core.case_manager_legacy import (
    LegacyCaseManager, CaseStatus as LegacyCaseStatus, 
    CasePriority as LegacyCasePriority, NoteType as LegacyNoteType,
    CaseNote as LegacyCaseNote, LegalCase as LegacyLegalCase
)

# Export the appropriate enums and classes based on availability
if DATABASE_AVAILABLE:
    # Use database enums and classes
    pass  # Already imported above
else:
    # Use legacy enums and classes
    CaseStatus = LegacyCaseStatus
    CasePriority = LegacyCasePriority
    NoteType = LegacyNoteType
    CaseNote = LegacyCaseNote
    LegalCase = LegacyLegalCase

logger = logging.getLogger(__name__)

class CaseManager:
    """
    Adaptive case management system for legal professionals.
    Automatically uses PostgreSQL database when available, falls back to JSON storage.
    Maintains full backward compatibility with existing interfaces.
    """
    
    def __init__(self, data_dir: str = "data/cases", firm_id: str = None, user_id: str = None):
        """
        Initialize case manager with automatic backend selection
        
        Args:
            data_dir: Directory for JSON storage (legacy mode only)
            firm_id: Law firm ID for multi-tenant database mode
            user_id: Current user ID for audit trails in database mode
        """
        self.firm_id = firm_id
        self.user_id = user_id
        self.data_dir = data_dir
        
        # Determine which backend to use
        if DATABASE_AVAILABLE and self._should_use_database():
            logger.info("Using PostgreSQL database backend")
            self.backend = DatabaseCaseManager(firm_id=firm_id, user_id=user_id)
            self.is_database_mode = True
        else:
            logger.info("Using legacy JSON file backend")
            self.backend = LegacyCaseManager(data_dir=data_dir)
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
    
    def load_cases(self) -> None:
        """Load cases from persistent storage"""
        return self.backend.load_cases()
    
    def save_cases(self) -> None:
        """Save cases to persistent storage"""
        return self.backend.save_cases()
    
    def create_case(self, 
                   title: str, 
                   client_name: str, 
                   practice_area: str, 
                   jurisdiction: str,
                   description: str = "",
                   priority: CasePriority = CasePriority.MEDIUM,
                   case_number: str = "",
                   opposing_party: str = "",
                   court: str = "") -> str:
        """Create a new legal case"""
        return self.backend.create_case(
            title=title,
            client_name=client_name,
            practice_area=practice_area,
            jurisdiction=jurisdiction,
            description=description,
            priority=priority,
            case_number=case_number,
            opposing_party=opposing_party,
            court=court
        )
    
    def edit_case(self, case_id: str, **kwargs) -> bool:
        """Edit an existing case"""
        return self.backend.edit_case(case_id, **kwargs)
    
    def archive_case(self, case_id: str) -> bool:
        """Archive a case (set status to archived)"""
        return self.backend.archive_case(case_id)
    
    def delete_case(self, case_id: str) -> bool:
        """Delete a case permanently"""
        return self.backend.delete_case(case_id)
    
    def get_case_list(self, status_filter: Optional[CaseStatus] = None) -> List[Dict]:
        """Get list of cases with optional status filtering"""
        return self.backend.get_case_list(status_filter)
    
    def get_case_details(self, case_id: str) -> Optional[Dict]:
        """Get detailed information about a specific case"""
        return self.backend.get_case_details(case_id)
    
    def add_case_note(self, 
                     case_id: str, 
                     note_type: NoteType, 
                     title: str, 
                     content: str,
                     tags: List[str] = None) -> bool:
        """Add a note to a case"""
        return self.backend.add_case_note(case_id, note_type, title, content, tags)
    
    def update_case_status(self, case_id: str, status: CaseStatus) -> bool:
        """Update case status"""
        return self.backend.update_case_status(case_id, status)
    
    def add_conversation_to_case(self, case_id: str, conversation_data: Dict) -> bool:
        """Add conversation data to a case"""
        return self.backend.add_conversation_to_case(case_id, conversation_data)
    
    def get_case_statistics(self) -> Dict[str, Any]:
        """Get comprehensive case statistics"""
        return self.backend.get_case_statistics()
    
    def search_cases(self, query: str, search_fields: List[str] = None) -> List[Dict]:
        """Search cases by query string"""
        return self.backend.search_cases(query, search_fields)
    
    def export_case_data(self, case_id: str, format: str = 'json') -> Optional[str]:
        """Export case data in specified format"""
        return self.backend.export_case_data(case_id, format)
    
    def get_active_cases(self) -> List[Dict]:
        """Get all active cases"""
        return self.backend.get_active_cases()
    
    def get_case_by_id(self, case_id: str) -> Optional[LegalCase]:
        """Get case object by ID"""
        return self.backend.get_case_by_id(case_id)
    
    def get_case(self, case_id: str) -> Optional[LegalCase]:
        """Get case object by ID (alias for get_case_by_id for UI compatibility)"""
        return self.backend.get_case(case_id)
    
    def get_all_cases(self) -> List[LegalCase]:
        """Get all cases as a list of LegalCase objects"""
        return self.backend.get_all_cases()
    
    def get_case_conversations(self, case_id: str) -> List[Dict]:
        """Get all conversations for a specific case"""
        return self.backend.get_case_conversations(case_id)
    
    def add_conversation(self, case_id: str, conversation_data: Dict) -> bool:
        """Add conversation data to a case (alias for add_conversation_to_case for UI compatibility)"""
        return self.backend.add_conversation(case_id, conversation_data)
    
    def add_note(self, case_id: str, note_content: str, note_type: str = "general") -> bool:
        """Add a note to a case (simplified interface for UI compatibility)"""
        return self.backend.add_note(case_id, note_content, note_type)
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the current backend being used"""
        return {
            'backend_type': 'database' if self.is_database_mode else 'json',
            'database_available': DATABASE_AVAILABLE,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'data_dir': self.data_dir
        }
    
    def migrate_to_database(self, firm_id: str, user_id: str) -> bool:
        """
        Migrate from JSON storage to database (if not already using database)
        
        Args:
            firm_id: Target firm ID for migration
            user_id: User performing the migration
            
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
            # Get all cases from JSON backend
            legacy_cases = self.backend.get_all_cases()
            
            # Initialize database backend
            db_backend = DatabaseCaseManager(firm_id=firm_id, user_id=user_id)
            
            # Migrate each case
            migrated_count = 0
            for case in legacy_cases:
                try:
                    new_case_id = db_backend.create_case(
                        title=case.title,
                        client_name=case.client_name,
                        practice_area=case.practice_area,
                        jurisdiction=case.jurisdiction,
                        description=case.description,
                        priority=case.priority,
                        case_number=case.case_number,
                        opposing_party=case.opposing_party,
                        court=case.court
                    )
                    
                    # Migrate conversation history
                    for conversation in case.conversation_history:
                        db_backend.add_conversation_to_case(new_case_id, conversation)
                    
                    # Migrate case notes
                    for note in case.case_notes:
                        db_backend.add_case_note(
                            case_id=new_case_id,
                            note_type=note.note_type,
                            title=note.title,
                            content=note.content,
                            tags=note.tags
                        )
                    
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate case {case.case_id}: {e}")
            
            # Switch to database backend
            self.backend = db_backend
            self.is_database_mode = True
            self.firm_id = firm_id
            self.user_id = user_id
            
            logger.info(f"Successfully migrated {migrated_count} cases to database")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

