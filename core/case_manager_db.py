"""
Database-integrated Legal Case Management System
Core case lifecycle management with PostgreSQL storage, multi-tenant architecture, and audit trails.
Maintains backward compatibility with existing JSON-based interface.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, func, desc

# Import database components
from database.database import db_manager, get_session
from shared.database.models import (
    Case, User, LawFirm, AIInteraction, AUFamilyLawRequirements,
    au_family_case_type, case_status_enum, user_role_enum
)

logger = logging.getLogger(__name__)

class CaseStatus(Enum):
    """Case status enumeration - mapped to database enum"""
    ACTIVE = "case_preparation"  # Maps to case_status_enum
    PENDING = "initial_consultation"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"
    NEGOTIATION = "negotiation"
    MEDIATION = "mediation"
    COURT_PROCEEDINGS = "court_proceedings"
    SETTLEMENT = "settlement"

class CasePriority(Enum):
    """Case priority enumeration"""
    LOW = 1
    MEDIUM = 3
    HIGH = 4
    URGENT = 5

class NoteType(Enum):
    """Case note type enumeration"""
    RESEARCH = "research"
    CLIENT_COMMUNICATION = "client_communication"
    STRATEGY = "strategy"
    COURT_FILING = "court_filing"
    GENERAL = "general"

@dataclass
class CaseNote:
    """Individual case note data structure - compatible with existing interface"""
    note_id: str
    note_type: NoteType
    title: str
    content: str
    created_date: datetime
    created_by: str = "system"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class LegalCase:
    """Main legal case data structure - compatible with existing interface"""
    case_id: str
    title: str
    client_name: str
    practice_area: str
    jurisdiction: str
    status: CaseStatus
    priority: CasePriority
    created_date: datetime
    last_updated: datetime
    case_notes: List[CaseNote]
    conversation_history: List[Dict]
    metadata: Dict[str, Any]
    description: str = ""
    case_number: str = ""
    opposing_party: str = ""
    court: str = ""
    next_deadline: Optional[datetime] = None
    estimated_hours: float = 0.0
    billable_rate: float = 0.0
    
    def __post_init__(self):
        if self.case_notes is None:
            self.case_notes = []
        if self.conversation_history is None:
            self.conversation_history = []
        if self.metadata is None:
            self.metadata = {}


class DatabaseCaseManager:
    """
    Database-integrated case management system for legal professionals.
    Handles case lifecycle, metadata, notes, and conversation history with PostgreSQL storage.
    Maintains full backward compatibility with existing JSON-based interface.
    """
    
    def __init__(self, firm_id: str = None, user_id: str = None, data_dir: str = "data/cases"):
        """
        Initialize database case manager with multi-tenant context
        
        Args:
            firm_id: Law firm ID for multi-tenant isolation
            user_id: Current user ID for audit trails
            data_dir: Legacy parameter for backward compatibility (ignored)
        """
        self.firm_id = firm_id
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        
        # Initialize database if not already done
        if not db_manager.engine:
            try:
                db_manager.initialize_database()
                self.logger.info("Database initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {e}")
                raise
        
        # Validate firm and user context
        if self.firm_id and self.user_id:
            self._validate_context()

    def _validate_context(self) -> bool:
        """Validate firm and user context"""
        try:
            with get_session() as session:
                # Validate firm exists
                firm = session.query(LawFirm).filter(
                    LawFirm.id == self.firm_id,
                    LawFirm.is_active == True
                ).first()
                if not firm:
                    raise ValueError(f"Invalid or inactive firm_id: {self.firm_id}")
                
                # Validate user exists and belongs to firm
                user = session.query(User).filter(
                    User.id == self.user_id,
                    User.firm_id == self.firm_id,
                    User.is_active == True
                ).first()
                if not user:
                    raise ValueError(f"Invalid user_id or user doesn't belong to firm: {self.user_id}")
                
                return True
        except Exception as e:
            self.logger.error(f"Context validation failed: {e}")
            raise

    def _map_case_type_to_db(self, practice_area: str) -> str:
        """Map practice area to database case type"""
        practice_area_mapping = {
            'family_law': 'divorce',
            'divorce': 'divorce',
            'property_settlement': 'property_settlement',
            'child_custody': 'child_custody',
            'parenting_orders': 'parenting_orders',
            'spousal_maintenance': 'spousal_maintenance',
            'child_support': 'child_support',
            'domestic_violence': 'domestic_violence',
            'adoption': 'adoption',
            'surrogacy': 'surrogacy',
            'defacto_separation': 'defacto_separation',
            'consent_orders': 'consent_orders'
        }
        return practice_area_mapping.get(practice_area.lower(), 'divorce')

    def _map_status_to_db(self, status: CaseStatus) -> str:
        """Map CaseStatus enum to database case_status_enum"""
        status_mapping = {
            CaseStatus.ACTIVE: 'case_preparation',
            CaseStatus.PENDING: 'initial_consultation',
            CaseStatus.ON_HOLD: 'on_hold',
            CaseStatus.COMPLETED: 'completed',
            CaseStatus.ARCHIVED: 'archived',
            CaseStatus.NEGOTIATION: 'negotiation',
            CaseStatus.MEDIATION: 'mediation',
            CaseStatus.COURT_PROCEEDINGS: 'court_proceedings',
            CaseStatus.SETTLEMENT: 'settlement'
        }
        return status_mapping.get(status, 'case_preparation')

    def _map_status_from_db(self, db_status: str) -> CaseStatus:
        """Map database status to CaseStatus enum"""
        status_mapping = {
            'case_preparation': CaseStatus.ACTIVE,
            'initial_consultation': CaseStatus.PENDING,
            'on_hold': CaseStatus.ON_HOLD,
            'completed': CaseStatus.COMPLETED,
            'archived': CaseStatus.ARCHIVED,
            'negotiation': CaseStatus.NEGOTIATION,
            'mediation': CaseStatus.MEDIATION,
            'court_proceedings': CaseStatus.COURT_PROCEEDINGS,
            'settlement': CaseStatus.SETTLEMENT
        }
        return status_mapping.get(db_status, CaseStatus.ACTIVE)

    def _convert_db_case_to_legacy(self, db_case: Case) -> LegalCase:
        """Convert database Case model to legacy LegalCase dataclass"""
        # Extract case notes from AI interactions (simplified approach)
        case_notes = []
        
        # Extract conversation history from AI interactions
        conversation_history = []
        with get_session() as session:
            ai_interactions = session.query(AIInteraction).filter(
                AIInteraction.case_id == db_case.id
            ).order_by(AIInteraction.created_at).all()
            
            for interaction in ai_interactions:
                conversation_history.append({
                    'timestamp': interaction.created_at.isoformat(),
                    'conversation_id': str(interaction.id),
                    'user_query': interaction.user_query,
                    'ai_response': interaction.ai_response,
                    'interaction_type': interaction.interaction_type,
                    'model_used': interaction.ai_model_used,
                    'user_rating': interaction.user_rating,
                    'user_feedback': interaction.user_feedback
                })

        return LegalCase(
            case_id=str(db_case.id),
            title=db_case.title,
            client_name=db_case.applicant_details.get('name', '') if db_case.applicant_details else '',
            practice_area=db_case.case_type,
            jurisdiction=db_case.jurisdiction,
            status=self._map_status_from_db(db_case.status),
            priority=CasePriority(db_case.priority),
            created_date=db_case.created_at,
            last_updated=db_case.updated_at,
            case_notes=case_notes,
            conversation_history=conversation_history,
            metadata=db_case.ai_recommendations or {},
            description=db_case.description or "",
            case_number=db_case.case_number,
            opposing_party=db_case.respondent_details.get('name', '') if db_case.respondent_details else '',
            court=db_case.court_location or "",
            next_deadline=None,  # Could be extracted from workflow tasks
            estimated_hours=0.0,  # Could be calculated from workflow tasks
            billable_rate=0.0
        )

    def create_case(self, 
                   title: str, 
                   client_name: str, 
                   practice_area: str, 
                   jurisdiction: str = "australia",
                   description: str = "",
                   priority: CasePriority = CasePriority.MEDIUM,
                   case_number: str = "",
                   opposing_party: str = "",
                   court: str = "") -> str:
        """Create a new legal case in the database"""
        try:
            with get_session() as session:
                # Generate internal case number if not provided
                if not case_number:
                    case_count = session.query(func.count(Case.id)).filter(
                        Case.firm_id == self.firm_id
                    ).scalar()
                    case_number = f"CASE-{case_count + 1:04d}"
                
                # Map case type
                db_case_type = self._map_case_type_to_db(practice_area)
                
                # Create new case
                new_case = Case(
                    firm_id=self.firm_id,
                    case_number=case_number,
                    case_type=db_case_type,
                    jurisdiction=jurisdiction,
                    court_location=court,
                    applicant_details={'name': client_name, 'contact': {}},
                    respondent_details={'name': opposing_party} if opposing_party else {},
                    title=title,
                    description=description,
                    status=self._map_status_to_db(CaseStatus.ACTIVE),
                    priority=priority.value,
                    assigned_lawyer_id=self.user_id,
                    created_by=self.user_id
                )
                
                session.add(new_case)
                session.flush()  # Get the ID
                
                # Create Australian Family Law requirements if applicable
                if db_case_type in ['divorce', 'property_settlement', 'child_custody', 'parenting_orders']:
                    family_law_req = AUFamilyLawRequirements(
                        case_id=new_case.id,
                        mediation_required=True if db_case_type in ['parenting_orders', 'child_custody'] else False,
                        asset_disclosure_complete=False if db_case_type == 'property_settlement' else None
                    )
                    session.add(family_law_req)
                
                session.commit()
                
                case_id = str(new_case.id)
                self.logger.info(f"Created case {case_id} for firm {self.firm_id}")
                
                # Add initial case interaction as "note"
                self._add_system_interaction(
                    case_id=case_id,
                    interaction_type="case_creation",
                    content=f"Case '{title}' created for client '{client_name}'"
                )
                
                return case_id
                
        except Exception as e:
            self.logger.error(f"Failed to create case: {e}")
            raise

    def _add_system_interaction(self, case_id: str, interaction_type: str, content: str):
        """Add a system-generated AI interaction for tracking purposes"""
        try:
            with get_session() as session:
                interaction = AIInteraction(
                    case_id=uuid.UUID(case_id),
                    user_id=self.user_id,
                    firm_id=self.firm_id,
                    session_id=f"system-{uuid.uuid4()}",
                    interaction_type=interaction_type,
                    user_query="System generated",
                    ai_response=content,
                    ai_model_used="system",
                    jurisdiction="australia",
                    practice_area="family_law"
                )
                session.add(interaction)
                session.commit()
        except Exception as e:
            self.logger.warning(f"Failed to add system interaction: {e}")

    def get_case(self, case_id: str) -> Optional[LegalCase]:
        """Get case object by ID"""
        try:
            with get_session() as session:
                db_case = session.query(Case).filter(
                    Case.id == uuid.UUID(case_id),
                    Case.firm_id == self.firm_id
                ).first()
                
                if not db_case:
                    return None
                
                return self._convert_db_case_to_legacy(db_case)
                
        except Exception as e:
            self.logger.error(f"Failed to get case {case_id}: {e}")
            return None

    def get_case_by_id(self, case_id: str) -> Optional[LegalCase]:
        """Get case object by ID (alias for backward compatibility)"""
        return self.get_case(case_id)

    def edit_case(self, case_id: str, **kwargs) -> bool:
        """Edit an existing case"""
        try:
            with get_session() as session:
                db_case = session.query(Case).filter(
                    Case.id == uuid.UUID(case_id),
                    Case.firm_id == self.firm_id
                ).first()
                
                if not db_case:
                    return False
                
                # Map legacy fields to database fields
                field_mapping = {
                    'title': 'title',
                    'description': 'description',
                    'case_number': 'case_number',
                    'court': 'court_location',
                    'jurisdiction': 'jurisdiction',
                    'client_name': lambda value: self._update_applicant_name(db_case, value),
                    'opposing_party': lambda value: self._update_respondent_name(db_case, value),
                    'priority': lambda value: setattr(db_case, 'priority', value.value if isinstance(value, CasePriority) else value),
                    'status': lambda value: setattr(db_case, 'status', self._map_status_to_db(value) if isinstance(value, CaseStatus) else value),
                    'practice_area': lambda value: setattr(db_case, 'case_type', self._map_case_type_to_db(value))
                }
                
                for field, value in kwargs.items():
                    if field in field_mapping:
                        mapping = field_mapping[field]
                        if callable(mapping):
                            mapping(value)
                        else:
                            setattr(db_case, mapping, value)
                
                db_case.updated_at = datetime.now()
                session.commit()
                
                self.logger.info(f"Updated case {case_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to edit case {case_id}: {e}")
            return False

    def _update_applicant_name(self, db_case: Case, name: str):
        """Update applicant name in JSON field"""
        if not db_case.applicant_details:
            db_case.applicant_details = {}
        db_case.applicant_details['name'] = name

    def _update_respondent_name(self, db_case: Case, name: str):
        """Update respondent name in JSON field"""
        if not db_case.respondent_details:
            db_case.respondent_details = {}
        db_case.respondent_details['name'] = name

    def update_case_status(self, case_id: str, status: CaseStatus) -> bool:
        """Update case status"""
        return self.edit_case(case_id, status=status)

    def archive_case(self, case_id: str) -> bool:
        """Archive a case (set status to archived)"""
        return self.edit_case(case_id, status=CaseStatus.ARCHIVED)

    def delete_case(self, case_id: str) -> bool:
        """Soft delete a case (archive it)"""
        return self.archive_case(case_id)

    def get_case_list(self, status_filter: Optional[CaseStatus] = None) -> List[Dict]:
        """Get list of cases with optional status filtering"""
        try:
            with get_session() as session:
                query = session.query(Case).filter(Case.firm_id == self.firm_id)
                
                if status_filter:
                    db_status = self._map_status_to_db(status_filter)
                    query = query.filter(Case.status == db_status)
                
                db_cases = query.order_by(desc(Case.updated_at)).all()
                
                cases_list = []
                for db_case in db_cases:
                    # Count AI interactions as conversations
                    conversations_count = session.query(func.count(AIInteraction.id)).filter(
                        AIInteraction.case_id == db_case.id
                    ).scalar()
                    
                    cases_list.append({
                        'case_id': str(db_case.id),
                        'title': db_case.title,
                        'client_name': db_case.applicant_details.get('name', '') if db_case.applicant_details else '',
                        'practice_area': db_case.case_type,
                        'jurisdiction': db_case.jurisdiction,
                        'status': self._map_status_from_db(db_case.status).value,
                        'priority': CasePriority(db_case.priority).value,
                        'created_date': db_case.created_at.isoformat(),
                        'last_updated': db_case.updated_at.isoformat(),
                        'notes_count': 0,  # Could implement actual case notes
                        'conversations_count': conversations_count
                    })
                
                return cases_list
                
        except Exception as e:
            self.logger.error(f"Failed to get case list: {e}")
            return []

    def get_case_details(self, case_id: str) -> Optional[Dict]:
        """Get detailed information about a specific case"""
        case = self.get_case(case_id)
        if not case:
            return None
        
        return {
            'case_id': case.case_id,
            'title': case.title,
            'client_name': case.client_name,
            'practice_area': case.practice_area,
            'jurisdiction': case.jurisdiction,
            'status': case.status.value,
            'priority': case.priority.value,
            'created_date': case.created_date.isoformat(),
            'last_updated': case.last_updated.isoformat(),
            'description': case.description,
            'case_number': case.case_number,
            'opposing_party': case.opposing_party,
            'court': case.court,
            'next_deadline': case.next_deadline.isoformat() if case.next_deadline else None,
            'estimated_hours': case.estimated_hours,
            'billable_rate': case.billable_rate,
            'case_notes': [asdict(note) for note in case.case_notes],
            'conversations_count': len(case.conversation_history),
            'metadata': case.metadata
        }

    def add_conversation_to_case(self, case_id: str, conversation_data: Dict) -> bool:
        """Add conversation data to a case"""
        try:
            with get_session() as session:
                # Verify case exists and belongs to firm
                case_exists = session.query(Case).filter(
                    Case.id == uuid.UUID(case_id),
                    Case.firm_id == self.firm_id
                ).first()
                
                if not case_exists:
                    return False
                
                # Create AI interaction record
                interaction = AIInteraction(
                    case_id=uuid.UUID(case_id),
                    user_id=self.user_id,
                    firm_id=self.firm_id,
                    session_id=conversation_data.get('session_id', str(uuid.uuid4())),
                    interaction_type=conversation_data.get('interaction_type', 'query'),
                    user_query=conversation_data.get('user_input', ''),
                    ai_response=conversation_data.get('ai_response', ''),
                    ai_model_used=conversation_data.get('model_used', 'unknown'),
                    ai_confidence_score=conversation_data.get('confidence_score'),
                    jurisdiction=conversation_data.get('jurisdiction', 'australia'),
                    practice_area='family_law',
                    user_rating=conversation_data.get('user_rating'),
                    user_feedback=conversation_data.get('user_feedback')
                )
                
                session.add(interaction)
                
                # Update case last_updated
                case_exists.updated_at = datetime.now()
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add conversation to case {case_id}: {e}")
            return False

    def add_conversation(self, case_id: str, conversation_data: Dict) -> bool:
        """Add conversation data to a case (alias for UI compatibility)"""
        return self.add_conversation_to_case(case_id, conversation_data)

    def get_case_conversations(self, case_id: str) -> List[Dict]:
        """Get all conversations for a specific case"""
        case = self.get_case(case_id)
        return case.conversation_history if case else []

    def add_case_note(self, 
                     case_id: str, 
                     note_type: NoteType, 
                     title: str, 
                     content: str,
                     tags: List[str] = None) -> bool:
        """Add a note to a case (stored as AI interaction)"""
        conversation_data = {
            'session_id': f"note-{uuid.uuid4()}",
            'interaction_type': 'case_note',
            'user_input': f"Note: {title}",
            'ai_response': content,
            'model_used': 'system',
            'note_type': note_type.value,
            'tags': tags or []
        }
        return self.add_conversation_to_case(case_id, conversation_data)

    def add_note(self, case_id: str, note_content: str, note_type: str = "general") -> bool:
        """Add a note to a case (simplified interface for UI compatibility)"""
        try:
            note_type_enum = NoteType(note_type.lower())
        except ValueError:
            note_type_enum = NoteType.GENERAL
        
        return self.add_case_note(
            case_id=case_id,
            note_type=note_type_enum,
            title="Case Note",
            content=note_content
        )

    def get_active_cases(self) -> List[Dict]:
        """Get all active cases"""
        return self.get_case_list(status_filter=CaseStatus.ACTIVE)

    def get_all_cases(self) -> List[LegalCase]:
        """Get all cases as a list of LegalCase objects"""
        try:
            with get_session() as session:
                db_cases = session.query(Case).filter(
                    Case.firm_id == self.firm_id
                ).order_by(desc(Case.updated_at)).all()
                
                return [self._convert_db_case_to_legacy(case) for case in db_cases]
                
        except Exception as e:
            self.logger.error(f"Failed to get all cases: {e}")
            return []

    def search_cases(self, query: str, search_fields: List[str] = None) -> List[Dict]:
        """Search cases by query string"""
        try:
            with get_session() as session:
                search_query = session.query(Case).filter(Case.firm_id == self.firm_id)
                
                if query:
                    # Search in multiple fields
                    search_conditions = [
                        Case.title.ilike(f'%{query}%'),
                        Case.description.ilike(f'%{query}%'),
                        Case.case_number.ilike(f'%{query}%'),
                        Case.applicant_details['name'].astext.ilike(f'%{query}%'),
                        Case.respondent_details['name'].astext.ilike(f'%{query}%')
                    ]
                    
                    search_query = search_query.filter(or_(*search_conditions))
                
                db_cases = search_query.order_by(desc(Case.updated_at)).all()
                
                matching_cases = []
                for db_case in db_cases:
                    matching_cases.append({
                        'case_id': str(db_case.id),
                        'title': db_case.title,
                        'client_name': db_case.applicant_details.get('name', '') if db_case.applicant_details else '',
                        'practice_area': db_case.case_type,
                        'status': self._map_status_from_db(db_case.status).value,
                        'priority': CasePriority(db_case.priority).value,
                        'last_updated': db_case.updated_at.isoformat()
                    })
                
                return matching_cases
                
        except Exception as e:
            self.logger.error(f"Failed to search cases: {e}")
            return []

    def get_case_statistics(self) -> Dict[str, Any]:
        """Get comprehensive case statistics"""
        try:
            with get_session() as session:
                # Total cases
                total_cases = session.query(func.count(Case.id)).filter(
                    Case.firm_id == self.firm_id
                ).scalar()
                
                if total_cases == 0:
                    return {
                        'total_cases': 0,
                        'status_breakdown': {},
                        'priority_breakdown': {},
                        'practice_area_breakdown': {},
                        'recent_activity': [],
                        'total_notes': 0,
                        'total_conversations': 0
                    }
                
                # Status breakdown
                status_counts = {}
                for status in case_status_enum.__members__.values():
                    count = session.query(func.count(Case.id)).filter(
                        Case.firm_id == self.firm_id,
                        Case.status == status
                    ).scalar()
                    status_counts[status] = count
                
                # Priority breakdown
                priority_counts = {}
                for priority in [1, 2, 3, 4, 5]:
                    count = session.query(func.count(Case.id)).filter(
                        Case.firm_id == self.firm_id,
                        Case.priority == priority
                    ).scalar()
                    priority_counts[CasePriority(priority).name.lower()] = count
                
                # Practice area breakdown
                practice_area_counts = session.query(
                    Case.case_type, func.count(Case.id)
                ).filter(
                    Case.firm_id == self.firm_id
                ).group_by(Case.case_type).all()
                
                practice_areas = {area: count for area, count in practice_area_counts}
                
                # Recent activity
                recent_cases = session.query(Case).filter(
                    Case.firm_id == self.firm_id
                ).order_by(desc(Case.updated_at)).limit(10).all()
                
                recent_activity = []
                for case in recent_cases:
                    recent_activity.append({
                        'case_id': str(case.id),
                        'title': case.title,
                        'client_name': case.applicant_details.get('name', '') if case.applicant_details else '',
                        'last_updated': case.updated_at.isoformat(),
                        'status': case.status
                    })
                
                # Total conversations (AI interactions)
                total_conversations = session.query(func.count(AIInteraction.id)).filter(
                    AIInteraction.firm_id == self.firm_id
                ).scalar()
                
                return {
                    'total_cases': total_cases,
                    'status_breakdown': status_counts,
                    'priority_breakdown': priority_counts,
                    'practice_area_breakdown': practice_areas,
                    'recent_activity': recent_activity,
                    'total_notes': 0,  # Could implement actual notes count
                    'total_conversations': total_conversations
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get case statistics: {e}")
            return {}

    def export_case_data(self, case_id: str, format: str = 'json') -> Optional[str]:
        """Export case data in specified format"""
        case_details = self.get_case_details(case_id)
        if not case_details:
            return None
        
        if format.lower() == 'json':
            import json
            return json.dumps(case_details, indent=2, ensure_ascii=False)
        
        return None

    # Legacy compatibility methods
    def load_cases(self) -> None:
        """Legacy method for backward compatibility (no-op in DB version)"""
        pass

    def save_cases(self) -> None:
        """Legacy method for backward compatibility (no-op in DB version)"""
        pass


# Backward compatibility alias
CaseManager = DatabaseCaseManager