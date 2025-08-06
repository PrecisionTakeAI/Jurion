"""
SQLAlchemy models for LegalLLM Professional
Multi-tenant architecture for Australian Family Law
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, DECIMAL, 
    ForeignKey, ARRAY, Index, CheckConstraint, UniqueConstraint,
    BigInteger, JSON
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# Australian legal system ENUM types
user_role_enum = ENUM(
    'principal', 'senior_lawyer', 'lawyer', 'paralegal', 
    'law_clerk', 'admin', 'client', 'read_only',
    name='user_role_enum',
    create_type=False
)

au_family_case_type = ENUM(
    'divorce', 'property_settlement', 'child_custody', 'parenting_orders',
    'spousal_maintenance', 'child_support', 'domestic_violence',
    'adoption', 'surrogacy', 'defacto_separation', 'consent_orders',
    name='au_family_case_type',
    create_type=False
)

case_status_enum = ENUM(
    'initial_consultation', 'case_preparation', 'negotiation',
    'mediation', 'court_proceedings', 'settlement', 'completed',
    'on_hold', 'archived',
    name='case_status_enum',
    create_type=False
)

document_category = ENUM(
    'court_documents', 'financial_documents', 'correspondence',
    'affidavits', 'expert_reports', 'property_valuations',
    'bank_statements', 'tax_returns', 'superannuation_statements',
    'business_documents', 'parenting_plans', 'consent_orders',
    'medical_reports', 'child_assessments', 'other',
    name='document_category',
    create_type=False
)

document_subcategory = ENUM(
    # Court Documents
    'application', 'response', 'reply', 'court_orders', 'judgment',
    'subpoena', 'notice_to_produce', 'interim_orders',
    # Financial Documents  
    'asset_statement', 'liability_statement', 'income_statement',
    'form_13', 'form_13a', 'property_valuation', 'business_valuation',
    # Correspondence
    'letter_to_court', 'letter_to_opposing_party', 'internal_memo',
    'email_correspondence', 'file_note',
    # Other
    'contract', 'agreement', 'certificate', 'statutory_declaration',
    name='document_subcategory',
    create_type=False
)


class LawFirm(Base):
    """Multi-tenant law firm isolation"""
    __tablename__ = 'law_firms'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    abn = Column(String(20))  # Australian Business Number
    address = Column(JSON)
    phone = Column(String(20), nullable=True)  # Firm contact phone number
    jurisdiction = Column(String(50), default='australia')  # Primary jurisdiction
    subscription_tier = Column(String(50), default='professional')
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    users = relationship("User", back_populates="firm", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="firm")
    documents = relationship("Document", back_populates="firm")
    ai_interactions = relationship("AIInteraction", back_populates="firm")


class User(Base):
    """User management with Australian legal roles"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(255), nullable=False)  # Required for PBKDF2 hashing
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)  # Full name for compatibility
    role = Column(user_role_enum, nullable=False)
    australian_lawyer_number = Column(String(50))  # For admitted lawyers
    practitioner_number = Column(String(50))  # Alternative field name for compatibility
    practitioner_jurisdiction = Column(String(10))  # Australian state/territory
    mfa_secret = Column(String(255))
    mfa_secret_pending = Column(String(255))  # For MFA setup process
    mfa_enabled = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm", back_populates="users")
    assigned_cases = relationship("Case", foreign_keys="Case.assigned_lawyer_id", back_populates="assigned_lawyer")
    supervised_cases = relationship("Case", foreign_keys="Case.supervising_partner_id", back_populates="supervising_partner")
    created_cases = relationship("Case", foreign_keys="Case.created_by", back_populates="creator")
    uploaded_documents = relationship("Document", foreign_keys="Document.uploaded_by", back_populates="uploader")
    reviewed_documents = relationship("Document", foreign_keys="Document.reviewed_by", back_populates="reviewer")
    approved_documents = relationship("Document", foreign_keys="Document.approved_by", back_populates="approver")
    ai_interactions = relationship("AIInteraction", back_populates="user")


