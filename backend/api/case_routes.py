"""
Case Management API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime

from ..database import get_db
from ..models import User, Case
from ..models.enums import AustralianFamilyCaseType, CaseStatus, CasePriority, CourtSystem
from ..auth.dependencies import get_current_active_user, require_permission
from ..services import CaseService

router = APIRouter(prefix="/cases", tags=["Case Management"])
case_service = CaseService()

# Pydantic models for request/response

class CaseTypeInfo(BaseModel):
    """Case type information"""
    case_type: AustralianFamilyCaseType
    display_name: str
    description: str
    typical_duration_months: int
    required_documents: List[str]
    complexity_factors: List[str]

class WizardStepRequest(BaseModel):
    """Wizard step processing request"""
    wizard_session_id: str
    step: str
    step_data: Dict[str, Any]

class WizardStepResponse(BaseModel):
    """Wizard step processing response"""
    success: bool
    current_step: str
    next_step: Optional[str] = None
    progress: Dict[str, int]
    step_result: Dict[str, Any] = {}
    ai_suggestions: List[Dict[str, Any]] = []
    errors: List[str] = []
    warnings: List[str] = []
    next_step_info: Optional[Dict[str, Any]] = None
    case_creation: Optional[Dict[str, Any]] = None

class CaseClassificationRequest(BaseModel):
    """Case classification step request"""
    case_type: AustralianFamilyCaseType
    title: str
    description: Optional[str] = None
    urgency: Optional[str] = "normal"
    applicant_name: Optional[str] = None
    respondent_name: Optional[str] = None

class ClientInfoRequest(BaseModel):
    """Client information step request"""
    applicant_name: str = Field(..., min_length=2, max_length=255)
    respondent_name: str = Field(..., min_length=2, max_length=255)
    applicant_email: Optional[str] = None
    respondent_email: Optional[str] = None
    applicant_phone: Optional[str] = None
    respondent_phone: Optional[str] = None
    applicant_address: Optional[str] = None
    respondent_address: Optional[str] = None

class FinancialInfoRequest(BaseModel):
    """Financial information step request"""
    estimated_value: Optional[float] = None
    applicant_financial: Optional[Dict[str, Any]] = {}
    respondent_financial: Optional[Dict[str, Any]] = {}
    joint_assets: Optional[List[Dict[str, Any]]] = []
    joint_debts: Optional[List[Dict[str, Any]]] = []

class ChildInfo(BaseModel):
    """Child information model"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    current_living_arrangement: Optional[str] = None
    proposed_living_arrangement: Optional[str] = None
    school_name: Optional[str] = None
    school_year: Optional[str] = None
    special_needs: bool = False
    special_needs_details: Optional[str] = None

class ChildrenInfoRequest(BaseModel):
    """Children information step request"""
    children: List[ChildInfo] = []
    current_parenting_arrangements: Optional[str] = None
    proposed_parenting_arrangements: Optional[str] = None

class CourtInfoRequest(BaseModel):
    """Court information step request"""
    court_level: Optional[CourtSystem] = None
    court_location: Optional[str] = None
    urgency_level: Optional[str] = "normal"
    special_circumstances: Optional[str] = None

class CaseResponse(BaseModel):
    """Case response model"""
    id: str
    case_number: str
    case_type: AustralianFamilyCaseType
    title: str
    description: Optional[str] = None
    status: CaseStatus
    priority: CasePriority
    created_by: str
    assigned_lawyer: Optional[str] = None
    opposing_party_name: Optional[str] = None
    court_level: Optional[CourtSystem] = None
    estimated_value: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CaseListResponse(BaseModel):
    """Case list response"""
    cases: List[CaseResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool

# API Endpoints

@router.get("/case-types", response_model=List[CaseTypeInfo])
async def get_case_types():
    """
    Get available case types with detailed information
    
    Returns information about all supported Australian family law case types
    including typical duration, required documents, and complexity factors.
    """
    case_types_info = [
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.DIVORCE,
            display_name="Divorce",
            description="Legal dissolution of marriage",
            typical_duration_months=6,
            required_documents=["Marriage Certificate", "Application for Divorce", "Financial Statement"],
            complexity_factors=["Property settlement", "Children involved", "Contested proceedings"]
        ),
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.PROPERTY_SETTLEMENT,
            display_name="Property Settlement",
            description="Division of assets and liabilities after separation",
            typical_duration_months=8,
            required_documents=["Financial Statement", "Property Valuations", "Bank Statements"],
            complexity_factors=["High asset value", "Business interests", "International assets"]
        ),
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.CHILD_CUSTODY,
            display_name="Child Custody",
            description="Arrangements for children's care and contact",
            typical_duration_months=6,
            required_documents=["Children's best interests report", "Parenting plan", "School reports"],
            complexity_factors=["Multiple children", "Interstate issues", "Safety concerns"]
        ),
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.PARENTING_ORDERS,
            display_name="Parenting Orders",
            description="Court orders regarding children's living arrangements",
            typical_duration_months=5,
            required_documents=["Application for parenting orders", "Family report", "Evidence affidavit"],
            complexity_factors=["Relocation requests", "Special needs children", "Family violence"]
        ),
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.CHILD_SUPPORT,
            display_name="Child Support",
            description="Financial support for children",
            typical_duration_months=3,
            required_documents=["Child support assessment", "Income statements", "Care percentage evidence"],
            complexity_factors=["Self-employed parents", "High income earners", "Special circumstances"]
        ),
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.SPOUSAL_MAINTENANCE,
            display_name="Spousal Maintenance",
            description="Financial support for former spouse",
            typical_duration_months=4,
            required_documents=["Financial statement", "Medical evidence", "Employment history"],
            complexity_factors=["Disability/illness", "Career sacrifices", "Age factors"]
        ),
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.DE_FACTO_SEPARATION,
            display_name="De Facto Separation",
            description="Property and parenting matters for de facto relationships",
            typical_duration_months=7,
            required_documents=["Evidence of relationship", "Financial records", "Separation certificate"],
            complexity_factors=["Relationship duration", "Financial contributions", "Future needs"]
        ),
        CaseTypeInfo(
            case_type=AustralianFamilyCaseType.DOMESTIC_VIOLENCE,
            display_name="Domestic Violence",
            description="Protection orders and safety measures",
            typical_duration_months=2,
            required_documents=["Application for protection order", "Evidence of violence", "Police reports"],
            complexity_factors=["Immediate danger", "Children at risk", "Complex family dynamics"]
        )
    ]
    
    return case_types_info

