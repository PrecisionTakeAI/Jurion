"""
Adaptive Enhanced Legal LLM Engine with Cost Optimization
Handles intelligent legal query processing with multi-LLM support, jurisdiction awareness, and compliance logging.
Automatically uses PostgreSQL database when available, falls back to legacy processing.
Includes Claude Max Plan detection and cost optimization for external API usage.
Maintains full backward compatibility with existing interfaces.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

# Performance optimization: Dependency caching
_dependency_cache = {}
_is_production = os.getenv('ENVIRONMENT', '').lower() == 'production'

def check_langchain_availability():
    """Cached check for langchain_openai availability"""
    if 'langchain_openai' in _dependency_cache:
        return _dependency_cache['langchain_openai']
    
    try:
        import langchain_openai
        _dependency_cache['langchain_openai'] = True
        if not _is_production:
            logging.info("✅ langchain_openai available")
        return True
    except ImportError:
        _dependency_cache['langchain_openai'] = False
        if not _is_production:
            logging.info("LangChain not available - using alternative AI clients")
        return False

# Import API configuration and cost optimization
from .api_config import api_config, ProcessingMode, UserPlanType

# Import the new database-based LLM engine
try:
    from core.enhanced_llm_engine_db import (
        DatabaseLegalLLMEngine, EnhancedLegalQuery as DBEnhancedLegalQuery,
        EnhancedLegalResponse as DBEnhancedLegalResponse, LegalPracticeArea,
        InteractionType, AdviceClassification, ComplianceFlag
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    logging.info("Database LLM engine not available - using legacy AI clients (Groq direct API)")

# Import legacy LLM engine as fallback
from core.enhanced_llm_engine_legacy import (
    LegacyEnhancedLegalLLMEngine, EnhancedLegalQuery as LegacyEnhancedLegalQuery,
    EnhancedLegalResponse as LegacyEnhancedLegalResponse, LegalPracticeArea as LegacyLegalPracticeArea
)

# Import local LLM capabilities
try:
    from core.local_llm_adapter import EnhancedLocalLLMEngine
    LOCAL_LLM_AVAILABLE = True
except ImportError as e:
    LOCAL_LLM_AVAILABLE = False
    logging.warning(f"Local LLM adapter not available: {e}")

# Import jurisdiction manager
from .jurisdiction_manager import JurisdictionManager, LegalJurisdiction

# Export the appropriate classes based on availability
if DATABASE_AVAILABLE:
    # Use database classes when available
    EnhancedLegalQuery = DBEnhancedLegalQuery
    EnhancedLegalResponse = DBEnhancedLegalResponse
else:
    # Use legacy classes as fallback
    EnhancedLegalQuery = LegacyEnhancedLegalQuery
    EnhancedLegalResponse = LegacyEnhancedLegalResponse
    LegalPracticeArea = LegacyLegalPracticeArea

logger = logging.getLogger(__name__)

class EnhancedLegalLLMEngine:
    """
    Adaptive enhanced legal LLM engine for legal professionals with cost optimization.
    Automatically detects Claude Max Plan users and provides local processing benefits.
    Uses PostgreSQL database when available, falls back to legacy processing.
    Includes comprehensive API usage monitoring and cost controls.
    Maintains full backward compatibility with existing interfaces.
    """
    
    def __init__(self, api_key: Optional[str] = None, firm_id: str = None, user_id: str = None):
        """
        Initialize enhanced legal LLM engine with automatic backend selection and cost optimization
        
        Args:
            api_key: OpenAI API key (optional, can be loaded from environment)
            firm_id: Law firm ID for multi-tenant database mode
            user_id: Current user ID for audit trails in database mode
        """
        self.api_key = api_key
        self.firm_id = firm_id
        self.user_id = user_id
        self.api_config = api_config
        self.processing_mode = api_config.get_processing_mode()
        
        # Log user plan and processing mode for transparency
        logger.info(f"🔧 Initializing LLM Engine - Plan: {api_config.user_plan.value}, Mode: {self.processing_mode.value}")
        
        # Initialize local LLM adapter if available and preferred
        self.local_adapter = None
        if LOCAL_LLM_AVAILABLE and self._should_use_local_processing():
            try:
                self.local_adapter = EnhancedLocalLLMEngine()
                logger.info("✅ Local LLM adapter initialized for cost-free processing")
            except Exception as e:
                logger.warning(f"Failed to initialize local LLM adapter: {e}")
        
        # Determine which backend to use based on cost optimization
        self.backend = self._select_optimal_backend()
        self.is_database_mode = isinstance(self.backend, DatabaseLegalLLMEngine) if DATABASE_AVAILABLE else False
        
        # Log cost optimization recommendations
        recommendations = api_config.get_cost_optimization_recommendations()
        if recommendations:
            logger.info("💡 Cost Optimization Recommendations:")
            for rec in recommendations:
                logger.info(f"   {rec}")
    
    def _should_use_local_processing(self) -> bool:
        """Determine if local processing should be prioritized"""
        # Claude Max Plan users should get local processing by default
        if self.api_config.user_plan == UserPlanType.CLAUDE_MAX:
            return True
        
        # Local-only processing mode
        if self.processing_mode == ProcessingMode.LOCAL_ONLY:
            return True
        
        # Prefer local when configured
        if self.api_config.config['PREFER_LOCAL_LLMS'] and self.api_config.config['OLLAMA_AVAILABLE']:
            return True
        
        return False
    
    def _select_optimal_backend(self):
        """Select the optimal backend based on cost optimization and availability"""
        # For Claude Max Plan users in LOCAL_ONLY mode, prefer local adapter
        if (self.processing_mode == ProcessingMode.LOCAL_ONLY and 
            self.local_adapter and 
            self.api_config.user_plan == UserPlanType.CLAUDE_MAX):
            logger.info("🔒 Using local processing for Claude Max Plan user (cost-free)")
            return self.local_adapter
        
        # Check if external APIs should be used
        should_use_external = self.api_config.should_use_external_api('database' if self._should_use_database() else 'legacy')
        
        if not should_use_external:
            logger.info("💰 External API usage blocked by cost optimization - using local fallback")
            if self.local_adapter:
                return self.local_adapter
            else:
                logger.warning("⚠️ Local processing unavailable - using legacy mode without API calls")
                return LegacyEnhancedLegalLLMEngine(api_key=None)  # No API key to prevent external calls
        
        # Use database backend if available and appropriate
        if DATABASE_AVAILABLE and self._should_use_database():
            logger.info("🗄️ Using PostgreSQL database backend for AI interactions with compliance logging")
            return DatabaseLegalLLMEngine(
                api_key=self.api_key,
                firm_id=self.firm_id,
                user_id=self.user_id
            )
        else:
            logger.info("📋 Using legacy backend for AI interactions")
            return LegacyEnhancedLegalLLMEngine(api_key=self.api_key)
    
    def _should_use_database(self) -> bool:
        """Determine if database should be used based on environment and context"""
        # Use database if explicitly requested via environment variable
        if os.getenv('USE_DATABASE', '').lower() in ['true', '1', 'yes']:
            return True
        
        # Use database if firm_id is provided (multi-tenant context)
        if self.firm_id:
            return True
        
        # Use database if DATABASE_URL is configured
        if os.getenv('DATABASE_URL') or (
            os.getenv('DB_HOST') and os.getenv('DB_NAME') and os.getenv('DB_USER')
        ):
            return True
        
        # Default to legacy mode for backward compatibility
        return False
    
    def _determine_api_type(self) -> str:
        """Determine which API type is being used"""
        if self.local_adapter and self.backend == self.local_adapter:
            return 'local'
        elif self.is_database_mode:
            return 'openai'  # Database mode uses OpenAI
        else:
            return 'openai'  # Legacy mode also uses OpenAI
    
    def _should_process_query(self, api_type: str) -> bool:
        """Check if query should be processed based on cost optimization"""
        if api_type == 'local':
            return True  # Local processing is always allowed
        
        return self.api_config.should_use_external_api(api_type)
    
    def _estimate_query_cost(self, query: str, response: Any, api_type: str) -> float:
        """Estimate the cost of processing this query"""
        if api_type == 'local':
            return 0.0
        
        # Estimate token usage if not provided
        query_tokens = len(query.split()) * 1.3  # Rough token estimation
        response_tokens = len(str(response).split()) * 1.3 if response else 100
        
        # OpenAI GPT-4 pricing (approximate)
        if api_type == 'openai':
            input_cost = (query_tokens / 1000) * 0.03  # $0.03 per 1K input tokens
            output_cost = (response_tokens / 1000) * 0.06  # $0.06 per 1K output tokens
            return input_cost + output_cost
        
        # Groq pricing (much cheaper)
        elif api_type == 'groq':
            return (query_tokens + response_tokens) / 1000 * 0.0001  # Very rough estimate
        
        return 0.001  # Default small cost
    
    def _create_cost_blocked_response(self, query: str):
        """Create a response when query is blocked due to cost optimization"""
        message = f"""