class Case(Base):
    """Australian family law specific case management"""
    __tablename__ = 'cases'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id'), nullable=False)
    case_number = Column(String(50), nullable=False)  # Firm's internal case number
    court_file_number = Column(String(100))  # Official court file number
    
    # Case Classification
    case_type = Column(au_family_case_type, nullable=False)
    jurisdiction = Column(String(50), default='australia')
    court_location = Column(String(100))  # Melbourne, Sydney, Brisbane, etc.
    
    # Parties Information
    applicant_details = Column(JSON, nullable=False)  # Primary client details
    respondent_details = Column(JSON)  # Other party details
    children_details = Column(JSON, default=[])  # Array of children information
    
    # Case Metadata
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(case_status_enum, default='initial_consultation')
    priority = Column(Integer, default=3)
    
    # Australian Family Law Specific
    relationship_type = Column(String(50))  # marriage, defacto, etc.
    relationship_start_date = Column(DateTime)
    separation_date = Column(DateTime)
    marriage_date = Column(DateTime)
    marriage_location = Column(String(100))
    
    # Financial Information
    estimated_asset_pool = Column(DECIMAL(15, 2))
    has_business_interests = Column(Boolean, default=False)
    has_superannuation = Column(Boolean, default=False)
    has_real_estate = Column(Boolean, default=False)
    
    # Children Information
    children_count = Column(Integer, default=0)
    children_ages = Column(ARRAY(Integer), default=[])
    parenting_arrangements = Column(Text)
    
    # Case Management
    assigned_lawyer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    supervising_partner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    estimated_completion_date = Column(DateTime)
    
    # AI and Analytics
    ai_case_summary = Column(Text)
    ai_risk_assessment = Column(JSON)
    ai_recommendations = Column(JSON, default=[])
    
    # Timestamps and Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True))
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('firm_id', 'case_number'),
        CheckConstraint('priority BETWEEN 1 AND 5', name='check_priority_range'),
    )
    
    # Relationships
    firm = relationship("LawFirm", back_populates="cases")
    assigned_lawyer = relationship("User", foreign_keys=[assigned_lawyer_id], back_populates="assigned_cases")
    supervising_partner = relationship("User", foreign_keys=[supervising_partner_id], back_populates="supervised_cases")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_cases")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    ai_interactions = relationship("AIInteraction", back_populates="case")
    family_law_requirements = relationship("AUFamilyLawRequirements", back_populates="case", uselist=False)
    workflows = relationship("CaseWorkflow", back_populates="case", cascade="all, delete-orphan")


class Document(Base):
    """Comprehensive document management"""
    __tablename__ = 'documents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id'), nullable=False)
    
    # File Information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 for integrity
    
    # Document Classification
    category = Column(document_category, nullable=False)
    subcategory = Column(document_subcategory)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    tags = Column(ARRAY(String), default=[])
    
    # OCR and AI Processing
    ocr_text = Column(Text)
    ocr_confidence = Column(DECIMAL(5, 4))  # 0.0 to 1.0
    ai_summary = Column(Text)
    ai_extracted_entities = Column(JSON, default={})
    ai_key_dates = Column(JSON, default=[])
    ai_financial_amounts = Column(JSON, default=[])
    
    # Legal Significance
    is_privileged = Column(Boolean, default=False)
    privilege_type = Column(String(50))  # legal_professional, litigation, etc.
    confidentiality_level = Column(Integer, default=1)
    disclosure_status = Column(String(50), default='not_disclosed')
    
    # Version Control
    version = Column(Integer, default=1)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'))
    is_current_version = Column(Boolean, default=True)
    
    # Workflow and Approval
    review_status = Column(String(50), default='pending_review')
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    approval_status = Column(String(50), default='pending')
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(DateTime(timezone=True))
    
    # Audit Trail
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidentiality_level BETWEEN 1 AND 5', name='check_confidentiality_range'),
    )
    
    # Relationships
    case = relationship("Case", back_populates="documents")
    firm = relationship("LawFirm", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by], back_populates="uploaded_documents")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="reviewed_documents")
    approver = relationship("User", foreign_keys=[approved_by], back_populates="approved_documents")
    parent_document = relationship("Document", remote_side=[id])
    ai_analyses = relationship("DocumentAIAnalysis", back_populates="document", cascade="all, delete-orphan")


