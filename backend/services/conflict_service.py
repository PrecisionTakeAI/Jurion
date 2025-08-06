"""
Conflict Check Service for legal conflict detection
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
import re
from difflib import SequenceMatcher

from ..models import Case, User, LawFirm, AuditLog
from ..models.enums import CaseStatus

class ConflictCheckService:
    """Service for checking legal conflicts of interest"""
    
    def __init__(self):
        self.similarity_threshold = 0.8  # 80% similarity threshold
        self.fuzzy_match_threshold = 0.7  # 70% for fuzzy matching
    
    async def check_conflicts(self, applicant_name: str, respondent_name: str, 
                            firm_id: str, db: Session) -> Dict[str, Any]:
        """
        Basic conflict check for party names
        
        Args:
            applicant_name: Name of the applicant
            respondent_name: Name of the respondent  
            firm_id: Current firm ID
            db: Database session
            
        Returns:
            Dict with conflict check results
        """
        conflict_result = {
            "has_conflicts": False,
            "conflicts": [],
            "warnings": [],
            "recommendations": [],
            "confidence_score": 1.0
        }
        
        if not applicant_name or not respondent_name:
            return conflict_result
        
        # Check for exact name matches in existing cases
        exact_conflicts = await self._check_exact_name_conflicts(
            applicant_name, respondent_name, firm_id, db
        )
        
        # Check for similar name matches (fuzzy matching)
        similar_conflicts = await self._check_similar_name_conflicts(
            applicant_name, respondent_name, firm_id, db
        )
        
        # Check for reversed party roles
        reversed_conflicts = await self._check_reversed_party_conflicts(
            applicant_name, respondent_name, firm_id, db
        )
        
        # Compile all conflicts
        all_conflicts = exact_conflicts + similar_conflicts + reversed_conflicts
        
        if all_conflicts:
            conflict_result["has_conflicts"] = True
            conflict_result["conflicts"] = all_conflicts
            conflict_result["confidence_score"] = min([c.get("confidence", 1.0) for c in all_conflicts])
        
        # Add warnings for potential issues
        if len(all_conflicts) == 0:
            # Check for common names that might need extra verification
            if self._is_common_name(applicant_name) or self._is_common_name(respondent_name):
                conflict_result["warnings"].append(
                    "Common names detected - manual verification recommended"
                )
        
        # Add recommendations
        conflict_result["recommendations"] = self._generate_conflict_recommendations(all_conflicts)
        
        return conflict_result
    
    async def check_detailed_conflicts(self, case_data: Dict[str, Any], 
                                     firm_id: str, db: Session) -> Dict[str, Any]:
        """
        Detailed conflict check with additional case information
        
        Args:
            case_data: Complete case data including contact info, addresses, etc.
            firm_id: Current firm ID
            db: Database session
            
        Returns:
            Enhanced conflict check results
        """
        # Start with basic name conflict check
        basic_conflicts = await self.check_conflicts(
            case_data.get("applicant_name", ""),
            case_data.get("respondent_name", ""),
            firm_id,
            db
        )
        
        # Enhanced checks with additional data
        enhanced_conflicts = []
        
        # Check email conflicts
        if case_data.get("applicant_email") or case_data.get("respondent_email"):
            email_conflicts = await self._check_email_conflicts(case_data, firm_id, db)
            enhanced_conflicts.extend(email_conflicts)
        
        # Check phone number conflicts
        if case_data.get("applicant_phone") or case_data.get("respondent_phone"):
            phone_conflicts = await self._check_phone_conflicts(case_data, firm_id, db)
            enhanced_conflicts.extend(phone_conflicts)
        
        # Check address conflicts
        if case_data.get("applicant_address") or case_data.get("respondent_address"):
            address_conflicts = await self._check_address_conflicts(case_data, firm_id, db)
            enhanced_conflicts.extend(address_conflicts)
        
        # Merge results
        all_conflicts = basic_conflicts["conflicts"] + enhanced_conflicts
        
        return {
            "has_conflicts": len(all_conflicts) > 0,
            "conflicts": all_conflicts,
            "warnings": basic_conflicts["warnings"],
            "recommendations": self._generate_conflict_recommendations(all_conflicts),
            "confidence_score": min([c.get("confidence", 1.0) for c in all_conflicts]) if all_conflicts else 1.0,
            "enhanced_check": True
        }
    
    async def _check_exact_name_conflicts(self, applicant_name: str, respondent_name: str,
                                        firm_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for exact name matches in existing cases"""
        conflicts = []
        
        # Normalize names for comparison
        applicant_normalized = self._normalize_name(applicant_name)
        respondent_normalized = self._normalize_name(respondent_name)
        
        # Query existing cases for exact matches
        existing_cases = db.query(Case).filter(
            Case.firm_id == firm_id,
            Case.status.in_([CaseStatus.ACTIVE, CaseStatus.ON_HOLD]),
            or_(
                # Applicant appears in any role in existing cases
                func.lower(Case.title).contains(applicant_normalized.lower()),
                func.lower(Case.opposing_party_name).contains(applicant_normalized.lower()),
                # Respondent appears in any role in existing cases
                func.lower(Case.title).contains(respondent_normalized.lower()),
                func.lower(Case.opposing_party_name).contains(respondent_normalized.lower())
            )
        ).all()
        
        for case in existing_cases:
            # Check if this represents a genuine conflict
            conflict_type = self._determine_conflict_type(
                applicant_name, respondent_name, case
            )
            
            if conflict_type:
                conflicts.append({
                    "type": "exact_match",
                    "conflict_type": conflict_type,
                    "existing_case_id": str(case.id),
                    "existing_case_number": case.case_number,
                    "existing_case_title": case.title,
                    "conflicted_party": self._identify_conflicted_party(
                        applicant_name, respondent_name, case
                    ),
                    "confidence": 1.0,
                    "severity": "high",
                    "recommendation": "Manual review required before proceeding"
                })
        
        return conflicts
    
    async def _check_similar_name_conflicts(self, applicant_name: str, respondent_name: str,
                                          firm_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for similar name matches using fuzzy matching"""
        conflicts = []
        
        # Get all active cases for similarity comparison
        active_cases = db.query(Case).filter(
            Case.firm_id == firm_id,
            Case.status.in_([CaseStatus.ACTIVE, CaseStatus.ON_HOLD])
        ).all()
        
        for case in active_cases:
            # Extract names from case title and opposing party
            case_names = self._extract_names_from_case(case)
            
            for case_name in case_names:
                # Check similarity with applicant
                applicant_similarity = self._calculate_name_similarity(applicant_name, case_name)
                if applicant_similarity >= self.fuzzy_match_threshold:
                    conflicts.append({
                        "type": "similar_match",
                        "conflict_type": "potential_same_party",
                        "existing_case_id": str(case.id),
                        "existing_case_number": case.case_number,
                        "existing_case_title": case.title,
                        "conflicted_party": applicant_name,
                        "similar_name": case_name,
                        "similarity_score": applicant_similarity,
                        "confidence": applicant_similarity,
                        "severity": "medium" if applicant_similarity > 0.9 else "low",
                        "recommendation": "Verify if this is the same person"
                    })
                
                # Check similarity with respondent
                respondent_similarity = self._calculate_name_similarity(respondent_name, case_name)
                if respondent_similarity >= self.fuzzy_match_threshold:
                    conflicts.append({
                        "type": "similar_match",
                        "conflict_type": "potential_same_party",
                        "existing_case_id": str(case.id),
                        "existing_case_number": case.case_number,
                        "existing_case_title": case.title,
                        "conflicted_party": respondent_name,
                        "similar_name": case_name,
                        "similarity_score": respondent_similarity,
                        "confidence": respondent_similarity,
                        "severity": "medium" if respondent_similarity > 0.9 else "low",
                        "recommendation": "Verify if this is the same person"
                    })
        
        return conflicts
    
    async def _check_reversed_party_conflicts(self, applicant_name: str, respondent_name: str,
                                            firm_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for cases where parties have reversed roles"""
        conflicts = []
        
        # Look for cases where current applicant was respondent or vice versa
        existing_cases = db.query(Case).filter(
            Case.firm_id == firm_id,
            Case.status.in_([CaseStatus.ACTIVE, CaseStatus.ON_HOLD])
        ).all()
        
        for case in existing_cases:
            case_names = self._extract_names_from_case(case)
            
            # Check if applicant and respondent are swapped
            if (self._names_match(applicant_name, case_names) and 
                self._names_match(respondent_name, case_names)):
                
                conflicts.append({
                    "type": "reversed_parties",
                    "conflict_type": "role_reversal",
                    "existing_case_id": str(case.id),
                    "existing_case_number": case.case_number,
                    "existing_case_title": case.title,
                    "conflicted_party": f"{applicant_name} and {respondent_name}",
                    "confidence": 0.9,
                    "severity": "high",
                    "recommendation": "Check if this is a related matter or role reversal"
                })
        
        return conflicts
    
    async def _check_email_conflicts(self, case_data: Dict[str, Any], 
                                   firm_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for email address conflicts"""
        conflicts = []
        
        # In a real implementation, this would check against a client database
        # For now, we'll simulate basic email conflict detection
        
        emails_to_check = []
        if case_data.get("applicant_email"):
            emails_to_check.append(("applicant", case_data["applicant_email"]))
        if case_data.get("respondent_email"):
            emails_to_check.append(("respondent", case_data["respondent_email"]))
        
        for role, email in emails_to_check:
            # Check against existing case metadata (if stored)
            # This is a placeholder - in production, check against client database
            if email in ["test@conflicttest.com", "conflict@example.com"]:
                conflicts.append({
                    "type": "email_conflict",
                    "conflict_type": "existing_client",
                    "conflicted_party": role,
                    "conflicted_email": email,
                    "confidence": 0.8,
                    "severity": "medium",
                    "recommendation": "Verify client relationship and potential conflicts"
                })
        
        return conflicts
    
    async def _check_phone_conflicts(self, case_data: Dict[str, Any], 
                                   firm_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for phone number conflicts"""
        conflicts = []
        
        # Similar to email conflicts - would check against client database
        # Placeholder implementation
        
        phones_to_check = []
        if case_data.get("applicant_phone"):
            phones_to_check.append(("applicant", case_data["applicant_phone"]))
        if case_data.get("respondent_phone"):
            phones_to_check.append(("respondent", case_data["respondent_phone"]))
        
        for role, phone in phones_to_check:
            # Normalize phone number
            normalized_phone = self._normalize_phone(phone)
            
            # Check against known conflict numbers (placeholder)
            if normalized_phone in ["0400000000", "0411111111"]:
                conflicts.append({
                    "type": "phone_conflict",
                    "conflict_type": "existing_client",
                    "conflicted_party": role,
                    "conflicted_phone": phone,
                    "confidence": 0.7,
                    "severity": "low",
                    "recommendation": "Verify if this is an existing client"
                })
        
        return conflicts
    
    async def _check_address_conflicts(self, case_data: Dict[str, Any], 
                                     firm_id: str, db: Session) -> List[Dict[str, Any]]:
        """Check for address conflicts"""
        conflicts = []
        
        # Check for same address conflicts (might indicate same person)
        applicant_address = case_data.get("applicant_address")
        respondent_address = case_data.get("respondent_address")
        
        if applicant_address and respondent_address:
            similarity = self._calculate_address_similarity(applicant_address, respondent_address)
            
            if similarity > 0.8:
                conflicts.append({
                    "type": "address_conflict",
                    "conflict_type": "same_address",
                    "conflicted_party": "applicant and respondent",
                    "similarity_score": similarity,
                    "confidence": similarity,
                    "severity": "medium",
                    "recommendation": "Verify if parties live at the same address - possible family relationship"
                })
        
        return conflicts
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        if not name:
            return ""
        
        # Convert to lowercase, remove extra spaces, handle common variations
        normalized = re.sub(r'\s+', ' ', name.strip().lower())
        
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(mr|mrs|ms|dr|prof)\.?\s+', '', normalized)
        normalized = re.sub(r'\s+(jr|sr|ii|iii)\.?$', '', normalized)
        
        return normalized
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        if not name1 or not name2:
            return 0.0
        
        # Normalize names
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)
        
        # Use sequence matcher for similarity
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between two addresses"""
        if not addr1 or not addr2:
            return 0.0
        
        # Normalize addresses
        norm1 = re.sub(r'\s+', ' ', addr1.strip().lower())
        norm2 = re.sub(r'\s+', ' ', addr2.strip().lower())
        
        # Remove common variations
        norm1 = re.sub(r'(street|st|avenue|ave|road|rd|drive|dr)', 'st', norm1)
        norm2 = re.sub(r'(street|st|avenue|ave|road|rd|drive|dr)', 'st', norm2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison"""
        if not phone:
            return ""
        
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', phone)
        
        # Handle Australian phone numbers
        if digits_only.startswith('61'):  # Country code
            digits_only = digits_only[2:]
        elif digits_only.startswith('0'):  # Local format
            digits_only = digits_only[1:]
        
        return digits_only
    
    def _extract_names_from_case(self, case: Case) -> List[str]:
        """Extract names from case title and opposing party field"""
        names = []
        
        if case.title:
            # Common patterns for family law case titles
            # "Smith v Jones", "Smith vs Jones", "Smith and Jones"
            vs_pattern = r'([^v]+)\s+v[s]?\s+([^v]+)'
            match = re.search(vs_pattern, case.title, re.IGNORECASE)
            if match:
                names.extend([match.group(1).strip(), match.group(2).strip()])
            else:
                # Split on common separators
                potential_names = re.split(r'\s+(?:and|&)\s+', case.title)
                names.extend([name.strip() for name in potential_names])
        
        if case.opposing_party_name:
            names.append(case.opposing_party_name.strip())
        
        # Clean and deduplicate names
        cleaned_names = []
        for name in names:
            cleaned = re.sub(r'[^\w\s]', '', name).strip()
            if len(cleaned) > 2 and cleaned not in cleaned_names:
                cleaned_names.append(cleaned)
        
        return cleaned_names
    
    def _names_match(self, target_name: str, case_names: List[str]) -> bool:
        """Check if target name matches any name in the list"""
        target_normalized = self._normalize_name(target_name)
        
        for case_name in case_names:
            case_normalized = self._normalize_name(case_name)
            similarity = SequenceMatcher(None, target_normalized, case_normalized).ratio()
            if similarity >= self.similarity_threshold:
                return True
        
        return False
    
    def _determine_conflict_type(self, applicant_name: str, respondent_name: str, 
                               case: Case) -> Optional[str]:
        """Determine the type of conflict based on the case"""
        
        case_names = self._extract_names_from_case(case)
        
        applicant_in_case = self._names_match(applicant_name, case_names)
        respondent_in_case = self._names_match(respondent_name, case_names)
        
        if applicant_in_case and respondent_in_case:
            return "same_parties"
        elif applicant_in_case:
            return "applicant_conflict"
        elif respondent_in_case:
            return "respondent_conflict"
        
        return None
    
    def _identify_conflicted_party(self, applicant_name: str, respondent_name: str, 
                                 case: Case) -> str:
        """Identify which party has the conflict"""
        
        case_names = self._extract_names_from_case(case)
        
        conflicts = []
        if self._names_match(applicant_name, case_names):
            conflicts.append(applicant_name)
        if self._names_match(respondent_name, case_names):
            conflicts.append(respondent_name)
        
        return " and ".join(conflicts) if conflicts else "Unknown"
    
    def _is_common_name(self, name: str) -> bool:
        """Check if name is very common (requires extra verification)"""
        common_names = [
            "smith", "jones", "williams", "brown", "taylor", "davis", "miller", 
            "wilson", "moore", "white", "martin", "thompson", "garcia", "martinez",
            "robinson", "clark", "rodriguez", "lewis", "lee", "walker", "hall",
            "allen", "young", "hernandez", "king", "wright", "lopez", "hill"
        ]
        
        normalized = self._normalize_name(name)
        return any(common in normalized.lower() for common in common_names)
    
    def _generate_conflict_recommendations(self, conflicts: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on conflicts found"""
        
        if not conflicts:
            return ["No conflicts detected - proceed with case creation"]
        
        recommendations = []
        
        # Count conflict types
        high_severity = len([c for c in conflicts if c.get("severity") == "high"])
        medium_severity = len([c for c in conflicts if c.get("severity") == "medium"])
        
        if high_severity > 0:
            recommendations.append("CRITICAL: High-severity conflicts detected - do not proceed without senior partner approval")
            recommendations.append("Conduct thorough conflict waiver analysis before proceeding")
            recommendations.append("Document all conflict checks and approvals in case file")
        
        if medium_severity > 0:
            recommendations.append("Medium-severity conflicts detected - verify client relationships")
            recommendations.append("Consider conflict waivers if proceeding is appropriate")
        
        # Specific recommendations based on conflict types
        conflict_types = [c.get("conflict_type") for c in conflicts]
        
        if "same_parties" in conflict_types:
            recommendations.append("Same parties found in existing case - check if this is a related matter")
        
        if "role_reversal" in conflict_types:
            recommendations.append("Party role reversal detected - ensure this is not a related cross-claim")
        
        if "similar_match" in conflict_types:
            recommendations.append("Similar names detected - verify party identities with additional information")
        
        return recommendations