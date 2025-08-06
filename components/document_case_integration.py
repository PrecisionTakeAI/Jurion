#!/usr/bin/env python3
"""
Document-Case Integration Components for LegalLLM Professional
Enhanced document management with case-specific linking and Australian legal categorization
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import os
import sys
from enum import Enum

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import existing components
try:
    from shared.database.models import Document, Case, User
    from core.document_processor import DocumentProcessor
    from core.case_manager import CaseManager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database components not available: {e}")
    DATABASE_AVAILABLE = False

# Australian Legal Document Categories (Enhanced from existing system)
class DocumentCategory(Enum):
    COURT_DOCUMENTS = "court_documents"
    FINANCIAL_DOCUMENTS = "financial_documents"
    PROPERTY_DOCUMENTS = "property_documents"
    PARENTING_DOCUMENTS = "parenting_documents"
    CORRESPONDENCE = "correspondence"
    AGREEMENTS = "agreements"
    EVIDENCE = "evidence"
    EXPERT_REPORTS = "expert_reports"
    AFFIDAVITS = "affidavits"
    APPLICATIONS = "applications"
    ORDERS = "orders"
    COMPLIANCE_DOCUMENTS = "compliance_documents"
    CLIENT_INSTRUCTIONS = "client_instructions"
    LEGAL_RESEARCH = "legal_research"
    OTHER = "other"

# Australian Family Law Document Subcategories
DOCUMENT_SUBCATEGORIES = {
    DocumentCategory.COURT_DOCUMENTS: [
        "Application for Divorce (Form 1)",
        "Affidavit (Form 2)", 
        "Application for Property Orders (Form 4)",
        "Notice of Risk (Form 4A)",
        "Application for Consent Orders (Form 11)",
        "Response to Application",
        "Court Orders",
        "Judgments",
        "Other Court Documents"
    ],
    DocumentCategory.FINANCIAL_DOCUMENTS: [
        "Financial Statement (Form 13)",
        "Financial Statement Short Form (Form 13A)",  
        "Bank Statements",
        "Tax Returns",
        "Pay Slips",
        "Superannuation Statements",
        "Investment Statements", 
        "Business Financial Records",
        "Asset Valuations",
        "Debt Statements"
    ],
    DocumentCategory.PROPERTY_DOCUMENTS: [
        "Property Valuations",
        "Mortgage Documents",
        "Title Deeds",
        "Real Estate Contracts",
        "Property Settlement Agreements",
        "Transfer Documents",
        "Lease Agreements",
        "Property Insurance",
        "Council Rates",
        "Other Property Documents"
    ],
    DocumentCategory.PARENTING_DOCUMENTS: [
        "Parenting Plans",
        "Parenting Orders",
        "Child Support Assessments",
        "School Reports",
        "Medical Reports - Children",
        "Family Report",
        "Child Impact Report",
        "Care Arrangements",
        "Child Support Agreements",
        "Parenting Affidavits"
    ],
    DocumentCategory.CORRESPONDENCE: [
        "Letters to Other Party",
        "Letters from Other Party",
        "Court Correspondence",
        "Client Correspondence",
        "Third Party Correspondence",
        "Email Communications",
        "Text Messages",
        "Settlement Negotiations",
        "Mediation Communications",
        "Other Correspondence"
    ],
    DocumentCategory.AGREEMENTS: [
        "Binding Financial Agreements",
        "Separation Agreements",
        "Property Settlement Agreements",
        "Parenting Agreements",
        "Child Support Agreements",
        "Spousal Maintenance Agreements",
        "Minutes of Consent Orders",
        "Mediation Agreements",
        "Collaborative Law Agreements",
        "Other Agreements"
    ]
}

# Document privilege levels
class PrivilegeLevel(Enum):
    PUBLIC = "public"
    CLIENT_CONFIDENTIAL = "client_confidential"
    LEGAL_PROFESSIONAL_PRIVILEGE = "legal_professional_privilege"
    WITHOUT_PREJUDICE = "without_prejudice"
    SETTLEMENT_PRIVILEGED = "settlement_privileged"

def render_case_document_dashboard(case_id: str, user_role: str, user_info: Dict):
    """Render document dashboard for a specific case"""
    
    st.markdown(f"## 📄 Case Documents")
    
    if not DATABASE_AVAILABLE:
        st.error("🚫 Document management system is not available.")
        return
    
    # Document overview metrics
    render_document_metrics(case_id)
    
    # Document upload section
    render_case_document_upload(case_id, user_role, user_info)
    
    # Document list and management
    render_case_document_list(case_id, user_role, user_info)
    
    # Document analysis and AI integration
    render_document_ai_analysis(case_id, user_role, user_info)

def render_document_metrics(case_id: str):
    """Render document metrics for the case"""
    
    # Get document statistics (mock data for now)
    total_documents = 24
    recent_uploads = 3
    privileged_documents = 8
    pending_review = 2
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{total_documents}</span>
            <div class="metric-label">Total Documents</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{recent_uploads}</span>
            <div class="metric-label">Recent Uploads</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{privileged_documents}</span>
            <div class="metric-label">Privileged</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{pending_review}</span>
            <div class="metric-label">Pending Review</div>
        </div>
        """, unsafe_allow_html=True)