class AIInteraction(Base):
    """AI conversation tracking with legal context"""
    __tablename__ = 'ai_interactions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id'), nullable=False)
    
    # Interaction Context
    session_id = Column(String(100), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # query, document_analysis, generation
    
    # Query Information
    user_query = Column(Text, nullable=False)
    query_intent = Column(String(100))  # AI-detected intent
    query_entities = Column(JSON, default={})
    
    # AI Response
    ai_response = Column(Text, nullable=False)
    ai_model_used = Column(String(100), nullable=False)
    ai_confidence_score = Column(DECIMAL(5, 4))
    ai_processing_time_ms = Column(Integer)
    
    # Legal Context
    jurisdiction = Column(String(50), default='australia')
    practice_area = Column(String(50), default='family_law')
    legal_citations = Column(JSON, default=[])
    
    # Document Context
    referenced_documents = Column(ARRAY(UUID), default=[])
    document_excerpts = Column(JSON, default=[])
    
    # Quality and Feedback
    user_rating = Column(Integer)
    user_feedback = Column(Text)
    requires_lawyer_review = Column(Boolean, default=False)
    lawyer_reviewed = Column(Boolean, default=False)
    lawyer_review_notes = Column(Text)
    
    # Compliance and Audit
    compliance_flags = Column(JSON, default={})
    contains_legal_advice = Column(Boolean, default=False)
    disclaimer_shown = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint('user_rating BETWEEN 1 AND 5', name='check_rating_range'),
    )
    
    # Relationships
    case = relationship("Case", back_populates="ai_interactions")
    user = relationship("User", back_populates="ai_interactions")
    firm = relationship("LawFirm", back_populates="ai_interactions")
    document_analyses = relationship("DocumentAIAnalysis", back_populates="ai_interaction", cascade="all, delete-orphan")


class DocumentAIAnalysis(Base):
    """Document-AI relationship tracking"""
    __tablename__ = 'document_ai_analysis'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    ai_interaction_id = Column(UUID(as_uuid=True), ForeignKey('ai_interactions.id'), nullable=False)
    
    # Analysis Results
    analysis_type = Column(String(50), nullable=False)  # summary, entities, dates, amounts
    analysis_results = Column(JSON, nullable=False)
    confidence_score = Column(DECIMAL(5, 4))
    
    # Processing Information
    processing_time_ms = Column(Integer)
    model_version = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('document_id', 'ai_interaction_id', 'analysis_type'),
    )
    
    # Relationships
    document = relationship("Document", back_populates="ai_analyses")
    ai_interaction = relationship("AIInteraction", back_populates="document_analyses")


class AUFamilyLawRequirements(Base):
    """Australian Family Law Act compliance tracking"""
    __tablename__ = 'au_family_law_requirements'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    
    # Section 60I Certificate (mediation requirement)
    mediation_required = Column(Boolean, default=True)
    mediation_completed = Column(Boolean, default=False)
    mediation_certificate_issued = Column(Boolean, default=False)
    exemption_reason = Column(String(100))
    
    # Property Settlement Requirements
    asset_disclosure_complete = Column(Boolean, default=False)
    form_13_filed = Column(Boolean, default=False)
    form_13a_filed = Column(Boolean, default=False)
    
    # Parenting Matters
    best_interests_assessment_done = Column(Boolean, default=False)
    child_representative_appointed = Column(Boolean, default=False)
    family_report_ordered = Column(Boolean, default=False)
    
    # Court Requirements
    conciliation_conference_required = Column(Boolean, default=False)
    conciliation_completed = Column(Boolean, default=False)
    
    # Compliance Status
    compliance_percentage = Column(DECIMAL(5, 2), default=0.00)
    last_compliance_check = Column(DateTime(timezone=True), server_default=func.now())
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="family_law_requirements")


class WorkflowTemplate(Base):
    """Predefined workflows for Australian family law"""
    __tablename__ = 'workflow_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    case_type = Column(au_family_case_type, nullable=False)
    jurisdiction = Column(String(50), default='australia')
    
    # Workflow Definition
    description = Column(Text)
    steps = Column(JSON, nullable=False)  # Array of workflow steps
    estimated_duration_days = Column(Integer)
    
    # Legal Framework
    relevant_legislation = Column(JSON, default=[])
    court_rules = Column(JSON, default=[])
    required_forms = Column(JSON, default=[])
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    case_workflows = relationship("CaseWorkflow", back_populates="template")


