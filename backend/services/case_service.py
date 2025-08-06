"""
Case Service for managing case creation wizard and case operations
"""

from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
import json
import uuid

from ..models import Case, User, LawFirm, FinancialInformation, ChildrenInformation, AuditLog
from ..models.enums import (
    AustralianFamilyCaseType, CaseStatus, CasePriority, CourtSystem, 
    PartyType, UserRole
)
from .ai_service import AIService
from .conflict_service import ConflictCheckService

class CaseCreationStep(str):
    """Case creation wizard steps"""
    CLASSIFICATION = "classification"
    CLIENT_INFO = "client_info"
    FINANCIAL_INFO = "financial_info"
    CHILDREN_INFO = "children_info"
    COURT_INFO = "court_info"
    DOCUMENT_UPLOAD = "document_upload"

class CaseService:
    """Service for case management operations"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.conflict_service = ConflictCheckService()
    
    async def start_case_creation_wizard(self, user: User, db: Session) -> Dict[str, Any]:
        """
        Start a new case creation wizard session
        
        Args:
            user: Current user
            db: Database session
            
        Returns:
            Dict with wizard session ID and initial step
        """
        wizard_session_id = str(uuid.uuid4())
        
        # Store initial wizard state in session (in production, use Redis or database)
        wizard_state = {
            "session_id": wizard_session_id,
            "current_step": CaseCreationStep.CLASSIFICATION,
            "completed_steps": [],
            "data": {},
            "created_by": str(user.id),
            "firm_id": str(user.firm_id),
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # In a real implementation, store this in Redis or database
        # For now, we'll return it and expect the client to manage state
        
        return {
            "wizard_session_id": wizard_session_id,
            "current_step": CaseCreationStep.CLASSIFICATION,
            "step_info": await self._get_step_info(CaseCreationStep.CLASSIFICATION),
            "progress": {"completed": 0, "total": 6},
            "state": wizard_state
        }
    
    async def process_wizard_step(self, wizard_session_id: str, step: str, 
                                step_data: Dict[str, Any], user: User, 
                                db: Session) -> Dict[str, Any]:
        """
        Process a step in the case creation wizard
        
        Args:
            wizard_session_id: Wizard session ID
            step: Current step being processed
            step_data: Data for this step
            user: Current user
            db: Database session
            
        Returns:
            Dict with validation results and next step info
        """
        # Validate step data
        validation_result = await self._validate_step_data(step, step_data)
        if not validation_result["is_valid"]:
            return {
                "success": False,
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"]
            }
        
        # Process specific step logic
        step_result = await self._process_step_logic(step, step_data, user, db)
        if not step_result["success"]:
            return step_result
        
        # Determine next step
        next_step = self._get_next_step(step, step_data)
        
        # Prepare response
        response = {
            "success": True,
            "current_step": step,
            "next_step": next_step,
            "step_result": step_result,
            "progress": self._calculate_progress(step),
            "ai_suggestions": step_result.get("ai_suggestions", [])
        }
        
        # If final step, create the case
        if next_step is None:
            case_creation_result = await self._finalize_case_creation(
                wizard_session_id, step_data, user, db)
            response["case_creation"] = case_creation_result
        else:
            # Get next step info
            response["next_step_info"] = await self._get_step_info(next_step)
        
        return response
    
    async def _validate_step_data(self, step: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data for a specific wizard step"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        if step == CaseCreationStep.CLASSIFICATION:
            # Validate case classification
            if not step_data.get("case_type"):
                validation_result["errors"].append("Case type is required")
            elif step_data["case_type"] not in [ct.value for ct in AustralianFamilyCaseType]:
                validation_result["errors"].append("Invalid case type")
            
            if not step_data.get("title"):
                validation_result["errors"].append("Case title is required")
            elif len(step_data["title"]) < 10:
                validation_result["warnings"].append("Case title should be more descriptive")
        
        elif step == CaseCreationStep.CLIENT_INFO:
            # Validate client information
            required_fields = ["applicant_name", "respondent_name"]
            for field in required_fields:
                if not step_data.get(field):
                    validation_result["errors"].append(f"{field.replace('_', ' ').title()} is required")
            
            # Validate contact information
            if step_data.get("applicant_email") and "@" not in step_data["applicant_email"]:
                validation_result["errors"].append("Invalid applicant email format")
        
        elif step == CaseCreationStep.FINANCIAL_INFO:
            # Validate financial information (if case type requires it)
            case_type = step_data.get("case_type")
            if case_type in ["property_settlement", "divorce"]:
                if not step_data.get("estimated_value"):
                    validation_result["warnings"].append("Estimated case value helps with planning")
                elif step_data["estimated_value"] < 0:
                    validation_result["errors"].append("Estimated value cannot be negative")
        
        elif step == CaseCreationStep.CHILDREN_INFO:
            # Validate children information
            case_type = step_data.get("case_type")
            if case_type in ["child_custody", "parenting_orders", "child_support"]:
                children = step_data.get("children", [])
                if not children:
                    validation_result["errors"].append("Children information is required for this case type")
                else:
                    for i, child in enumerate(children):
                        if not child.get("first_name"):
                            validation_result["errors"].append(f"Child {i+1} first name is required")
                        if not child.get("date_of_birth"):
                            validation_result["errors"].append(f"Child {i+1} date of birth is required")
        
        elif step == CaseCreationStep.COURT_INFO:
            # Validate court information
            if not step_data.get("court_level"):
                validation_result["warnings"].append("Court level helps with case planning")
            
            if step_data.get("court_level") and step_data["court_level"] not in [cs.value for cs in CourtSystem]:
                validation_result["errors"].append("Invalid court system")
        
        elif step == CaseCreationStep.DOCUMENT_UPLOAD:
            # Document upload validation handled separately
            pass
        
        validation_result["is_valid"] = len(validation_result["errors"]) == 0
        return validation_result
    
    async def _process_step_logic(self, step: str, step_data: Dict[str, Any], 
                                user: User, db: Session) -> Dict[str, Any]:
        """Process specific logic for each wizard step"""
        
        if step == CaseCreationStep.CLASSIFICATION:
            return await self._process_classification_step(step_data, user, db)
        elif step == CaseCreationStep.CLIENT_INFO:
            return await self._process_client_info_step(step_data, user, db)
        elif step == CaseCreationStep.FINANCIAL_INFO:
            return await self._process_financial_info_step(step_data, user, db)
        elif step == CaseCreationStep.CHILDREN_INFO:
            return await self._process_children_info_step(step_data, user, db)
        elif step == CaseCreationStep.COURT_INFO:
            return await self._process_court_info_step(step_data, user, db)
        elif step == CaseCreationStep.DOCUMENT_UPLOAD:
            return await self._process_document_upload_step(step_data, user, db)
        else:
            return {"success": False, "error": "Invalid step"}
    
    async def _process_classification_step(self, step_data: Dict[str, Any], 
                                         user: User, db: Session) -> Dict[str, Any]:
        """Process case classification step with AI suggestions"""
        
        # Get AI suggestions for case type if description provided
        ai_suggestions = []
        if step_data.get("description"):
            try:
                case_type_suggestion = await self.ai_service.suggest_case_type(
                    step_data["description"], 
                    step_data
                )
                ai_suggestions.append({
                    "type": "case_type_suggestion",
                    "suggestion": case_type_suggestion
                })
            except Exception as e:
                # Continue without AI suggestions if they fail
                pass
        
        # Perform conflict check
        conflict_check = await self.conflict_service.check_conflicts(
            applicant_name=step_data.get("applicant_name", ""),
            respondent_name=step_data.get("respondent_name", ""),
            firm_id=str(user.firm_id),
            db=db
        )
        
        return {
            "success": True,
            "ai_suggestions": ai_suggestions,
            "conflict_check": conflict_check,
            "suggested_documents": await self._get_suggested_documents(step_data.get("case_type"))
        }
    
    async def _process_client_info_step(self, step_data: Dict[str, Any], 
                                      user: User, db: Session) -> Dict[str, Any]:
        """Process client information step"""
        
        # Additional conflict check with more detailed client info
        conflict_check = await self.conflict_service.check_detailed_conflicts(
            step_data, str(user.firm_id), db
        )
        
        ai_suggestions = []
        
        # AI suggestion for case complexity based on client info
        try:
            complexity_analysis = await self.ai_service.analyze_case_complexity(step_data)
            ai_suggestions.append({
                "type": "complexity_analysis",
                "suggestion": complexity_analysis
            })
        except Exception:
            pass
        
        return {
            "success": True,
            "conflict_check": conflict_check,
            "ai_suggestions": ai_suggestions
        }
    
    async def _process_financial_info_step(self, step_data: Dict[str, Any], 
                                         user: User, db: Session) -> Dict[str, Any]:
        """Process financial information step"""
        
        ai_suggestions = []
        
        # AI suggestions for financial matters
        if step_data.get("estimated_value", 0) > 0:
            try:
                # Suggest required financial documents
                financial_docs = await self.ai_service.suggest_required_documents(
                    AustralianFamilyCaseType.PROPERTY_SETTLEMENT,
                    step_data
                )
                ai_suggestions.append({
                    "type": "financial_documents",
                    "suggestion": financial_docs
                })
            except Exception:
                pass
        
        return {
            "success": True,
            "ai_suggestions": ai_suggestions,
            "financial_validation": self._validate_financial_data(step_data)
        }
    
    async def _process_children_info_step(self, step_data: Dict[str, Any], 
                                        user: User, db: Session) -> Dict[str, Any]:
        """Process children information step"""
        
        ai_suggestions = []
        
        # AI suggestions for children matters
        if step_data.get("children"):
            try:
                children_docs = await self.ai_service.suggest_required_documents(
                    AustralianFamilyCaseType.CHILD_CUSTODY,
                    step_data
                )
                ai_suggestions.append({
                    "type": "children_documents",
                    "suggestion": children_docs
                })
            except Exception:
                pass
        
        return {
            "success": True,
            "ai_suggestions": ai_suggestions,
            "children_validation": self._validate_children_data(step_data)
        }
    
    async def _process_court_info_step(self, step_data: Dict[str, Any], 
                                     user: User, db: Session) -> Dict[str, Any]:
        """Process court information step"""
        
        ai_suggestions = []
        
        # AI suggestions for court procedures
        try:
            case_timeline = await self._generate_case_timeline(step_data)
            ai_suggestions.append({
                "type": "case_timeline",
                "suggestion": case_timeline
            })
        except Exception:
            pass
        
        return {
            "success": True,
            "ai_suggestions": ai_suggestions,
            "court_suggestions": self._get_court_suggestions(step_data)
        }
    
    async def _process_document_upload_step(self, step_data: Dict[str, Any], 
                                          user: User, db: Session) -> Dict[str, Any]:
        """Process document upload step"""
        
        # This will be handled by the document service
        return {
            "success": True,
            "message": "Ready for document upload",
            "supported_formats": ["PDF", "DOCX", "PNG", "JPG", "TIFF"],
            "max_file_size": "50MB",
            "processing_features": [
                "Automatic text extraction",
                "OCR for scanned documents", 
                "Document classification",
                "Key information extraction"
            ]
        }
    
    async def _finalize_case_creation(self, wizard_session_id: str, 
                                    combined_data: Dict[str, Any], 
                                    user: User, db: Session) -> Dict[str, Any]:
        """Create the final case from wizard data"""
        
        try:
            # Generate case number
            case_number = await self._generate_case_number(user.firm_id, db)
            
            # Create main case record
            case = Case(
                firm_id=user.firm_id,
                case_number=case_number,
                case_type=AustralianFamilyCaseType(combined_data["case_type"]),
                title=combined_data["title"],
                description=combined_data.get("description"),
                created_by=user.id,
                assigned_lawyer=combined_data.get("assigned_lawyer", user.id),
                client_id=combined_data.get("client_id"),
                opposing_party_name=combined_data.get("respondent_name"),
                court_level=CourtSystem(combined_data["court_level"]) if combined_data.get("court_level") else None,
                court_location=combined_data.get("court_location"),
                estimated_value=combined_data.get("estimated_value"),
                priority=CasePriority(combined_data.get("priority", "medium"))
            )
            
            db.add(case)
            db.flush()  # Get case ID
            
            # Create financial information if provided
            if combined_data.get("financial_info"):
                await self._create_financial_information(case.id, combined_data["financial_info"], db)
            
            # Create children information if provided
            if combined_data.get("children"):
                await self._create_children_information(case.id, combined_data["children"], db)
            
            # Generate AI case summary
            try:
                case_summary = await self.ai_service.generate_case_summary(combined_data)
                case.ai_risk_assessment = {"summary": case_summary}
            except Exception:
                pass
            
            # Create audit log
            audit_log = AuditLog.log_user_action(
                firm_id=str(user.firm_id),
                user_id=str(user.id),
                action="create",
                description=f"Case created via wizard: {case.title}",
                entity_type="case",
                entity_id=str(case.id)
            )
            db.add(audit_log)
            
            db.commit()
            
            return {
                "success": True,
                "case_id": str(case.id),
                "case_number": case_number,
                "message": "Case created successfully",
                "next_steps": [
                    "Upload initial documents",
                    "Schedule client meeting",
                    "File court applications",
                    "Serve papers on respondent"
                ]
            }
            
        except IntegrityError as e:
            db.rollback()
            return {
                "success": False,
                "error": "Case number already exists. Please try again."
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": f"Failed to create case: {str(e)}"
            }
    
    async def _create_financial_information(self, case_id: str, 
                                          financial_data: Dict[str, Any], 
                                          db: Session):
        """Create financial information records"""
        
        # Create applicant financial info
        if financial_data.get("applicant"):
            applicant_info = FinancialInformation(
                case_id=case_id,
                party_type=PartyType.APPLICANT,
                real_estate=financial_data["applicant"].get("real_estate", []),
                bank_accounts=financial_data["applicant"].get("bank_accounts", []),
                investments=financial_data["applicant"].get("investments", []),
                superannuation=financial_data["applicant"].get("superannuation", []),
                debts_liabilities=financial_data["applicant"].get("debts_liabilities", []),
                income_details=financial_data["applicant"].get("income_details", {}),
                expenses=financial_data["applicant"].get("expenses", {})
            )
            applicant_info.calculate_totals()
            db.add(applicant_info)
        
        # Create respondent financial info
        if financial_data.get("respondent"):
            respondent_info = FinancialInformation(
                case_id=case_id,
                party_type=PartyType.RESPONDENT,
                real_estate=financial_data["respondent"].get("real_estate", []),
                bank_accounts=financial_data["respondent"].get("bank_accounts", []),
                investments=financial_data["respondent"].get("investments", []),
                superannuation=financial_data["respondent"].get("superannuation", []),
                debts_liabilities=financial_data["respondent"].get("debts_liabilities", []),
                income_details=financial_data["respondent"].get("income_details", {}),
                expenses=financial_data["respondent"].get("expenses", {})
            )
            respondent_info.calculate_totals()
            db.add(respondent_info)
    
    async def _create_children_information(self, case_id: str, 
                                         children_data: List[Dict[str, Any]], 
                                         db: Session):
        """Create children information records"""
        
        for child_data in children_data:
            child_info = ChildrenInformation(
                case_id=case_id,
                first_name=child_data["first_name"],
                last_name=child_data["last_name"],
                date_of_birth=datetime.strptime(child_data["date_of_birth"], "%Y-%m-%d").date(),
                current_living_arrangement=child_data.get("current_living_arrangement"),
                proposed_living_arrangement=child_data.get("proposed_living_arrangement"),
                school_name=child_data.get("school_name"),
                school_year=child_data.get("school_year"),
                special_needs=child_data.get("special_needs", False),
                special_needs_details=child_data.get("special_needs_details"),
                current_parenting_time=child_data.get("current_parenting_time"),
                proposed_parenting_time=child_data.get("proposed_parenting_time")
            )
            db.add(child_info)
    
    async def _generate_case_number(self, firm_id: str, db: Session) -> str:
        """Generate unique case number for firm"""
        
        # Get firm prefix
        firm = db.query(LawFirm).filter(LawFirm.id == firm_id).first()
        firm_prefix = firm.name[:3].upper() if firm else "LEG"
        
        # Get current year
        year = datetime.now().year
        
        # Get next sequence number for this firm and year
        existing_cases = db.query(Case).filter(
            Case.firm_id == firm_id,
            Case.case_number.like(f"{firm_prefix}-{year}-%")
        ).count()
        
        sequence = existing_cases + 1
        
        return f"{firm_prefix}-{year}-{sequence:04d}"
    
    def _get_next_step(self, current_step: str, step_data: Dict[str, Any]) -> Optional[str]:
        """Determine the next step in the wizard"""
        
        step_order = [
            CaseCreationStep.CLASSIFICATION,
            CaseCreationStep.CLIENT_INFO,
            CaseCreationStep.FINANCIAL_INFO,
            CaseCreationStep.CHILDREN_INFO,
            CaseCreationStep.COURT_INFO,
            CaseCreationStep.DOCUMENT_UPLOAD
        ]
        
        try:
            current_index = step_order.index(current_step)
            
            # Skip steps based on case type
            case_type = step_data.get("case_type")
            
            if current_step == CaseCreationStep.CLIENT_INFO:
                # Skip financial info if not property-related
                if case_type not in ["property_settlement", "divorce", "spousal_maintenance"]:
                    if case_type in ["child_custody", "parenting_orders", "child_support"]:
                        return CaseCreationStep.CHILDREN_INFO
                    else:
                        return CaseCreationStep.COURT_INFO
            
            elif current_step == CaseCreationStep.FINANCIAL_INFO:
                # Skip children info if not child-related
                if case_type not in ["child_custody", "parenting_orders", "child_support", "divorce"]:
                    return CaseCreationStep.COURT_INFO
            
            # Return next step in order
            if current_index + 1 < len(step_order):
                return step_order[current_index + 1]
            else:
                return None  # Final step
                
        except ValueError:
            return None
    
    def _calculate_progress(self, current_step: str) -> Dict[str, int]:
        """Calculate wizard progress"""
        step_numbers = {
            CaseCreationStep.CLASSIFICATION: 1,
            CaseCreationStep.CLIENT_INFO: 2,
            CaseCreationStep.FINANCIAL_INFO: 3,
            CaseCreationStep.CHILDREN_INFO: 4,
            CaseCreationStep.COURT_INFO: 5,
            CaseCreationStep.DOCUMENT_UPLOAD: 6
        }
        
        completed = step_numbers.get(current_step, 1)
        return {"completed": completed, "total": 6}
    
    async def _get_step_info(self, step: str) -> Dict[str, Any]:
        """Get information about a wizard step"""
        
        step_info = {
            CaseCreationStep.CLASSIFICATION: {
                "title": "Case Classification",
                "description": "Select the type of family law matter and provide basic details",
                "required_fields": ["case_type", "title"],
                "optional_fields": ["description", "urgency"],
                "estimated_time": "2 minutes"
            },
            CaseCreationStep.CLIENT_INFO: {
                "title": "Client Information", 
                "description": "Enter details about the parties involved",
                "required_fields": ["applicant_name", "respondent_name"],
                "optional_fields": ["applicant_email", "respondent_email", "applicant_phone"],
                "estimated_time": "3 minutes"
            },
            CaseCreationStep.FINANCIAL_INFO: {
                "title": "Financial Information",
                "description": "Property, assets, and financial details (if applicable)",
                "required_fields": [],
                "optional_fields": ["estimated_value", "property_details", "income_details"],
                "estimated_time": "5 minutes"
            },
            CaseCreationStep.CHILDREN_INFO: {
                "title": "Children Information",
                "description": "Details about children involved (if applicable)",
                "required_fields": ["children"],
                "optional_fields": ["parenting_arrangements", "school_details"],
                "estimated_time": "4 minutes"
            },
            CaseCreationStep.COURT_INFO: {
                "title": "Court Information",
                "description": "Court jurisdiction and procedural details",
                "required_fields": [],
                "optional_fields": ["court_level", "court_location", "urgency"],
                "estimated_time": "2 minutes"
            },
            CaseCreationStep.DOCUMENT_UPLOAD: {
                "title": "Document Upload",
                "description": "Upload initial documents and supporting materials",
                "required_fields": [],
                "optional_fields": ["documents"],
                "estimated_time": "5 minutes"
            }
        }
        
        return step_info.get(step, {})
    
    async def _get_suggested_documents(self, case_type: str) -> List[Dict[str, Any]]:
        """Get suggested documents for case type"""
        
        if case_type:
            try:
                return await self.ai_service.suggest_required_documents(
                    AustralianFamilyCaseType(case_type), {}
                )
            except Exception:
                pass
        
        # Default suggestions
        return [
            {
                "document_name": "Application Form",
                "priority": "high",
                "description": "Initial court application",
                "deadline_days": 30
            }
        ]
    
    def _validate_financial_data(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate financial data completeness"""
        
        validation = {
            "completeness_score": 0.0,
            "missing_items": [],
            "recommendations": []
        }
        
        financial_items = [
            "real_estate", "bank_accounts", "investments", 
            "superannuation", "debts_liabilities", "income_details"
        ]
        
        provided_items = 0
        for item in financial_items:
            if step_data.get(item):
                provided_items += 1
            else:
                validation["missing_items"].append(item.replace("_", " ").title())
        
        validation["completeness_score"] = provided_items / len(financial_items)
        
        if validation["completeness_score"] < 0.5:
            validation["recommendations"].append("Consider providing more financial details for better case preparation")
        
        return validation
    
    def _validate_children_data(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate children data completeness"""
        
        validation = {
            "completeness_score": 1.0,
            "missing_items": [],
            "recommendations": []
        }
        
        children = step_data.get("children", [])
        if not children:
            return validation
        
        required_fields = ["first_name", "last_name", "date_of_birth"]
        optional_fields = ["school_name", "current_living_arrangement", "special_needs"]
        
        total_completeness = 0
        for child in children:
            child_completeness = 0
            child_total = len(required_fields) + len(optional_fields)
            
            for field in required_fields + optional_fields:
                if child.get(field):
                    child_completeness += 1
            
            total_completeness += child_completeness / child_total
        
        validation["completeness_score"] = total_completeness / len(children) if children else 0
        
        return validation
    
    def _get_court_suggestions(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get court-related suggestions"""
        
        case_type = step_data.get("case_type")
        estimated_value = step_data.get("estimated_value", 0)
        
        suggestions = {
            "recommended_court": "federal_circuit_family_court",
            "reasoning": "Most family law matters are handled by the Federal Circuit and Family Court",
            "alternative_courts": [],
            "filing_requirements": [
                "Complete application form",
                "Pay filing fee",
                "Serve papers on respondent"
            ]
        }
        
        # Adjust based on case complexity
        if estimated_value > 750000 or case_type in ["complex_property_settlement"]:
            suggestions["recommended_court"] = "family_court_australia"
            suggestions["reasoning"] = "Complex or high-value matters may require Family Court of Australia"
        
        return suggestions
    
    async def _generate_case_timeline(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate suggested case timeline"""
        
        case_type = step_data.get("case_type")
        
        # Basic timeline for family law matters
        timeline = {
            "estimated_duration_months": 6,
            "key_milestones": [
                {"task": "File application", "deadline_days": 14, "priority": "high"},
                {"task": "Serve respondent", "deadline_days": 28, "priority": "high"},
                {"task": "Response deadline", "deadline_days": 56, "priority": "medium"},
                {"task": "Financial disclosure", "deadline_days": 84, "priority": "high"},
                {"task": "Mediation", "deadline_days": 112, "priority": "medium"},
                {"task": "Final hearing", "deadline_days": 180, "priority": "high"}
            ],
            "critical_deadlines": ["File application", "Serve respondent", "Financial disclosure"]
        }
        
        # Adjust based on case type
        if case_type in ["child_custody", "parenting_orders"]:
            timeline["key_milestones"].insert(2, {
                "task": "Children's court report", "deadline_days": 70, "priority": "high"
            })
        
        return timeline