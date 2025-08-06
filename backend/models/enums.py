"""
Enumerations for LegalAI Hub
Defines all enum types used across the application
"""

import enum

class UserRole(enum.Enum):
    """User roles with hierarchical permissions"""
    PRINCIPAL = "principal"
    SENIOR_LAWYER = "senior_lawyer"
    LAWYER = "lawyer"
    PARALEGAL = "paralegal"
    ADMIN = "admin"
    CLIENT = "client"

class AustralianState(enum.Enum):
    """Australian states and territories"""
    NSW = "nsw"  # New South Wales
    VIC = "vic"  # Victoria
    QLD = "qld"  # Queensland
    WA = "wa"    # Western Australia
    SA = "sa"    # South Australia
    TAS = "tas"  # Tasmania
    ACT = "act"  # Australian Capital Territory
    NT = "nt"    # Northern Territory

class SubscriptionTier(enum.Enum):
    """Subscription tiers for law firms"""
    STARTER = "starter"
    PROFESSIONAL = "professional" 
    ENTERPRISE = "enterprise"
    ENTERPRISE_PLUS = "enterprise_plus"

class ComplianceStatus(enum.Enum):
    """Compliance status for law firms"""
    PENDING = "pending"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"

class CaseStatus(enum.Enum):
    """Case status tracking"""
    ACTIVE = "active"
    COMPLETED = "completed"
    SETTLED = "settled"
    WITHDRAWN = "withdrawn"
    ON_HOLD = "on_hold"
    ARCHIVED = "archived"

class CasePriority(enum.Enum):
    """Case priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high" 
    URGENT = "urgent"

class AustralianFamilyCaseType(enum.Enum):
    """Australian family law case types"""
    DIVORCE = "divorce"
    PROPERTY_SETTLEMENT = "property_settlement"
    CHILD_CUSTODY = "child_custody"
    PARENTING_ORDERS = "parenting_orders"
    CHILD_SUPPORT = "child_support"
    SPOUSAL_MAINTENANCE = "spousal_maintenance"
    DE_FACTO_SEPARATION = "de_facto_separation"
    DOMESTIC_VIOLENCE = "domestic_violence"

class CourtSystem(enum.Enum):
    """Australian court system levels"""
    FEDERAL_CIRCUIT_FAMILY_COURT = "federal_circuit_family_court"
    FAMILY_COURT_AUSTRALIA = "family_court_australia"
    SUPREME_COURT = "supreme_court"
    DISTRICT_COURT = "district_court"
    MAGISTRATES_COURT = "magistrates_court"
    CHILDRENS_COURT = "childrens_court"

class DocumentType(enum.Enum):
    """Document type classification"""
    AGREEMENT = "agreement"
    AFFIDAVIT = "affidavit"
    COURT_ORDER = "court_order"
    FINANCIAL_STATEMENT = "financial_statement"
    CORRESPONDENCE = "correspondence"
    EVIDENCE = "evidence"
    PLEADING = "pleading"
    CONTRACT = "contract"
    WILL = "will"
    POWER_OF_ATTORNEY = "power_of_attorney"
    OTHER = "other"

class ProcessingStatus(enum.Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"

class AIInteractionType(enum.Enum):
    """Types of AI interactions for logging"""
    LEGAL_QUERY = "legal_query"
    DOCUMENT_ANALYSIS = "document_analysis"
    CASE_RESEARCH = "case_research"
    DOCUMENT_GENERATION = "document_generation"
    PRECEDENT_SEARCH = "precedent_search"
    RISK_ASSESSMENT = "risk_assessment"
    SETTLEMENT_PREDICTION = "settlement_prediction"

class PartyType(enum.Enum):
    """Party types in legal proceedings"""
    APPLICANT = "applicant"
    RESPONDENT = "respondent"
    CHILD = "child"
    THIRD_PARTY = "third_party"