🔒 **Query Blocked - Cost Optimization Active**

Your query has been blocked to prevent unexpected API charges.

**Current Settings:**
- User Plan: {self.api_config.user_plan.value}
- Processing Mode: {self.processing_mode.value}
- Cost Limit: ${self.api_config.config['MAX_API_COST_PER_HOUR']:.2f}/hour
- Current Usage: ${self.api_config.usage_stats.estimated_cost:.2f}

**Recommendations:**
{chr(10).join(self.api_config.get_cost_optimization_recommendations())}

**To process this query:**
1. Set USE_LOCAL_PROCESSING=true for cost-free local processing
2. Install Ollama for local LLM capabilities
3. Or increase MAX_API_COST_PER_HOUR if external APIs are needed

Your query: "{query[:100]}{'...' if len(query) > 100 else ''}"
        """
        
        # Create a simple response object
        if DATABASE_AVAILABLE:
            return DBEnhancedLegalResponse(
                legal_analysis=message,
                confidence_score=1.0,
                practice_area=LegalPracticeArea.GENERAL,
                jurisdiction=LegalJurisdiction.GENERAL,
                disclaimers=["Cost optimization active - query blocked"]
            )
        else:
            return LegacyEnhancedLegalResponse(
                legal_analysis=message,
                confidence_score=1.0,
                practice_area=LegacyLegalPracticeArea.GENERAL,
                jurisdiction=LegalJurisdiction.GENERAL,
                disclaimers=["Cost optimization active - query blocked"]
            )
    
    def _process_with_fallback(self, query: str, practice_area, jurisdiction, context, **kwargs) -> EnhancedLegalResponse:
        """Process query with fallback when database is not available"""
        try:
            # Use legacy backend as fallback
            if hasattr(self, 'legacy_backend'):
                response = self.legacy_backend.process_query(
                    query=query,
                    practice_area=practice_area,
                    jurisdiction=jurisdiction,
                    context=context
                )
                logger.info("Successfully used fallback processing")
                return response
            else:
                return self._create_error_response(query, "No fallback backend available", practice_area, jurisdiction, **kwargs)
        except Exception as e:
            logger.error(f"Fallback processing failed: {str(e)}")
            return self._create_error_response(query, str(e), practice_area, jurisdiction, **kwargs)
    
    def _process_with_legacy(self, query: str, practice_area, jurisdiction, context, **kwargs) -> EnhancedLegalResponse:
        """Process query with legacy backend"""
        try:
            # Create legacy backend instance if needed
            if not hasattr(self, 'legacy_backend'):
                self.legacy_backend = LegacyEnhancedLegalLLMEngine()
            
            response = self.legacy_backend.process_query(
                query=query,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                context=context
            )
            logger.info("Successfully used legacy processing")
            return response
        except Exception as e:
            logger.error(f"Legacy processing failed: {str(e)}")
            return self._create_error_response(query, str(e), practice_area, jurisdiction, **kwargs)
    
    def _create_error_response(self, query: str, error_msg: str, practice_area, jurisdiction, **kwargs) -> EnhancedLegalResponse:
        """Create structured error response"""
        # Convert practice_area and jurisdiction to strings if they're enums
        practice_area_str = practice_area.value if hasattr(practice_area, 'value') else str(practice_area)
        jurisdiction_str = jurisdiction.value if hasattr(jurisdiction, 'value') else str(jurisdiction)
        
        error_response = {
            "analysis": f"Error processing legal query: {error_msg}",
            "confidence": "Low",
            "lawyer_review_recommended": True,
            "legal_considerations": "Error occurred during legal analysis",
            "recommendations": ["Please consult with a qualified attorney"],
            "jurisdiction": jurisdiction_str,
            "practice_area": practice_area_str
        }
        
        # Return appropriate response type based on availability
        if DATABASE_AVAILABLE:
            return DBEnhancedLegalResponse(
                response=error_response["analysis"],
                confidence="Low",
                lawyer_review_recommended=True,
                legal_considerations=error_response["legal_considerations"],
                recommendations=error_response["recommendations"],
                jurisdiction=jurisdiction_str,
                practice_area=practice_area_str,
                query_id=None,
                processing_time=0.0,
                tokens_used=0
            )
        else:
            return LegacyEnhancedLegalResponse(
                response=error_response["analysis"],
                confidence="Low",
                lawyer_review_recommended=True,
                legal_considerations=error_response["legal_considerations"],
                recommendations=error_response["recommendations"],
                jurisdiction=jurisdiction_str,
                practice_area=practice_area_str
            )

    def _try_local_fallback(self, query: str, practice_area, jurisdiction, context, **kwargs):
        """Try to process query with local fallback if external API fails"""
        if self.local_adapter and self.local_adapter != self.backend:
            logger.info("🔄 Attempting local fallback after external API failure")
            try:
                return self.local_adapter.process_query(
                    query=query,
                    practice_area=practice_area,
                    jurisdiction=jurisdiction,
                    context=context,
                    **kwargs
                )
            except Exception as e:
                logger.error(f"Local fallback also failed: {e}")
        
        # Return error response if all options exhausted
        return self._create_error_response("All processing options failed")
    
    def _create_error_response(self, error_message: str):
        """Create an error response"""
        if DATABASE_AVAILABLE:
            return DBEnhancedLegalResponse(
                legal_analysis=f"Error: {error_message}",
                confidence_score=0.0,
                practice_area=LegalPracticeArea.GENERAL,
                jurisdiction=LegalJurisdiction.GENERAL,
                disclaimers=["Processing error occurred"]
            )
        else:
            return LegacyEnhancedLegalResponse(
                legal_analysis=f"Error: {error_message}",
                confidence_score=0.0,
                practice_area=LegacyLegalPracticeArea.GENERAL,
                jurisdiction=LegalJurisdiction.GENERAL,
                disclaimers=["Processing error occurred"]
            )

    # ==========================================
    # PROXY METHODS - Forward all calls to backend
    # ==========================================
    
    def process_query(
        self,
        query: str,
        practice_area: Union[str, LegalPracticeArea],
        jurisdiction: Union[str, LegalJurisdiction],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> EnhancedLegalResponse:
        """
        Process a legal query with enhanced features, compliance logging, and cost optimization
        Delegates to the appropriate backend based on user plan and cost settings
        """
        start_time = datetime.now()
        
        try:
            # Add debug logging
            logger.info(f"Processing legal query: {query[:100]}...")
            
            # Pre-process check for API usage
            api_type = self._determine_api_type()
            
            # Check if database is available
            if hasattr(self.backend, 'db_available'):
                if not self.backend.db_available:
                    logger.warning("Database backend not available, using fallback")
                    return self._process_with_fallback(query, practice_area, jurisdiction, context, **kwargs)
            
            # Log the query attempt for transparency
            logger.info(f"🔍 Processing legal query - Backend: {type(self.backend).__name__}, "
                       f"Plan: {self.api_config.user_plan.value}, API: {api_type}")
            
            # Check if this query should be processed based on cost optimization
            if not self._should_process_query(api_type):
                return self._create_cost_blocked_response(query)
            
            # Try database processing first
            try:
                if DATABASE_AVAILABLE and self._should_use_database():
                    logger.info("Using database backend for query processing")
                    response = self.backend.process_query(
                        query=query,
                        practice_area=practice_area, 
                        jurisdiction=jurisdiction,
                        context=context,
                        **kwargs
                    )
                else:
                    # Legacy mode uses standard parameters
                    logger.info("Using legacy backend for query processing")
                    response = self.backend.process_query(
                        query=query,
                        practice_area=practice_area,
                        jurisdiction=jurisdiction, 
                        context=context
                    )
                
            except Exception as db_error:
                logger.error(f"Database processing failed: {str(db_error)}")
                logger.info("Falling back to legacy processing")
                return self._process_with_legacy(query, practice_area, jurisdiction, context, **kwargs)
            
            # Calculate processing time and estimated cost
            processing_time = (datetime.now() - start_time).total_seconds()
            estimated_cost = self._estimate_query_cost(query, response, api_type)
            
            # Log API usage for monitoring
            self.api_config.log_api_usage(
                api_type=api_type,
                tokens_used=getattr(response, 'tokens_used', 0),
                estimated_cost=estimated_cost
            )
            
            # Add cost information to response if available
            if hasattr(response, '__dict__'):
                response.processing_cost = estimated_cost
                response.processing_time = processing_time
                response.api_type_used = api_type
                response.user_plan = self.api_config.user_plan.value
            
            logger.info(f"✅ Query processed successfully - Cost: ${estimated_cost:.4f}, Time: {processing_time:.2f}s")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in process_query: {str(e)}", exc_info=True)
            # Return structured error response
            return self._create_error_response(query, str(e), practice_area, jurisdiction, **kwargs)
    
    def get_practice_areas(self) -> List[str]:
        """Get list of supported practice areas"""
        if hasattr(self.backend, 'get_practice_areas'):
            return self.backend.get_practice_areas()
        else:
            # Default practice areas for legacy mode
            return [area.value for area in LegalPracticeArea]
    
    def query_documents(self, query: str, documents: List[Any]) -> Dict[str, Any]:
        """Query documents with proper error handling"""
        try:
            logger.info(f"Processing document query: {query[:100]}...")
            
            # Extract context from documents
            context = self._extract_relevant_context(documents, query)
            
            # Check for loan-specific queries
            if "loan" in query.lower() and "amount" in query.lower():
                # Extract loan amounts from documents
                loan_info = self._extract_loan_information(documents)
                
                # Format response
                return {
                    "analysis": self._format_loan_analysis(loan_info),
                    "confidence": "High" if loan_info else "Low",
                    "lawyer_review_recommended": False,
                    "legal_considerations": "This is a factual summary of loan documents",
                    "recommendations": ["Verify amounts against original documents"],
                    "jurisdiction": "Australia",
                    "practice_area": "Family"
                }
            
            # General document query processing
            return {
                "analysis": f"Document analysis for query: {query}",
                "confidence": "Medium",
                "lawyer_review_recommended": True,
                "legal_considerations": "Document analysis requires legal expertise",
                "recommendations": ["Review documents with qualified attorney"],
                "jurisdiction": "Australia",
                "practice_area": "General"
            }
                
        except Exception as e:
            logger.error(f"Document query error: {str(e)}", exc_info=True)
            # Return structured error response
            return {
                "analysis": "Unable to process document query at this time",
                "confidence": "Low",
                "lawyer_review_recommended": True,
                "legal_considerations": "Technical error prevented analysis",
                "recommendations": ["Please try again or contact support"],
                "jurisdiction": "Australia",
                "practice_area": "Family"
            }
    
    def _extract_relevant_context(self, documents: List[Any], query: str) -> str:
        """Extract relevant context from documents for query"""
        try:
            # Simple implementation - would be more sophisticated in production
            context_parts = []
            for doc in documents[:5]:  # Limit to first 5 documents
                if hasattr(doc, 'content'):
                    context_parts.append(doc.content[:500])  # First 500 chars
                elif isinstance(doc, dict) and 'content' in doc:
                    context_parts.append(str(doc['content'])[:500])
                elif isinstance(doc, str):
                    context_parts.append(doc[:500])
            
            return " ".join(context_parts)
        except Exception as e:
            logger.warning(f"Error extracting document context: {e}")
            return ""
    
    def _extract_loan_information(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract loan information from documents"""
        try:
            loan_info = {}
            
            # Simple pattern matching for loan amounts
            import re
            amount_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            
            for doc in documents:
                content = ""
                if hasattr(doc, 'content'):
                    content = doc.content
                elif isinstance(doc, dict) and 'content' in doc:
                    content = str(doc['content'])
                elif isinstance(doc, str):
                    content = doc
                
                # Look for loan-related amounts
                if "loan" in content.lower():
                    amounts = re.findall(amount_pattern, content)
                    if amounts:
                        loan_info['amounts'] = amounts
                        loan_info['found_in_document'] = True
            
            return loan_info
        except Exception as e:
            logger.warning(f"Error extracting loan information: {e}")
            return {}
    
    def _format_loan_analysis(self, loan_info: Dict[str, Any]) -> str:
        """Format loan information analysis"""
        try:
            if not loan_info or not loan_info.get('amounts'):
                return "No loan amounts could be identified in the provided documents."
            
            amounts = loan_info['amounts']
            if len(amounts) == 1:
                return f"One loan amount identified: ${amounts[0]}"
            else:
                amounts_str = ", ".join([f"${amt}" for amt in amounts])
                return f"Multiple loan amounts identified: {amounts_str}"
                
        except Exception as e:
            logger.warning(f"Error formatting loan analysis: {e}")
            return "Error formatting loan analysis"

    def get_query_types(self) -> List[str]:
        """Get list of supported query types"""
        if hasattr(self.backend, 'get_query_types'):
            return self.backend.get_query_types()
        else:
            # Default query types for legacy mode
            return [
                "general_legal_question", "document_review", "contract_analysis",
                "legal_research", "compliance_check", "risk_assessment"
            ]
    
    def get_jurisdictions(self) -> List[str]:
        """Get list of supported jurisdictions"""
        return [jurisdiction.value for jurisdiction in LegalJurisdiction]
    
    # ==========================================
    # DATABASE-SPECIFIC METHODS (Available only in database mode)
    # ==========================================
    
    def log_ai_interaction(
        self,
        query: str,
        response: str,
        practice_area: str,
        jurisdiction: str,
        **kwargs
    ) -> Optional[str]:
        """Log AI interaction to database (database mode only)"""
        if self.is_database_mode:
            return self.backend.log_ai_interaction(
                query=query,
                response=response,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                **kwargs
            )
        else:
            logger.warning("AI interaction logging not available in legacy mode")
            return None
    
    def get_interaction_history(self, case_id: str = None, user_id: str = None) -> List[Dict[str, Any]]:
        """Get AI interaction history (database mode only)"""
        if self.is_database_mode:
            return self.backend.get_interaction_history(case_id=case_id, user_id=user_id)
        else:
            logger.warning("Interaction history not available in legacy mode")
            return []
    
    def get_compliance_summary(self, case_id: str = None) -> Dict[str, Any]:
        """Get compliance summary for case or firm (database mode only)"""
        if self.is_database_mode:
            return self.backend.get_compliance_summary(case_id=case_id)
        else:
            logger.warning("Compliance summary not available in legacy mode")
            return {}
    
    def process_query_with_case(
        self,
        query: str,
        practice_area: Union[str, LegalPracticeArea],
        jurisdiction: Union[str, LegalJurisdiction],
        case_id: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> EnhancedLegalResponse:
        """
        Process a query with case linking (database mode preferred)
        Falls back to basic processing in legacy mode
        """
        if self.is_database_mode:
            return self.backend.process_query(
                query=query,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                case_id=case_id,
                context=context,
                **kwargs
            )
        else:
            logger.warning("Case-linked query processing not available in legacy mode")
            return self.backend.process_query(
                query=query,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                context=context
            )
    
    def process_legal_query(self, query: str, context: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Process legal query with document context - compatible with legacy interface
        This method provides backward compatibility for existing code that calls process_legal_query
        """
        try:
            # Extract documents from kwargs if available
            documents = kwargs.get('documents', [])
            
            # Prepare documents for context
            if documents and not context:
                context = self._extract_context_from_documents(documents)
            
            # Set default values
            practice_area = kwargs.get('practice_area', 'family')
            jurisdiction = kwargs.get('jurisdiction', 'australia')
            
            logger.info(f"Processing legal query via legacy interface: {query[:100]}...")
            
            # Call the main process_query method
            response = self.process_query(
                query=query,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                context={'documents': documents} if documents else None
            )
            
            # Convert response to dictionary format for backward compatibility
            if hasattr(response, '__dict__'):
                return {
                    "analysis": getattr(response, 'response', getattr(response, 'legal_analysis', str(response))),
                    "confidence": getattr(response, 'confidence_level', getattr(response, 'confidence_score', 'Medium')),
                    "lawyer_review_recommended": getattr(response, 'requires_human_review', getattr(response, 'lawyer_review_recommended', True)),
                    "legal_considerations": getattr(response, 'legal_considerations', 'Standard legal analysis completed'),
                    "recommendations": getattr(response, 'recommendations', ['Consult with qualified attorney']),
                    "jurisdiction": kwargs.get('jurisdiction', 'Australia'),
                    "practice_area": kwargs.get('practice_area', 'Family')
                }
            else:
                # If response is already a dict or string
                return {
                    "analysis": str(response),
                    "confidence": "Medium",
                    "lawyer_review_recommended": True,
                    "legal_considerations": "Standard legal analysis completed",
                    "recommendations": ["Consult with qualified attorney"],
                    "jurisdiction": kwargs.get('jurisdiction', 'Australia'),
                    "practice_area": kwargs.get('practice_area', 'Family')
                }
                
        except Exception as e:
            logger.error(f"Error in process_legal_query: {str(e)}", exc_info=True)
            # Return error response in expected format
            return {
                "analysis": f"Error processing legal query: {str(e)}",
                "confidence": "Low",
                "lawyer_review_recommended": True,
                "legal_considerations": "Error occurred during legal analysis",
                "recommendations": ["Please consult with a qualified attorney"],
                "jurisdiction": kwargs.get('jurisdiction', 'Australia'),
                "practice_area": kwargs.get('practice_area', 'Family')
            }
    
    def _extract_context_from_documents(self, documents: List[Any]) -> str:
        """Extract text context from documents for processing"""
        try:
            context_parts = []
            for doc in documents[:5]:  # Limit to first 5 documents
                if isinstance(doc, dict):
                    if 'content' in doc:
                        context_parts.append(f"Document: {doc.get('name', 'Unknown')}\\n{str(doc['content'])[:500]}")
                    elif 'extracted_text' in doc:
                        context_parts.append(f"Document: {doc.get('filename', 'Unknown')}\\n{doc['extracted_text'][:500]}")
                elif hasattr(doc, 'content'):
                    context_parts.append(f"Document: {getattr(doc, 'filename', 'Unknown')}\\n{doc.content[:500]}")
                elif isinstance(doc, str):
                    context_parts.append(f"Document Content:\\n{doc[:500]}")
            
            return "\\n\\n".join(context_parts)
        except Exception as e:
            logger.warning(f"Error extracting document context: {e}")
            return ""
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get comprehensive API usage and cost summary"""
        return self.api_config.get_usage_summary()
    
    def reset_usage_stats(self):
        """Reset API usage statistics"""
        self.api_config.reset_usage_stats()
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the current backend being used"""
        info = {
            'backend_type': 'database' if self.is_database_mode else 'legacy',
            'database_available': DATABASE_AVAILABLE,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'api_key_configured': bool(self.api_key),
            'enhanced_features_available': self.is_database_mode
        }
        
        # Add backend-specific information
        if hasattr(self.backend, 'get_backend_info'):
            backend_info = self.backend.get_backend_info()
            info.update(backend_info)
        
        return info
    
    def migrate_to_database(self, firm_id: str, user_id: str) -> bool:
        """
        Migrate from legacy mode to database mode
        
        Args:
            firm_id: Target firm ID for migration
            user_id: User performing the migration
            
        Returns:
            bool: True if migration successful or already using database
        """
        if self.is_database_mode:
            logger.info("Already using database backend")
            return True
        
        if not DATABASE_AVAILABLE:
            logger.error("Database backend not available for migration")
            return False
        
        try:
            # Switch to database backend
            self.backend = DatabaseLegalLLMEngine(
                api_key=self.api_key,
                firm_id=firm_id,
                user_id=user_id
            )
            self.is_database_mode = True
            self.firm_id = firm_id
            self.user_id = user_id
            
            logger.info("Successfully migrated to database backend with compliance logging")
            return True
            
        except Exception as e:
            logger.error(f"Migration to database failed: {e}")
            return False
    
    def get_australian_family_law_info(self) -> Dict[str, Any]:
        """Get Australian family law specific information (database mode enhanced)"""
        if self.is_database_mode and hasattr(self.backend, 'get_australian_family_law_info'):
            return self.backend.get_australian_family_law_info()
        else:
            # Basic information for legacy mode
            return {
                'case_types': ['divorce', 'property_settlement', 'child_custody', 'parenting_orders'],
                'compliance_acts': ['Family Law Act 1975'],
                'enhanced_features_available': False
            }
    
# Compatibility function for older code
def analyze_legal_query(
    query: str,
    practice_area: Union[str, LegalPracticeArea],
    jurisdiction: LegalJurisdiction,
    api_key: str,
    context: Optional[Dict[str, Any]] = None
) -> EnhancedLegalResponse:
    """Compatibility function for analyze_legal_query"""
    engine = EnhancedLegalLLMEngine(api_key=api_key)
    return engine.process_query(query, practice_area, jurisdiction, context)

# Export main classes with backward compatibility
if DATABASE_AVAILABLE:
    __all__ = [
        'EnhancedLegalLLMEngine', 'EnhancedLegalQuery', 'EnhancedLegalResponse',
        'LegalPracticeArea', 'InteractionType', 'AdviceClassification', 'ComplianceFlag'
    ]
else:
    __all__ = ['EnhancedLegalLLMEngine', 'EnhancedLegalQuery', 'EnhancedLegalResponse', 'LegalPracticeArea']

    
    def _get_legal_framework(self, practice_area: LegalPracticeArea, query_type: str = "general") -> str:
        """Get appropriate legal analysis framework"""
        
        frameworks = self.knowledge_base.legal_reasoning_frameworks
        
        if practice_area in [LegalPracticeArea.CONTRACT, LegalPracticeArea.CORPORATE]:
            return frameworks.get("contract_analysis", {}).get("analysis_framework", [])
        elif practice_area == LegalPracticeArea.LITIGATION:
            return frameworks.get("litigation_analysis", {}).get("analysis_framework", [])
        elif practice_area == LegalPracticeArea.REGULATORY_COMPLIANCE:
            return frameworks.get("compliance_analysis", {}).get("analysis_framework", [])
        else:
            return [
                "Identify applicable legal principles and authorities",
                "Analyze relevant statutes and regulations",
                "Consider jurisdiction-specific requirements",
                "Assess legal risks and implications",
                "Provide practical recommendations"
            ]
    
    def _get_analysis_template(self, practice_area: LegalPracticeArea) -> str:
        """Get appropriate analysis template"""
        
        templates = self.knowledge_base.legal_analysis_templates
        
        if practice_area in [LegalPracticeArea.CONTRACT, LegalPracticeArea.CORPORATE]:
            return templates.get("contract_analysis", "")
        elif practice_area == LegalPracticeArea.LITIGATION:
            return templates.get("litigation_assessment", "")
        else:
            return """
LEGAL ANALYSIS FRAMEWORK:

1. LEGAL ISSUE IDENTIFICATION
   - Primary legal questions
   - Applicable legal standards
   - Jurisdiction-specific considerations

2. LEGAL RESEARCH AND ANALYSIS
   - Relevant statutes and regulations
   - Case law and precedents
   - Legal principles application

3. RISK ASSESSMENT
   - Legal risks and exposures
   - Compliance requirements
   - Potential consequences

4. RECOMMENDATIONS
   - Specific action items
   - Risk mitigation strategies
   - Legal compliance measures
"""
    
    def process_query(
        self,
        query: str,
        practice_area: Union[str, LegalPracticeArea],
        jurisdiction: Union[str, LegalJurisdiction],
        context: Optional[Dict[str, Any]] = None
    ) -> EnhancedLegalResponse:
        """Process a legal query with sophisticated legal analysis"""
        
        logger.info(f"Processing sophisticated legal query: {query[:100]}...")
        
        # Convert practice area to enum if needed
        if isinstance(practice_area, str):
            try:
                # Handle common practice area name variations
                practice_area_mapping = {
                    'general law': LegalPracticeArea.GENERAL,
                    'general': LegalPracticeArea.GENERAL,
                    'family law': LegalPracticeArea.FAMILY,
                    'family': LegalPracticeArea.FAMILY,
                    'corporate law': LegalPracticeArea.CORPORATE,
                    'corporate': LegalPracticeArea.CORPORATE,
                    'criminal law': LegalPracticeArea.CRIMINAL,
                    'criminal': LegalPracticeArea.CRIMINAL,
                    'real estate law': LegalPracticeArea.REAL_ESTATE,
                    'real estate': LegalPracticeArea.REAL_ESTATE,
                    'property law': LegalPracticeArea.REAL_ESTATE,
                    'employment law': LegalPracticeArea.EMPLOYMENT,
                    'employment': LegalPracticeArea.EMPLOYMENT,
                    'intellectual property': LegalPracticeArea.INTELLECTUAL_PROPERTY,
                    'ip law': LegalPracticeArea.INTELLECTUAL_PROPERTY,
                    'immigration law': LegalPracticeArea.IMMIGRATION,
                    'immigration': LegalPracticeArea.IMMIGRATION,
                    'tax law': LegalPracticeArea.TAX,
                    'tax': LegalPracticeArea.TAX,
                    'personal injury': LegalPracticeArea.PERSONAL_INJURY,
                    'bankruptcy law': LegalPracticeArea.BANKRUPTCY,
                    'bankruptcy': LegalPracticeArea.BANKRUPTCY,
                    'environmental law': LegalPracticeArea.ENVIRONMENTAL,
                    'environmental': LegalPracticeArea.ENVIRONMENTAL,
                    'contract law': LegalPracticeArea.CONTRACT,
                    'contract': LegalPracticeArea.CONTRACT,
                    'litigation': LegalPracticeArea.LITIGATION,
                    'regulatory compliance': LegalPracticeArea.REGULATORY_COMPLIANCE,
                    'estate planning': LegalPracticeArea.ESTATE_PLANNING
                }
                practice_area_key = practice_area.lower().strip()
                practice_area = practice_area_mapping.get(practice_area_key, LegalPracticeArea.GENERAL)
            except (ValueError, AttributeError):
                practice_area = LegalPracticeArea.GENERAL
        
        # Convert jurisdiction to enum if needed
        if isinstance(jurisdiction, str):
            try:
                # Handle common jurisdiction name variations
                jurisdiction_mapping = {
                    'united states': LegalJurisdiction.UNITED_STATES,
                    'usa': LegalJurisdiction.UNITED_STATES,
                    'us': LegalJurisdiction.UNITED_STATES,
                    'australia': LegalJurisdiction.AUSTRALIA,
                    'au': LegalJurisdiction.AUSTRALIA,
                    'united kingdom': LegalJurisdiction.UNITED_KINGDOM,
                    'uk': LegalJurisdiction.UNITED_KINGDOM,
                    'britain': LegalJurisdiction.UNITED_KINGDOM,
                    'canada': LegalJurisdiction.CANADA,
                    'ca': LegalJurisdiction.CANADA
                }
                jurisdiction_key = jurisdiction.lower().strip()
                jurisdiction = jurisdiction_mapping.get(jurisdiction_key, LegalJurisdiction.UNITED_STATES)
            except (ValueError, AttributeError):
                jurisdiction = LegalJurisdiction.UNITED_STATES
        
        # Get jurisdiction information
        jurisdiction_info_obj = self.jurisdiction_manager.get_jurisdiction_info(jurisdiction)
        jurisdiction_name = jurisdiction_info_obj.name if hasattr(jurisdiction_info_obj, 'name') else jurisdiction.value.replace('_', ' ').title()
        
        disclaimers = self.knowledge_base.legal_disclaimers.get(jurisdiction, [])
        
        # Get legal framework and analysis template
        legal_framework = "\n".join([f"- {item}" for item in self._get_legal_framework(practice_area)])
        analysis_template = self._get_analysis_template(practice_area)
        
        # Prepare context
        context_str = ""
        document_content = ""
        
        if context and 'document_analysis' in context:
            doc_analysis = context['document_analysis']
            
            # Get document content intelligently
            if hasattr(doc_analysis, 'extracted_text') and doc_analysis.extracted_text:
                document_content = doc_analysis.extracted_text
                # Limit document content to prevent token issues while preserving quality
                if len(document_content.split()) > 2000:
                    words = document_content.split()[:2000]
                    document_content = ' '.join(words) + "\n\n[Document truncated - full analysis available]"
            else:
                document_content = getattr(doc_analysis, 'summary', 'Document analysis available')
            
            context_str = f"Document Analysis Context: {document_content}"
            
            if 'document_name' in context:
                context_str += f"\nDocument: {context['document_name']}"
        
        # Choose appropriate prompt template
        if context and 'document_analysis' in context:
            prompt = self.sophisticated_document_prompt
            prompt_vars = {
                "jurisdiction": jurisdiction_name,
                "practice_area": practice_area.value.replace('_', ' ').title(),
                "document_content": document_content,
                "query": query,
                "analysis_framework": analysis_template,
                "disclaimers": "\n".join(disclaimers)
            }
        else:
            prompt = self.sophisticated_legal_prompt
            prompt_vars = {
                "jurisdiction": jurisdiction_name,
                "practice_area": practice_area.value.replace('_', ' ').title(),
                "query": query,
                "context": context_str,
                "legal_framework": legal_framework,
                "disclaimers": "\n".join(disclaimers)
            }
        
        # Create and run the chain
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        try:
            response = chain.run(**prompt_vars)
            
            # Enhance response with Groq if available
            if self.groq_enhancement:
                try:
                    enhanced_response = self.groq_enhancement.enhance_legal_query_processing(
                        query=response,
                        context={
                            "original_query": query,
                            "practice_area": practice_area.value,
                            "jurisdiction": jurisdiction_name,
                            "context": context_str
                        }
                    )
                    response = enhanced_response
                    logger.info("Response enhanced with Groq intelligence")
                except Exception as e:
                    logger.warning(f"Groq enhancement failed, using original response: {str(e)}")
            
            # Sophisticated analysis of response quality
            confidence_level = self._assess_legal_confidence(query, response, practice_area, jurisdiction)
            requires_review = self._assess_review_requirement(query, response, practice_area, confidence_level)
            
            # Extract sophisticated legal analysis
            legal_considerations = self._extract_legal_considerations(response, practice_area)
            recommendations = self._extract_legal_recommendations(response, practice_area)
            
            # Return sophisticated legal response
            return EnhancedLegalResponse(
                response=response,
                confidence_level=confidence_level,
                requires_human_review=requires_review,
                legal_considerations=legal_considerations,
                recommendations=recommendations,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                jurisdiction_specific_notes=disclaimers,
                document_analysis=context.get('document_analysis') if context else None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error processing sophisticated legal query: {str(e)}")
            return EnhancedLegalResponse(
                response=f"Error processing legal query: {str(e)}",
                confidence_level="Low",
                requires_human_review=True,
                legal_considerations=["Error occurred during legal analysis"],
                recommendations=["Please consult with a qualified attorney"],
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                jurisdiction_specific_notes=disclaimers,
                timestamp=datetime.now()
            )
    
    def _assess_legal_confidence(self, query: str, response: str, practice_area: LegalPracticeArea, jurisdiction: LegalJurisdiction) -> str:
        """Sophisticated legal confidence assessment"""
        
        confidence_score = 0
        
        # Check for legal authority references
        legal_authorities = ["statute", "regulation", "case law", "precedent", "court", "§", "USC", "CFR"]
        authority_count = sum(1 for auth in legal_authorities if auth.lower() in response.lower())
        confidence_score += min(30, authority_count * 5)
        
        # Check for jurisdiction-specific content
        jurisdiction_terms = {
            LegalJurisdiction.UNITED_STATES: ["federal", "state", "USC", "CFR", "circuit"],
            LegalJurisdiction.AUSTRALIA: ["commonwealth", "state", "territory", "federal court"],
            LegalJurisdiction.UNITED_KINGDOM: ["england", "wales", "scotland", "northern ireland"],
            LegalJurisdiction.CANADA: ["federal", "provincial", "territorial", "supreme court"]
        }
        
        jurisdiction_specific = jurisdiction_terms.get(jurisdiction, [])
        jurisdiction_score = sum(1 for term in jurisdiction_specific if term.lower() in response.lower())
        confidence_score += min(20, jurisdiction_score * 5)
        
        # Check for practice area expertise
        practice_frameworks = self.knowledge_base.legal_reasoning_frameworks
        if practice_area.value in ["contract", "corporate"]:
            contract_terms = practice_frameworks.get("contract_analysis", {}).get("elements", [])
            expertise_score = sum(1 for term in contract_terms if term.lower() in response.lower())
            confidence_score += min(25, expertise_score * 5)
        
        # Check response depth and structure
        if len(response.split()) > 200:
            confidence_score += 15
        if "recommendation" in response.lower():
            confidence_score += 10
        
        # Convert to confidence level
        if confidence_score >= 70:
            return "High"
        elif confidence_score >= 40:
            return "Medium"
        else:
            return "Low"
    
    def _assess_review_requirement(self, query: str, response: str, practice_area: LegalPracticeArea, confidence: str) -> bool:
        """Sophisticated assessment of human review requirement"""
        
        # Always require review for low confidence
        if confidence == "Low":
            return True
        
        # High-risk practice areas
        high_risk_areas = [
            LegalPracticeArea.CRIMINAL, 
            LegalPracticeArea.LITIGATION, 
            LegalPracticeArea.REGULATORY_COMPLIANCE
        ]
        if practice_area in high_risk_areas:
            return True
        
        # Complex legal issues
        complex_indicators = [
            "constitutional", "federal court", "supreme court", "class action", 
            "criminal charges", "securities", "antitrust", "intellectual property"
        ]
        if any(indicator in query.lower() for indicator in complex_indicators):
            return True
        
        # Urgent matters
        urgent_indicators = [
            "deadline", "statute of limitations", "emergency", "injunction", 
            "restraining order", "immediate", "urgent"
        ]
        if any(indicator in query.lower() for indicator in urgent_indicators):
            return True
        
        return False
    
    def _extract_legal_considerations(self, response: str, practice_area: LegalPracticeArea) -> List[str]:
        """Extract sophisticated legal considerations"""
        considerations = []
        
        # Look for structured legal analysis
        lines = response.split('\n')
        in_considerations_section = False
        
        for line in lines:
            line = line.strip()
            
            # Identify considerations sections
            if any(keyword in line.lower() for keyword in ['consideration', 'important', 'note', 'risk', 'factor']):
                in_considerations_section = True
                continue
            
            if in_considerations_section and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                considerations.append(line.lstrip('•-* '))
            elif in_considerations_section and line and not line[0].isalnum():
                in_considerations_section = False
        
        # If no structured considerations found, extract from content
        if not considerations:
            legal_keywords = ['must', 'should', 'required', 'compliance', 'liability', 'risk', 'obligation']
            for line in lines:
                if any(keyword in line.lower() for keyword in legal_keywords) and len(line.strip()) > 20:
                    considerations.append(line.strip())
                    if len(considerations) >= 5:
                        break
        
        return considerations[:5]
    
    def _extract_legal_recommendations(self, response: str, practice_area: LegalPracticeArea) -> List[str]:
        """Extract sophisticated legal recommendations"""
        recommendations = []
        
        # Look for recommendation sections
        lines = response.split('\n')
        in_recommendations_section = False
        
        for line in lines:
            line = line.strip()
            
            # Identify recommendation sections
            if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'advise', 'action', 'step']):
                in_recommendations_section = True
                continue
            
            if in_recommendations_section and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                recommendations.append(line.lstrip('•-* '))
            elif in_recommendations_section and line and not line[0].isalnum():
                in_recommendations_section = False
        
        # If no structured recommendations found, extract actionable items
        if not recommendations:
            action_keywords = ['should', 'recommend', 'advise', 'consider', 'ensure', 'implement']
            for line in lines:
                if any(keyword in line.lower() for keyword in action_keywords) and len(line.strip()) > 20:
                    recommendations.append(line.strip())
                    if len(recommendations) >= 5:
                        break
        
        return recommendations[:5]

# Compatibility function for older code
def analyze_legal_query(
    query: str,
    practice_area: Union[str, LegalPracticeArea],
    jurisdiction: LegalJurisdiction,
    api_key: str,
    context: Optional[Dict[str, Any]] = None
) -> EnhancedLegalResponse:
    """Compatibility function for analyze_legal_query"""
    engine = EnhancedLegalLLMEngine(api_key=api_key)
    return engine.process_query(query, practice_area, jurisdiction, context)

