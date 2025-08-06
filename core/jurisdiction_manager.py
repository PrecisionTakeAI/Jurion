"""
Multi-Jurisdiction Legal Analysis System
Enhanced Legal LLM with support for multiple legal jurisdictions
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class LegalJurisdiction(Enum):
    """Supported legal jurisdictions"""
    GENERAL = "general"
    UNITED_STATES = "united_states"
    AUSTRALIA = "australia"
    UNITED_KINGDOM = "united_kingdom"
    CANADA = "canada"

class LegalSystem(Enum):
    """Types of legal systems"""
    COMMON_LAW = "common_law"
    CIVIL_LAW = "civil_law"
    MIXED = "mixed"

@dataclass
class JurisdictionInfo:
    """Information about a legal jurisdiction"""
    name: str
    code: str
    legal_system: LegalSystem
    primary_language: str
    currency: str
    court_system: List[str]
    regulatory_bodies: List[str]
    primary_legislation: List[str]
    practice_areas: Dict[str, Dict[str, Any]]

class JurisdictionManager:
    """Manages legal jurisdictions and their specific requirements"""
    
    def __init__(self):
        self.jurisdictions = self._initialize_jurisdictions()
        self.default_jurisdiction = LegalJurisdiction.UNITED_STATES
    
    def _initialize_jurisdictions(self) -> Dict[LegalJurisdiction, JurisdictionInfo]:
        """Initialize all supported jurisdictions with their legal frameworks"""
        
        jurisdictions = {}
        
        # United States
        jurisdictions[LegalJurisdiction.UNITED_STATES] = JurisdictionInfo(
            name="United States",
            code="US",
            legal_system=LegalSystem.COMMON_LAW,
            primary_language="English",
            currency="USD",
            court_system=[
                "Supreme Court",
                "Federal Courts of Appeals",
                "Federal District Courts",
                "State Supreme Courts",
                "State Courts of Appeals",
                "State Trial Courts"
            ],
            regulatory_bodies=[
                "SEC", "FTC", "FDA", "EPA", "OSHA", "FCC", "CFTC"
            ],
            primary_legislation=[
                "US Constitution",
                "Federal Statutes",
                "Code of Federal Regulations",
                "State Constitutions",
                "State Statutes"
            ],
            practice_areas={
                "corporate": {
                    "primary_law": "Delaware General Corporation Law",
                    "key_regulations": ["Securities Act 1933", "Securities Exchange Act 1934"],
                    "regulatory_body": "SEC"
                },
                "family": {
                    "primary_law": "State Family Codes",
                    "key_concepts": ["no_fault_divorce", "best_interests_of_child"],
                    "court": "Family Court"
                },
                "criminal": {
                    "primary_law": "Federal Criminal Code",
                    "key_concepts": ["miranda_rights", "due_process"],
                    "court": "Criminal Court"
                }
            }
        )
        
        # Australia
        jurisdictions[LegalJurisdiction.AUSTRALIA] = JurisdictionInfo(
            name="Australia",
            code="AU",
            legal_system=LegalSystem.COMMON_LAW,
            primary_language="English",
            currency="AUD",
            court_system=[
                "High Court of Australia",
                "Federal Court of Australia",
                "Family Court of Australia",
                "State Supreme Courts",
                "State District Courts",
                "Local Courts"
            ],
            regulatory_bodies=[
                "ASIC", "ACCC", "AUSTRAC", "APRA", "ATO", "ACMA"
            ],
            primary_legislation=[
                "Australian Constitution",
                "Commonwealth Acts",
                "State Acts",
                "Regulations"
            ],
            practice_areas={
                "corporate": {
                    "primary_law": "Corporations Act 2001",
                    "key_regulations": ["Australian Securities and Investments Commission Act 2001"],
                    "regulatory_body": "ASIC"
                },
                "family": {
                    "primary_law": "Family Law Act 1975",
                    "key_concepts": ["best_interests_of_child", "property_settlement"],
                    "court": "Family Court of Australia"
                },
                "criminal": {
                    "primary_law": "Criminal Code Act 1995",
                    "key_concepts": ["burden_of_proof", "reasonable_doubt"],
                    "court": "State Criminal Courts"
                }
            }
        )
        
        # United Kingdom
        jurisdictions[LegalJurisdiction.UNITED_KINGDOM] = JurisdictionInfo(
            name="United Kingdom",
            code="UK",
            legal_system=LegalSystem.COMMON_LAW,
            primary_language="English",
            currency="GBP",
            court_system=[
                "Supreme Court of the United Kingdom",
                "Court of Appeal",
                "High Court",
                "Crown Court",
                "County Court",
                "Magistrates' Court"
            ],
            regulatory_bodies=[
                "FCA", "PRA", "CMA", "Ofcom", "HSE", "ICO"
            ],
            primary_legislation=[
                "Acts of Parliament",
                "Statutory Instruments",
                "Common Law",
                "European Retained Law"
            ],
            practice_areas={
                "corporate": {
                    "primary_law": "Companies Act 2006",
                    "key_regulations": ["Financial Services and Markets Act 2000"],
                    "regulatory_body": "FCA"
                },
                "family": {
                    "primary_law": "Matrimonial Causes Act 1973",
                    "key_concepts": ["welfare_of_child", "financial_provision"],
                    "court": "Family Court"
                },
                "criminal": {
                    "primary_law": "Criminal Justice Act 2003",
                    "key_concepts": ["beyond_reasonable_doubt", "right_to_silence"],
                    "court": "Crown Court"
                }
            }
        )
        
        # Canada
        jurisdictions[LegalJurisdiction.CANADA] = JurisdictionInfo(
            name="Canada",
            code="CA",
            legal_system=LegalSystem.MIXED,  # Common law + Civil law (Quebec)
            primary_language="English/French",
            currency="CAD",
            court_system=[
                "Supreme Court of Canada",
                "Federal Court of Appeal",
                "Federal Court",
                "Provincial Courts of Appeal",
                "Provincial Superior Courts",
                "Provincial Courts"
            ],
            regulatory_bodies=[
                "OSC", "CSA", "CRA", "CRTC", "Competition Bureau"
            ],
            primary_legislation=[
                "Constitution Act 1982",
                "Federal Statutes",
                "Provincial Statutes",
                "Regulations"
            ],
            practice_areas={
                "corporate": {
                    "primary_law": "Canada Business Corporations Act",
                    "key_regulations": ["Securities Acts (Provincial)"],
                    "regulatory_body": "Provincial Securities Commissions"
                },
                "family": {
                    "primary_law": "Divorce Act",
                    "key_concepts": ["best_interests_of_child", "spousal_support"],
                    "court": "Provincial Superior Court"
                },
                "criminal": {
                    "primary_law": "Criminal Code of Canada",
                    "key_concepts": ["charter_rights", "reasonable_doubt"],
                    "court": "Provincial Court"
                }
            }
        )
        
        return jurisdictions
    
    def get_jurisdiction_info(self, jurisdiction: LegalJurisdiction) -> JurisdictionInfo:
        """Get detailed information about a jurisdiction"""
        return self.jurisdictions.get(jurisdiction, self.jurisdictions[self.default_jurisdiction])
    
    def detect_jurisdiction(self, query_text: str, user_location: Optional[str] = None) -> LegalJurisdiction:
        """Detect the most appropriate jurisdiction for a legal query"""
        
        # Location-based detection
        if user_location:
            location_lower = user_location.lower()
            if any(term in location_lower for term in ["australia", "australian", "au", "sydney", "melbourne"]):
                return LegalJurisdiction.AUSTRALIA
            elif any(term in location_lower for term in ["uk", "united kingdom", "britain", "england", "london"]):
                return LegalJurisdiction.UNITED_KINGDOM
            elif any(term in location_lower for term in ["canada", "canadian", "toronto", "vancouver"]):
                return LegalJurisdiction.CANADA
            elif any(term in location_lower for term in ["usa", "us", "united states", "america"]):
                return LegalJurisdiction.UNITED_STATES
        
        # Content-based detection
        query_lower = query_text.lower()
        
        # Australian indicators
        australian_terms = [
            "asic", "accc", "corporations act", "family court of australia",
            "high court of australia", "australian constitution", "ato"
        ]
        if any(term in query_lower for term in australian_terms):
            return LegalJurisdiction.AUSTRALIA
        
        # UK indicators
        uk_terms = [
            "companies act 2006", "fca", "court of appeal", "crown court",
            "acts of parliament", "solicitor", "barrister"
        ]
        if any(term in query_lower for term in uk_terms):
            return LegalJurisdiction.UNITED_KINGDOM
        
        # Canadian indicators
        canadian_terms = [
            "supreme court of canada", "charter", "criminal code of canada",
            "divorce act", "provincial court"
        ]
        if any(term in query_lower for term in canadian_terms):
            return LegalJurisdiction.CANADA
        
        # US indicators (default)
        us_terms = [
            "sec", "ftc", "federal court", "supreme court", "constitution",
            "delaware", "securities act"
        ]
        if any(term in query_lower for term in us_terms):
            return LegalJurisdiction.UNITED_STATES
        
        # Default to US if no clear indicators
        return self.default_jurisdiction
    
    def get_jurisdiction_specific_prompt(self, jurisdiction: LegalJurisdiction, practice_area: str) -> str:
        """Generate jurisdiction-specific prompts for legal analysis"""
        
        jurisdiction_info = self.get_jurisdiction_info(jurisdiction)
        practice_info = jurisdiction_info.practice_areas.get(practice_area, {})
        
        prompt = f"""
