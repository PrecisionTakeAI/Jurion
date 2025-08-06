"""
Case model for legal case management
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func, DECIMAL, Integer, Date
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship, validates
from .base import Base, generate_uuid
from .enums import CaseStatus, CasePriority, AustralianFamilyCaseType, CourtSystem
import re

class Case(Base):
    """
    Legal case entity with AI-enhanced features
    """
    __tablename__ = 'cases'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False, index=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Case details
    case_type = Column(ENUM(AustralianFamilyCaseType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(ENUM(CaseStatus), default=CaseStatus.ACTIVE, index=True)
    priority = Column(ENUM(CasePriority), default=CasePriority.MEDIUM, index=True)
    
    # People involved
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    assigned_lawyer = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    client_id = Column(UUID(as_uuid=True))  # Flexible client reference
    opposing_party_name = Column(String(255))
    
    # Court information
    court_level = Column(ENUM(CourtSystem))
    court_location = Column(String(255))
    file_number = Column(String(100))
    
    # Financial information
    estimated_value = Column(DECIMAL(15, 2))
    retainer_amount = Column(DECIMAL(10, 2))
    billable_rate = Column(DECIMAL(8, 2))
    time_budget_hours = Column(Integer)
    
    # Important dates
    deadline_date = Column(Date)
    next_milestone = Column(Date)
    
    # AI-enhanced features
    ai_risk_assessment = Column(JSONB)
    ai_settlement_prediction = Column(JSONB)
    ai_timeline = Column(JSONB)
    compliance_checklist = Column(JSONB, default=dict)
    
    # Additional metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm", back_populates="cases")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_cases")
    lawyer = relationship("User", foreign_keys=[assigned_lawyer], back_populates="assigned_cases")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    financial_info = relationship("FinancialInformation", back_populates="case", cascade="all, delete-orphan")
    children_info = relationship("ChildrenInformation", back_populates="case", cascade="all, delete-orphan")
    ai_interactions = relationship("AIInteraction", back_populates="case")
    
    def __repr__(self):
        return f"<Case(case_number='{self.case_number}', type='{self.case_type.value}')>"
    
    @validates('case_number')
    def validate_case_number(self, key, case_number):
        """Validate case number format"""
        if not re.match(r'^[A-Z0-9\-]{3,50}$', case_number):
            raise ValueError("Case number must be 3-50 characters, alphanumeric with hyphens")
        return case_number.upper()
    
    @validates('file_number')
    def validate_file_number(self, key, file_number):
        """Validate court file number format"""
        if file_number and not re.match(r'^[A-Z0-9\/\-]{3,100}$', file_number):
            raise ValueError("Invalid file number format")
        return file_number.upper() if file_number else file_number
    
    def get_document_count(self):
        """Get total document count for this case"""
        return len(self.documents)
    
    def get_privileged_document_count(self):
        """Get count of privileged documents"""
        return len([doc for doc in self.documents if doc.is_privileged])
    
    def calculate_total_time_spent(self):
        """Calculate total billable time spent on case"""
        # This would integrate with time tracking system
        # For now, return placeholder
        return 0
    
    def get_next_deadline(self):
        """Get the next upcoming deadline"""
        if self.deadline_date and self.next_milestone:
            return min(self.deadline_date, self.next_milestone)
        return self.deadline_date or self.next_milestone
    
    def update_ai_risk_assessment(self, risk_data: dict):
        """Update AI risk assessment with new data"""
        if not self.ai_risk_assessment:
            self.ai_risk_assessment = {}
        
        self.ai_risk_assessment.update({
            'assessment': risk_data,
            'updated_at': func.now(),
            'confidence_score': risk_data.get('confidence', 0.0)
        })
    
    def update_compliance_checklist(self, item: str, completed: bool):
        """Update compliance checklist item"""
        if not self.compliance_checklist:
            self.compliance_checklist = {}
        
        self.compliance_checklist[item] = {
            'completed': completed,
            'completed_at': func.now() if completed else None
        }
    
    def get_compliance_progress(self):
        """Get compliance checklist progress percentage"""
        if not self.compliance_checklist:
            return 0
        
        total_items = len(self.compliance_checklist)
        completed_items = len([item for item in self.compliance_checklist.values() 
                             if item.get('completed', False)])
        
        return (completed_items / total_items) * 100 if total_items > 0 else 0