class CaseWorkflow(Base):
    """Case-specific workflow instances"""
    __tablename__ = 'case_workflows'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey('workflow_templates.id'))
    
    # Workflow State
    current_step = Column(Integer, default=1)
    status = Column(String(50), default='in_progress')
    steps_completed = Column(JSON, default=[])
    
    # Timeline
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    estimated_completion = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    supervising_lawyer = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Progress Tracking
    completion_percentage = Column(DECIMAL(5, 2), default=0.00)
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="workflows")
    template = relationship("WorkflowTemplate", back_populates="case_workflows")
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    supervising_user = relationship("User", foreign_keys=[supervising_lawyer])
    tasks = relationship("WorkflowTask", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowTask(Base):
    """Individual workflow tasks"""
    __tablename__ = 'workflow_tasks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('case_workflows.id', ondelete='CASCADE'), nullable=False)
    
    # Task Details
    step_number = Column(Integer, nullable=False)
    task_name = Column(String(255), nullable=False)
    description = Column(Text)
    task_type = Column(String(50))  # document_review, client_meeting, court_filing, etc.
    
    # Status and Assignment
    status = Column(String(50), default='pending')
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    priority = Column(Integer, default=3)
    
    # Timeline
    due_date = Column(DateTime(timezone=True))
    estimated_hours = Column(DECIMAL(5, 2))
    actual_hours = Column(DECIMAL(5, 2))
    
    # Dependencies
    depends_on_task_ids = Column(ARRAY(UUID), default=[])
    
    # Completion
    completed_at = Column(DateTime(timezone=True))
    completion_notes = Column(Text)
    requires_review = Column(Boolean, default=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint('priority BETWEEN 1 AND 5', name='check_task_priority_range'),
    )
    
    # Relationships
    workflow = relationship("CaseWorkflow", back_populates="tasks")
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# Performance indexes
Index('idx_cases_firm_status', Case.firm_id, Case.status)
Index('idx_cases_assigned_lawyer', Case.assigned_lawyer_id)
Index('idx_cases_type_jurisdiction', Case.case_type, Case.jurisdiction)

Index('idx_documents_case_category', Document.case_id, Document.category)
Index('idx_documents_firm_status', Document.firm_id, Document.review_status)

Index('idx_ai_interactions_session', AIInteraction.session_id)
Index('idx_ai_interactions_case', AIInteraction.case_id)
Index('idx_ai_interactions_type_date', AIInteraction.interaction_type, AIInteraction.created_at)

Index('idx_workflow_tasks_workflow_step', WorkflowTask.workflow_id, WorkflowTask.step_number)


# Enum classes for backward compatibility with authentication system
class UserRole:
    """User role constants for authentication system compatibility"""
    PRINCIPAL = 'principal'
    SENIOR_LAWYER = 'senior_lawyer'
    LAWYER = 'lawyer'
    PARALEGAL = 'paralegal'
    LAW_CLERK = 'law_clerk'
    ADMIN = 'admin'
    CLIENT = 'client'
    READ_ONLY = 'read_only'
    
    @classmethod
    def all_roles(cls):
        """Get all available roles"""
        return [
            cls.PRINCIPAL, cls.SENIOR_LAWYER, cls.LAWYER, cls.PARALEGAL,
            cls.LAW_CLERK, cls.ADMIN, cls.CLIENT, cls.READ_ONLY
        ]


class CaseType:
    """Australian family law case type constants"""
    DIVORCE = 'divorce'
    PROPERTY_SETTLEMENT = 'property_settlement'
    CHILD_CUSTODY = 'child_custody'
    PARENTING_ORDERS = 'parenting_orders'
    CHILD_SUPPORT = 'child_support'
    SPOUSE_MAINTENANCE = 'spouse_maintenance'
    BINDING_FINANCIAL_AGREEMENT = 'binding_financial_agreement'
    DE_FACTO_RELATIONSHIPS = 'de_facto_relationships'
    ADOPTION = 'adoption'
    SURROGACY = 'surrogacy'
    FAMILY_VIOLENCE = 'family_violence'
    INTERNATIONAL_FAMILY_LAW = 'international_family_law'
    
    @classmethod
    def all_types(cls):
        """Get all available case types"""
        return [
            cls.DIVORCE, cls.PROPERTY_SETTLEMENT, cls.CHILD_CUSTODY,
            cls.PARENTING_ORDERS, cls.CHILD_SUPPORT, cls.SPOUSE_MAINTENANCE,
            cls.BINDING_FINANCIAL_AGREEMENT, cls.DE_FACTO_RELATIONSHIPS,
            cls.ADOPTION, cls.SURROGACY, cls.FAMILY_VIOLENCE,
            cls.INTERNATIONAL_FAMILY_LAW
        ]