You are a specialized AI legal assistant for {jurisdiction_info.name} law.

JURISDICTION CONTEXT:
- Legal System: {jurisdiction_info.legal_system.value}
- Primary Language: {jurisdiction_info.primary_language}
- Court System: {', '.join(jurisdiction_info.court_system[:3])}
- Key Regulatory Bodies: {', '.join(jurisdiction_info.regulatory_bodies[:3])}

PRACTICE AREA: {practice_area.title()}
"""
        
        if practice_info:
            prompt += f"""
RELEVANT LEGISLATION:
- Primary Law: {practice_info.get('primary_law', 'N/A')}
- Key Regulations: {practice_info.get('key_regulations', ['N/A'])}
- Regulatory Body: {practice_info.get('regulatory_body', 'N/A')}
- Relevant Court: {practice_info.get('court', 'N/A')}
"""
        
        prompt += f"""
ANALYSIS REQUIREMENTS:
1. Base your analysis strictly on {jurisdiction_info.name} law and legal principles
2. Reference appropriate {jurisdiction_info.name} legislation, case law, and regulations
3. Consider {jurisdiction_info.name} court procedures and legal precedents
4. Include relevant {jurisdiction_info.name} regulatory requirements
5. Specify that this analysis applies to {jurisdiction_info.name} law only
6. Note any significant differences from other jurisdictions if relevant

