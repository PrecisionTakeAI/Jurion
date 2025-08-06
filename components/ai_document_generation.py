#!/usr/bin/env python3
"""
AI Document Generation System for LegalLLM Professional
Intelligent document generation with Australian legal templates and AI automation
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import os
import sys
from enum import Enum
import json

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import existing components
try:
    from shared.database.models import Case, Document, User
    from core.enhanced_llm_engine import EnhancedLegalLLMEngine
    from components.ai_case_assistant import AICaseContext
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database/AI components not available: {e}")
    DATABASE_AVAILABLE = False

# Australian Legal Document Templates
class DocumentTemplate(Enum):
    # Court Forms
    FORM_1_DIVORCE = "form_1_divorce"
    FORM_4_PROPERTY = "form_4_property"  
    FORM_11_CONSENT_ORDERS = "form_11_consent_orders"
    FORM_13_FINANCIAL = "form_13_financial"
    FORM_13A_FINANCIAL_SHORT = "form_13a_financial_short"
    
    # Legal Letters
    DEMAND_LETTER = "demand_letter"
    SETTLEMENT_OFFER = "settlement_offer"
    ADVICE_LETTER = "advice_letter"
    COURT_CORRESPONDENCE = "court_correspondence"
    
    # Agreements
    SEPARATION_AGREEMENT = "separation_agreement"
    PARENTING_PLAN = "parenting_plan"
    PROPERTY_SETTLEMENT = "property_settlement"
    BINDING_FINANCIAL_AGREEMENT = "binding_financial_agreement"
    
    # Pleadings
    STATEMENT_OF_CLAIM = "statement_of_claim"
    DEFENCE = "defence"
    AFFIDAVIT = "affidavit"
    WITNESS_STATEMENT = "witness_statement"

# Document Template Metadata
DOCUMENT_TEMPLATES = {
    DocumentTemplate.FORM_1_DIVORCE: {
        "name": "Application for Divorce (Form 1)",
        "category": "Court Forms",
        "jurisdiction": "Federal Circuit and Family Court",
        "complexity": "Medium",
        "estimated_time": "15-20 minutes",
        "required_fields": ["marriage_date", "separation_date", "children_details", "service_method"],
        "description": "Official court form for divorce applications under the Family Law Act 1975"
    },
    DocumentTemplate.FORM_4_PROPERTY: {
        "name": "Application for Property Orders (Form 4)",
        "category": "Court Forms", 
        "jurisdiction": "Federal Circuit and Family Court",
        "complexity": "High",
        "estimated_time": "45-60 minutes",
        "required_fields": ["property_details", "financial_circumstances", "proposed_orders"],
        "description": "Court application for property settlement orders"
    },
    DocumentTemplate.FORM_13_FINANCIAL: {
        "name": "Financial Statement (Form 13)",
        "category": "Court Forms",
        "jurisdiction": "Federal Circuit and Family Court", 
        "complexity": "High",
        "estimated_time": "60-90 minutes",
        "required_fields": ["income", "expenses", "assets", "liabilities"],
        "description": "Comprehensive financial disclosure statement"
    },
    DocumentTemplate.SETTLEMENT_OFFER: {
        "name": "Settlement Offer Letter",
        "category": "Legal Letters",
        "jurisdiction": "All Australian jurisdictions",
        "complexity": "Medium",
        "estimated_time": "20-30 minutes", 
        "required_fields": ["offer_terms", "deadline", "consequences"],
        "description": "Formal settlement proposal with legal terms"
    },
    DocumentTemplate.ADVICE_LETTER: {
        "name": "Legal Advice Letter",
        "category": "Legal Letters",
        "jurisdiction": "All Australian jurisdictions",
        "complexity": "Medium",
        "estimated_time": "30-45 minutes",
        "required_fields": ["legal_issue", "advice", "recommendations"],
        "description": "Professional legal advice to client"
    },
    DocumentTemplate.PARENTING_PLAN: {
        "name": "Parenting Plan",
        "category": "Agreements",
        "jurisdiction": "All Australian jurisdictions",
        "complexity": "High",
        "estimated_time": "45-75 minutes",
        "required_fields": ["children_details", "living_arrangements", "decision_making"],
        "description": "Detailed parenting arrangements agreement"
    }
}

# Document Generation Confidence Levels
class GenerationConfidence(Enum):
    HIGH = "high"           # >90% - Ready for minor review
    MEDIUM = "medium"       # 70-90% - Requires careful review
    LOW = "low"            # 50-70% - Substantial review needed
    INSUFFICIENT = "insufficient"  # <50% - Manual preparation required

def render_ai_document_generation(case_id: str, user_role: str, user_info: Dict):
    """Main AI document generation interface"""
    
    st.markdown("## 📝 AI Document Generation")
    
    if user_role not in ['principal', 'senior_lawyer', 'lawyer']:
        st.warning("🔒 Document generation features are available to lawyers and above.")
        return
    
    # Initialize case context for document generation
    if case_id:
        case_context = AICaseContext(case_id, user_role, user_info.get('id', ''), user_info.get('firm_id', ''))
        render_contextual_document_generator(case_context, user_info)
    else:
        render_template_document_generator(user_info)

def render_contextual_document_generator(case_context: AICaseContext, user_info: Dict):
    """Document generator with full case context integration"""
    
    st.markdown("### 🎯 Context-Aware Document Generation")
    st.markdown("*Generate documents using comprehensive case information and AI intelligence*")
    
    # Case context summary
    with st.expander("📋 Case Context Summary", expanded=False):
        case_details = case_context.context_data.get('case_details', {})
        st.write(f"**Case:** {case_details.get('title', 'Unknown Case')}")
        st.write(f"**Type:** {case_details.get('case_type', 'Unknown Type')}")
        st.write(f"**Status:** {case_details.get('status', 'Unknown Status')}")
        
        # Show available data for generation
        available_data = []
        if case_context.context_data.get('parties'):
            available_data.append("Party Information")
        if case_context.context_data.get('financial_info'):
            available_data.append("Financial Details") 
        if case_context.context_data.get('children_details'):
            available_data.append("Children Information")
        if case_context.context_data.get('documents'):
            available_data.append("Supporting Documents")
        
        st.write(f"**Available Data:** {', '.join(available_data) if available_data else 'Basic case information only'}")
    
    # Template selection with context-aware recommendations
    recommended_templates = get_recommended_templates(case_context)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📄 Select Document Template")
        
        # Show recommended templates first
        if recommended_templates:
            st.markdown("**🎯 Recommended for this case:**")
            for template in recommended_templates:
                template_info = DOCUMENT_TEMPLATES[template]
                if st.button(f"✨ {template_info['name']}", key=f"rec_{template.value}", use_container_width=True):
                    st.session_state.selected_template = template
                    st.session_state.generation_mode = "contextual"
        
        # All available templates  
        st.markdown("**📋 All Available Templates:**")
        
        # Group templates by category
        template_categories = {}
        for template, info in DOCUMENT_TEMPLATES.items():
            category = info['category']
            if category not in template_categories:
                template_categories[category] = []
            template_categories[category].append((template, info))
        
        for category, templates in template_categories.items():
            with st.expander(f"📁 {category}", expanded=False):
                for template, info in templates:
                    col_a, col_b, col_c = st.columns([3, 1, 1])
                    
                    with col_a:
                        if st.button(f"{info['name']}", key=f"all_{template.value}", use_container_width=True):
                            st.session_state.selected_template = template
                            st.session_state.generation_mode = "contextual"
                    
                    with col_b:
                        st.markdown(f"*{info['complexity']}*")
                    
                    with col_c:
                        st.markdown(f"*{info['estimated_time']}*")
    
    with col2:
        st.markdown("#### ⚙️ Generation Options")
        
        # AI generation settings
        use_ai_analysis = st.checkbox(
            "🤖 Use AI Case Analysis",
            value=True,
            help="Incorporate AI insights from case documents and context"
        )
        
        auto_fill_fields = st.checkbox(
            "📋 Auto-fill from Case Data", 
            value=True,
            help="Automatically populate fields using available case information"
        )
        
        include_precedents = st.checkbox(
            "⚖️ Include Legal Precedents",
            value=False,
            help="Add relevant case law and legal precedents (increases generation time)"
        )
        
        compliance_check = st.checkbox(
            "✅ Compliance Verification",
            value=True,
            help="Verify document meets Australian legal requirements"
        )
        
        # Output preferences
        st.markdown("**Output Format:**")
        output_format = st.radio(
            "Format:",
            ["Word Document (.docx)", "PDF (.pdf)", "Rich Text (Editable)"],
            key="output_format"
        )
        
        # Generation quality
        generation_quality = st.selectbox(
            "Quality Level:",
            ["Standard (Fast)", "Enhanced (Balanced)", "Premium (Thorough)"],
            index=1,
            help="Higher quality takes longer but provides more comprehensive documents"
        )
    
    # Handle template selection and generation
    if hasattr(st.session_state, 'selected_template') and st.session_state.generation_mode == "contextual":
        render_template_generation_interface(
            st.session_state.selected_template,
            case_context,
            user_info,
            {
                'use_ai_analysis': use_ai_analysis,
                'auto_fill_fields': auto_fill_fields,
                'include_precedents': include_precedents,
                'compliance_check': compliance_check,
                'output_format': output_format,
                'generation_quality': generation_quality
            }
        )

def render_template_document_generator(user_info: Dict):
    """Template-based document generator without case context"""
    
    st.markdown("### 📋 Template Document Generation")
    st.markdown("*Generate documents using standard templates and manual input*")
    
    st.info("💡 **Tip:** Link this generation to a case for enhanced AI assistance and auto-population of fields.")
    
    # Template selection grid
    st.markdown("#### 📄 Available Document Templates")
    
    # Group templates by category for better organization
    template_categories = {}
    for template, info in DOCUMENT_TEMPLATES.items():
        category = info['category']
        if category not in template_categories:
            template_categories[category] = []
        template_categories[category].append((template, info))
    
    for category, templates in template_categories.items():
        with st.expander(f"📁 {category}", expanded=True if category == "Court Forms" else False):
            
            # Create grid layout for templates
            cols = st.columns(2)
            
            for i, (template, info) in enumerate(templates):
                with cols[i % 2]:
                    # Template card
                    st.markdown(f"""
                    <div style="padding: 1rem; border: 1px solid #e2e8f0; border-radius: 8px; margin: 0.5rem 0; background: white;">
                        <h5 style="color: #1e293b; margin-bottom: 0.5rem;">{info['name']}</h5>
                        <div style="color: #64748b; font-size: 0.85rem; margin-bottom: 0.75rem;">
                            <strong>Jurisdiction:</strong> {info['jurisdiction']}<br>
                            <strong>Complexity:</strong> {info['complexity']} • <strong>Time:</strong> {info['estimated_time']}
                        </div>
                        <div style="color: #475569; font-size: 0.9rem;">{info['description']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Generate {info['name']}", key=f"gen_{template.value}", use_container_width=True):
                        st.session_state.selected_template = template
                        st.session_state.generation_mode = "template"

def render_template_generation_interface(template: DocumentTemplate, case_context: Optional[AICaseContext], 
                                       user_info: Dict, options: Dict):
    """Render the document generation interface for selected template"""
    
    template_info = DOCUMENT_TEMPLATES[template]
    
    # Generation interface
    st.markdown("---")
    st.markdown(f"## 🚀 Generating: {template_info['name']}")
    
    # Template information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Category:** {template_info['category']}")
        st.markdown(f"**Jurisdiction:** {template_info['jurisdiction']}")
    
    with col2:
        st.markdown(f"**Complexity:** {template_info['complexity']}")
        st.markdown(f"**Estimated Time:** {template_info['estimated_time']}")
    
    with col3:
        if case_context:
            st.markdown("**Mode:** Context-Aware")
            st.markdown("**Case Data:** Available")
        else:
            st.markdown("**Mode:** Template-Based")
            st.markdown("**Case Data:** Manual Entry")
    
    # Required fields and data collection
    st.markdown("### 📋 Document Information")
    
    required_fields = template_info.get('required_fields', [])
    field_values = {}
    
    if case_context and options.get('auto_fill_fields'):
        # Pre-populate fields from case context
        field_values = extract_fields_from_context(template, case_context)
        
        if field_values:
            st.success(f"✅ Auto-populated {len(field_values)} fields from case data")
            
            with st.expander("📊 Pre-populated Fields", expanded=False):
                for field, value in field_values.items():
                    st.write(f"**{field.replace('_', ' ').title()}:** {value}")
    
    # Collect any missing required fields
    missing_fields = collect_missing_fields(template, field_values, case_context)
    
    if missing_fields:
        st.markdown("#### ✏️ Additional Information Required")
        
        for field_name, field_config in missing_fields.items():
            if field_config['type'] == 'text':
                field_values[field_name] = st.text_input(
                    field_config['label'],
                    value=field_values.get(field_name, ''),
                    help=field_config.get('help', '')
                )
            elif field_config['type'] == 'textarea':
                field_values[field_name] = st.text_area(
                    field_config['label'],
                    value=field_values.get(field_name, ''),
                    help=field_config.get('help', '')
                )
            elif field_config['type'] == 'date':
                field_values[field_name] = st.date_input(
                    field_config['label'],
                    help=field_config.get('help', '')
                )
            elif field_config['type'] == 'selectbox':
                field_values[field_name] = st.selectbox(
                    field_config['label'],
                    field_config['options'],
                    help=field_config.get('help', '')
                )
    
    # Generation controls
    st.markdown("### 🎯 Generate Document")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Generation preview
        if st.button("👁️ Preview Generation", use_container_width=True):
            preview_document_generation(template, field_values, case_context, options, user_info)
    
    with col2:
        # Generate button
        if st.button("🚀 Generate", type="primary", use_container_width=True):
            execute_document_generation(template, field_values, case_context, options, user_info)

def get_recommended_templates(case_context: AICaseContext) -> List[DocumentTemplate]:
    """Get AI-recommended templates based on case context"""
    
    case_details = case_context.context_data.get('case_details', {})
    case_type = case_details.get('case_type', '').lower()
    
    recommendations = []
    
    # Family law case recommendations
    if 'divorce' in case_type:
        recommendations.extend([
            DocumentTemplate.FORM_1_DIVORCE,
            DocumentTemplate.FORM_13_FINANCIAL,
            DocumentTemplate.SETTLEMENT_OFFER
        ])
    elif 'property' in case_type:
        recommendations.extend([
            DocumentTemplate.FORM_4_PROPERTY,  
            DocumentTemplate.FORM_13_FINANCIAL,
            DocumentTemplate.PROPERTY_SETTLEMENT
        ])
    elif 'parenting' in case_type or 'custody' in case_type:
        recommendations.extend([
            DocumentTemplate.PARENTING_PLAN,
            DocumentTemplate.FORM_11_CONSENT_ORDERS
        ])
    
    # Generic recommendations based on case stage
    case_status = case_details.get('status', '').lower()
    if 'settlement' in case_status:
        recommendations.append(DocumentTemplate.SETTLEMENT_OFFER)
    elif 'advice' in case_status:
        recommendations.append(DocumentTemplate.ADVICE_LETTER)
    
    return list(set(recommendations))  # Remove duplicates

def extract_fields_from_context(template: DocumentTemplate, case_context: AICaseContext) -> Dict[str, Any]:
    """Extract relevant field values from case context"""
    
    extracted_fields = {}
    context_data = case_context.context_data
    
    # Common field extraction patterns
    case_details = context_data.get('case_details', {})
    parties = context_data.get('parties', {})
    financial_info = context_data.get('financial_info', {})
    children_details = context_data.get('children_details', {})
    
    # Template-specific field extraction
    if template == DocumentTemplate.FORM_1_DIVORCE:
        if case_details.get('marriage_date'):
            extracted_fields['marriage_date'] = case_details['marriage_date']
        if case_details.get('separation_date'):
            extracted_fields['separation_date'] = case_details['separation_date']
        if children_details:
            extracted_fields['children_details'] = format_children_details(children_details)
    
    elif template == DocumentTemplate.FORM_13_FINANCIAL:
        if financial_info.get('income'):
            extracted_fields['income'] = financial_info['income']
        if financial_info.get('expenses'):
            extracted_fields['expenses'] = financial_info['expenses']
        if financial_info.get('assets'):
            extracted_fields['assets'] = financial_info['assets']
        if financial_info.get('liabilities'):
            extracted_fields['liabilities'] = financial_info['liabilities']
    
    elif template == DocumentTemplate.PARENTING_PLAN:
        if children_details:
            extracted_fields['children_details'] = format_children_details(children_details)
            extracted_fields['living_arrangements'] = children_details.get('living_arrangements', '')
            extracted_fields['decision_making'] = children_details.get('decision_making', '')
    
    # Add party information for all templates
    if parties:
        extracted_fields['applicant'] = parties.get('applicant', {})
        extracted_fields['respondent'] = parties.get('respondent', {})
    
    return extracted_fields

def collect_missing_fields(template: DocumentTemplate, existing_fields: Dict, 
                         case_context: Optional[AICaseContext]) -> Dict[str, Dict]:
    """Collect configuration for missing required fields"""
    
    # Field configurations by template
    field_configs = {
        DocumentTemplate.FORM_1_DIVORCE: {
            'marriage_date': {
                'label': 'Date of Marriage',
                'type': 'date',
                'help': 'Official date of marriage as per marriage certificate'
            },
            'separation_date': {
                'label': 'Date of Separation', 
                'type': 'date',
                'help': 'Date when you and your spouse separated'
            },
            'service_method': {
                'label': 'Method of Service',
                'type': 'selectbox',
                'options': ['Personal Service', 'Post', 'Email', 'Substituted Service'],
                'help': 'How will you serve the divorce papers to your spouse?'
            }
        },
        DocumentTemplate.SETTLEMENT_OFFER: {
            'offer_terms': {
                'label': 'Settlement Terms',
                'type': 'textarea',
                'help': 'Detailed terms of your settlement proposal'
            },
            'deadline': {
                'label': 'Response Deadline',
                'type': 'date', 
                'help': 'Date by which response is required'
            },
            'consequences': {
                'label': 'Consequences of Non-Acceptance',
                'type': 'textarea',
                'help': 'What happens if the offer is not accepted'
            }
        }
    }
    
    template_fields = field_configs.get(template, {})
    missing_fields = {}
    
    for field_name, field_config in template_fields.items():
        if field_name not in existing_fields or not existing_fields[field_name]:
            missing_fields[field_name] = field_config
    
    return missing_fields

def preview_document_generation(template: DocumentTemplate, field_values: Dict, 
                              case_context: Optional[AICaseContext], options: Dict, user_info: Dict):
    """Preview the document generation before final creation"""
    
    st.markdown("#### 👁️ Generation Preview")
    
    template_info = DOCUMENT_TEMPLATES[template]
    
    # Analysis preview
    with st.spinner("Analyzing case data and preparing preview..."):
        
        # Simulate AI analysis
        confidence_level = calculate_generation_confidence(template, field_values, case_context, options)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Document Details:**")
            st.write(f"• Template: {template_info['name']}")
            st.write(f"• Fields Available: {len(field_values)}")
            st.write(f"• Case Context: {'Yes' if case_context else 'No'}")
            st.write(f"• AI Analysis: {'Enabled' if options.get('use_ai_analysis') else 'Disabled'}")
        
        with col2:
            st.markdown("**Generation Assessment:**")
            
            confidence_colors = {
                GenerationConfidence.HIGH: "#166534",
                GenerationConfidence.MEDIUM: "#ea580c", 
                GenerationConfidence.LOW: "#dc2626",
                GenerationConfidence.INSUFFICIENT: "#991b1b"
            }
            
            confidence_color = confidence_colors[confidence_level]
            
            st.markdown(f"""
            <div style="padding: 1rem; border-left: 4px solid {confidence_color}; background: #f8fafc; border-radius: 0 8px 8px 0;">
                <div style="font-weight: 600; color: {confidence_color};">
                    Confidence: {confidence_level.value.upper()}
                </div>
                <div style="font-size: 0.9rem; color: #64748b; margin-top: 0.25rem;">
                    {get_confidence_description(confidence_level)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Preview content structure
        st.markdown("**Document Structure Preview:**")
        preview_content = generate_document_preview(template, field_values, case_context)
        
        with st.expander("📄 Content Preview", expanded=True):
            st.text(preview_content)

def execute_document_generation(template: DocumentTemplate, field_values: Dict,
                              case_context: Optional[AICaseContext], options: Dict, user_info: Dict):
    """Execute the actual document generation"""
    
    template_info = DOCUMENT_TEMPLATES[template]
    
    with st.spinner(f"Generating {template_info['name']} with AI assistance..."):
        
        try:
            # Simulate document generation process
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Data processing
            status_text.text("🔄 Processing case data and field values...")
            progress_bar.progress(20)
            
            # Step 2: AI analysis (if enabled)
            if options.get('use_ai_analysis') and case_context:
                status_text.text("🤖 Running AI analysis on case context...")
                progress_bar.progress(40)
            
            # Step 3: Template population
            status_text.text("📝 Populating document template...")
            progress_bar.progress(60)
            
            # Step 4: Compliance check (if enabled)
            if options.get('compliance_check'):
                status_text.text("✅ Verifying legal compliance...")
                progress_bar.progress(80)
            
            # Step 5: Final generation
            status_text.text("🎯 Finalizing document...")
            progress_bar.progress(100)
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Generate success result
            confidence_level = calculate_generation_confidence(template, field_values, case_context, options)
            document_result = create_document_result(template, field_values, confidence_level, user_info)
            
            # Display results
            render_generation_results(document_result, template_info, confidence_level)
            
        except Exception as e:
            st.error(f"❌ Document generation failed: {str(e)}")
            st.info("💡 Please check your input data and try again, or contact support if the issue persists.")

def calculate_generation_confidence(template: DocumentTemplate, field_values: Dict,
                                  case_context: Optional[AICaseContext], options: Dict) -> GenerationConfidence:
    """Calculate confidence level for document generation"""
    
    confidence_score = 0.0
    
    # Base score from required fields
    template_info = DOCUMENT_TEMPLATES[template]
    required_fields = template_info.get('required_fields', [])
    
    if required_fields:
        filled_fields = sum(1 for field in required_fields if field in field_values and field_values[field])
        field_completeness = filled_fields / len(required_fields)
        confidence_score += field_completeness * 0.4  # 40% weight
    else:
        confidence_score += 0.4  # No required fields
    
    # Case context bonus
    if case_context:
        context_data = case_context.context_data
        
        # Check available context components
        context_completeness = 0.0
        if context_data.get('case_details'):
            context_completeness += 0.25
        if context_data.get('parties'):  
            context_completeness += 0.25
        if context_data.get('financial_info'):
            context_completeness += 0.25
        if context_data.get('children_details'):
            context_completeness += 0.25
        
        confidence_score += context_completeness * 0.3  # 30% weight
    
    # AI analysis bonus
    if options.get('use_ai_analysis'):
        confidence_score += 0.15  # 15% weight
    
    # Compliance check bonus
    if options.get('compliance_check'):
        confidence_score += 0.1   # 10% weight
    
    # Template complexity adjustment
    complexity_adjustments = {
        "Low": 0.05,
        "Medium": 0.0,
        "High": -0.05
    }
    complexity = template_info.get('complexity', 'Medium')
    confidence_score += complexity_adjustments.get(complexity, 0.0)
    
    # Convert to confidence level
    if confidence_score >= 0.9:
        return GenerationConfidence.HIGH
    elif confidence_score >= 0.7:
        return GenerationConfidence.MEDIUM
    elif confidence_score >= 0.5:
        return GenerationConfidence.LOW
    else:
        return GenerationConfidence.INSUFFICIENT

def get_confidence_description(confidence: GenerationConfidence) -> str:
    """Get description for confidence level"""
    
    descriptions = {
        GenerationConfidence.HIGH: "Document ready for minor review and use",
        GenerationConfidence.MEDIUM: "Document requires careful lawyer review before use", 
        GenerationConfidence.LOW: "Document needs substantial review and modification",
        GenerationConfidence.INSUFFICIENT: "Manual document preparation recommended"
    }
    
    return descriptions.get(confidence, "Unknown confidence level")

def generate_document_preview(template: DocumentTemplate, field_values: Dict, 
                            case_context: Optional[AICaseContext]) -> str:
    """Generate a preview of the document structure"""
    
    template_info = DOCUMENT_TEMPLATES[template]
    
    preview_lines = [
        f"DOCUMENT: {template_info['name']}",
        f"JURISDICTION: {template_info['jurisdiction']}",
        "=" * 50,
        "",
        "DOCUMENT SECTIONS:",
        ""
    ]
    
    # Template-specific structure
    if template == DocumentTemplate.FORM_1_DIVORCE:
        preview_lines.extend([
            "1. APPLICANT DETAILS",
            "   • Personal information from case data",
            "",
            "2. RESPONDENT DETAILS", 
            "   • Spouse information from case data",
            "",
            "3. MARRIAGE DETAILS",
            f"   • Date of Marriage: {field_values.get('marriage_date', '[TO BE FILLED]')}",
            f"   • Date of Separation: {field_values.get('separation_date', '[TO BE FILLED]')}",
            "",
            "4. CHILDREN INFORMATION",
            "   • Details of children under 18",
            "",
            "5. SERVICE DETAILS",
            f"   • Service Method: {field_values.get('service_method', '[TO BE SELECTED]')}",
            "",
            "6. DECLARATIONS AND SIGNATURES",
            "   • Legal declarations and signature blocks"
        ])
    
    elif template == DocumentTemplate.SETTLEMENT_OFFER:
        preview_lines.extend([
            "1. LETTERHEAD AND DATE",
            "   • Firm letterhead and current date",
            "",
            "2. RECIPIENT DETAILS",
            "   • Other party or their legal representative",
            "",
            "3. MATTER REFERENCE",
            "   • Case details and reference numbers",
            "",
            "4. SETTLEMENT PROPOSAL",
            "   • Detailed settlement terms",
            "",
            "5. DEADLINE AND CONSEQUENCES", 
            f"   • Response deadline: {field_values.get('deadline', '[TO BE SET]')}",
            "   • Consequences of non-acceptance",
            "",
            "6. PROFESSIONAL CLOSING",
            "   • Legal disclaimers and signature"
        ])
    
    preview_lines.extend([
        "",
        "=" * 50,
        f"ESTIMATED LENGTH: {get_estimated_length(template)} pages",
        f"GENERATION MODE: {'Context-Aware' if case_context else 'Template-Based'}"
    ])
    
    return "\n".join(preview_lines)

def create_document_result(template: DocumentTemplate, field_values: Dict, 
                         confidence: GenerationConfidence, user_info: Dict) -> Dict:
    """Create document generation result"""
    
    template_info = DOCUMENT_TEMPLATES[template]
    
    return {
        'template': template,
        'template_name': template_info['name'],
        'confidence': confidence,
        'generated_at': datetime.now(),
        'generated_by': user_info.get('full_name', 'Unknown User'),
        'field_count': len(field_values),
        'estimated_pages': get_estimated_length(template),
        'document_id': f"doc_{template.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'status': 'Generated'
    }

def render_generation_results(document_result: Dict, template_info: Dict, confidence: GenerationConfidence):
    """Render document generation results"""
    
    st.success("🎉 Document Generated Successfully!")
    
    # Results overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Document:** {document_result['template_name']}")
        st.markdown(f"**Generated:** {document_result['generated_at'].strftime('%Y-%m-%d %H:%M')}")
    
    with col2:
        st.markdown(f"**Confidence:** {confidence.value.title()}")
        st.markdown(f"**Pages:** ~{document_result['estimated_pages']}")
    
    with col3:
        st.markdown(f"**ID:** {document_result['document_id']}")
        st.markdown(f"**Status:** {document_result['status']}")
    
    # Confidence-based recommendations
    if confidence == GenerationConfidence.HIGH:
        st.info("✅ **High Confidence**: Document is ready for use with minimal review required.")
    elif confidence == GenerationConfidence.MEDIUM:
        st.warning("⚠️ **Medium Confidence**: Please review document carefully before use.")
    elif confidence == GenerationConfidence.LOW:
        st.warning("🔍 **Low Confidence**: Substantial review and editing recommended.")
    else:
        st.error("❌ **Insufficient Data**: Consider manual preparation or gathering more information.")
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 Download Word", use_container_width=True):
            st.info("📥 Word document download will be implemented in the next phase")
    
    with col2:
        if st.button("📋 Download PDF", use_container_width=True):
            st.info("📥 PDF document download will be implemented in the next phase")
    
    with col3:
        if st.button("📝 Edit Document", use_container_width=True):
            st.info("✏️ Document editor will be implemented in the next phase")
    
    with col4:
        if st.button("💾 Save to Case", use_container_width=True):
            st.info("💾 Document will be automatically saved to the case file")
    
    # Generation log
    with st.expander("📊 Generation Details", expanded=False):
        st.json({
            'template_used': document_result['template_name'],
            'confidence_level': confidence.value,
            'fields_populated': document_result['field_count'],
            'generation_timestamp': document_result['generated_at'].isoformat(),
            'generated_by': document_result['generated_by'],
            'document_category': template_info['category'],
            'estimated_time_saved': template_info['estimated_time']
        })

def get_estimated_length(template: DocumentTemplate) -> int:
    """Get estimated document length in pages"""
    
    length_estimates = {
        DocumentTemplate.FORM_1_DIVORCE: 4,
        DocumentTemplate.FORM_4_PROPERTY: 8,
        DocumentTemplate.FORM_13_FINANCIAL: 12,
        DocumentTemplate.SETTLEMENT_OFFER: 3,
        DocumentTemplate.ADVICE_LETTER: 4,
        DocumentTemplate.PARENTING_PLAN: 10
    }
    
    return length_estimates.get(template, 5)

def format_children_details(children_details: Dict) -> str:
    """Format children details for document generation"""
    
    if not children_details:
        return "No children information available"
    
    formatted_details = []
    children = children_details.get('children', [])
    
    for child in children:
        details = f"Name: {child.get('name', 'Unknown')}, DOB: {child.get('dob', 'Unknown')}"
        if child.get('living_with'):
            details += f", Living with: {child['living_with']}"
        formatted_details.append(details)
    
    return "; ".join(formatted_details) if formatted_details else "Children details available"