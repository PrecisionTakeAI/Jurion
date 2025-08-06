"""
Financial Settlement Analysis Engine for Australian Family Law
Comprehensive financial analysis system for property settlements under Family Law Act 1975
Integrates with multi-agent system and performance infrastructure for optimal processing
"""

import os
import asyncio
import logging
import time
import json
import re
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import statistics

# Performance optimization: Dependency caching
_dependency_cache = {}
_is_production = os.getenv('ENVIRONMENT', '').lower() == 'production'

# Import existing system components following established patterns
try:
    from core.enhanced_llm_engine import EnhancedLegalLLMEngine, EnhancedLegalQuery, EnhancedLegalResponse
    from core.document_processor import DocumentProcessor, ProcessingResult
    from core.performance_infrastructure import AsyncDocumentPipeline, ProcessingPriority
    CORE_SYSTEMS_AVAILABLE = True
except ImportError as e:
    CORE_SYSTEMS_AVAILABLE = False
    logging.warning(f"Core systems not fully available: {e}")

# Database integration with fallback pattern
try:
    from database.database import get_session, get_async_session
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    logging.info("Database integration not available - using legacy processing")

logger = logging.getLogger(__name__)

class AustralianAssetCategory(Enum):
    """Asset categories under Australian Family Law Act 1975"""
    REAL_ESTATE = "real_estate"
    BANK_ACCOUNTS = "bank_accounts"
    SUPERANNUATION = "superannuation"
    VEHICLES = "vehicles"
    BUSINESS_INTERESTS = "business_interests"
    INVESTMENTS = "investments"
    PERSONAL_PROPERTY = "personal_property"
    LIFE_INSURANCE = "life_insurance"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    TRUSTS = "trusts"
    OVERSEAS_ASSETS = "overseas_assets"
    OTHER_ASSETS = "other_assets"

class AustralianLiabilityCategory(Enum):
    """Liability categories for family law financial statements"""
    MORTGAGES = "mortgages"
    CREDIT_CARDS = "credit_cards"
    PERSONAL_LOANS = "personal_loans"
    BUSINESS_DEBTS = "business_debts"
    TAX_LIABILITIES = "tax_liabilities"
    GUARANTEE_LIABILITIES = "guarantee_liabilities"
    LEGAL_COSTS = "legal_costs"
    OTHER_LIABILITIES = "other_liabilities"

class ContributionType(Enum):
    """Types of contributions under s79 Family Law Act 1975"""
    INITIAL_FINANCIAL = "initial_financial"
    ONGOING_FINANCIAL = "ongoing_financial"
    NON_FINANCIAL_DIRECT = "non_financial_direct"
    NON_FINANCIAL_INDIRECT = "non_financial_indirect"
    HOMEMAKER_PARENT = "homemaker_parent"
    SPECIAL_CONTRIBUTION = "special_contribution"

class FutureNeedsFactor(Enum):
    """Future needs factors under s75(2) Family Law Act 1975"""
    AGE_HEALTH = "age_health"
    INCOME_EARNING_CAPACITY = "income_earning_capacity"
    PROPERTY_RESOURCES = "property_resources"
    FINANCIAL_NEEDS = "financial_needs"
    CARE_OF_CHILDREN = "care_of_children"
    STANDARD_OF_LIVING = "standard_of_living"
    DURATION_OF_RELATIONSHIP = "duration_of_relationship"

@dataclass
class FinancialAsset:
    """Represents a financial asset in property settlement"""
    asset_id: str
    category: AustralianAssetCategory
    description: str
    current_value: Decimal
    valuation_date: datetime
    valuation_method: str
    joint_ownership: bool = False
    ownership_percentage: Dict[str, float] = field(default_factory=dict)
    encumbrances: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    valuation_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class FinancialLiability:
    """Represents a financial liability"""
    liability_id: str
    category: AustralianLiabilityCategory
    description: str
    current_balance: Decimal
    original_amount: Decimal
    creditor: str
    joint_liability: bool = False
    liability_percentage: Dict[str, float] = field(default_factory=dict)
    security_details: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Form13Analysis:
    """Analysis results for Form 13 compliance"""
    completeness_score: float
    missing_sections: List[str]
    inconsistencies: List[str]
    red_flags: List[str]
    total_assets_declared: Decimal
    total_liabilities_declared: Decimal
    net_worth_calculated: Decimal
    analysis_timestamp: datetime
    compliance_issues: List[str] = field(default_factory=list)

@dataclass
class SettlementScenario:
    """Property settlement scenario with detailed breakdown"""
    scenario_id: str
    scenario_name: str
    party_1_share: Decimal
    party_2_share: Decimal
    percentage_split: Tuple[float, float]
    rationale: str
    contribution_adjustments: Dict[ContributionType, float]
    future_needs_adjustments: Dict[FutureNeedsFactor, float]
    practical_considerations: List[str]
    tax_implications: Dict[str, Any]
    implementation_steps: List[str]
    confidence_score: float

@dataclass
class SuperannuationSplitting:
    """Superannuation splitting analysis"""
    total_super_pool: Decimal
    splitting_scenarios: List[Dict[str, Any]]
    tax_implications: Dict[str, Any]
    preservation_requirements: Dict[str, Any]
    payment_methods: List[str]
    recommended_approach: str