DISCLAIMERS:
- This analysis is based on {jurisdiction_info.name} law as of the current date
- Laws may vary between states/provinces within {jurisdiction_info.name}
- This is not legal advice and should not replace consultation with a qualified {jurisdiction_info.name} lawyer
- Legal requirements may have changed since the last update

Please provide a comprehensive legal analysis based on {jurisdiction_info.name} law.
"""
        
        return prompt
    
    def get_available_jurisdictions(self) -> List[Dict[str, str]]:
        """Get list of available jurisdictions for UI display"""
        return [
            {
                "code": jurisdiction.value,
                "name": info.name,
                "flag": self._get_flag_emoji(jurisdiction)
            }
            for jurisdiction, info in self.jurisdictions.items()
        ]
    
    def _get_flag_emoji(self, jurisdiction: LegalJurisdiction) -> str:
        """Get flag emoji for jurisdiction"""
        flag_map = {
            LegalJurisdiction.UNITED_STATES: "🇺🇸",
            LegalJurisdiction.AUSTRALIA: "🇦🇺",
            LegalJurisdiction.UNITED_KINGDOM: "🇬🇧",
            LegalJurisdiction.CANADA: "🇨🇦"
        }
        return flag_map.get(jurisdiction, "🌍")
    
    def validate_jurisdiction_compatibility(self, jurisdiction: LegalJurisdiction, practice_area: str) -> bool:
        """Check if a practice area is supported in the given jurisdiction"""
        jurisdiction_info = self.get_jurisdiction_info(jurisdiction)
        return practice_area in jurisdiction_info.practice_areas
    
    def get_jurisdiction_comparison(self, jurisdictions: List[LegalJurisdiction], practice_area: str) -> Dict[str, Any]:
        """Compare legal approaches across multiple jurisdictions"""
        comparison = {
            "practice_area": practice_area,
            "jurisdictions": {},
            "common_principles": [],
            "key_differences": []
        }
        
        for jurisdiction in jurisdictions:
            jurisdiction_info = self.get_jurisdiction_info(jurisdiction)
            practice_info = jurisdiction_info.practice_areas.get(practice_area, {})
            
            comparison["jurisdictions"][jurisdiction.value] = {
                "name": jurisdiction_info.name,
                "legal_system": jurisdiction_info.legal_system.value,
                "primary_law": practice_info.get("primary_law", "N/A"),
                "regulatory_body": practice_info.get("regulatory_body", "N/A"),
                "key_concepts": practice_info.get("key_concepts", [])
            }
        
        return comparison

# Export the main classes
__all__ = [
    'LegalJurisdiction',
    'LegalSystem', 
    'JurisdictionInfo',
    'JurisdictionManager'
]

