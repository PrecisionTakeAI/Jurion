"""
AI Service for multi-LLM integration and legal intelligence
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum
import openai
from groq import Groq
import requests
from datetime import datetime

from ..models import AIInteraction, Case, Document
from ..models.enums import AIInteractionType, AustralianFamilyCaseType, CourtSystem

class LLMProvider(str, Enum):
    """Available LLM providers"""
    OPENAI = "openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

class AIService:
    """Multi-LLM AI service for legal intelligence"""
    
    def __init__(self):
        self.openai_client = None
        self.groq_client = None
        
        # Initialize OpenAI
        if os.getenv("OPENAI_API_KEY"):
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.openai_client = openai
        
        # Initialize Groq
        if os.getenv("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    async def suggest_case_type(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest case type based on initial description
        
        Args:
            description: User description of the legal matter
            context: Additional context (children involved, assets, etc.)
            
        Returns:
            Dict with suggested case type, confidence, and reasoning
        """
        prompt = self._build_case_type_prompt(description, context)
        
        try:
            # Try Groq first (faster and cost-effective)
            if self.groq_client:
                response = await self._query_groq(prompt, "case_type_suggestion")
            elif self.openai_client:
                response = await self._query_openai(prompt, "case_type_suggestion")
            else:
                # Fallback to rule-based suggestion
                response = self._rule_based_case_type_suggestion(description, context)
            
            return self._parse_case_type_response(response)
            
        except Exception as e:
            # Fallback to rule-based if AI fails
            return self._rule_based_case_type_suggestion(description, context)
    
    async def analyze_case_complexity(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze case complexity and provide recommendations
        
        Args:
            case_data: Complete case information
            
        Returns:
            Dict with complexity analysis and recommendations
        """
        prompt = self._build_complexity_analysis_prompt(case_data)
        
        try:
            if self.groq_client:
                response = await self._query_groq(prompt, "complexity_analysis")
            elif self.openai_client:
                response = await self._query_openai(prompt, "complexity_analysis")
            else:
                response = self._rule_based_complexity_analysis(case_data)
            
            return self._parse_complexity_response(response)
            
        except Exception as e:
            return self._rule_based_complexity_analysis(case_data)
    
    async def suggest_required_documents(self, case_type: AustralianFamilyCaseType, 
                                       case_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Suggest required documents based on case type and details
        
        Args:
            case_type: Type of family law case
            case_details: Specific case details
            
        Returns:
            List of required documents with priorities
        """
        prompt = self._build_document_suggestion_prompt(case_type, case_details)
        
        try:
            if self.groq_client:
                response = await self._query_groq(prompt, "document_suggestion")
            elif self.openai_client:
                response = await self._query_openai(prompt, "document_suggestion")
            else:
                response = self._rule_based_document_suggestions(case_type, case_details)
            
            return self._parse_document_suggestions(response)
            
        except Exception as e:
            return self._rule_based_document_suggestions(case_type, case_details)
    
    async def validate_case_information(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate case information for completeness and consistency
        
        Args:
            case_data: Case information to validate
            
        Returns:
            Dict with validation results and suggestions
        """
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "completeness_score": 0.0
        }
        
        # Required field validation
        required_fields = self._get_required_fields(case_data.get('case_type'))
        missing_fields = []
        
        for field in required_fields:
            if not case_data.get(field):
                missing_fields.append(field)
                validation_results["errors"].append(f"Missing required field: {field}")
        
        # Consistency checks
        consistency_issues = self._check_consistency(case_data)
        validation_results["warnings"].extend(consistency_issues)
        
        # Calculate completeness score
        total_fields = len(required_fields) + len(self._get_optional_fields(case_data.get('case_type')))
        completed_fields = sum(1 for field in required_fields + self._get_optional_fields(case_data.get('case_type')) 
                              if case_data.get(field))
        validation_results["completeness_score"] = completed_fields / total_fields if total_fields > 0 else 0
        
        # Generate AI suggestions if available
        if self.groq_client or self.openai_client:
            try:
                ai_suggestions = await self._get_ai_validation_suggestions(case_data, validation_results)
                validation_results["suggestions"].extend(ai_suggestions)
            except Exception:
                pass  # Continue without AI suggestions
        
        validation_results["is_valid"] = len(validation_results["errors"]) == 0
        return validation_results
    
    async def generate_case_summary(self, case_data: Dict[str, Any]) -> str:
        """
        Generate a comprehensive case summary
        
        Args:
            case_data: Complete case information
            
        Returns:
            Generated case summary
        """
        prompt = self._build_case_summary_prompt(case_data)
        
        try:
            if self.groq_client:
                response = await self._query_groq(prompt, "case_summary")
                return response.get("content", "")
            elif self.openai_client:
                response = await self._query_openai(prompt, "case_summary")
                return response.get("content", "")
            else:
                return self._rule_based_case_summary(case_data)
                
        except Exception as e:
            return self._rule_based_case_summary(case_data)
    
    async def _query_groq(self, prompt: str, interaction_type: str) -> Dict[str, Any]:
        """Query Groq API"""
        try:
            completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert Australian family lawyer providing precise legal analysis."},
                    {"role": "user", "content": prompt}
                ],
                model="mixtral-8x7b-32768",
                temperature=0.1,
                max_tokens=2000
            )
            
            return {
                "content": completion.choices[0].message.content,
                "tokens_used": completion.usage.total_tokens,
                "model": "mixtral-8x7b-32768",
                "provider": "groq"
            }
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")
    
    async def _query_openai(self, prompt: str, interaction_type: str) -> Dict[str, Any]:
        """Query OpenAI API"""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert Australian family lawyer providing precise legal analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            return {
                "content": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "model": "gpt-4",
                "provider": "openai"
            }
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _build_case_type_prompt(self, description: str, context: Dict[str, Any]) -> str:
        """Build prompt for case type suggestion"""
        return f"""
        Analyze this family law matter and suggest the most appropriate case type from Australian family law:
        
        Description: {description}
        
        Additional Context:
        - Children involved: {context.get('children_involved', 'Unknown')}
        - Property/Assets: {context.get('assets_involved', 'Unknown')}
        - Current relationship status: {context.get('relationship_status', 'Unknown')}
        - Urgency: {context.get('urgency', 'Normal')}
        
        Available case types:
        - divorce
        - property_settlement
        - child_custody
        - parenting_orders
        - child_support
        - spousal_maintenance
        - de_facto_separation
        - domestic_violence
        
        Respond in JSON format:
        {{
            "suggested_case_type": "case_type",
            "confidence": 0.95,
            "reasoning": "Explanation of why this case type fits",
            "alternative_types": ["other_possible_types"],
            "required_court": "federal_circuit_family_court"
        }}
        """
    
    def _build_complexity_analysis_prompt(self, case_data: Dict[str, Any]) -> str:
        """Build prompt for complexity analysis"""
        return f"""
        Analyze the complexity of this Australian family law case:
        
        Case Type: {case_data.get('case_type')}
        Estimated Value: ${case_data.get('estimated_value', 0):,}
        Children Involved: {len(case_data.get('children', []))} children
        Property Types: {len(case_data.get('assets', []))} different asset types
        Special Circumstances: {case_data.get('special_circumstances', 'None')}
        
        Provide analysis in JSON format:
        {{
            "complexity_level": "low|medium|high|very_high",
            "estimated_duration_months": 6,
            "key_challenges": ["challenge1", "challenge2"],
            "recommended_resources": ["senior_lawyer", "financial_expert"],
            "priority_level": "high",
            "estimated_cost_range": {{"min": 5000, "max": 15000}}
        }}
        """
    
    def _build_document_suggestion_prompt(self, case_type: AustralianFamilyCaseType, 
                                        case_details: Dict[str, Any]) -> str:
        """Build prompt for document suggestions"""
        return f"""
        Suggest required documents for this Australian family law case:
        
        Case Type: {case_type.value}
        Case Details: {json.dumps(case_details, default=str)}
        
        Provide suggestions in JSON format:
        {{
            "required_documents": [
                {{
                    "document_name": "Financial Statement",
                    "priority": "high",
                    "description": "Complete financial disclosure",
                    "deadline_days": 60,
                    "form_number": "Form 13"
                }}
            ],
            "optional_documents": [
                {{
                    "document_name": "Property Valuation",
                    "priority": "medium",
                    "description": "Professional property valuation",
                    "recommended_timing": "early"
                }}
            ]
        }}
        """
    
    def _build_case_summary_prompt(self, case_data: Dict[str, Any]) -> str:
        """Build prompt for case summary generation"""
        return f"""
        Generate a professional case summary for this Australian family law matter:
        
        {json.dumps(case_data, default=str, indent=2)}
        
        Create a comprehensive summary including:
        1. Case overview and key parties
        2. Main legal issues
        3. Financial and property matters
        4. Children and parenting arrangements (if applicable)
        5. Next steps and key deadlines
        6. Risk assessment and recommendations
        
        Write in professional legal language suitable for court documents and client communications.
        """
    
    def _rule_based_case_type_suggestion(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based fallback for case type suggestion"""
        description_lower = description.lower()
        
        # Simple keyword matching
        if any(word in description_lower for word in ['divorce', 'dissolution', 'end marriage']):
            return {
                "suggested_case_type": "divorce",
                "confidence": 0.8,
                "reasoning": "Keywords indicate divorce proceedings",
                "alternative_types": ["property_settlement"],
                "required_court": "federal_circuit_family_court"
            }
        elif any(word in description_lower for word in ['property', 'assets', 'settlement']):
            return {
                "suggested_case_type": "property_settlement", 
                "confidence": 0.7,
                "reasoning": "Keywords indicate property settlement",
                "alternative_types": ["divorce"],
                "required_court": "federal_circuit_family_court"
            }
        elif any(word in description_lower for word in ['child', 'custody', 'parenting']):
            return {
                "suggested_case_type": "child_custody",
                "confidence": 0.8,
                "reasoning": "Keywords indicate child custody matters",
                "alternative_types": ["parenting_orders"],
                "required_court": "federal_circuit_family_court"
            }
        else:
            return {
                "suggested_case_type": "divorce",
                "confidence": 0.5,
                "reasoning": "Default suggestion - requires manual review",
                "alternative_types": ["property_settlement", "child_custody"],
                "required_court": "federal_circuit_family_court"
            }
    
    def _rule_based_complexity_analysis(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based complexity analysis"""
        complexity_score = 0
        
        # Scoring factors
        if case_data.get('estimated_value', 0) > 1000000:
            complexity_score += 3
        elif case_data.get('estimated_value', 0) > 500000:
            complexity_score += 2
        elif case_data.get('estimated_value', 0) > 100000:
            complexity_score += 1
        
        if len(case_data.get('children', [])) > 2:
            complexity_score += 2
        elif len(case_data.get('children', [])) > 0:
            complexity_score += 1
        
        if len(case_data.get('assets', [])) > 5:
            complexity_score += 2
        elif len(case_data.get('assets', [])) > 2:
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score >= 6:
            complexity_level = "very_high"
            duration = 18
        elif complexity_score >= 4:
            complexity_level = "high"
            duration = 12
        elif complexity_score >= 2:
            complexity_level = "medium"
            duration = 8
        else:
            complexity_level = "low"
            duration = 4
        
        return {
            "complexity_level": complexity_level,
            "estimated_duration_months": duration,
            "key_challenges": ["Document complexity", "Multiple parties"],
            "recommended_resources": ["senior_lawyer"] if complexity_score >= 4 else ["lawyer"],
            "priority_level": "high" if complexity_score >= 4 else "medium",
            "estimated_cost_range": {"min": complexity_score * 2000, "max": complexity_score * 5000}
        }
    
    def _rule_based_document_suggestions(self, case_type: AustralianFamilyCaseType, 
                                       case_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rule-based document suggestions"""
        base_documents = [
            {
                "document_name": "Application for Divorce",
                "priority": "high",
                "description": "Formal divorce application",
                "deadline_days": 30,
                "form_number": "Form 1"
            }
        ]
        
        if case_type == AustralianFamilyCaseType.PROPERTY_SETTLEMENT:
            base_documents.extend([
                {
                    "document_name": "Financial Statement",
                    "priority": "high", 
                    "description": "Complete financial disclosure",
                    "deadline_days": 60,
                    "form_number": "Form 13"
                },
                {
                    "document_name": "Property Valuation",
                    "priority": "medium",
                    "description": "Professional property valuation",
                    "recommended_timing": "early"
                }
            ])
        
        return base_documents
    
    def _rule_based_case_summary(self, case_data: Dict[str, Any]) -> str:
        """Rule-based case summary generation"""
        case_type = case_data.get('case_type', 'Unknown')
        parties = f"{case_data.get('applicant_name', 'Applicant')} vs {case_data.get('respondent_name', 'Respondent')}"
        
        summary = f"""
        CASE SUMMARY
        
        Case Type: {case_type.replace('_', ' ').title()}
        Parties: {parties}
        Case Number: {case_data.get('case_number', 'TBD')}
        
        Overview: This is a {case_type.replace('_', ' ')} matter involving the above parties.
        
        Key Issues:
        - Property settlement and asset division
        - Parenting arrangements (if children involved)
        - Financial support obligations
        
        Next Steps:
        - Complete document collection
        - File formal application
        - Serve papers on respondent
        - Attend mandatory mediation
        
        This summary was generated automatically and should be reviewed by a qualified lawyer.
        """
        
        return summary.strip()
    
    def _parse_case_type_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response for case type suggestion"""
        try:
            content = response.get("content", "")
            # Try to parse JSON from response
            if "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback parsing
        return {
            "suggested_case_type": "divorce",
            "confidence": 0.5,
            "reasoning": "Could not parse AI response",
            "alternative_types": [],
            "required_court": "federal_circuit_family_court"
        }
    
    def _parse_complexity_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response for complexity analysis"""
        try:
            content = response.get("content", "")
            if "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        return {
            "complexity_level": "medium",
            "estimated_duration_months": 6,
            "key_challenges": ["Unknown complexity"],
            "recommended_resources": ["lawyer"],
            "priority_level": "medium",
            "estimated_cost_range": {"min": 5000, "max": 15000}
        }
    
    def _parse_document_suggestions(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse AI response for document suggestions"""
        try:
            content = response.get("content", "")
            if "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
                parsed = json.loads(json_str)
                return parsed.get("required_documents", []) + parsed.get("optional_documents", [])
        except:
            pass
        
        return []
    
    def _get_required_fields(self, case_type: str) -> List[str]:
        """Get required fields for case type"""
        base_fields = ['case_type', 'title', 'applicant_name', 'respondent_name']
        
        if case_type == 'property_settlement':
            base_fields.extend(['estimated_value', 'property_details'])
        elif case_type in ['child_custody', 'parenting_orders']:
            base_fields.extend(['children_details'])
        
        return base_fields
    
    def _get_optional_fields(self, case_type: str) -> List[str]:
        """Get optional fields for case type"""
        return ['description', 'special_circumstances', 'urgency_level']
    
    def _check_consistency(self, case_data: Dict[str, Any]) -> List[str]:
        """Check for consistency issues in case data"""
        issues = []
        
        # Check if children details exist when case type requires them
        if case_data.get('case_type') in ['child_custody', 'parenting_orders']:
            if not case_data.get('children_details'):
                issues.append("Children details required for this case type")
        
        # Check estimated value consistency
        if case_data.get('estimated_value', 0) > 0 and case_data.get('case_type') not in ['property_settlement', 'divorce']:
            issues.append("Estimated value may not be relevant for this case type")
        
        return issues
    
    async def _get_ai_validation_suggestions(self, case_data: Dict[str, Any], 
                                           validation_results: Dict[str, Any]) -> List[str]:
        """Get AI suggestions for improving case data"""
        # This would make an AI call to get improvement suggestions
        # For now, return rule-based suggestions
        suggestions = []
        
        if validation_results["completeness_score"] < 0.7:
            suggestions.append("Consider adding more details to improve case completeness")
        
        if len(validation_results["errors"]) > 0:
            suggestions.append("Review and complete all required fields before proceeding")
        
        return suggestions