class PropertyAssetClassifier:
    """
    Classifies assets according to Australian Family Law Act 1975 requirements
    Maintains compatibility with existing document processing patterns
    """
    
    def __init__(self, firm_id: str = None, user_id: str = None):
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Initialize LLM engine following existing pattern
        if CORE_SYSTEMS_AVAILABLE:
            self.llm_engine = EnhancedLegalLLMEngine(firm_id=firm_id, user_id=user_id)
        else:
            self.llm_engine = None
            
        # Asset classification patterns
        self.classification_patterns = self._initialize_classification_patterns()
        
        # Performance tracking
        self.classification_metrics = {
            'assets_classified': 0,
            'accuracy_score': 0.0,
            'processing_time': 0.0
        }
        
        logger.info("PropertyAssetClassifier initialized")
    
    def _initialize_classification_patterns(self) -> Dict[AustralianAssetCategory, List[str]]:
        """Initialize asset classification patterns for Australian family law"""
        return {
            AustralianAssetCategory.REAL_ESTATE: [
                'property', 'house', 'apartment', 'unit', 'land', 'real estate',
                'residential', 'commercial', 'investment property', 'family home'
            ],
            AustralianAssetCategory.BANK_ACCOUNTS: [
                'bank account', 'savings', 'cheque account', 'term deposit',
                'cash', 'offset account', 'transaction account'
            ],
            AustralianAssetCategory.SUPERANNUATION: [
                'superannuation', 'super', 'retirement fund', 'pension',
                'self-managed super fund', 'smsf', 'industry fund'
            ],
            AustralianAssetCategory.VEHICLES: [
                'car', 'vehicle', 'motorcycle', 'boat', 'caravan',
                'truck', 'trailer', 'aircraft'
            ],
            AustralianAssetCategory.BUSINESS_INTERESTS: [
                'business', 'company', 'partnership', 'sole trader',
                'shares', 'equity', 'goodwill', 'business asset'
            ],
            AustralianAssetCategory.INVESTMENTS: [
                'shares', 'stocks', 'bonds', 'managed funds',
                'investment', 'portfolio', 'securities', 'options'
            ]
        }
    
    async def classify_asset(self, asset_description: str, asset_value: Decimal = None) -> Tuple[AustralianAssetCategory, float]:
        """
        Classify an asset based on description and value
        Returns tuple of (category, confidence_score)
        """
        start_time = time.time()
        
        try:
            # First attempt: Pattern matching
            pattern_result = self._classify_by_patterns(asset_description)
            
            # If low confidence, use AI classification
            if pattern_result[1] < 0.7 and self.llm_engine:
                ai_result = await self._classify_with_ai(asset_description, asset_value)
                
                # Combine results with weighted average
                if ai_result[1] > pattern_result[1]:
                    result = ai_result
                else:
                    result = pattern_result
            else:
                result = pattern_result
            
            # Update metrics
            processing_time = time.time() - start_time
            self.classification_metrics['assets_classified'] += 1
            self.classification_metrics['processing_time'] += processing_time
            
            logger.debug(f"Classified asset '{asset_description[:50]}...' as {result[0].value} (confidence: {result[1]:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error classifying asset: {e}")
            return AustralianAssetCategory.OTHER_ASSETS, 0.1
    
    def _classify_by_patterns(self, description: str) -> Tuple[AustralianAssetCategory, float]:
        """Classify asset using pattern matching"""
        description_lower = description.lower()
        
        # Calculate matches for each category
        category_scores = {}
        
        for category, patterns in self.classification_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in description_lower:
                    # Weight longer patterns more heavily
                    score += len(pattern.split()) * 0.2
            
            if score > 0:
                category_scores[category] = min(score, 1.0)
        
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            return best_category[0], best_category[1]
        else:
            return AustralianAssetCategory.OTHER_ASSETS, 0.3
    
    async def _classify_with_ai(self, description: str, value: Decimal = None) -> Tuple[AustralianAssetCategory, float]:
        """Use AI to classify asset with high accuracy"""
        
        value_context = f" with value of ${value:,.2f}" if value else ""
        
        query_text = f"""
        Classify the following asset according to Australian Family Law Act 1975 categories:
        Asset description: {description}{value_context}
        
        Categories available:
        - real_estate: Property, houses, land, commercial property
        - bank_accounts: Cash, savings, transaction accounts, term deposits
        - superannuation: Super funds, retirement savings, pension accounts
        - vehicles: Cars, boats, motorcycles, aircraft
        - business_interests: Companies, partnerships, business assets, goodwill
        - investments: Shares, bonds, managed funds, securities
        - personal_property: Furniture, jewelry, art, collectibles
        - life_insurance: Life insurance policies with cash value
        - intellectual_property: Patents, trademarks, copyrights
        - trusts: Trust interests and distributions
        - overseas_assets: Assets located outside Australia
        - other_assets: Assets not fitting other categories
        
        Provide the most appropriate category and confidence level (0.0-1.0).
        """
        
        query = EnhancedLegalQuery(
            query_text=query_text,
            practice_area="family_law",
            jurisdiction="australia",
            query_type="asset_classification"
        )
        
        try:
            response = await asyncio.to_thread(self.llm_engine.process_query, query)
            
            # Parse AI response to extract category and confidence
            category, confidence = self._parse_ai_classification_response(response.response)
            return category, confidence
            
        except Exception as e:
            logger.error(f"AI classification error: {e}")
            return AustralianAssetCategory.OTHER_ASSETS, 0.2
    
    def _parse_ai_classification_response(self, response: str) -> Tuple[AustralianAssetCategory, float]:
        """Parse AI response to extract asset category and confidence"""
        response_lower = response.lower()
        
        # Look for category mentions
        for category in AustralianAssetCategory:
            if category.value in response_lower:
                # Extract confidence if mentioned
                confidence_match = re.search(r'confidence[:\s]+(\d+\.?\d*)%?', response_lower)
                if confidence_match:
                    confidence = float(confidence_match.group(1))
                    if confidence > 1.0:  # Assume percentage
                        confidence = confidence / 100.0
                else:
                    confidence = 0.8  # Default high confidence for AI classification
                
                return category, min(confidence, 1.0)
        
        return AustralianAssetCategory.OTHER_ASSETS, 0.5
    
    async def classify_assets_batch(self, assets: List[Dict[str, Any]]) -> List[Tuple[str, AustralianAssetCategory, float]]:
        """
        Classify multiple assets in batch for performance
        Returns list of (asset_id, category, confidence)
        """
        
        if not assets:
            return []
        
        start_time = time.time()
        
        # Process assets concurrently
        tasks = []
        for asset in assets:
            task = self._classify_single_asset_from_dict(asset)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        classified_assets = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Error classifying asset {i}: {result}")
                classified_assets.append((
                    assets[i].get('id', f'asset_{i}'),
                    AustralianAssetCategory.OTHER_ASSETS,
                    0.1
                ))
            else:
                asset_id = assets[i].get('id', f'asset_{i}')
                classified_assets.append((asset_id, result[0], result[1]))
        
        processing_time = time.time() - start_time
        logger.info(f"Batch classified {len(assets)} assets in {processing_time:.2f}s")
        
        return classified_assets
    
    async def _classify_single_asset_from_dict(self, asset: Dict[str, Any]) -> Tuple[AustralianAssetCategory, float]:
        """Helper method to classify asset from dictionary"""
        description = asset.get('description', '')
        value = asset.get('value')
        if value is not None:
            value = Decimal(str(value))
        
        return await self.classify_asset(description, value)
    
    def get_classification_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for asset classification"""
        return {
            **self.classification_metrics,
            'average_processing_time': (
                self.classification_metrics['processing_time'] / 
                max(self.classification_metrics['assets_classified'], 1)
            )
        }

class PropertyValuationTracker:
    """
    Tracks asset valuations over time for property settlement analysis
    Maintains valuation history and identifies valuation discrepancies
    """
    
    def __init__(self, firm_id: str = None, user_id: str = None):
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Valuation storage (in production, this would use database)
        self.valuations: Dict[str, List[Dict[str, Any]]] = {}
        
        # Valuation thresholds and rules
        self.valuation_thresholds = {
            'significant_change': 0.15,  # 15% change is significant
            'major_change': 0.30,        # 30% change is major
            'stale_valuation_days': 365,  # Valuations older than 1 year are stale
            'real_estate_refresh_days': 180,  # Real estate should be revalued every 6 months
            'business_refresh_days': 90   # Business interests every 3 months
        }
        
        logger.info("PropertyValuationTracker initialized")
    
    async def add_valuation(self, asset_id: str, valuation_data: Dict[str, Any]) -> bool:
        """Add a new valuation for an asset"""
        
        try:
            # Validate valuation data
            required_fields = ['value', 'valuation_date', 'valuation_method']
            if not all(field in valuation_data for field in required_fields):
                raise ValueError(f"Missing required fields: {required_fields}")
            
            # Initialize asset valuations if not exists
            if asset_id not in self.valuations:
                self.valuations[asset_id] = []
            
            # Add timestamp and metadata
            valuation_entry = {
                **valuation_data,
                'recorded_at': datetime.now(),
                'firm_id': self.firm_id,
                'user_id': self.user_id
            }
            
            # Insert valuation in chronological order
            self.valuations[asset_id].append(valuation_entry)
            self.valuations[asset_id].sort(key=lambda x: x['valuation_date'])
            
            logger.debug(f"Added valuation for asset {asset_id}: ${valuation_data['value']:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding valuation: {e}")
            return False
    
    async def get_current_valuation(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent valuation for an asset"""
        
        if asset_id not in self.valuations or not self.valuations[asset_id]:
            return None
        
        # Return most recent valuation
        return self.valuations[asset_id][-1]
    
    async def get_valuation_history(self, asset_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get valuation history for an asset"""
        
        if asset_id not in self.valuations:
            return []
        
        history = self.valuations[asset_id]
        
        if limit:
            return history[-limit:]
        
        return history
    
    async def analyze_valuation_trends(self, asset_id: str) -> Dict[str, Any]:
        """Analyze valuation trends for an asset"""
        
        history = await self.get_valuation_history(asset_id)
        
        if len(history) < 2:
            return {
                'trend': 'insufficient_data',
                'change_percentage': 0.0,
                'volatility': 0.0,
                'recommendations': ['Obtain additional valuations for trend analysis']
            }
        
        # Calculate trend metrics
        values = [float(v['value']) for v in history]
        dates = [v['valuation_date'] for v in history]
        
        # Overall change
        initial_value = values[0]
        final_value = values[-1]
        change_percentage = (final_value - initial_value) / initial_value if initial_value != 0 else 0
        
        # Volatility (standard deviation of percentage changes)
        if len(values) > 2:
            pct_changes = []
            for i in range(1, len(values)):
                if values[i-1] != 0:
                    pct_change = (values[i] - values[i-1]) / values[i-1]
                    pct_changes.append(pct_change)
            
            volatility = statistics.stdev(pct_changes) if len(pct_changes) > 1 else 0.0
        else:
            volatility = 0.0
        
        # Determine trend
        if change_percentage > 0.05:
            trend = 'increasing'
        elif change_percentage < -0.05:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Generate recommendations
        recommendations = self._generate_valuation_recommendations(
            change_percentage, volatility, history
        )
        
        return {
            'trend': trend,
            'change_percentage': change_percentage,
            'volatility': volatility,
            'total_valuations': len(history),
            'date_range': {
                'earliest': dates[0],
                'latest': dates[-1]
            },
            'value_range': {
                'lowest': min(values),
                'highest': max(values),
                'current': final_value
            },
            'recommendations': recommendations
        }
    
    def _generate_valuation_recommendations(self, change_pct: float, volatility: float, history: List) -> List[str]:
        """Generate recommendations based on valuation analysis"""
        recommendations = []
        
        # Significant change recommendations
        if abs(change_pct) > self.valuation_thresholds['significant_change']:
            recommendations.append(f"Significant valuation change detected ({change_pct:.1%}). Consider obtaining independent valuation.")
        
        # High volatility recommendations
        if volatility > 0.2:
            recommendations.append("High valuation volatility detected. Recommend obtaining average of multiple recent valuations.")
        
        # Stale valuation check
        if history:
            latest_date = history[-1]['valuation_date']
            if isinstance(latest_date, str):
                latest_date = datetime.fromisoformat(latest_date)
            
            days_old = (datetime.now() - latest_date).days
            
            if days_old > self.valuation_thresholds['stale_valuation_days']:
                recommendations.append(f"Latest valuation is {days_old} days old. Consider obtaining fresh valuation.")
        
        return recommendations
    
    async def identify_valuation_discrepancies(self, asset_pool: List[FinancialAsset]) -> List[Dict[str, Any]]:
        """Identify potential valuation discrepancies across asset pool"""
        
        discrepancies = []
        
        for asset in asset_pool:
            asset_id = asset.asset_id
            current_value = asset.current_value
            
            # Get valuation history
            history = await self.get_valuation_history(asset_id)
            
            if len(history) < 2:
                continue
            
            # Check for unusual jumps
            for i in range(1, len(history)):
                prev_value = float(history[i-1]['value'])
                curr_value = float(history[i]['value'])
                
                if prev_value == 0:
                    continue
                
                change_pct = (curr_value - prev_value) / prev_value
                
                if abs(change_pct) > self.valuation_thresholds['major_change']:
                    discrepancies.append({
                        'asset_id': asset_id,
                        'asset_description': asset.description,
                        'discrepancy_type': 'unusual_change',
                        'previous_value': prev_value,
                        'current_value': curr_value,
                        'change_percentage': change_pct,
                        'valuation_dates': [history[i-1]['valuation_date'], history[i]['valuation_date']],
                        'severity': 'high' if abs(change_pct) > 0.5 else 'medium'
                    })
        
        return discrepancies

class Form13ComplianceAnalyzer:
    """
    Analyzes Form 13 financial statements for completeness and compliance
    Identifies missing information and potential red flags
    """
    
    def __init__(self, firm_id: str = None, user_id: str = None):
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Initialize LLM engine for document analysis
        if CORE_SYSTEMS_AVAILABLE:
            self.llm_engine = EnhancedLegalLLMEngine(firm_id=firm_id, user_id=user_id)
            self.doc_processor = DocumentProcessor(firm_id=firm_id, user_id=user_id)
        else:
            self.llm_engine = None
            self.doc_processor = None
        
        # Form 13 requirements checklist
        self.form13_requirements = {
            'personal_details': [
                'full_name', 'date_of_birth', 'address', 'occupation'
            ],
            'real_estate': [
                'property_address', 'ownership_type', 'current_value', 'mortgage_details'
            ],
            'bank_accounts': [
                'account_details', 'current_balance', 'account_type'
            ],
            'superannuation': [
                'fund_name', 'member_number', 'current_balance', 'contribution_history'
            ],
            'vehicles': [
                'vehicle_details', 'registration', 'current_value'
            ],
            'other_assets': [
                'asset_description', 'current_value', 'ownership_details'
            ],
            'liabilities': [
                'creditor_details', 'amount_owing', 'repayment_terms'
            ],
            'income': [
                'employment_income', 'investment_income', 'other_income'
            ],
            'expenses': [
                'living_expenses', 'loan_repayments', 'other_expenses'
            ]
        }
        
        logger.info("Form13ComplianceAnalyzer initialized")
    
    async def analyze_form13_compliance(self, document_content: bytes, filename: str = "form13.pdf") -> Form13Analysis:
        """
        Analyze Form 13 document for compliance and completeness
        """
        
        start_time = time.time()
        
        try:
            # Extract text from document
            if self.doc_processor:
                processing_result = self.doc_processor.process_document(document_content, filename)
                if not processing_result.success:
                    raise ValueError(f"Document processing failed: {processing_result.error_message}")
                
                document_text = processing_result.extracted_text
            else:
                # Fallback text extraction
                document_text = document_content.decode('utf-8', errors='ignore')
            
            # Analyze compliance using AI
            compliance_analysis = await self._analyze_compliance_with_ai(document_text)
            
            # Perform rule-based validation
            rule_based_analysis = self._analyze_compliance_rules(document_text)
            
            # Combine analyses
            combined_analysis = self._combine_compliance_analyses(compliance_analysis, rule_based_analysis)
            
            # Calculate completeness score
            completeness_score = self._calculate_completeness_score(combined_analysis)
            
            # Identify red flags
            red_flags = self._identify_red_flags(document_text, combined_analysis)
            
            # Calculate financial totals
            financial_totals = self._extract_financial_totals(document_text)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Form 13 analysis completed in {processing_time:.2f}s (completeness: {completeness_score:.1%})")
            
            return Form13Analysis(
                completeness_score=completeness_score,
                missing_sections=combined_analysis.get('missing_sections', []),
                inconsistencies=combined_analysis.get('inconsistencies', []),
                red_flags=red_flags,
                total_assets_declared=financial_totals['total_assets'],
                total_liabilities_declared=financial_totals['total_liabilities'],
                net_worth_calculated=financial_totals['total_assets'] - financial_totals['total_liabilities'],
                analysis_timestamp=datetime.now(),
                compliance_issues=combined_analysis.get('compliance_issues', [])
            )
            
        except Exception as e:
            logger.error(f"Error analyzing Form 13 compliance: {e}")
            return Form13Analysis(
                completeness_score=0.0,
                missing_sections=['analysis_failed'],
                inconsistencies=[],
                red_flags=[str(e)],
                total_assets_declared=Decimal('0.00'),
                total_liabilities_declared=Decimal('0.00'),
                net_worth_calculated=Decimal('0.00'),
                analysis_timestamp=datetime.now(),
                compliance_issues=['Analysis failed due to technical error']
            )
    
    async def _analyze_compliance_with_ai(self, document_text: str) -> Dict[str, Any]:
        """Use AI to analyze Form 13 compliance"""
        
        if not self.llm_engine:
            return {'error': 'AI analysis not available'}
        
        query_text = f"""
        Analyze this Form 13 Financial Statement for compliance with Australian Family Law requirements:
        
        {document_text[:3000]}...  # Limit text for AI processing
        
        Check for:
        1. Completeness of asset disclosure (real estate, bank accounts, superannuation, vehicles, other assets)
        2. Completeness of liability disclosure (mortgages, credit cards, loans, other debts)
        3. Income and expense declarations
        4. Missing mandatory sections
        5. Inconsistencies in figures or information
        6. Potential red flags or undisclosed items
        
        Provide a detailed analysis including:
        - Missing sections or information
        - Inconsistencies found
        - Completeness assessment
        - Compliance concerns
        """
        
        query = EnhancedLegalQuery(
            query_text=query_text,
            practice_area="family_law",
            jurisdiction="australia",
            query_type="form13_compliance"
        )
        
        try:
            response = await asyncio.to_thread(self.llm_engine.process_query, query)
            return self._parse_ai_compliance_response(response.response)
            
        except Exception as e:
            logger.error(f"AI compliance analysis error: {e}")
            return {'error': str(e)}
    
    def _parse_ai_compliance_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for compliance analysis"""
        
        analysis = {
            'missing_sections': [],
            'inconsistencies': [],
            'compliance_issues': [],
            'ai_assessment': response[:500]  # Store first 500 chars
        }
        
        response_lower = response.lower()
        
        # Extract missing sections
        if 'missing' in response_lower:
            # Simple extraction - in production would use more sophisticated NLP
            missing_indicators = ['missing', 'absent', 'not disclosed', 'not provided']
            lines = response.split('\n')
            for line in lines:
                if any(indicator in line.lower() for indicator in missing_indicators):
                    analysis['missing_sections'].append(line.strip())
        
        # Extract inconsistencies
        if 'inconsistent' in response_lower or 'discrepancy' in response_lower:
            inconsistency_indicators = ['inconsistent', 'discrepancy', 'mismatch', 'contradiction']
            lines = response.split('\n')
            for line in lines:
                if any(indicator in line.lower() for indicator in inconsistency_indicators):
                    analysis['inconsistencies'].append(line.strip())
        
        return analysis
    
    def _analyze_compliance_rules(self, document_text: str) -> Dict[str, Any]:
        """Rule-based compliance analysis"""
        
        text_lower = document_text.lower()
        analysis = {
            'sections_found': [],
            'missing_sections': [],
            'completeness_scores': {}
        }
        
        # Check for required sections
        for section, requirements in self.form13_requirements.items():
            section_score = 0
            found_requirements = 0
            
            for requirement in requirements:
                # Simple keyword matching (in production would be more sophisticated)
                if any(keyword in text_lower for keyword in requirement.split('_')):
                    found_requirements += 1
            
            section_score = found_requirements / len(requirements)
            analysis['completeness_scores'][section] = section_score
            
            if section_score > 0.3:  # At least 30% of requirements found
                analysis['sections_found'].append(section)
            else:
                analysis['missing_sections'].append(section)
        
        return analysis
    
    def _combine_compliance_analyses(self, ai_analysis: Dict, rule_analysis: Dict) -> Dict[str, Any]:
        """Combine AI and rule-based analyses"""
        
        combined = {
            'missing_sections': [],
            'inconsistencies': ai_analysis.get('inconsistencies', []),
            'compliance_issues': ai_analysis.get('compliance_issues', []),
            'completeness_scores': rule_analysis.get('completeness_scores', {}),
            'sections_found': rule_analysis.get('sections_found', [])
        }
        
        # Combine missing sections from both analyses
        ai_missing = set(ai_analysis.get('missing_sections', []))
        rule_missing = set(rule_analysis.get('missing_sections', []))
        combined['missing_sections'] = list(ai_missing.union(rule_missing))
        
        return combined
    
    def _calculate_completeness_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall completeness score"""
        
        section_scores = analysis.get('completeness_scores', {})
        
        if not section_scores:
            return 0.0
        
        # Weight sections by importance
        section_weights = {
            'personal_details': 0.05,
            'real_estate': 0.25,
            'bank_accounts': 0.15,
            'superannuation': 0.20,
            'vehicles': 0.05,
            'other_assets': 0.10,
            'liabilities': 0.15,
            'income': 0.05,
            'expenses': 0.05
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for section, score in section_scores.items():
            weight = section_weights.get(section, 0.05)
            weighted_score += score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _identify_red_flags(self, document_text: str, analysis: Dict[str, Any]) -> List[str]:
        """Identify potential red flags in Form 13"""
        
        red_flags = []
        text_lower = document_text.lower()
        
        # Common red flag indicators
        red_flag_patterns = [
            ('zero assets', 'No assets declared despite income'),
            ('minimal assets', 'Very low asset declaration relative to income'),
            ('round numbers', 'Suspiciously round numbers in valuations'),
            ('no bank accounts', 'No bank accounts declared'),
            ('cash business', 'Cash-based business with minimal records'),
            ('overseas', 'Potential undisclosed overseas assets mentioned'),
            ('trust', 'Trust arrangements that may require disclosure'),
            ('loan from family', 'Family loans that may need verification')
        ]
        
        for pattern, description in red_flag_patterns:
            if pattern in text_lower:
                red_flags.append(description)
        
        # Missing major asset categories
        if 'real_estate' in analysis.get('missing_sections', []):
            red_flags.append("No real estate disclosed - unusual for most family law cases")
        
        if 'superannuation' in analysis.get('missing_sections', []):
            red_flags.append("No superannuation disclosed - required for most employed individuals")
        
        return red_flags
    
    def _extract_financial_totals(self, document_text: str) -> Dict[str, Decimal]:
        """Extract total asset and liability figures from document"""
        
        # Simple regex patterns for dollar amounts
        dollar_pattern = r'\$[\d,]+(?:\.\d{2})?'
        
        # Find all dollar amounts
        amounts = re.findall(dollar_pattern, document_text)
        
        # Convert to decimals
        decimal_amounts = []
        for amount in amounts:
            try:
                # Remove $ and commas, convert to Decimal
                clean_amount = amount.replace('$', '').replace(',', '')
                decimal_amounts.append(Decimal(clean_amount))
            except:
                continue
        
        # Simple heuristic: assume largest amounts are totals
        # In production, would use more sophisticated extraction
        if decimal_amounts:
            decimal_amounts.sort(reverse=True)
            total_assets = decimal_amounts[0] if len(decimal_amounts) > 0 else Decimal('0.00')
            total_liabilities = decimal_amounts[1] if len(decimal_amounts) > 1 else Decimal('0.00')
        else:
            total_assets = Decimal('0.00')
            total_liabilities = Decimal('0.00')
        
        return {
            'total_assets': total_assets,
            'total_liabilities': total_liabilities
        }

class PropertySettlementCalculator:
    """
    Calculates property settlement scenarios under Australian Family Law Act 1975
    Implements s79 and s75 factors for property and maintenance calculations
    """
    
    def __init__(self, firm_id: str = None, user_id: str = None):
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Standard percentage splits used in Australian family law
        self.standard_splits = {
            'equal': (0.5, 0.5),
            'minor_adjustment': (0.55, 0.45),
            'moderate_adjustment': (0.60, 0.40),
            'significant_adjustment': (0.65, 0.35),
            'major_adjustment': (0.70, 0.30)
        }
        
        # Contribution and future needs weightings
        self.factor_weights = {
            'contributions': 0.6,  # 60% weight to contributions
            'future_needs': 0.4    # 40% weight to future needs
        }
        
        logger.info("PropertySettlementCalculator initialized")
    
    async def calculate_settlement_scenarios(self, 
                                           asset_pool: List[FinancialAsset], 
                                           liability_pool: List[FinancialLiability],
                                           case_context: Dict[str, Any]) -> List[SettlementScenario]:
        """
        Calculate multiple settlement scenarios based on case factors
        """
        
        start_time = time.time()
        
        try:
            # Calculate net asset pool
            total_assets = sum(asset.current_value for asset in asset_pool)
            total_liabilities = sum(liability.current_balance for liability in liability_pool)
            net_pool = total_assets - total_liabilities
            
            if net_pool <= 0:
                logger.warning("Net asset pool is zero or negative")
                return []
            
            # Analyze contributions and future needs
            contribution_analysis = await self._analyze_contributions(case_context)
            future_needs_analysis = await self._analyze_future_needs(case_context)
            
            # Generate scenarios
            scenarios = []
            
            # Scenario 1: Equal split (starting point)
            equal_scenario = await self._create_equal_split_scenario(net_pool, case_context)
            scenarios.append(equal_scenario)
            
            # Scenario 2: Contribution-adjusted split
            contribution_scenario = await self._create_contribution_adjusted_scenario(
                net_pool, contribution_analysis, case_context
            )
            scenarios.append(contribution_scenario)
            
            # Scenario 3: Future needs adjusted split
            future_needs_scenario = await self._create_future_needs_adjusted_scenario(
                net_pool, future_needs_analysis, case_context
            )
            scenarios.append(future_needs_scenario)
            
            # Scenario 4: Combined factors scenario (recommended)
            combined_scenario = await self._create_combined_factors_scenario(
                net_pool, contribution_analysis, future_needs_analysis, case_context
            )
            scenarios.append(combined_scenario)
            
            # Calculate tax implications for each scenario
            for scenario in scenarios:
                scenario.tax_implications = await self._calculate_tax_implications(
                    scenario, asset_pool, liability_pool
                )
            
            processing_time = time.time() - start_time
            logger.info(f"Generated {len(scenarios)} settlement scenarios in {processing_time:.2f}s")
            
            return scenarios
            
        except Exception as e:
            logger.error(f"Error calculating settlement scenarios: {e}")
            return []
    
    async def _analyze_contributions(self, case_context: Dict[str, Any]) -> Dict[str, float]:
        """Analyze contributions under s79 Family Law Act 1975"""
        
        # Default contribution scores (equal)
        contributions = {
            ContributionType.INITIAL_FINANCIAL.value: 0.0,
            ContributionType.ONGOING_FINANCIAL.value: 0.0,
            ContributionType.NON_FINANCIAL_DIRECT.value: 0.0,
            ContributionType.NON_FINANCIAL_INDIRECT.value: 0.0,
            ContributionType.HOMEMAKER_PARENT.value: 0.0,
            ContributionType.SPECIAL_CONTRIBUTION.value: 0.0
        }
        
        # Analyze case context for contribution indicators
        relationship_duration = case_context.get('relationship_duration_years', 10)
        children_involved = case_context.get('children_involved', False)
        primary_breadwinner = case_context.get('primary_breadwinner')  # 'party_1' or 'party_2'
        primary_homemaker = case_context.get('primary_homemaker')
        special_contributions = case_context.get('special_contributions', [])
        
        # Adjust for relationship duration
        if relationship_duration < 5:
            # Short relationship - initial contributions more significant
            contributions[ContributionType.INITIAL_FINANCIAL.value] = 0.3
        elif relationship_duration > 20:
            # Long relationship - ongoing contributions more significant
            contributions[ContributionType.ONGOING_FINANCIAL.value] = 0.2
        
        # Adjust for children and homemaking
        if children_involved:
            contributions[ContributionType.HOMEMAKER_PARENT.value] = 0.2
            contributions[ContributionType.NON_FINANCIAL_INDIRECT.value] = 0.1
        
        # Primary breadwinner advantage
        if primary_breadwinner == 'party_1':
            contributions[ContributionType.ONGOING_FINANCIAL.value] += 0.1
        elif primary_breadwinner == 'party_2':
            contributions[ContributionType.ONGOING_FINANCIAL.value] -= 0.1
        
        # Special contributions
        for special_contribution in special_contributions:
            contribution_type = special_contribution.get('type')
            value = special_contribution.get('adjustment', 0.0)
            
            if contribution_type in contributions:
                contributions[contribution_type] += value
        
        return contributions
    
    async def _analyze_future_needs(self, case_context: Dict[str, Any]) -> Dict[str, float]:
        """Analyze future needs under s75(2) Family Law Act 1975"""
        
        future_needs = {
            FutureNeedsFactor.AGE_HEALTH.value: 0.0,
            FutureNeedsFactor.INCOME_EARNING_CAPACITY.value: 0.0,
            FutureNeedsFactor.PROPERTY_RESOURCES.value: 0.0,
            FutureNeedsFactor.FINANCIAL_NEEDS.value: 0.0,
            FutureNeedsFactor.CARE_OF_CHILDREN.value: 0.0,
            FutureNeedsFactor.STANDARD_OF_LIVING.value: 0.0,
            FutureNeedsFactor.DURATION_OF_RELATIONSHIP.value: 0.0
        }
        
        # Analyze case context
        party_1_age = case_context.get('party_1_age', 40)
        party_2_age = case_context.get('party_2_age', 40)
        children_with_party = case_context.get('children_primary_residence')  # 'party_1' or 'party_2'
        income_disparity = case_context.get('income_disparity_ratio', 1.0)  # ratio of party_1 to party_2 income
        health_issues = case_context.get('health_issues', {})
        
        # Age and health adjustments
        age_difference = abs(party_1_age - party_2_age)
        if age_difference > 10:
            older_party = 'party_1' if party_1_age > party_2_age else 'party_2'
            future_needs[FutureNeedsFactor.AGE_HEALTH.value] = 0.1 if older_party == 'party_1' else -0.1
        
        # Health issues
        if health_issues.get('party_1'):
            future_needs[FutureNeedsFactor.AGE_HEALTH.value] += 0.1
        if health_issues.get('party_2'):
            future_needs[FutureNeedsFactor.AGE_HEALTH.value] -= 0.1
        
        # Income earning capacity
        if income_disparity > 1.5:  # Party 1 earns 50% more
            future_needs[FutureNeedsFactor.INCOME_EARNING_CAPACITY.value] = -0.1
        elif income_disparity < 0.67:  # Party 2 earns 50% more
            future_needs[FutureNeedsFactor.INCOME_EARNING_CAPACITY.value] = 0.1
        
        # Care of children
        if children_with_party == 'party_1':
            future_needs[FutureNeedsFactor.CARE_OF_CHILDREN.value] = 0.15
        elif children_with_party == 'party_2':
            future_needs[FutureNeedsFactor.CARE_OF_CHILDREN.value] = -0.15
        
        return future_needs
    
    async def _create_equal_split_scenario(self, net_pool: Decimal, case_context: Dict[str, Any]) -> SettlementScenario:
        """Create equal 50/50 split scenario"""
        
        party_1_share = net_pool / 2
        party_2_share = net_pool / 2
        
        return SettlementScenario(
            scenario_id="equal_split",
            scenario_name="Equal Split (50/50)",
            party_1_share=party_1_share,
            party_2_share=party_2_share,
            percentage_split=(50.0, 50.0),
            rationale="Equal division of matrimonial property as starting point under s79 Family Law Act 1975",
            contribution_adjustments={},
            future_needs_adjustments={},
            practical_considerations=[
                "Simple and fair division",
                "Minimizes disputes over contributions",
                "Suitable for relationships of moderate duration with similar contributions"
            ],
            tax_implications={},
            implementation_steps=[
                "Obtain agreement on asset valuations",
                "Determine method of division (sale vs transfer)",
                "Consider stamp duty and CGT implications"
            ],
            confidence_score=0.8
        )
    
    async def _create_contribution_adjusted_scenario(self, 
                                                   net_pool: Decimal, 
                                                   contributions: Dict[str, float],
                                                   case_context: Dict[str, Any]) -> SettlementScenario:
        """Create scenario adjusted for contributions"""
        
        # Calculate total contribution adjustment
        total_adjustment = sum(contributions.values())
        
        # Cap adjustment at reasonable limits
        total_adjustment = max(-0.20, min(0.20, total_adjustment))  # ±20% maximum
        
        # Calculate split
        party_1_percentage = 0.5 + total_adjustment
        party_2_percentage = 0.5 - total_adjustment
        
        party_1_share = net_pool * Decimal(str(party_1_percentage))
        party_2_share = net_pool * Decimal(str(party_2_percentage))
        
        return SettlementScenario(
            scenario_id="contribution_adjusted",
            scenario_name=f"Contribution Adjusted ({party_1_percentage:.0%}/{party_2_percentage:.0%})",
            party_1_share=party_1_share,
            party_2_share=party_2_share,
            percentage_split=(party_1_percentage * 100, party_2_percentage * 100),
            rationale=f"Adjusted for contributions under s79(4)(a)-(c) Family Law Act 1975. Total adjustment: {total_adjustment:+.1%}",
            contribution_adjustments=contributions,
            future_needs_adjustments={},
            practical_considerations=[
                "Recognizes different contribution levels",
                "May require detailed evidence of contributions",
                "Consider whether contributions are quantifiable"
            ],
            tax_implications={},
            implementation_steps=[
                "Document and quantify contributions",
                "Obtain valuations at time of contributions",
                "Consider inflation and opportunity cost"
            ],
            confidence_score=0.7
        )
    
    async def _create_future_needs_adjusted_scenario(self, 
                                                   net_pool: Decimal,
                                                   future_needs: Dict[str, float],
                                                   case_context: Dict[str, Any]) -> SettlementScenario:
        """Create scenario adjusted for future needs"""
        
        # Calculate total future needs adjustment
        total_adjustment = sum(future_needs.values())
        
        # Cap adjustment
        total_adjustment = max(-0.25, min(0.25, total_adjustment))  # ±25% maximum
        
        # Calculate split
        party_1_percentage = 0.5 + total_adjustment
        party_2_percentage = 0.5 - total_adjustment
        
        party_1_share = net_pool * Decimal(str(party_1_percentage))
        party_2_share = net_pool * Decimal(str(party_2_percentage))
        
        return SettlementScenario(
            scenario_id="future_needs_adjusted",
            scenario_name=f"Future Needs Adjusted ({party_1_percentage:.0%}/{party_2_percentage:.0%})",
            party_1_share=party_1_share,
            party_2_share=party_2_share,
            percentage_split=(party_1_percentage * 100, party_2_percentage * 100),
            rationale=f"Adjusted for future needs under s75(2) Family Law Act 1975. Total adjustment: {total_adjustment:+.1%}",
            contribution_adjustments={},
            future_needs_adjustments=future_needs,
            practical_considerations=[
                "Addresses future financial needs",
                "Considers care of children and earning capacity",
                "May require ongoing maintenance in addition"
            ],
            tax_implications={},
            implementation_steps=[
                "Assess ongoing financial needs",
                "Consider interaction with spousal maintenance",
                "Plan for children's expenses if applicable"
            ],
            confidence_score=0.75
        )
    
    async def _create_combined_factors_scenario(self, 
                                              net_pool: Decimal,
                                              contributions: Dict[str, float],
                                              future_needs: Dict[str, float],
                                              case_context: Dict[str, Any]) -> SettlementScenario:
        """Create scenario combining contributions and future needs"""
        
        # Weight contributions and future needs
        contribution_adjustment = sum(contributions.values()) * self.factor_weights['contributions']
        future_needs_adjustment = sum(future_needs.values()) * self.factor_weights['future_needs']
        
        total_adjustment = contribution_adjustment + future_needs_adjustment
        
        # Cap total adjustment
        total_adjustment = max(-0.30, min(0.30, total_adjustment))  # ±30% maximum
        
        # Calculate split
        party_1_percentage = 0.5 + total_adjustment
        party_2_percentage = 0.5 - total_adjustment
        
        party_1_share = net_pool * Decimal(str(party_1_percentage))
        party_2_share = net_pool * Decimal(str(party_2_percentage))
        
        return SettlementScenario(
            scenario_id="combined_factors",
            scenario_name=f"Combined Factors ({party_1_percentage:.0%}/{party_2_percentage:.0%}) - RECOMMENDED",
            party_1_share=party_1_share,
            party_2_share=party_2_share,
            percentage_split=(party_1_percentage * 100, party_2_percentage * 100),
            rationale=f"Comprehensive analysis under s79 and s75 Family Law Act 1975. "
                     f"Contributions: {contribution_adjustment:+.1%}, Future needs: {future_needs_adjustment:+.1%}",
            contribution_adjustments=contributions,
            future_needs_adjustments=future_needs,
            practical_considerations=[
                "Balanced approach considering all statutory factors",
                "Most defensible in court proceedings",
                "Addresses both past contributions and future needs"
            ],
            tax_implications={},
            implementation_steps=[
                "Prepare comprehensive evidence of contributions",
                "Document future needs assessment",
                "Consider tax-effective implementation methods",
                "Plan for any ongoing maintenance requirements"
            ],
            confidence_score=0.9
        )
    
    async def _calculate_tax_implications(self, 
                                        scenario: SettlementScenario,
                                        asset_pool: List[FinancialAsset],
                                        liability_pool: List[FinancialLiability]) -> Dict[str, Any]:
        """Calculate tax implications for settlement scenario"""
        
        tax_implications = {
            'stamp_duty_estimated': Decimal('0.00'),
            'cgt_implications': [],
            'depreciation_recapture': Decimal('0.00'),
            'gst_implications': [],
            'recommendations': []
        }
        
        # Estimate stamp duty for real estate transfers
        real_estate_assets = [asset for asset in asset_pool if asset.category == AustralianAssetCategory.REAL_ESTATE]
        
        for asset in real_estate_assets:
            # Simplified stamp duty calculation (varies by state)
            # Using NSW rates as example - would need state-specific calculations
            if asset.current_value > Decimal('1000000'):
                stamp_duty_rate = Decimal('0.055')  # 5.5% for properties over $1M
            else:
                stamp_duty_rate = Decimal('0.04')   # 4% for properties under $1M
            
            estimated_duty = asset.current_value * stamp_duty_rate
            tax_implications['stamp_duty_estimated'] += estimated_duty
        
        # CGT implications for investment properties and businesses
        investment_assets = [asset for asset in asset_pool 
                           if asset.category in [AustralianAssetCategory.INVESTMENTS, 
                                               AustralianAssetCategory.BUSINESS_INTERESTS]]
        
        for asset in investment_assets:
            tax_implications['cgt_implications'].append({
                'asset_id': asset.asset_id,
                'asset_description': asset.description,
                'potential_cgt_event': True,
                'recommendation': 'Obtain tax advice on CGT rollover relief under Subdivision 126-A ITAA 1997'
            })
        
        # General recommendations
        tax_implications['recommendations'] = [
            "Consider family law property settlement CGT rollover relief",
            "Plan timing of asset transfers to minimize tax impact",
            "Obtain professional tax advice before implementation",
            "Consider establishing binding financial agreement to document settlement"
        ]
        
        return tax_implications
    
    async def calculate_superannuation_splitting(self, 
                                               super_assets: List[FinancialAsset],
                                               case_context: Dict[str, Any]) -> SuperannuationSplitting:
        """Calculate superannuation splitting scenarios"""
        
        total_super = sum(asset.current_value for asset in super_assets)
        
        # Standard splitting scenarios
        scenarios = [
            {
                'scenario_name': 'Equal Split',
                'party_1_share': total_super / 2,
                'party_2_share': total_super / 2,
                'rationale': 'Equal division of superannuation interests'
            },
            {
                'scenario_name': 'Proportional to Contributions',
                'party_1_share': total_super * Decimal('0.6'),
                'party_2_share': total_super * Decimal('0.4'),
                'rationale': 'Proportional to estimated contribution levels'
            }
        ]
        
        return SuperannuationSplitting(
            total_super_pool=total_super,
            splitting_scenarios=scenarios,
            tax_implications={
                'no_immediate_tax': True,
                'preservation_maintained': True,
                'future_tax_implications': 'Tax payable when benefits accessed'
            },
            preservation_requirements={
                'preservation_age': 'Varies by birth date (55-60 years)',
                'conditions_of_release': 'Retirement, death, disability, financial hardship'
            },
            payment_methods=['Lump sum', 'Pension', 'Combination'],
            recommended_approach='Equal split with preservation maintained'
        )

# Adaptive Engine Pattern following existing architecture
class AustralianFamilyLawFinancialEngine:
    """
    Main financial settlement analysis engine following the adaptive pattern
    Automatically selects database vs legacy mode like other core components
    """
    
    def __init__(self, firm_id: str = None, user_id: str = None):
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Initialize core components
        self.asset_classifier = PropertyAssetClassifier(firm_id=firm_id, user_id=user_id)
        self.valuation_tracker = PropertyValuationTracker(firm_id=firm_id, user_id=user_id)
        self.form13_analyzer = Form13ComplianceAnalyzer(firm_id=firm_id, user_id=user_id)
        self.settlement_calculator = PropertySettlementCalculator(firm_id=firm_id, user_id=user_id)
        
        # Performance metrics
        self.engine_metrics = {
            'analyses_completed': 0,
            'average_processing_time': 0.0,
            'total_processing_time': 0.0
        }
        
        logger.info(f"AustralianFamilyLawFinancialEngine initialized for firm: {firm_id}")
    
    async def analyze_financial_documents(self, 
                                        documents: List[bytes], 
                                        case_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive financial analysis for property settlements
        Main entry point for document-based financial analysis
        """
        
        start_time = time.time()
        
        try:
            # Extract financial entities from documents
            financial_entities = await self._extract_financial_entities(documents)
            
            # Classify assets and liabilities
            asset_pool = await self._create_asset_pool(financial_entities['assets'])
            liability_pool = await self._create_liability_pool(financial_entities['liabilities'])
            
            # Analyze Form 13 compliance if present
            form13_analysis = None
            if financial_entities.get('form13_document'):
                form13_analysis = await self.form13_analyzer.analyze_form13_compliance(
                    financial_entities['form13_document']
                )
            
            # Calculate settlement scenarios
            settlement_scenarios = await self.settlement_calculator.calculate_settlement_scenarios(
                asset_pool, liability_pool, case_context or {}
            )
            
            # Analyze superannuation splitting
            super_assets = [asset for asset in asset_pool 
                          if asset.category == AustralianAssetCategory.SUPERANNUATION]
            super_splitting = await self.settlement_calculator.calculate_superannuation_splitting(
                super_assets, case_context or {}
            )
            
            # Detect disclosure gaps
            disclosure_gaps = await self._detect_disclosure_gaps(asset_pool, liability_pool, case_context)
            
            processing_time = time.time() - start_time
            
            # Update metrics
            self.engine_metrics['analyses_completed'] += 1
            self.engine_metrics['total_processing_time'] += processing_time
            self.engine_metrics['average_processing_time'] = (
                self.engine_metrics['total_processing_time'] / 
                self.engine_metrics['analyses_completed']
            )
            
            logger.info(f"Financial analysis completed in {processing_time:.2f}s")
            
            return {
                'analysis_summary': {
                    'total_documents_processed': len(documents),
                    'total_asset_pool': sum(asset.current_value for asset in asset_pool),
                    'total_liabilities': sum(liability.current_balance for liability in liability_pool),
                    'net_asset_pool': sum(asset.current_value for asset in asset_pool) - 
                                    sum(liability.current_balance for liability in liability_pool),
                    'analysis_timestamp': datetime.now(),
                    'processing_time_seconds': processing_time
                },
                'asset_pool_analysis': {
                    'total_assets': len(asset_pool),
                    'asset_breakdown': self._summarize_asset_breakdown(asset_pool),
                    'valuation_issues': await self._identify_valuation_issues(asset_pool)
                },
                'liability_analysis': {
                    'total_liabilities': len(liability_pool),
                    'liability_breakdown': self._summarize_liability_breakdown(liability_pool)
                },
                'form13_compliance': form13_analysis,
                'settlement_scenarios': settlement_scenarios,
                'superannuation_splitting': super_splitting,
                'disclosure_analysis': {
                    'completeness_score': self._calculate_disclosure_completeness(asset_pool, liability_pool),
                    'missing_disclosures': disclosure_gaps,
                    'red_flags': self._identify_financial_red_flags(asset_pool, liability_pool)
                },
                'recommendations': self._generate_strategic_recommendations(
                    asset_pool, liability_pool, settlement_scenarios, form13_analysis
                ),
                'performance_metrics': self.engine_metrics.copy()
            }
            
        except Exception as e:
            logger.error(f"Financial analysis error: {e}")
            return {
                'error': str(e),
                'analysis_summary': {
                    'total_documents_processed': len(documents),
                    'analysis_timestamp': datetime.now(),
                    'processing_time_seconds': time.time() - start_time
                }
            }
    
    async def _extract_financial_entities(self, documents: List[bytes]) -> Dict[str, Any]:
        """Extract financial entities from documents using AI and pattern matching"""
        
        entities = {
            'assets': [],
            'liabilities': [],
            'income_items': [],
            'expense_items': [],
            'form13_document': None
        }
        
        # Process each document
        for i, doc_content in enumerate(documents):
            try:
                # Use document processor if available
                if CORE_SYSTEMS_AVAILABLE:
                    doc_processor = DocumentProcessor(firm_id=self.firm_id, user_id=self.user_id)
                    result = doc_processor.process_document(doc_content, f"financial_doc_{i}.pdf")
                    
                    if result.success:
                        text_content = result.extracted_text
                    else:
                        continue
                else:
                    # Fallback text extraction
                    text_content = doc_content.decode('utf-8', errors='ignore')
                
                # Extract entities from text
                doc_entities = await self._extract_entities_from_text(text_content, i)
                
                # Merge entities
                entities['assets'].extend(doc_entities.get('assets', []))
                entities['liabilities'].extend(doc_entities.get('liabilities', []))
                entities['income_items'].extend(doc_entities.get('income_items', []))
                entities['expense_items'].extend(doc_entities.get('expense_items', []))
                
                # Check if this is a Form 13
                if 'form 13' in text_content.lower() or 'financial statement' in text_content.lower():
                    entities['form13_document'] = doc_content
                
            except Exception as e:
                logger.warning(f"Error processing document {i}: {e}")
                continue
        
        return entities
    
    async def _extract_entities_from_text(self, text: str, doc_index: int) -> Dict[str, List]:
        """Extract financial entities from document text"""
        
        entities = {
            'assets': [],
            'liabilities': [],
            'income_items': [],
            'expense_items': []
        }
        
        # Simple pattern-based extraction (in production would use more sophisticated NLP)
        lines = text.split('\n')
        
        # Look for asset patterns
        asset_patterns = [
            r'property.*\$([0-9,]+)',
            r'bank.*account.*\$([0-9,]+)',
            r'superannuation.*\$([0-9,]+)',
            r'vehicle.*\$([0-9,]+)',
            r'shares.*\$([0-9,]+)'
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Skip empty lines
            if not line_lower:
                continue
            
            # Extract dollar amounts
            dollar_matches = re.findall(r'\$([0-9,]+(?:\.[0-9]{2})?)', line)
            
            if dollar_matches:
                amount_str = dollar_matches[0].replace(',', '')
                try:
                    amount = Decimal(amount_str)
                    
                    # Classify as asset or liability based on context
                    if any(keyword in line_lower for keyword in ['owing', 'debt', 'loan', 'mortgage', 'credit card']):
                        entities['liabilities'].append({
                            'id': f'liability_{doc_index}_{len(entities["liabilities"])}',
                            'description': line.strip(),
                            'amount': amount,
                            'source_document': doc_index
                        })
                    elif any(keyword in line_lower for keyword in ['property', 'account', 'super', 'vehicle', 'shares', 'asset']):
                        entities['assets'].append({
                            'id': f'asset_{doc_index}_{len(entities["assets"])}',
                            'description': line.strip(),
                            'value': amount,
                            'source_document': doc_index
                        })
                
                except (ValueError, InvalidOperation):
                    continue
        
        return entities
    
    async def _create_asset_pool(self, asset_data: List[Dict]) -> List[FinancialAsset]:
        """Create FinancialAsset objects from extracted data"""
        
        asset_pool = []
        
        for asset_info in asset_data:
            # Classify asset
            category, confidence = await self.asset_classifier.classify_asset(
                asset_info['description'], 
                asset_info.get('value', Decimal('0'))
            )
            
            # Create FinancialAsset
            asset = FinancialAsset(
                asset_id=asset_info['id'],
                category=category,
                description=asset_info['description'],
                current_value=asset_info.get('value', Decimal('0')),
                valuation_date=datetime.now(),
                valuation_method='document_extraction',
                joint_ownership=False,  # Would need to be determined from document analysis
                metadata={
                    'source_document': asset_info.get('source_document'),
                    'classification_confidence': confidence,
                    'extraction_method': 'pattern_matching'
                }
            )
            
            asset_pool.append(asset)
        
        return asset_pool
    
    async def _create_liability_pool(self, liability_data: List[Dict]) -> List[FinancialLiability]:
        """Create FinancialLiability objects from extracted data"""
        
        liability_pool = []
        
        for liability_info in liability_data:
            # Classify liability (simplified classification)
            description_lower = liability_info['description'].lower()
            
            if 'mortgage' in description_lower:
                category = AustralianLiabilityCategory.MORTGAGES
            elif 'credit card' in description_lower:
                category = AustralianLiabilityCategory.CREDIT_CARDS
            elif 'loan' in description_lower:
                category = AustralianLiabilityCategory.PERSONAL_LOANS
            else:
                category = AustralianLiabilityCategory.OTHER_LIABILITIES
            
            # Create FinancialLiability
            liability = FinancialLiability(
                liability_id=liability_info['id'],
                category=category,
                description=liability_info['description'],
                current_balance=liability_info.get('amount', Decimal('0')),
                original_amount=liability_info.get('amount', Decimal('0')),  # Would need historical data
                creditor='Unknown',  # Would need to be extracted
                joint_liability=False,  # Would need to be determined
                metadata={
                    'source_document': liability_info.get('source_document'),
                    'extraction_method': 'pattern_matching'
                }
            )
            
            liability_pool.append(liability)
        
        return liability_pool
    
    def _summarize_asset_breakdown(self, asset_pool: List[FinancialAsset]) -> Dict[str, Any]:
        """Summarize asset pool by category"""
        
        breakdown = {}
        
        for asset in asset_pool:
            category = asset.category.value
            
            if category not in breakdown:
                breakdown[category] = {
                    'count': 0,
                    'total_value': Decimal('0.00'),
                    'assets': []
                }
            
            breakdown[category]['count'] += 1
            breakdown[category]['total_value'] += asset.current_value
            breakdown[category]['assets'].append({
                'id': asset.asset_id,
                'description': asset.description,
                'value': asset.current_value
            })
        
        return breakdown
    
    def _summarize_liability_breakdown(self, liability_pool: List[FinancialLiability]) -> Dict[str, Any]:
        """Summarize liability pool by category"""
        
        breakdown = {}
        
        for liability in liability_pool:
            category = liability.category.value
            
            if category not in breakdown:
                breakdown[category] = {
                    'count': 0,
                    'total_balance': Decimal('0.00'),
                    'liabilities': []
                }
            
            breakdown[category]['count'] += 1
            breakdown[category]['total_balance'] += liability.current_balance
            breakdown[category]['liabilities'].append({
                'id': liability.liability_id,
                'description': liability.description,
                'balance': liability.current_balance
            })
        
        return breakdown
    
    async def _identify_valuation_issues(self, asset_pool: List[FinancialAsset]) -> List[Dict[str, Any]]:
        """Identify potential valuation issues"""
        
        issues = []
        
        for asset in asset_pool:
            # Check for stale valuations
            valuation_age = (datetime.now() - asset.valuation_date).days
            
            if valuation_age > 365:  # Older than 1 year
                issues.append({
                    'asset_id': asset.asset_id,
                    'issue_type': 'stale_valuation',
                    'description': f"Valuation is {valuation_age} days old",
                    'severity': 'medium',
                    'recommendation': 'Obtain updated valuation'
                })
            
            # Check for round number valuations (potential estimates)
            if asset.current_value % 1000 == 0 and asset.current_value > 10000:
                issues.append({
                    'asset_id': asset.asset_id,
                    'issue_type': 'round_number_valuation',
                    'description': f"Valuation appears to be rounded (${asset.current_value:,.2f})",
                    'severity': 'low',
                    'recommendation': 'Verify if valuation is estimate or precise figure'
                })
        
        return issues
    
    async def _detect_disclosure_gaps(self, 
                                    asset_pool: List[FinancialAsset], 
                                    liability_pool: List[FinancialLiability],
                                    case_context: Dict[str, Any]) -> List[str]:
        """Detect potential gaps in financial disclosure"""
        
        gaps = []
        
        # Check for missing asset categories
        present_categories = set(asset.category for asset in asset_pool)
        expected_categories = {
            AustralianAssetCategory.BANK_ACCOUNTS,
            AustralianAssetCategory.SUPERANNUATION
        }
        
        missing_categories = expected_categories - present_categories
        
        for category in missing_categories:
            gaps.append(f"No {category.value.replace('_', ' ')} disclosed - unusual for most cases")
        
        # Check for unusually low asset pool
        total_assets = sum(asset.current_value for asset in asset_pool)
        if total_assets < 50000:  # Less than $50k seems low for property settlement
            gaps.append("Total asset pool appears unusually low for property settlement case")
        
        # Check income vs assets consistency
        if case_context and case_context.get('annual_income'):
            annual_income = case_context['annual_income']
            if total_assets < annual_income * 0.5:  # Assets less than 6 months income
                gaps.append("Asset pool appears low relative to reported income")
        
        return gaps
    
    def _calculate_disclosure_completeness(self, 
                                         asset_pool: List[FinancialAsset], 
                                         liability_pool: List[FinancialLiability]) -> float:
        """Calculate overall disclosure completeness score"""
        
        # Check for presence of major asset categories
        present_asset_categories = set(asset.category for asset in asset_pool)
        present_liability_categories = set(liability.category for liability in liability_pool)
        
        # Expected categories for typical family law case
        expected_asset_categories = {
            AustralianAssetCategory.REAL_ESTATE,
            AustralianAssetCategory.BANK_ACCOUNTS,
            AustralianAssetCategory.SUPERANNUATION,
            AustralianAssetCategory.VEHICLES
        }
        
        expected_liability_categories = {
            AustralianLiabilityCategory.MORTGAGES,
            AustralianLiabilityCategory.CREDIT_CARDS
        }
        
        # Calculate completeness
        asset_completeness = len(present_asset_categories & expected_asset_categories) / len(expected_asset_categories)
        liability_completeness = len(present_liability_categories & expected_liability_categories) / len(expected_liability_categories)
        
        # Weight assets more heavily
        overall_completeness = (asset_completeness * 0.7) + (liability_completeness * 0.3)
        
        return overall_completeness
    
    def _identify_financial_red_flags(self, 
                                    asset_pool: List[FinancialAsset], 
                                    liability_pool: List[FinancialLiability]) -> List[str]:
        """Identify financial red flags requiring attention"""
        
        red_flags = []
        
        # Check for negative net worth
        total_assets = sum(asset.current_value for asset in asset_pool)
        total_liabilities = sum(liability.current_balance for liability in liability_pool)
        
        if total_assets < total_liabilities:
            red_flags.append("Negative net worth - liabilities exceed assets")
        
        # Check for disproportionate cash holdings
        cash_assets = [asset for asset in asset_pool if asset.category == AustralianAssetCategory.BANK_ACCOUNTS]
        total_cash = sum(asset.current_value for asset in cash_assets)
        
        if total_assets > 0 and (total_cash / total_assets) > 0.5:
            red_flags.append("Unusually high proportion of assets in cash - potential asset concealment")
        
        # Check for missing superannuation
        super_assets = [asset for asset in asset_pool if asset.category == AustralianAssetCategory.SUPERANNUATION]
        if not super_assets:
            red_flags.append("No superannuation disclosed - required for most employed individuals")
        
        return red_flags
    
    def _generate_strategic_recommendations(self, 
                                          asset_pool: List[FinancialAsset],
                                          liability_pool: List[FinancialLiability],
                                          settlement_scenarios: List[SettlementScenario],
                                          form13_analysis: Optional[Form13Analysis]) -> List[str]:
        """Generate strategic recommendations for the case"""
        
        recommendations = []
        
        # Asset pool recommendations
        total_assets = sum(asset.current_value for asset in asset_pool)
        
        if total_assets > 2000000:  # High value case
            recommendations.append("High value case - consider engaging forensic accountant and obtaining independent valuations")
        
        # Form 13 recommendations
        if form13_analysis and form13_analysis.completeness_score < 0.8:
            recommendations.append(f"Form 13 completeness score is {form13_analysis.completeness_score:.1%} - request additional disclosure")
        
        # Settlement scenario recommendations
        if settlement_scenarios:
            recommended_scenario = max(settlement_scenarios, key=lambda s: s.confidence_score)
            recommendations.append(f"Recommended settlement approach: {recommended_scenario.scenario_name}")
        
        # Valuation recommendations
        real_estate_assets = [asset for asset in asset_pool if asset.category == AustralianAssetCategory.REAL_ESTATE]
        if real_estate_assets:
            recommendations.append("Obtain current independent valuations for all real estate assets")
        
        business_assets = [asset for asset in asset_pool if asset.category == AustralianAssetCategory.BUSINESS_INTERESTS]
        if business_assets:
            recommendations.append("Engage business valuator for accurate assessment of business interests")
        
        return recommendations

# Export main classes following existing pattern
__all__ = [
    'AustralianFamilyLawFinancialEngine',
    'PropertyAssetClassifier',
    'PropertyValuationTracker', 
    'Form13ComplianceAnalyzer',
    'PropertySettlementCalculator',
    'AustralianAssetCategory',
    'AustralianLiabilityCategory',
    'FinancialAsset',
    'FinancialLiability',
    'Form13Analysis',
    'SettlementScenario',
    'SuperannuationSplitting'
]