#!/usr/bin/env python3
"""
Case Management Components for LegalLLM Professional Enterprise Interface
Australian Family Law Case Management with Role-Based Access Control
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
import pandas as pd
import uuid
import os
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import existing backend components
try:
    from shared.database.models import Case, Document, User, LawFirm
    from core.case_manager import CaseManager
    from database.database import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database components not available: {e}")
    DATABASE_AVAILABLE = False

# Australian Family Law Constants
AUSTRALIAN_FAMILY_LAW_CASE_TYPES = {
    "divorce": {
        "name": "Divorce Application",
        "description": "Application for dissolution of marriage",
        "forms": ["Application for Divorce (Form 1)", "Affidavit (Form 2)"],
        "requirements": ["Marriage certificate", "Separation certificate or affidavit"],
        "timeline": "12+ months separation required"
    },
    "property_settlement": {
        "name": "Property Settlement",
        "description": "Division of assets and financial resources",
        "forms": ["Form 13 - Financial Statement", "Form 13A - Financial Statement (Short)"],
        "requirements": ["Asset valuations", "Financial disclosure", "Form 13/13A"],
        "timeline": "12 months after divorce order or 2 years after separation"
    },
    "parenting_orders": {
        "name": "Parenting Orders",
        "description": "Children's living arrangements and parental responsibilities",
        "forms": ["Application (Form 4)", "Notice of Risk (Form 4A)"],
        "requirements": ["Best interests assessment", "Family Dispute Resolution certificate"],
        "timeline": "Ongoing until children reach 18"
    },
    "child_support": {
        "name": "Child Support",
        "description": "Financial support for children",
        "forms": ["Child Support Assessment", "Change of Assessment"],
        "requirements": ["Income statements", "Care arrangements"],
        "timeline": "Until child reaches 18 or finishes secondary education"
    },
    "spousal_maintenance": {
        "name": "Spousal Maintenance",
        "description": "Financial support between former spouses",
        "forms": ["Application for Maintenance", "Financial Statement"],
        "requirements": ["Financial capacity assessment", "Needs assessment"],
        "timeline": "Variable based on circumstances"
    },
    "consent_orders": {
        "name": "Consent Orders",
        "description": "Agreed orders without court hearing",
        "forms": ["Minutes of Consent Orders", "Form 11 - Application for Consent Orders"],
        "requirements": ["Signed agreement", "Legal advice certificates"],
        "timeline": "Processed within 6-8 weeks if compliant"
    },
    "binding_financial_agreement": {
        "name": "Binding Financial Agreement",
        "description": "Pre-nuptial or post-separation financial agreement",
        "forms": ["BFA Agreement", "Legal Advice Certificates"],
        "requirements": ["Independent legal advice", "Financial disclosure"],
        "timeline": "Can be made before, during, or after marriage"
    },
    "de_facto_property": {
        "name": "De Facto Property Settlement",
        "description": "Property settlement for de facto relationships",
        "forms": ["Form 13", "Application for Property Orders"],
        "requirements": ["Proof of de facto relationship", "Financial disclosure"],
        "timeline": "2 years after separation"
    }
}

AUSTRALIAN_JURISDICTIONS = {
    "family_court": "Family Court of Australia",
    "family_circuit_court": "Family Circuit Court of Australia", 
    "federal_circuit_court": "Federal Circuit Court of Australia",
    "state_magistrates": "State Magistrates Court",
    "state_family_court": "State Family Court"
}

CASE_PRIORITY_LEVELS = {
    "urgent": {"label": "Urgent", "color": "#dc2626", "description": "Requires immediate attention"},
    "high": {"label": "High", "color": "#ea580c", "description": "Important matter with tight deadlines"},
    "medium": {"label": "Medium", "color": "#ca8a04", "description": "Standard priority"},
    "low": {"label": "Low", "color": "#16a34a", "description": "Low priority or long-term matter"}
}

CASE_STATUS_OPTIONS = {
    "active": {"label": "Active", "color": "#16a34a", "description": "Case is actively being worked on"},
    "pending": {"label": "Pending", "color": "#ca8a04", "description": "Awaiting client or court action"},
    "on_hold": {"label": "On Hold", "color": "#64748b", "description": "Temporarily suspended"},
    "completed": {"label": "Completed", "color": "#0ea5e9", "description": "Matter concluded successfully"},
    "closed": {"label": "Closed", "color": "#6b7280", "description": "Case closed without completion"}
}

def render_case_management_dashboard(user_role: str, user_info: Dict, firm_info: Dict):
    """Main case management dashboard with role-based access"""
    
    st.markdown("## 📋 Case Management")
    
    # Check database availability
    if not DATABASE_AVAILABLE:
        st.error("🚫 Case management system is not available. Please contact your system administrator.")
        return
    
    # Initialize case manager
    try:
        case_manager = CaseManager(
            firm_id=firm_info.get('id'),
            user_id=user_info.get('id')
        )
    except Exception as e:
        st.error(f"🚫 Failed to initialize case management: {str(e)}")
        return
    
    # Role-based dashboard content
    if user_role in ['principal', 'senior_lawyer']:
        render_executive_case_dashboard(case_manager, user_info, firm_info)
    elif user_role == 'lawyer':
        render_lawyer_case_dashboard(case_manager, user_info, firm_info) 
    elif user_role == 'paralegal':
        render_paralegal_case_dashboard(case_manager, user_info, firm_info)
    elif user_role == 'client':
        render_client_case_dashboard(case_manager, user_info, firm_info)
    else:
        st.error("🚫 Your role does not have access to case management features.")

def render_executive_case_dashboard(case_manager, user_info: Dict, firm_info: Dict):
    """Executive case dashboard for principals and senior lawyers"""
    
    # Case overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Get firm case statistics (mock data for now)
    total_cases = 45
    active_cases = 32
    pending_cases = 8
    completed_this_month = 5
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{total_cases}</span>
            <div class="metric-label">Total Cases</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{active_cases}</span>
            <div class="metric-label">Active Cases</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{pending_cases}</span>
            <div class="metric-label">Pending Cases</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{completed_this_month}</span>
            <div class="metric-label">Completed This Month</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📋 Create New Case", use_container_width=True):
            st.session_state.show_case_creation = True
            st.rerun()
    
    with col2:
        if st.button("📊 Case Analytics", use_container_width=True):
            render_case_analytics(case_manager, user_info, firm_info)
    
    with col3:
        if st.button("👥 Assign Cases", use_container_width=True):
            render_case_assignment_interface(case_manager, user_info, firm_info)
    
    with col4:
        if st.button("📋 Firm Case List", use_container_width=True):
            st.session_state.show_case_list = True
            st.rerun()
    
    # Handle case creation
    if st.session_state.get('show_case_creation', False):
        render_australian_family_law_case_wizard(case_manager, user_info, firm_info)
    
    # Handle case list view
    if st.session_state.get('show_case_list', False):
        render_firm_case_list(case_manager, user_info, firm_info, view_all=True)
    
    # Recent activity and case overview
    col1, col2 = st.columns(2)
    
    with col1:
        render_recent_case_activity(case_manager, user_info, firm_info)
    
    with col2:
        render_upcoming_deadlines(case_manager, user_info, firm_info)

def render_lawyer_case_dashboard(case_manager, user_info: Dict, firm_info: Dict):
    """Lawyer-specific case dashboard"""
    
    # Personal case metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Mock data for lawyer's cases
    my_active_cases = 12
    due_this_week = 3
    total_clients = 8
    hours_this_month = 45.5
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{my_active_cases}</span>
            <div class="metric-label">My Active Cases</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{due_this_week}</span>
            <div class="metric-label">Due This Week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{total_clients}</span>
            <div class="metric-label">Total Clients</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{hours_this_month}</span>
            <div class="metric-label">Hours This Month</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Lawyer actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 New Case", use_container_width=True):
            st.session_state.show_case_creation = True
            st.rerun()
    
    with col2:
        if st.button("📂 My Cases", use_container_width=True):
            st.session_state.show_my_cases = True
            st.rerun()
    
    with col3:
        if st.button("📅 Case Calendar", use_container_width=True):
            render_case_calendar(case_manager, user_info, firm_info)
    
    # Handle case creation
    if st.session_state.get('show_case_creation', False):
        render_australian_family_law_case_wizard(case_manager, user_info, firm_info)
    
    # Handle my cases view
    if st.session_state.get('show_my_cases', False):
        render_lawyer_case_list(case_manager, user_info, firm_info)
    
    # Lawyer case overview
    render_lawyer_case_overview(case_manager, user_info, firm_info)

def render_paralegal_case_dashboard(case_manager, user_info: Dict, firm_info: Dict):
    """Paralegal-specific case dashboard"""
    
    st.markdown("### 📝 My Case Support Tasks")
    
    # Paralegal metrics
    col1, col2, col3, col4 = st.columns(4)
    
    assigned_cases = 6
    pending_tasks = 14
    completed_today = 3
    documents_processed = 8
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{assigned_cases}</span>
            <div class="metric-label">Assigned Cases</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{pending_tasks}</span>
            <div class="metric-label">Pending Tasks</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{completed_today}</span>
            <div class="metric-label">Completed Today</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{documents_processed}</span>
            <div class="metric-label">Documents Processed</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Paralegal task list
    render_paralegal_task_list(case_manager, user_info, firm_info)

def render_client_case_dashboard(case_manager, user_info: Dict, firm_info: Dict):
    """Client-specific case dashboard"""
    
    st.markdown("### 👤 My Legal Matters")
    
    # Client metrics
    col1, col2, col3 = st.columns(3)
    
    my_matters = 2
    pending_actions = 1
    uploaded_documents = 5
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{my_matters}</span>
            <div class="metric-label">My Matters</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{pending_actions}</span>
            <div class="metric-label">Pending Actions</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <span class="metric-value">{uploaded_documents}</span>
            <div class="metric-label">Documents Uploaded</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Client case overview
    render_client_case_overview(case_manager, user_info, firm_info)

def render_australian_family_law_case_wizard(case_manager, user_info: Dict, firm_info: Dict):
    """Comprehensive Australian Family Law case creation wizard"""
    
    st.markdown("## 🧙‍♂️ Australian Family Law Case Creation Wizard")
    
    # Initialize wizard state
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1
    if 'case_data' not in st.session_state:
        st.session_state.case_data = {}
    
    # Progress indicator
    total_steps = 6
    progress = st.session_state.wizard_step / total_steps
    st.progress(progress, text=f"Step {st.session_state.wizard_step} of {total_steps}")
    
    # Step routing
    if st.session_state.wizard_step == 1:
        render_case_type_selection()
    elif st.session_state.wizard_step == 2:
        render_client_intake_form()
    elif st.session_state.wizard_step == 3:
        render_case_details_form()
    elif st.session_state.wizard_step == 4:
        render_financial_information_form()
    elif st.session_state.wizard_step == 5:
        render_children_information_form()
    elif st.session_state.wizard_step == 6:
        render_case_summary_and_creation(case_manager, user_info, firm_info)
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.session_state.wizard_step > 1:
            if st.button("⬅️ Previous Step", use_container_width=True):
                st.session_state.wizard_step -= 1
                st.rerun()
    
    with col3:
        if st.session_state.wizard_step < total_steps:
            if st.button("Next Step ➡️", use_container_width=True):
                if validate_current_step():
                    st.session_state.wizard_step += 1
                    st.rerun()
                else:
                    st.error("❌ Please complete all required fields before continuing.")
    
    # Cancel wizard
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.show_case_creation = False
            st.session_state.wizard_step = 1
            st.session_state.case_data = {}
            st.rerun()

def render_case_type_selection():
    """Step 1: Case type selection"""
    
    st.markdown("### 📋 Step 1: Select Case Type")
    st.markdown("*Choose the primary type of family law matter*")
    
    # Display case type options
    selected_case_type = None
    
    # Create columns for case type display
    col1, col2 = st.columns(2)
    
    case_types = list(AUSTRALIAN_FAMILY_LAW_CASE_TYPES.keys())
    mid_point = len(case_types) // 2
    
    with col1:
        for case_type in case_types[:mid_point]:
            case_info = AUSTRALIAN_FAMILY_LAW_CASE_TYPES[case_type]
            
            if st.button(
                f"**{case_info['name']}**\n{case_info['description']}",
                key=f"case_type_{case_type}",
                use_container_width=True
            ):
                st.session_state.case_data['case_type'] = case_type
                selected_case_type = case_type
    
    with col2:
        for case_type in case_types[mid_point:]:
            case_info = AUSTRALIAN_FAMILY_LAW_CASE_TYPES[case_type]
            
            if st.button(
                f"**{case_info['name']}**\n{case_info['description']}",
                key=f"case_type_{case_type}",
                use_container_width=True
            ):
                st.session_state.case_data['case_type'] = case_type
                selected_case_type = case_type
    
    # Display selected case type information
    current_selection = st.session_state.case_data.get('case_type')
    if current_selection:
        case_info = AUSTRALIAN_FAMILY_LAW_CASE_TYPES[current_selection]
        
        st.markdown("---")
        st.markdown(f"### ✅ Selected: {case_info['name']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📋 Required Forms:**")
            for form in case_info['forms']:
                st.markdown(f"• {form}")
        
        with col2:
            st.markdown("**📄 Requirements:**")
            for req in case_info['requirements']:
                st.markdown(f"• {req}")
        
        st.markdown(f"**⏰ Timeline:** {case_info['timeline']}")

def render_client_intake_form():
    """Step 2: Client intake form"""
    
    st.markdown("### 👥 Step 2: Client Information") 
    st.markdown("*Enter client details for this family law matter*")
    
    # Party information tabs
    applicant_tab, respondent_tab = st.tabs(["👤 Applicant", "👥 Respondent"])
    
    with applicant_tab:
        st.markdown("#### Applicant (Your Client)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            applicant_title = st.selectbox(
                "Title",
                ["Mr", "Ms", "Mrs", "Dr", "Prof", "Other"],
                key="applicant_title"
            )
            
            applicant_first_name = st.text_input(
                "First Name *",
                placeholder="John",
                key="applicant_first_name"
            )
            
            applicant_last_name = st.text_input(
                "Last Name *", 
                placeholder="Smith",
                key="applicant_last_name"
            )
            
            applicant_dob = st.date_input(
                "Date of Birth *",
                key="applicant_dob",
                max_value=date.today()
            )
        
        with col2:
            applicant_email = st.text_input(
                "Email Address",
                placeholder="john.smith@email.com",
                key="applicant_email"
            )
            
            applicant_phone = st.text_input(
                "Phone Number *",
                placeholder="+61 4 0000 0000",
                key="applicant_phone"
            )
            
            applicant_occupation = st.text_input(
                "Occupation",
                placeholder="Software Engineer",
                key="applicant_occupation"
            )
            
            applicant_income = st.number_input(
                "Annual Income (AUD)",
                min_value=0,
                key="applicant_income",
                format="%d"
            )
        
        # Address information
        st.markdown("**📍 Current Address:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            applicant_address = st.text_area(
                "Street Address",
                placeholder="123 Main Street\nSydney NSW 2000",
                key="applicant_address"
            )
        
        with col2:
            applicant_postcode = st.text_input(
                "Postcode",
                placeholder="2000",
                key="applicant_postcode"
            )
            
            applicant_state = st.selectbox(
                "State/Territory",
                ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                key="applicant_state"
            )
    
    with respondent_tab:
        st.markdown("#### Respondent (Other Party)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            respondent_title = st.selectbox(
                "Title",
                ["Mr", "Ms", "Mrs", "Dr", "Prof", "Other"],
                key="respondent_title"
            )
            
            respondent_first_name = st.text_input(
                "First Name *",
                placeholder="Jane",
                key="respondent_first_name"
            )
            
            respondent_last_name = st.text_input(
                "Last Name *",
                placeholder="Smith", 
                key="respondent_last_name"
            )
            
            respondent_dob = st.date_input(
                "Date of Birth",
                key="respondent_dob",
                max_value=date.today()
            )
        
        with col2:
            respondent_email = st.text_input(
                "Email Address",
                placeholder="jane.smith@email.com",
                key="respondent_email"
            )
            
            respondent_phone = st.text_input(
                "Phone Number",
                placeholder="+61 4 1111 1111",
                key="respondent_phone"
            )
            
            respondent_occupation = st.text_input(
                "Occupation",
                placeholder="Teacher",
                key="respondent_occupation"
            )
            
            respondent_income = st.number_input(
                "Annual Income (AUD)",
                min_value=0,
                key="respondent_income",
                format="%d"
            )
        
        # Address information
        st.markdown("**📍 Known Address:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            respondent_address = st.text_area(
                "Street Address",
                placeholder="456 Oak Street\nMelbourne VIC 3000",
                key="respondent_address"
            )
        
        with col2:
            respondent_postcode = st.text_input(
                "Postcode",
                placeholder="3000",
                key="respondent_postcode"
            )
            
            respondent_state = st.selectbox(
                "State/Territory",
                ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                key="respondent_state"
            )
    
    # Store client information in session state
    st.session_state.case_data['client_info'] = {
        'applicant': {
            'title': applicant_title,
            'first_name': applicant_first_name,
            'last_name': applicant_last_name,
            'dob': applicant_dob,
            'email': applicant_email,
            'phone': applicant_phone,
            'occupation': applicant_occupation,
            'income': applicant_income,
            'address': applicant_address,
            'postcode': applicant_postcode,
            'state': applicant_state
        },
        'respondent': {
            'title': respondent_title,
            'first_name': respondent_first_name,
            'last_name': respondent_last_name, 
            'dob': respondent_dob,
            'email': respondent_email,
            'phone': respondent_phone,
            'occupation': respondent_occupation,
            'income': respondent_income,
            'address': respondent_address,
            'postcode': respondent_postcode,
            'state': respondent_state
        }
    }

def render_case_details_form():
    """Step 3: Case details and court information"""
    
    st.markdown("### ⚖️ Step 3: Case Details")
    st.markdown("*Legal and procedural information for this matter*")
    
    # Case metadata
    col1, col2 = st.columns(2)
    
    with col1:
        case_title = st.text_input(
            "Case Title *",
            placeholder="Smith v Smith",
            key="case_title",
            help="Short descriptive title for the case"
        )
        
        case_priority = st.selectbox(
            "Priority Level *",
            list(CASE_PRIORITY_LEVELS.keys()),
            format_func=lambda x: f"{CASE_PRIORITY_LEVELS[x]['label']} - {CASE_PRIORITY_LEVELS[x]['description']}",
            key="case_priority"
        )
        
        assigned_lawyer = st.selectbox(
            "Assigned Lawyer *",
            ["Current User", "John Chen", "Sarah Wilson", "Michael Brown"],  # This would be populated from firm lawyers
            key="assigned_lawyer"
        )
    
    with col2:
        case_status = st.selectbox(
            "Initial Status",
            list(CASE_STATUS_OPTIONS.keys()),
            format_func=lambda x: f"{CASE_STATUS_OPTIONS[x]['label']} - {CASE_STATUS_OPTIONS[x]['description']}",
            key="case_status",
            index=0  # Default to "active"
        )
        
        estimated_value = st.number_input(
            "Estimated Case Value (AUD)",
            min_value=0,
            key="estimated_value",
            format="%d",
            help="Estimated total value of assets/claims involved"
        )
        
        supervising_partner = st.selectbox(
            "Supervising Partner",
            ["None", "Principal Partner", "Senior Partner", "Managing Partner"],
            key="supervising_partner"
        )
    
    # Relationship and separation details
    st.markdown("#### 💑 Relationship Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        relationship_type = st.selectbox(
            "Relationship Type *",
            ["Married", "De Facto", "Civil Union", "Other"],
            key="relationship_type"
        )
        
        relationship_start_date = st.date_input(
            "Relationship Start Date",
            key="relationship_start_date",
            max_value=date.today()
        )
        
        marriage_date = st.date_input(
            "Marriage Date (if applicable)",
            key="marriage_date",
            max_value=date.today()
        )
    
    with col2:
        separation_date = st.date_input(
            "Separation Date *",
            key="separation_date",
            max_value=date.today(),
            help="Date parties separated"
        )
        
        cohabitation_duration = st.number_input(
            "Years of Cohabitation",
            min_value=0.0,
            key="cohabitation_duration",
            format="%.1f"
        )
        
        reconciliation_attempts = st.checkbox(
            "Reconciliation attempts made",
            key="reconciliation_attempts"
        )
    
    # Court and jurisdiction information
    st.markdown("#### 🏛️ Court Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        court_jurisdiction = st.selectbox(
            "Court Jurisdiction *",
            list(AUSTRALIAN_JURISDICTIONS.keys()),
            format_func=lambda x: AUSTRALIAN_JURISDICTIONS[x],
            key="court_jurisdiction"
        )
        
        court_location = st.text_input(
            "Court Location",
            placeholder="Sydney Registry",
            key="court_location"
        )
    
    with col2:
        file_number = st.text_input(
            "File Number (if known)",
            placeholder="SYF123456/2024",
            key="file_number"
        )
        
        urgency_factors = st.multiselect(
            "Urgency Factors",
            [
                "Children at risk", "Domestic violence", "Asset disposal risk",
                "Time-sensitive deadlines", "International elements", "Other"
            ],
            key="urgency_factors"
        )
    
    # Case description
    st.markdown("#### 📝 Case Description")
    
    case_summary = st.text_area(
        "Case Summary *",
        placeholder="Brief description of the matter, key issues, and client objectives...",
        height=100,
        key="case_summary",
        help="Provide a comprehensive overview of the case"
    )
    
    legal_issues = st.multiselect(
        "Primary Legal Issues",
        [
            "Property division", "Child arrangements", "Spousal maintenance",
            "Child support", "Domestic violence", "International child abduction",
            "Binding financial agreements", "Consent orders", "Other"
        ],
        key="legal_issues"
    )
    
    # Store case details in session state
    st.session_state.case_data['case_details'] = {
        'title': case_title,
        'priority': case_priority,
        'status': case_status,
        'assigned_lawyer': assigned_lawyer,
        'supervising_partner': supervising_partner,
        'estimated_value': estimated_value,
        'relationship_type': relationship_type,
        'relationship_start_date': relationship_start_date,
        'marriage_date': marriage_date,
        'separation_date': separation_date,
        'cohabitation_duration': cohabitation_duration,
        'reconciliation_attempts': reconciliation_attempts,
        'court_jurisdiction': court_jurisdiction,
        'court_location': court_location,
        'file_number': file_number,
        'urgency_factors': urgency_factors,
        'case_summary': case_summary,
        'legal_issues': legal_issues
    }

def render_financial_information_form():
    """Step 4: Financial information"""
    
    st.markdown("### 💰 Step 4: Financial Information")
    st.markdown("*Asset pool and financial disclosure details*")
    
    # Asset categories
    asset_tabs = st.tabs(["🏠 Real Estate", "💰 Financial Assets", "🚗 Personal Property", "💼 Business Interests", "📊 Superannuation", "💳 Liabilities"])
    
    with asset_tabs[0]:  # Real Estate
        st.markdown("#### 🏠 Real Estate Assets")
        
        num_properties = st.number_input("Number of Properties", min_value=0, max_value=10, key="num_properties")
        
        properties = []
        for i in range(int(num_properties)):
            with st.expander(f"Property {i+1}", expanded=i==0):
                col1, col2 = st.columns(2)
                
                with col1:
                    prop_address = st.text_input(f"Address", key=f"prop_address_{i}")
                    prop_type = st.selectbox(
                        f"Property Type",
                        ["Family Home", "Investment Property", "Commercial", "Land", "Other"],
                        key=f"prop_type_{i}"
                    )
                    prop_value = st.number_input(f"Estimated Value (AUD)", min_value=0, key=f"prop_value_{i}")
                
                with col2:
                    prop_ownership = st.selectbox(
                        f"Ownership",
                        ["Joint Tenants", "Tenants in Common", "Sole - Applicant", "Sole - Respondent"],
                        key=f"prop_ownership_{i}"
                    )
                    prop_mortgage = st.number_input(f"Outstanding Mortgage (AUD)", min_value=0, key=f"prop_mortgage_{i}")
                    prop_equity = st.number_input(f"Net Equity (AUD)", min_value=0, key=f"prop_equity_{i}")
                
                properties.append({
                    'address': prop_address,
                    'type': prop_type,
                    'value': prop_value,
                    'ownership': prop_ownership,
                    'mortgage': prop_mortgage,
                    'equity': prop_equity
                })
        
        st.session_state.case_data.setdefault('financial_info', {})['properties'] = properties
    
    with asset_tabs[1]:  # Financial Assets
        st.markdown("#### 💰 Financial Assets")
        
        col1, col2 = st.columns(2)
        
        with col1:
            bank_accounts_value = st.number_input("Bank Accounts Total (AUD)", min_value=0, key="bank_accounts")
            shares_value = st.number_input("Shares/Investments (AUD)", min_value=0, key="shares")
            term_deposits_value = st.number_input("Term Deposits (AUD)", min_value=0, key="term_deposits")
        
        with col2:
            managed_funds_value = st.number_input("Managed Funds (AUD)", min_value=0, key="managed_funds")
            cash_value = st.number_input("Cash on Hand (AUD)", min_value=0, key="cash")
            other_investments_value = st.number_input("Other Investments (AUD)", min_value=0, key="other_investments")
        
        st.session_state.case_data['financial_info']['financial_assets'] = {
            'bank_accounts': bank_accounts_value,
            'shares': shares_value,
            'term_deposits': term_deposits_value,
            'managed_funds': managed_funds_value,
            'cash': cash_value,
            'other_investments': other_investments_value
        }
    
    with asset_tabs[2]:  # Personal Property
        st.markdown("#### 🚗 Personal Property")
        
        col1, col2 = st.columns(2)
        
        with col1:
            vehicles_value = st.number_input("Vehicles Total (AUD)", min_value=0, key="vehicles")
            furniture_value = st.number_input("Furniture/Contents (AUD)", min_value=0, key="furniture")
            jewelry_value = st.number_input("Jewelry/Valuables (AUD)", min_value=0, key="jewelry")
        
        with col2:
            art_collectibles_value = st.number_input("Art/Collectibles (AUD)", min_value=0, key="art_collectibles")
            tools_equipment_value = st.number_input("Tools/Equipment (AUD)", min_value=0, key="tools_equipment")
            other_personal_value = st.number_input("Other Personal Property (AUD)", min_value=0, key="other_personal")
        
        st.session_state.case_data['financial_info']['personal_property'] = {
            'vehicles': vehicles_value,
            'furniture': furniture_value,
            'jewelry': jewelry_value,
            'art_collectibles': art_collectibles_value,
            'tools_equipment': tools_equipment_value,
            'other_personal': other_personal_value
        }
    
    with asset_tabs[3]:  # Business Interests
        st.markdown("#### 💼 Business Interests")
        
        has_business = st.checkbox("Business interests involved", key="has_business")
        
        if has_business:
            col1, col2 = st.columns(2)
            
            with col1:
                business_name = st.text_input("Business Name", key="business_name")
                business_type = st.selectbox(
                    "Business Type",
                    ["Sole Trader", "Partnership", "Company", "Trust", "Other"],
                    key="business_type"
                )
                business_value = st.number_input("Business Value (AUD)", min_value=0, key="business_value")
            
            with col2:
                business_ownership = st.text_input("Ownership Percentage", key="business_ownership")
                business_income = st.number_input("Annual Business Income (AUD)", min_value=0, key="business_income")
                business_liabilities = st.number_input("Business Liabilities (AUD)", min_value=0, key="business_liabilities")
            
            st.session_state.case_data['financial_info']['business'] = {
                'name': business_name,
                'type': business_type,
                'value': business_value,
                'ownership': business_ownership,
                'income': business_income,
                'liabilities': business_liabilities
            }
    
    with asset_tabs[4]:  # Superannuation
        st.markdown("#### 📊 Superannuation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            applicant_super = st.number_input("Applicant Super Balance (AUD)", min_value=0, key="applicant_super")
            applicant_super_fund = st.text_input("Applicant Super Fund", key="applicant_super_fund")
        
        with col2:
            respondent_super = st.number_input("Respondent Super Balance (AUD)", min_value=0, key="respondent_super")
            respondent_super_fund = st.text_input("Respondent Super Fund", key="respondent_super_fund")
        
        super_splitting = st.checkbox("Superannuation splitting applicable", key="super_splitting")
        
        st.session_state.case_data['financial_info']['superannuation'] = {
            'applicant_balance': applicant_super,
            'applicant_fund': applicant_super_fund,
            'respondent_balance': respondent_super,
            'respondent_fund': respondent_super_fund,
            'splitting_applicable': super_splitting
        }
    
    with asset_tabs[5]:  # Liabilities
        st.markdown("#### 💳 Liabilities")
        
        col1, col2 = st.columns(2)
        
        with col1:
            credit_cards = st.number_input("Credit Cards (AUD)", min_value=0, key="credit_cards")
            personal_loans = st.number_input("Personal Loans (AUD)", min_value=0, key="personal_loans")
            tax_debts = st.number_input("Tax Debts (AUD)", min_value=0, key="tax_debts")
        
        with col2:
            other_debts = st.number_input("Other Debts (AUD)", min_value=0, key="other_debts")
            contingent_liabilities = st.number_input("Contingent Liabilities (AUD)", min_value=0, key="contingent_liabilities")
            guarantees = st.number_input("Guarantees Given (AUD)", min_value=0, key="guarantees")
        
        st.session_state.case_data['financial_info']['liabilities'] = {
            'credit_cards': credit_cards,
            'personal_loans': personal_loans,
            'tax_debts': tax_debts,
            'other_debts': other_debts,
            'contingent_liabilities': contingent_liabilities,
            'guarantees': guarantees
        }
    
    # Calculate asset pool summary
    render_asset_pool_summary()

def render_children_information_form():
    """Step 5: Children information"""
    
    st.markdown("### 👶 Step 5: Children Information")
    st.markdown("*Details about children of the relationship*")
    
    has_children = st.checkbox("Children of the relationship", key="has_children")
    
    if has_children:
        num_children = st.number_input("Number of children", min_value=1, max_value=10, key="num_children")
        
        children = []
        for i in range(int(num_children)):
            with st.expander(f"Child {i+1}", expanded=i==0):
                col1, col2 = st.columns(2)
                
                with col1:
                    child_first_name = st.text_input(f"First Name", key=f"child_first_name_{i}")
                    child_last_name = st.text_input(f"Last Name", key=f"child_last_name_{i}")
                    child_dob = st.date_input(f"Date of Birth", key=f"child_dob_{i}", max_value=date.today())
                    child_gender = st.selectbox(f"Gender", ["Male", "Female", "Other"], key=f"child_gender_{i}")
                
                with col2:
                    child_school = st.text_input(f"School/Childcare", key=f"child_school_{i}")
                    child_special_needs = st.checkbox(f"Special needs", key=f"child_special_needs_{i}")
                    child_medical_conditions = st.text_area(f"Medical conditions", key=f"child_medical_conditions_{i}")
                
                # Current living arrangements
                st.markdown(f"**Current Living Arrangements - Child {i+1}:**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    current_residence = st.selectbox(
                        f"Currently lives with",
                        ["Applicant", "Respondent", "Shared care", "Other relative", "Other"],
                        key=f"current_residence_{i}"
                    )
                    
                    time_with_applicant = st.slider(
                        f"Time with Applicant (%)",
                        0, 100, 50,
                        key=f"time_with_applicant_{i}"
                    )
                
                with col2:
                    proposed_arrangements = st.text_area(
                        f"Proposed arrangements",
                        placeholder="Describe proposed parenting arrangements...",
                        key=f"proposed_arrangements_{i}"
                    )
                
                # Child support
                st.markdown(f"**Child Support - Child {i+1}:**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    child_support_paid = st.checkbox(f"Child support currently paid", key=f"child_support_paid_{i}")
                    child_support_amount = st.number_input(f"Current support amount (AUD/month)", min_value=0, key=f"child_support_amount_{i}")
                
                with col2:
                    child_support_assessment = st.checkbox(f"CSA assessment in place", key=f"child_support_assessment_{i}")
                    child_support_private = st.checkbox(f"Private arrangement", key=f"child_support_private_{i}")
                
                children.append({
                    'first_name': child_first_name,
                    'last_name': child_last_name,
                    'dob': child_dob,
                    'gender': child_gender,
                    'school': child_school,
                    'special_needs': child_special_needs,
                    'medical_conditions': child_medical_conditions,
                    'current_residence': current_residence,
                    'time_with_applicant': time_with_applicant,
                    'proposed_arrangements': proposed_arrangements,
                    'child_support_paid': child_support_paid,
                    'child_support_amount': child_support_amount,
                    'child_support_assessment': child_support_assessment,
                    'child_support_private': child_support_private
                })
        
        st.session_state.case_data['children_info'] = {
            'has_children': True,
            'children': children
        }
        
        # Parenting concerns
        st.markdown("### 🛡️ Parenting Concerns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            domestic_violence = st.checkbox("Domestic violence concerns", key="domestic_violence")
            substance_abuse = st.checkbox("Substance abuse concerns", key="substance_abuse")
            mental_health = st.checkbox("Mental health concerns", key="mental_health")
        
        with col2:
            neglect_concerns = st.checkbox("Child neglect concerns", key="neglect_concerns")
            alienation_concerns = st.checkbox("Parental alienation concerns", key="alienation_concerns")
            relocation_issues = st.checkbox("Relocation issues", key="relocation_issues")
        
        parenting_concerns_details = st.text_area(
            "Details of concerns",
            placeholder="Provide detailed information about any parenting concerns...",
            key="parenting_concerns_details"
        )
        
        st.session_state.case_data['children_info']['concerns'] = {
            'domestic_violence': domestic_violence,
            'substance_abuse': substance_abuse,
            'mental_health': mental_health,
            'neglect_concerns': neglect_concerns,
            'alienation_concerns': alienation_concerns,
            'relocation_issues': relocation_issues,
            'details': parenting_concerns_details
        }
    
    else:
        st.session_state.case_data['children_info'] = {'has_children': False}

def render_case_summary_and_creation(case_manager, user_info: Dict, firm_info: Dict):
    """Step 6: Case summary and final creation"""
    
    st.markdown("### 📋 Step 6: Case Summary & Creation")
    st.markdown("*Review case details and create the new matter*")
    
    # Display comprehensive case summary
    case_data = st.session_state.case_data
    
    # Case overview
    st.markdown("#### 📖 Case Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        case_type_info = AUSTRALIAN_FAMILY_LAW_CASE_TYPES.get(case_data.get('case_type', ''), {})
        st.markdown(f"**Case Type:** {case_type_info.get('name', 'Unknown')}")
        st.markdown(f"**Title:** {case_data.get('case_details', {}).get('title', 'Unknown')}")
        st.markdown(f"**Priority:** {case_data.get('case_details', {}).get('priority', 'Unknown')}")
        st.markdown(f"**Assigned Lawyer:** {case_data.get('case_details', {}).get('assigned_lawyer', 'Unknown')}")
    
    with col2:
        client_info = case_data.get('client_info', {}).get('applicant', {})
        st.markdown(f"**Client:** {client_info.get('first_name', '')} {client_info.get('last_name', '')}")
        st.markdown(f"**Respondent:** {case_data.get('client_info', {}).get('respondent', {}).get('first_name', '')} {case_data.get('client_info', {}).get('respondent', {}).get('last_name', '')}")
        st.markdown(f"**Estimated Value:** AUD ${case_data.get('case_details', {}).get('estimated_value', 0):,}")
        st.markdown(f"**Court:** {AUSTRALIAN_JURISDICTIONS.get(case_data.get('case_details', {}).get('court_jurisdiction', ''), 'Unknown')}")
    
    # Financial summary
    if 'financial_info' in case_data:
        st.markdown("#### 💰 Financial Summary")
        render_financial_summary(case_data['financial_info'])
    
    # Children summary
    if case_data.get('children_info', {}).get('has_children'):
        st.markdown("#### 👶 Children Summary")
        children = case_data['children_info'].get('children', [])
        st.markdown(f"**Number of children:** {len(children)}")
        
        for i, child in enumerate(children):
            age = (date.today() - child['dob']).days // 365 if child['dob'] else 0
            st.markdown(f"• {child['first_name']} {child['last_name']} (Age: {age})")
    
    # Case creation options
    st.markdown("#### ⚙️ Creation Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        create_initial_documents = st.checkbox(
            "Generate initial documents",
            value=True,
            help="Create standard forms and templates for this case type"
        )
        
        setup_workflows = st.checkbox(
            "Setup automated workflows",
            value=True,
            help="Create task templates and milestone tracking"
        )
    
    with col2:
        notify_team = st.checkbox(
            "Notify team members",
            value=True,
            help="Send notifications to assigned lawyer and support staff"
        )
        
        create_client_portal = st.checkbox(
            "Setup client portal access",
            value=False,
            help="Create secure client access to case information"
        )
    
    # Final confirmation and creation
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🏛️ Create Australian Family Law Case", use_container_width=True, type="primary"):
            if create_case(case_manager, case_data, user_info, firm_info):
                st.success("✅ Case created successfully!")
                st.balloons()
                
                # Reset wizard state
                st.session_state.show_case_creation = False
                st.session_state.wizard_step = 1
                st.session_state.case_data = {}
                
                # Redirect to case list
                st.session_state.show_case_list = True
                st.rerun()
            else:
                st.error("❌ Failed to create case. Please check the information and try again.")

# Helper functions
def validate_current_step() -> bool:
    """Validate current wizard step"""
    wizard_step = st.session_state.wizard_step
    case_data = st.session_state.case_data
    
    if wizard_step == 1:
        return 'case_type' in case_data
    elif wizard_step == 2:
        client_info = case_data.get('client_info', {})
        applicant = client_info.get('applicant', {})
        respondent = client_info.get('respondent', {})
        return (applicant.get('first_name') and applicant.get('last_name') and 
                respondent.get('first_name') and respondent.get('last_name'))
    elif wizard_step == 3:
        case_details = case_data.get('case_details', {})
        return (case_details.get('title') and case_details.get('case_summary') and
                case_details.get('separation_date'))
    elif wizard_step in [4, 5]:
        return True  # Financial and children info are optional
    elif wizard_step == 6:
        return True  # Summary step
    
    return False

def render_asset_pool_summary():
    """Render asset pool summary"""
    
    if 'financial_info' not in st.session_state.case_data:
        return
    
    financial_info = st.session_state.case_data['financial_info']
    
    # Calculate totals
    total_assets = 0
    total_liabilities = 0
    
    # Real estate
    properties = financial_info.get('properties', [])
    for prop in properties:
        total_assets += prop.get('value', 0)
        total_liabilities += prop.get('mortgage', 0)
    
    # Financial assets
    financial_assets = financial_info.get('financial_assets', {})
    total_assets += sum(financial_assets.values())
    
    # Personal property
    personal_property = financial_info.get('personal_property', {})
    total_assets += sum(personal_property.values())
    
    # Business interests
    business = financial_info.get('business', {})
    total_assets += business.get('value', 0)
    total_liabilities += business.get('liabilities', 0)
    
    # Superannuation
    superannuation = financial_info.get('superannuation', {})
    total_assets += superannuation.get('applicant_balance', 0)
    total_assets += superannuation.get('respondent_balance', 0)
    
    # Liabilities
    liabilities = financial_info.get('liabilities', {})
    total_liabilities += sum(liabilities.values())
    
    net_asset_pool = total_assets - total_liabilities
    
    # Display summary
    st.markdown("---")
    st.markdown("#### 📊 Asset Pool Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Assets", f"${total_assets:,.2f}")
    
    with col2:
        st.metric("Total Liabilities", f"${total_liabilities:,.2f}")
    
    with col3:
        st.metric("Net Asset Pool", f"${net_asset_pool:,.2f}")

def create_case(case_manager, case_data: Dict, user_info: Dict, firm_info: Dict) -> bool:
    """Create the case in the database"""
    
    try:
        # Prepare case data for database
        case_info = {
            'case_type': case_data.get('case_type'),
            'title': case_data.get('case_details', {}).get('title'),
            'description': case_data.get('case_details', {}).get('case_summary'),
            'priority': case_data.get('case_details', {}).get('priority'),
            'status': case_data.get('case_details', {}).get('status', 'active'),
            'assigned_lawyer_id': user_info.get('id'),  # Current user for now
            'firm_id': firm_info.get('id'),
            'client_name': f"{case_data.get('client_info', {}).get('applicant', {}).get('first_name', '')} {case_data.get('client_info', {}).get('applicant', {}).get('last_name', '')}",
            'created_by': user_info.get('id'),
            'case_data': case_data  # Store full case data as JSON
        }
        
        # Create case using case manager
        result = case_manager.create_case(case_info)
        
        return result.get('success', False)
        
    except Exception as e:
        st.error(f"Error creating case: {str(e)}")
        return False

# Additional rendering functions for other dashboard components
def render_recent_case_activity(case_manager, user_info: Dict, firm_info: Dict):
    """Render recent case activity"""
    
    st.markdown("### 🔔 Recent Activity")
    
    # Mock data for demonstration
    activities = [
        {"time": "2 hours ago", "activity": "New divorce application created", "case": "Smith v Smith", "user": "Sarah Chen"},
        {"time": "4 hours ago", "activity": "Financial disclosure uploaded", "case": "Wilson Property Settlement", "user": "AI Assistant"},
        {"time": "6 hours ago", "activity": "Court date scheduled", "case": "Brown Parenting Orders", "user": "Michael Wong"},
        {"time": "1 day ago", "activity": "Consent orders approved", "case": "Taylor Financial Agreement", "user": "System"},
    ]
    
    for activity in activities:
        st.markdown(f"""
        <div style="padding: 0.75rem; border-left: 3px solid #0ea5e9; margin: 0.5rem 0; background: #f8fafc;">
            <div style="font-size: 0.85rem; color: #64748b;">{activity['time']} • {activity['user']}</div>
            <div style="font-weight: 500; color: #1e293b;">{activity['activity']}</div>
            <div style="font-size: 0.85rem; color: #0ea5e9;">Case: {activity['case']}</div>
        </div>
        """, unsafe_allow_html=True)

def render_upcoming_deadlines(case_manager, user_info: Dict, firm_info: Dict):
    """Render upcoming deadlines"""
    
    st.markdown("### ⏰ Upcoming Deadlines")
    
    # Mock data for demonstration
    deadlines = [
        {"date": "Feb 15", "task": "File divorce application", "case": "Smith v Smith", "priority": "high"},
        {"date": "Feb 18", "task": "Submit Form 13", "case": "Wilson Settlement", "priority": "medium"},
        {"date": "Feb 22", "task": "Court hearing", "case": "Brown Parenting", "priority": "high"},
        {"date": "Feb 25", "task": "Mediation session", "case": "Taylor Agreement", "priority": "medium"},
    ]
    
    for deadline in deadlines:
        priority_color = "#dc2626" if deadline['priority'] == "high" else "#ea580c"
        
        st.markdown(f"""
        <div style="padding: 0.75rem; border-left: 4px solid {priority_color}; margin: 0.5rem 0; background: white; border-radius: 0 8px 8px 0;">
            <div style="font-weight: 600; color: #1e293b;">{deadline['date']} - {deadline['task']}</div>
            <div style="color: #64748b; font-size: 0.9rem;">Case: {deadline['case']}</div>
        </div>
        """, unsafe_allow_html=True)

def render_case_analytics(case_manager, user_info: Dict, firm_info: Dict):
    """Render case analytics"""
    st.info("📊 Case analytics dashboard will be implemented in Phase 3")

def render_case_assignment_interface(case_manager, user_info: Dict, firm_info: Dict):
    """Render case assignment interface"""
    st.info("👥 Case assignment interface will be implemented in Phase 3")

def render_firm_case_list(case_manager, user_info: Dict, firm_info: Dict, view_all: bool = False):
    """Render firm case list"""
    st.info("📋 Firm case list will be implemented in Phase 3")

def render_case_calendar(case_manager, user_info: Dict, firm_info: Dict):
    """Render case calendar"""
    st.info("📅 Case calendar will be implemented in Phase 3")

def render_lawyer_case_list(case_manager, user_info: Dict, firm_info: Dict):
    """Render lawyer's case list"""
    st.info("📂 Lawyer case list will be implemented in Phase 3")

def render_lawyer_case_overview(case_manager, user_info: Dict, firm_info: Dict):
    """Render lawyer case overview"""
    st.info("📋 Lawyer case overview will be implemented in Phase 3")

def render_paralegal_task_list(case_manager, user_info: Dict, firm_info: Dict):
    """Render paralegal task list"""
    st.info("📝 Paralegal task list will be implemented in Phase 3")

def render_client_case_overview(case_manager, user_info: Dict, firm_info: Dict):
    """Render client case overview"""  
    st.info("👤 Client case overview will be implemented in Phase 3")