@router.post("/wizard/start")
async def start_case_creation_wizard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start a new case creation wizard session
    
    Initializes a 6-step case creation wizard that guides users through:
    1. Case Classification
    2. Client Information  
    3. Financial Information
    4. Children Information
    5. Court Information
    6. Document Upload
    
    Returns a wizard session ID and information about the first step.
    """
    try:
        wizard_result = await case_service.start_case_creation_wizard(current_user, db)
        return wizard_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start wizard: {str(e)}"
        )

@router.post("/wizard/step", response_model=WizardStepResponse)
async def process_wizard_step(
    request: WizardStepRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process a step in the case creation wizard
    
    Each step validates the provided data, performs AI analysis for suggestions,
    and determines the next step in the workflow. Steps may be skipped based
    on case type (e.g., financial info for non-property cases).
    
    Features:
    - Real-time validation with user-friendly error messages
    - AI-powered suggestions and case type recommendations
    - Automatic conflict checking for party names
    - Progress tracking and step estimation
    - Accessibility-compliant error handling
    """
    try:
        result = await case_service.process_wizard_step(
            request.wizard_session_id,
            request.step,
            request.step_data,
            current_user,
            db
        )
        
        return WizardStepResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wizard step processing failed: {str(e)}"
        )

@router.post("/wizard/classification")
async def process_classification_step(
    request: CaseClassificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process case classification step with AI suggestions
    
    This endpoint handles the first step of the wizard where users select
    the case type and provide basic information. It includes:
    
    - AI-powered case type suggestions based on description
    - Conflict checking for party names
    - Document requirements based on case type
    - Court jurisdiction recommendations
    """
    step_data = request.dict()
    
    try:
        result = await case_service.process_wizard_step(
            "temp-session",  # In production, use proper session management
            "classification",
            step_data,
            current_user,
            db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification step failed: {str(e)}"
        )

@router.post("/wizard/client-info")
async def process_client_info_step(
    request: ClientInfoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process client information step with enhanced conflict checking
    
    This step collects detailed information about the parties involved
    and performs comprehensive conflict checking including:
    
    - Name similarity matching across existing cases
    - Email and phone number conflict detection
    - Address verification for potential relationship indicators
    - AI-powered complexity analysis based on client information
    """
    step_data = request.dict()
    
    try:
        result = await case_service.process_wizard_step(
            "temp-session",
            "client_info", 
            step_data,
            current_user,
            db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Client info step failed: {str(e)}"
        )

@router.post("/wizard/financial-info")
async def process_financial_info_step(
    request: FinancialInfoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process financial information step with AI analysis
    
    Collects and validates financial information for property settlement
    cases, including:
    
    - Asset and liability cataloging
    - Automatic financial document suggestions
    - Complexity assessment based on asset types and values
    - Settlement strategy recommendations
    """
    step_data = request.dict()
    
    try:
        result = await case_service.process_wizard_step(
            "temp-session",
            "financial_info",
            step_data,
            current_user,
            db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial info step failed: {str(e)}"
        )

@router.post("/wizard/children-info") 
async def process_children_info_step(
    request: ChildrenInfoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process children information step with best interests analysis
    
    Collects information about children involved in family law matters:
    
    - Child details with age-appropriate considerations
    - Current and proposed living arrangements
    - School and special needs information
    - AI suggestions for required children's reports and assessments
    """
    step_data = request.dict()
    
    try:
        result = await case_service.process_wizard_step(
            "temp-session",
            "children_info",
            step_data, 
            current_user,
            db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Children info step failed: {str(e)}"
        )

@router.post("/wizard/court-info")
async def process_court_info_step(
    request: CourtInfoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process court information step with jurisdiction analysis
    
    Determines appropriate court jurisdiction and procedural requirements:
    
    - Court level recommendations based on case complexity
    - Jurisdiction-specific filing requirements
    - AI-generated case timeline with key milestones
    - Procedural compliance checklist
    """
    step_data = request.dict()
    
    try:
        result = await case_service.process_wizard_step(
            "temp-session",
            "court_info",
            step_data,
            current_user,
            db
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Court info step failed: {str(e)}"
        )

@router.get("/", response_model=CaseListResponse)
async def list_cases(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[CaseStatus] = Query(None, description="Filter by case status"),
    case_type: Optional[AustralianFamilyCaseType] = Query(None, description="Filter by case type"),
    search: Optional[str] = Query(None, description="Search in case title or parties"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned lawyer"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List cases with filtering and pagination
    
    Supports comprehensive filtering and search capabilities:
    - Status-based filtering (active, completed, settled, etc.)
    - Case type filtering for specific family law matters
    - Full-text search across case titles and party names
    - Lawyer assignment filtering
    - Accessible pagination with clear navigation
    """
    try:
        # Build query filters
        query = db.query(Case).filter(Case.firm_id == current_user.firm_id)
        
        if status:
            query = query.filter(Case.status == status)
        
        if case_type:
            query = query.filter(Case.case_type == case_type)
        
        if assigned_to:
            query = query.filter(Case.assigned_lawyer == assigned_to)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                Case.title.ilike(search_filter) |
                Case.opposing_party_name.ilike(search_filter) |
                Case.case_number.ilike(search_filter)
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        cases = query.offset(offset).limit(page_size).all()
        
        # Convert to response models
        case_responses = [CaseResponse.from_orm(case) for case in cases]
        
        return CaseListResponse(
            cases=case_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cases: {str(e)}"
        )

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed case information
    
    Returns complete case details including:
    - Basic case information and status
    - Party details and contact information
    - Financial information (if applicable)
    - Children information (if applicable)
    - Document list and processing status
    - AI analysis and recommendations
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.firm_id == current_user.firm_id
    ).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    return CaseResponse.from_orm(case)

@router.get("/{case_id}/ai-analysis")
async def get_case_ai_analysis(
    case_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get AI analysis for a specific case
    
    Provides comprehensive AI-powered analysis including:
    - Case complexity assessment
    - Risk analysis and mitigation strategies
    - Settlement predictions and recommendations
    - Timeline analysis with critical milestones
    - Document completeness assessment
    - Strategic recommendations for case management
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.firm_id == current_user.firm_id
    ).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    try:
        # Get case data for analysis
        case_data = {
            "case_type": case.case_type.value,
            "title": case.title,
            "description": case.description,
            "estimated_value": float(case.estimated_value) if case.estimated_value else 0,
            "children": [
                {
                    "first_name": child.first_name,
                    "last_name": child.last_name,
                    "age": child.get_age()
                }
                for child in case.children_info
            ],
            "financial_info": [
                {
                    "party_type": info.party_type.value,
                    "total_assets": float(info.total_assets) if info.total_assets else 0,
                    "total_liabilities": float(info.total_liabilities) if info.total_liabilities else 0
                }
                for info in case.financial_info
            ]
        }
        
        # Get AI analysis
        analysis = await case_service.ai_service.analyze_case_complexity(case_data)
        
        # Get AI case summary if not already generated
        if not case.ai_risk_assessment:
            summary = await case_service.ai_service.generate_case_summary(case_data)
            analysis["case_summary"] = summary
        else:
            analysis["case_summary"] = case.ai_risk_assessment.get("summary", "")
        
        return analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(e)}"
        )

@router.post("/{case_id}/ai-suggestions")
async def get_case_ai_suggestions(
    case_id: str,
    suggestion_type: str = Query(..., description="Type of suggestions to get"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get AI suggestions for case management
    
    Available suggestion types:
    - documents: Required and recommended documents
    - strategy: Case strategy and approach recommendations
    - timeline: Suggested case timeline and milestones
    - settlement: Settlement negotiation suggestions
    - compliance: Compliance checklist and requirements
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.firm_id == current_user.firm_id
    ).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    try:
        if suggestion_type == "documents":
            suggestions = await case_service.ai_service.suggest_required_documents(
                case.case_type, {"case_id": case_id}
            )
        elif suggestion_type == "timeline":
            # Build case data for timeline generation
            case_data = {
                "case_type": case.case_type.value,
                "estimated_value": float(case.estimated_value) if case.estimated_value else 0,
                "children_count": len(case.children_info),
                "complexity": "high" if case.estimated_value and case.estimated_value > 500000 else "medium"
            }
            suggestions = await case_service._generate_case_timeline(case_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown suggestion type: {suggestion_type}"
            )
        
        return {
            "case_id": case_id,
            "suggestion_type": suggestion_type,
            "suggestions": suggestions,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestions: {str(e)}"
        )