def render_case_document_upload(case_id: str, user_role: str, user_info: Dict):
    """Render enhanced document upload with case-specific categorization"""
    
    st.markdown("### 📎 Upload Documents to Case")
    
    # Upload interface
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=['pdf', 'docx', 'txt', 'jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        help="Drag and drop multiple files • Supports PDF, DOCX, TXT, and images"
    )
    
    if uploaded_files:
        # Document processing options
        with st.expander("📋 Document Processing Options", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                # Category selection
                document_category = st.selectbox(
                    "Document Category *",
                    list(DocumentCategory),
                    format_func=lambda x: x.value.replace('_', ' ').title(),
                    help="Select the primary category for all uploaded documents"
                )
                
                # Subcategory selection
                subcategories = DOCUMENT_SUBCATEGORIES.get(document_category, [])
                document_subcategory = st.selectbox(
                    "Document Subcategory",
                    ["Auto-detect"] + subcategories,
                    help="Specific document type (auto-detection available)"
                )
                
                # Privilege level
                privilege_level = st.selectbox(
                    "Privilege Level *",
                    list(PrivilegeLevel),
                    format_func=lambda x: x.value.replace('_', ' ').title(),
                    index=1,  # Default to client_confidential
                    help="Legal privilege classification"
                )
            
            with col2:
                # Document source
                document_source = st.selectbox(
                    "Document Source",
                    ["Client", "Other Party", "Court", "Third Party", "Internal", "Expert", "Other"],
                    help="Source of the document"
                )
                
                # Processing options
                enable_ocr = st.checkbox(
                    "Enable OCR processing",
                    value=True,
                    help="Extract text from scanned documents and images"
                )
                
                auto_categorization = st.checkbox(
                    "AI-powered categorization",
                    value=True,
                    help="Use AI to automatically categorize and tag documents"
                )
                
                # Access control
                restrict_access = st.checkbox(
                    "Restrict access to case team",
                    value=False,
                    help="Limit access to assigned lawyers and authorized staff"
                )
        
        # Document descriptions
        document_descriptions = {}
        if len(uploaded_files) > 1:
            st.markdown("### 📝 Document Descriptions")
            
            for i, file in enumerate(uploaded_files):
                description = st.text_input(
                    f"Description for {file.name}:",
                    placeholder="Brief description of document content and purpose...",
                    key=f"desc_{i}"
                )
                document_descriptions[file.name] = description
        else:
            # Single document description
            description = st.text_area(
                "Document Description:",
                placeholder="Brief description of document content and purpose...",
                key="single_desc"
            )
            if uploaded_files:
                document_descriptions[uploaded_files[0].name] = description
        
        # Process documents
        if st.button("📤 Process and Upload Documents", type="primary"):
            with st.spinner("Processing documents with enhanced OCR and AI categorization..."):
                success_count = 0
                
                for file in uploaded_files:
                    try:
                        # Process document
                        result = process_case_document(
                            case_id=case_id,
                            uploaded_file=file,
                            category=document_category,
                            subcategory=document_subcategory if document_subcategory != "Auto-detect" else None,
                            privilege_level=privilege_level,
                            source=document_source,
                            description=document_descriptions.get(file.name, ""),
                            enable_ocr=enable_ocr,
                            auto_categorization=auto_categorization,
                            restrict_access=restrict_access,
                            user_info=user_info
                        )
                        
                        if result['success']:
                            success_count += 1
                            
                            # Show processing results
                            st.success(f"✅ {file.name} processed successfully")
                            
                            if result.get('ai_categorization'):
                                st.info(f"🤖 AI detected category: {result['ai_categorization']}")
                            
                            if result.get('ocr_processed'):
                                st.info(f"🔍 OCR extracted {result['text_length']} characters")
                        
                        else:
                            st.error(f"❌ Failed to process {file.name}: {result['error']}")
                    
                    except Exception as e:
                        st.error(f"❌ Error processing {file.name}: {str(e)}")
                
                if success_count > 0:
                    st.success(f"🎉 Successfully processed {success_count} of {len(uploaded_files)} documents!")
                    st.rerun()

def render_case_document_list(case_id: str, user_role: str, user_info: Dict):
    """Render organized case document list with filtering and search"""
    
    st.markdown("### 📋 Case Document Library")
    
    # Document filters
    with st.expander("🔍 Document Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_category = st.multiselect(
                "Categories:",
                [cat.value.replace('_', ' ').title() for cat in DocumentCategory],
                help="Filter by document category"
            )
            
            filter_source = st.multiselect(
                "Source:",
                ["Client", "Other Party", "Court", "Third Party", "Internal", "Expert", "Other"],
                help="Filter by document source"
            )
        
        with col2:
            filter_privilege = st.multiselect(
                "Privilege Level:",
                [priv.value.replace('_', ' ').title() for priv in PrivilegeLevel],
                help="Filter by privilege level"
            )
            
            date_range = st.date_input(
                "Date Range:",
                value=[],
                help="Filter by upload date range"
            )
        
        with col3:
            search_query = st.text_input(
                "Search:",
                placeholder="Search document names, descriptions, or content...",
                help="Search across document metadata and content"
            )
            
            sort_by = st.selectbox(
                "Sort by:",
                ["Upload Date (Newest)", "Upload Date (Oldest)", "Name (A-Z)", "Name (Z-A)", "Size (Largest)", "Size (Smallest)"],
                help="Sort documents"
            )
    
    # Get filtered documents
    documents = get_case_documents(
        case_id=case_id,
        category_filter=filter_category,
        source_filter=filter_source,
        privilege_filter=filter_privilege,
        date_range=date_range,
        search_query=search_query,
        sort_by=sort_by,
        user_role=user_role
    )
    
    if not documents:
        st.info("📄 No documents found matching the current filters.")
        return
    
    # Group documents by category
    grouped_documents = group_documents_by_category(documents)
    
    # Render document groups
    for category, docs in grouped_documents.items():
        with st.expander(f"📁 {category} ({len(docs)} documents)", expanded=True):
            
            for doc in docs:
                render_document_item(doc, case_id, user_role, user_info)

def render_document_item(document: Dict, case_id: str, user_role: str, user_info: Dict):
    """Render individual document item with actions"""
    
    # Document card
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            # Document name and description
            privilege_icon = get_privilege_icon(document.get('privilege_level'))
            st.markdown(f"**{privilege_icon} {document['name']}**")
            
            if document.get('description'):
                st.markdown(f"*{document['description']}*")
            
            # Document metadata
            st.markdown(f"📂 {document.get('subcategory', 'Unknown Category')}")
        
        with col2:
            # Document details
            st.markdown(f"📅 {document.get('upload_date', 'Unknown Date')}")
            st.markdown(f"👤 {document.get('uploaded_by', 'Unknown User')}")
            st.markdown(f"📏 {document.get('file_size', 'Unknown Size')}")
        
        with col3:
            # Processing status
            if document.get('ocr_processed'):
                st.markdown("🔍 OCR: ✅")
            
            if document.get('ai_analyzed'):
                st.markdown("🤖 AI: ✅")
            
            if document.get('reviewed'):
                st.markdown("👁️ Reviewed: ✅")
        
        with col4:
            # Action buttons
            if user_role in ['principal', 'senior_lawyer', 'lawyer']:
                if st.button("👁️", key=f"view_{document['id']}", help="View document"):
                    render_document_viewer(document)
                
                if st.button("📝", key=f"edit_{document['id']}", help="Edit metadata"):
                    render_document_editor(document, case_id)
                
                if st.button("🤖", key=f"analyze_{document['id']}", help="AI analysis"):
                    render_document_ai_analysis_modal(document, case_id)
            else:
                # Limited access for other roles
                if document.get('accessible_to_role', {}).get(user_role, False):
                    if st.button("👁️", key=f"view_{document['id']}", help="View document"):
                        render_document_viewer(document)
        
        st.markdown("---")

def render_document_ai_analysis(case_id: str, user_role: str, user_info: Dict):
    """Render AI-powered document analysis for the case"""
    
    st.markdown("### 🤖 AI Document Analysis")
    
    if user_role not in ['principal', 'senior_lawyer', 'lawyer']:
        st.info("🔒 AI analysis features are available to lawyers and above.")
        return
    
    # Analysis options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Bulk Analysis")
        
        if st.button("🔍 Analyze All Documents", use_container_width=True):
            run_bulk_document_analysis(case_id)
        
        if st.button("📋 Generate Document Summary", use_container_width=True):
            generate_case_document_summary(case_id)
        
        if st.button("⚠️ Identify Missing Documents", use_container_width=True):
            identify_missing_documents(case_id)
    
    with col2:
        st.markdown("#### 🎯 Specific Analysis")
        
        if st.button("💰 Financial Analysis", use_container_width=True):
            run_financial_document_analysis(case_id)
        
        if st.button("👶 Parenting Analysis", use_container_width=True):
            run_parenting_document_analysis(case_id)
        
        if st.button("🔍 Risk Assessment", use_container_width=True):
            run_document_risk_assessment(case_id)
    
    # Recent analysis results
    render_recent_analysis_results(case_id)

def render_document_privilege_management(case_id: str, user_role: str):
    """Render document privilege and access control management"""
    
    if user_role not in ['principal', 'senior_lawyer']:
        return
    
    st.markdown("### 🔒 Document Privilege Management")
    
    # Privilege overview
    privilege_stats = get_document_privilege_stats(case_id)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Legal Professional Privilege", privilege_stats.get('lpp', 0))
    
    with col2:
        st.metric("Without Prejudice", privilege_stats.get('without_prejudice', 0))
    
    with col3:
        st.metric("Settlement Privileged", privilege_stats.get('settlement', 0))
    
    # Privilege audit
    with st.expander("📋 Privilege Audit Log", expanded=False):
        audit_logs = get_privilege_audit_logs(case_id)
        
        for log in audit_logs:
            st.markdown(f"• **{log['timestamp']}** - {log['action']} by {log['user']} - Document: {log['document']}")

# Helper functions for document processing
def process_case_document(case_id: str, uploaded_file, category: DocumentCategory, 
                         subcategory: Optional[str], privilege_level: PrivilegeLevel,
                         source: str, description: str, enable_ocr: bool, 
                         auto_categorization: bool, restrict_access: bool, 
                         user_info: Dict) -> Dict:
    """Process uploaded document with case integration"""
    
    try:
        # Mock processing - would integrate with existing document processor
        result = {
            'success': True,
            'document_id': f"doc_{case_id}_{uploaded_file.name}",
            'ai_categorization': subcategory if auto_categorization else None,
            'ocr_processed': enable_ocr,
            'text_length': 1250 if enable_ocr else 0
        }
        
        # Would save to database with case linkage
        return result
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_case_documents(case_id: str, category_filter: List[str], source_filter: List[str],
                      privilege_filter: List[str], date_range: List, search_query: str,
                      sort_by: str, user_role: str) -> List[Dict]:
    """Get filtered and sorted case documents"""
    
    # Mock data - would query database with filters
    mock_documents = [
        {
            'id': 'doc_1',
            'name': 'Financial Statement Form 13.pdf',
            'category': 'Financial Documents',
            'subcategory': 'Financial Statement (Form 13)',
            'privilege_level': 'client_confidential',
            'source': 'Client',
            'description': 'Completed Form 13 financial statement',
            'upload_date': '2024-02-10',
            'uploaded_by': 'Sarah Chen',
            'file_size': '2.3 MB',
            'ocr_processed': True,
            'ai_analyzed': True,
            'reviewed': True
        },
        {
            'id': 'doc_2', 
            'name': 'Property Valuation - 123 Main St.pdf',
            'category': 'Property Documents',
            'subcategory': 'Property Valuations',
            'privilege_level': 'client_confidential',
            'source': 'Expert',
            'description': 'Independent property valuation report',
            'upload_date': '2024-02-08',
            'uploaded_by': 'Michael Wong',
            'file_size': '5.1 MB',
            'ocr_processed': True,
            'ai_analyzed': False,
            'reviewed': False
        }
    ]
    
    return mock_documents

def group_documents_by_category(documents: List[Dict]) -> Dict[str, List[Dict]]:
    """Group documents by category"""
    
    grouped = {}
    for doc in documents:
        category = doc.get('category', 'Other')
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(doc)
    
    return grouped

def get_privilege_icon(privilege_level: str) -> str:
    """Get icon for privilege level"""
    
    privilege_icons = {
        'public': '🌐',
        'client_confidential': '🔒',
        'legal_professional_privilege': '⚖️',
        'without_prejudice': '🤝',
        'settlement_privileged': '📄'
    }
    
    return privilege_icons.get(privilege_level, '📄')

def render_document_viewer(document: Dict):
    """Render document viewer modal"""
    st.info("📄 Document viewer will be implemented in Phase 3")

def render_document_editor(document: Dict, case_id: str):
    """Render document metadata editor"""
    st.info("📝 Document editor will be implemented in Phase 3")

def render_document_ai_analysis_modal(document: Dict, case_id: str):
    """Render AI analysis modal for specific document"""
    st.info("🤖 Document AI analysis will be implemented in Phase 3")

def run_bulk_document_analysis(case_id: str):
    """Run AI analysis on all case documents"""
    st.info("🔍 Bulk document analysis will be implemented in Phase 3")

def generate_case_document_summary(case_id: str):
    """Generate comprehensive document summary for case"""
    st.info("📋 Document summary generation will be implemented in Phase 3")

def identify_missing_documents(case_id: str):
    """Identify potentially missing documents for case type"""
    st.info("⚠️ Missing document identification will be implemented in Phase 3")

def run_financial_document_analysis(case_id: str):
    """Run specialized financial document analysis"""
    st.info("💰 Financial analysis will be implemented in Phase 3")

def run_parenting_document_analysis(case_id: str):
    """Run specialized parenting document analysis"""
    st.info("👶 Parenting analysis will be implemented in Phase 3")

def run_document_risk_assessment(case_id: str):
    """Run document-based risk assessment"""
    st.info("🔍 Risk assessment will be implemented in Phase 3")

def render_recent_analysis_results(case_id: str):
    """Render recent AI analysis results"""
    st.info("📊 Recent analysis results will be shown in Phase 3")

def get_document_privilege_stats(case_id: str) -> Dict[str, int]:
    """Get document privilege statistics"""
    return {'lpp': 5, 'without_prejudice': 3, 'settlement': 2}

def get_privilege_audit_logs(case_id: str) -> List[Dict]:
    """Get privilege audit logs"""
    return [
        {
            'timestamp': '2024-02-10 14:30',
            'action': 'Privilege level changed',
            'user': 'Sarah Chen',
            'document': 'Settlement Offer Letter.pdf'
        }
    ]