"""
Legacy Case Manager - JSON-based implementation
Preserved for backward compatibility and fallback scenarios
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import os
from pathlib import Path

class CaseStatus(Enum):
    """Case status enumeration"""
    ACTIVE = "active"
    PENDING = "pending"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"

class CasePriority(Enum):
    """Case priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NoteType(Enum):
    """Case note type enumeration"""
    RESEARCH = "research"
    CLIENT_COMMUNICATION = "client_communication"
    STRATEGY = "strategy"
    COURT_FILING = "court_filing"
    GENERAL = "general"

@dataclass
class CaseNote:
    """Individual case note data structure"""
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
    """Main legal case data structure"""
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

class LegacyCaseManager:
    """
    Legacy JSON-based case management system
    Preserved for backward compatibility
    """
    
    def __init__(self, data_dir: str = "data/cases"):
        """Initialize case manager with data directory"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cases_file = self.data_dir / "cases.json"
        self.cases: Dict[str, LegalCase] = {}
        self.load_cases()
    
    def load_cases(self) -> None:
        """Load cases from persistent storage"""
        try:
            if self.cases_file.exists():
                with open(self.cases_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for case_id, case_data in data.items():
                    # Convert datetime strings back to datetime objects
                    case_data['created_date'] = datetime.fromisoformat(case_data['created_date'])
                    case_data['last_updated'] = datetime.fromisoformat(case_data['last_updated'])
                    
                    if case_data.get('next_deadline'):
                        case_data['next_deadline'] = datetime.fromisoformat(case_data['next_deadline'])
                    
                    # Convert enum strings back to enums
                    case_data['status'] = CaseStatus(case_data['status'])
                    case_data['priority'] = CasePriority(case_data['priority'])
                    
                    # Convert case notes
                    notes = []
                    for note_data in case_data.get('case_notes', []):
                        note_data['created_date'] = datetime.fromisoformat(note_data['created_date'])
                        note_data['note_type'] = NoteType(note_data['note_type'])
                        notes.append(CaseNote(**note_data))
                    case_data['case_notes'] = notes
                    
                    self.cases[case_id] = LegalCase(**case_data)
                    
        except Exception as e:
            print(f"Warning: Could not load cases from {self.cases_file}: {e}")
            self.cases = {}
    
    def save_cases(self) -> None:
        """Save cases to persistent storage"""
        try:
            # Convert cases to JSON-serializable format
            data = {}
            for case_id, case in self.cases.items():
                case_dict = asdict(case)
                
                # Convert datetime objects to ISO format strings
                case_dict['created_date'] = case.created_date.isoformat()
                case_dict['last_updated'] = case.last_updated.isoformat()
                
                if case.next_deadline:
                    case_dict['next_deadline'] = case.next_deadline.isoformat()
                else:
                    case_dict['next_deadline'] = None
                
                # Convert enums to strings
                case_dict['status'] = case.status.value
                case_dict['priority'] = case.priority.value
                
                # Convert case notes
                notes_data = []
                for note in case.case_notes:
                    note_dict = asdict(note)
                    note_dict['created_date'] = note.created_date.isoformat()
                    note_dict['note_type'] = note.note_type.value
                    notes_data.append(note_dict)
                case_dict['case_notes'] = notes_data
                
                data[case_id] = case_dict
            
            with open(self.cases_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving cases to {self.cases_file}: {e}")
    
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
        case_id = str(uuid.uuid4())
        now = datetime.now()
        
        new_case = LegalCase(
            case_id=case_id,
            title=title,
            client_name=client_name,
            practice_area=practice_area,
            jurisdiction=jurisdiction,
            status=CaseStatus.ACTIVE,
            priority=priority,
            created_date=now,
            last_updated=now,
            case_notes=[],
            conversation_history=[],
            metadata={},
            description=description,
            case_number=case_number,
            opposing_party=opposing_party,
            court=court
        )
        
        self.cases[case_id] = new_case
        self.save_cases()
        
        # Add initial case note
        self.add_case_note(
            case_id=case_id,
            note_type=NoteType.GENERAL,
            title="Case Created",
            content=f"Case '{title}' created for client '{client_name}'"
        )
        
        return case_id
    
    def edit_case(self, case_id: str, **kwargs) -> bool:
        """Edit an existing case"""
        if case_id not in self.cases:
            return False
        
        case = self.cases[case_id]
        
        # Update allowed fields
        allowed_fields = [
            'title', 'client_name', 'practice_area', 'jurisdiction',
            'description', 'case_number', 'opposing_party', 'court',
            'priority', 'status', 'next_deadline', 'estimated_hours', 'billable_rate'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'priority' and isinstance(value, str):
                    value = CasePriority(value)
                elif field == 'status' and isinstance(value, str):
                    value = CaseStatus(value)
                elif field == 'next_deadline' and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                
                setattr(case, field, value)
        
        case.last_updated = datetime.now()
        self.save_cases()
        
        return True
    
    def archive_case(self, case_id: str) -> bool:
        """Archive a case (set status to archived)"""
        return self.edit_case(case_id, status=CaseStatus.ARCHIVED)
    
    def delete_case(self, case_id: str) -> bool:
        """Delete a case permanently"""
        if case_id not in self.cases:
            return False
        
        del self.cases[case_id]
        self.save_cases()
        return True
    
    def get_case_list(self, status_filter: Optional[CaseStatus] = None) -> List[Dict]:
        """Get list of cases with optional status filtering"""
        cases_list = []
        
        for case in self.cases.values():
            if status_filter is None or case.status == status_filter:
                cases_list.append({
                    'case_id': case.case_id,
                    'title': case.title,
                    'client_name': case.client_name,
                    'practice_area': case.practice_area,
                    'jurisdiction': case.jurisdiction,
                    'status': case.status.value,
                    'priority': case.priority.value,
                    'created_date': case.created_date.isoformat(),
                    'last_updated': case.last_updated.isoformat(),
                    'notes_count': len(case.case_notes),
                    'conversations_count': len(case.conversation_history)
                })
        
        # Sort by last updated (most recent first)
        cases_list.sort(key=lambda x: x['last_updated'], reverse=True)
        return cases_list
    
    def get_case_details(self, case_id: str) -> Optional[Dict]:
        """Get detailed information about a specific case"""
        if case_id not in self.cases:
            return None
        
        case = self.cases[case_id]
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
    
    def add_case_note(self, 
                     case_id: str, 
                     note_type: NoteType, 
                     title: str, 
                     content: str,
                     tags: List[str] = None) -> bool:
        """Add a note to a case"""
        if case_id not in self.cases:
            return False
        
        note_id = str(uuid.uuid4())
        note = CaseNote(
            note_id=note_id,
            note_type=note_type,
            title=title,
            content=content,
            created_date=datetime.now(),
            tags=tags or []
        )
        
        self.cases[case_id].case_notes.append(note)
        self.cases[case_id].last_updated = datetime.now()
        self.save_cases()
        
        return True
    
    def update_case_status(self, case_id: str, status: CaseStatus) -> bool:
        """Update case status"""
        return self.edit_case(case_id, status=status)
    
    def add_conversation_to_case(self, case_id: str, conversation_data: Dict) -> bool:
        """Add conversation data to a case"""
        if case_id not in self.cases:
            return False
        
        conversation_entry = {
            'timestamp': datetime.now().isoformat(),
            'conversation_id': str(uuid.uuid4()),
            **conversation_data
        }
        
        self.cases[case_id].conversation_history.append(conversation_entry)
        self.cases[case_id].last_updated = datetime.now()
        self.save_cases()
        
        return True
    
    def get_case_statistics(self) -> Dict[str, Any]:
        """Get comprehensive case statistics"""
        total_cases = len(self.cases)
        
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
        for status in CaseStatus:
            status_counts[status.value] = sum(1 for case in self.cases.values() if case.status == status)
        
        # Priority breakdown
        priority_counts = {}
        for priority in CasePriority:
            priority_counts[priority.value] = sum(1 for case in self.cases.values() if case.priority == priority)
        
        # Practice area breakdown
        practice_areas = {}
        for case in self.cases.values():
            area = case.practice_area
            practice_areas[area] = practice_areas.get(area, 0) + 1
        
        # Recent activity (last 10 updated cases)
        recent_cases = sorted(
            self.cases.values(),
            key=lambda x: x.last_updated,
            reverse=True
        )[:10]
        
        recent_activity = [
            {
                'case_id': case.case_id,
                'title': case.title,
                'client_name': case.client_name,
                'last_updated': case.last_updated.isoformat(),
                'status': case.status.value
            }
            for case in recent_cases
        ]
        
        return {
            'total_cases': total_cases,
            'status_breakdown': status_counts,
            'priority_breakdown': priority_counts,
            'practice_area_breakdown': practice_areas,
            'recent_activity': recent_activity,
            'total_notes': sum(len(case.case_notes) for case in self.cases.values()),
            'total_conversations': sum(len(case.conversation_history) for case in self.cases.values())
        }
    
    def search_cases(self, query: str, search_fields: List[str] = None) -> List[Dict]:
        """Search cases by query string"""
        if search_fields is None:
            search_fields = ['title', 'client_name', 'description', 'case_number']
        
        query = query.lower()
        matching_cases = []
        
        for case in self.cases.values():
            match_found = False
            
            for field in search_fields:
                field_value = getattr(case, field, "")
                if isinstance(field_value, str) and query in field_value.lower():
                    match_found = True
                    break
            
            # Also search in case notes
            if not match_found:
                for note in case.case_notes:
                    if (query in note.title.lower() or 
                        query in note.content.lower() or
                        any(query in tag.lower() for tag in note.tags)):
                        match_found = True
                        break
            
            if match_found:
                matching_cases.append({
                    'case_id': case.case_id,
                    'title': case.title,
                    'client_name': case.client_name,
                    'practice_area': case.practice_area,
                    'status': case.status.value,
                    'priority': case.priority.value,
                    'last_updated': case.last_updated.isoformat()
                })
        
        return matching_cases
    
    def export_case_data(self, case_id: str, format: str = 'json') -> Optional[str]:
        """Export case data in specified format"""
        if case_id not in self.cases:
            return None
        
        case_details = self.get_case_details(case_id)
        
        if format.lower() == 'json':
            return json.dumps(case_details, indent=2, ensure_ascii=False)
        
        # Add other export formats as needed
        return None
    
    def get_active_cases(self) -> List[Dict]:
        """Get all active cases"""
        return self.get_case_list(status_filter=CaseStatus.ACTIVE)
    
    def get_case_by_id(self, case_id: str) -> Optional[LegalCase]:
        """Get case object by ID"""
        return self.cases.get(case_id)
    
    def get_case(self, case_id: str) -> Optional[LegalCase]:
        """Get case object by ID (alias for get_case_by_id for UI compatibility)"""
        return self.get_case_by_id(case_id)
    
    def get_all_cases(self) -> List[LegalCase]:
        """Get all cases as a list of LegalCase objects"""
        return list(self.cases.values())
    
    def get_case_conversations(self, case_id: str) -> List[Dict]:
        """Get all conversations for a specific case"""
        if case_id not in self.cases:
            return []
        
        case = self.cases[case_id]
        return case.conversation_history
    
    def add_conversation(self, case_id: str, conversation_data: Dict) -> bool:
        """Add conversation data to a case (alias for add_conversation_to_case for UI compatibility)"""
        return self.add_conversation_to_case(case_id, conversation_data)
    
    def add_note(self, case_id: str, note_content: str, note_type: str = "general") -> bool:
        """Add a note to a case (simplified interface for UI compatibility)"""
        # Convert string note_type to NoteType enum
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