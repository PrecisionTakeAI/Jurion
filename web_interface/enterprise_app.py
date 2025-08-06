#!/usr/bin/env python3
"""
LegalLLM Professional - Enterprise Multi-Tenant Interface
Australian Legal AI Platform with Role-Based Access Control

Enterprise interface with:
- Multi-tenant firm authentication
- Role-based dashboards (Partner, Senior Lawyer, Lawyer, Paralegal, Client)
- Australian legal compliance and terminology
- Professional case management interface
"""

import streamlit as st
import os
import sys
from datetime import datetime, timedelta
import uuid
from typing import Optional, Dict, List, Any

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import authentication and database components
try:
    from shared.auth.authentication import LegalAuthenticationSystem, AuthenticationRole
    from database.database import DatabaseManager
    from shared.database.models import LawFirm, User, Case, Document
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database components not available: {e}")
    DATABASE_AVAILABLE = False

# Import UI components
from components.auth_components import render_login_form, render_firm_registration
from components.dashboard_components import render_role_dashboard
from components.navigation_components import render_sidebar_navigation
from components.case_management_components import render_case_management_dashboard
from components.workflow_components import render_workflow_dashboard

# Page configuration for professional interface
st.set_page_config(
    page_title="LegalLLM Professional - Enterprise",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling for legal enterprise interface
st.markdown("""
<style>
    /* Global styling for professional legal interface */
    .main-container {
        background: #f8fafc;
        min-height: 100vh;
    }
    
    /* Header styling */
    .enterprise-header {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1.5rem 2rem;
        color: white;
        border-bottom: 3px solid #0ea5e9;
        margin-bottom: 0;
    }
    
    .enterprise-header h1 {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    .enterprise-header .subtitle {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.25rem;
    }
    
    /* Login form styling */
    .login-container {
        max-width: 400px;
        margin: 3rem auto;
        background: white;
        padding: 2.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .login-header h2 {
        color: #1e293b;
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .login-header p {
        color: #64748b;
        font-size: 0.9rem;
    }
    
    /* Form elements */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e2e8f0;
        padding: 0.75rem;
        font-size: 0.95rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #0ea5e9;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 0.95rem;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
    }
    
    /* Dashboard styling */
    .dashboard-container {
        padding: 2rem;
        background: white;
        margin: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
        display: block;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.5rem;
    }
    
    /* Role badge styling */
    .role-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .role-principal {
        background: #fef3c7;
        color: #92400e;
    }
    
    .role-senior-lawyer {
        background: #dbeafe;
        color: #1e40af;
    }
    
    .role-lawyer {
        background: #dcfce7;
        color: #166534;
    }
    
    .role-paralegal {
        background: #f3e8ff;
        color: #7c3aed;
    }
    
    .role-client {
        background: #f1f5f9;
        color: #475569;
    }
    
    /* Sidebar styling */
    .sidebar-nav {
        background: #1e293b;
        color: white;
        height: 100vh;
        padding: 1rem 0;
    }
    
    .nav-item {
        padding: 0.75rem 1.5rem;
        cursor: pointer;
        transition: background 0.2s ease;
        border-left: 4px solid transparent;
    }
    
    .nav-item:hover {
        background: #334155;
        border-left-color: #0ea5e9;
    }
    
    .nav-item.active {
        background: #334155;
        border-left-color: #0ea5e9;
    }
    
    /* Australian legal styling */
    .jurisdiction-badge {
        background: #059669;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    /* Alert styling */
    .alert-info {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #1e40af;
    }
    
    .alert-warning {
        background: #fffbeb;
        border: 1px solid #fed7aa;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #92400e;
    }
    
    .alert-success {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #166534;
    }
    
    /* Loading states */
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 200px;
        color: #64748b;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .login-container {
            margin: 1rem;
            padding: 1.5rem;
        }
        
        .dashboard-container {
            margin: 0.5rem;
            padding: 1rem;
        }
        
        .enterprise-header {
            padding: 1rem;
        }
        
        .enterprise-header h1 {
            font-size: 1.4rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for enterprise interface
def initialize_enterprise_session():
    """Initialize session state variables for enterprise interface"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'firm_info' not in st.session_state:
        st.session_state.firm_info = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"
    if 'auth_system' not in st.session_state and DATABASE_AVAILABLE:
        st.session_state.auth_system = LegalAuthenticationSystem()

def render_enterprise_header():
    """Render professional enterprise header"""
    if st.session_state.authenticated and st.session_state.firm_info:
        firm_name = st.session_state.firm_info.get('name', 'Unknown Firm')
        user_name = st.session_state.user_info.get('full_name', 'User')
        user_role = st.session_state.user_info.get('role', 'user')
        
        # Get role badge class
        role_class_map = {
            'principal': 'role-principal',
            'senior_lawyer': 'role-senior-lawyer', 
            'lawyer': 'role-lawyer',
            'paralegal': 'role-paralegal',
            'client': 'role-client'
        }
        role_class = role_class_map.get(user_role, 'role-client')
        
        st.markdown(f"""
        <div class="enterprise-header">
            <div style="display: flex; justify-content: between; align-items: center;">
                <div>
                    <h1>⚖️ LegalLLM Professional</h1>
                    <div class="subtitle">{firm_name} • {user_name} • <span class="role-badge {role_class}">{user_role.replace('_', ' ').title()}</span></div>
                </div>
                <div style="margin-left: auto;">
                    <span class="jurisdiction-badge">🇦🇺 Australia</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="enterprise-header">
            <h1>⚖️ LegalLLM Professional</h1>
            <div class="subtitle">Enterprise Legal AI Platform • Australian Law Firms</div>
        </div>
        """, unsafe_allow_html=True)

def handle_authentication():
    """Handle user authentication flow"""
    if not DATABASE_AVAILABLE:
        st.error("🚫 Database system is not available. Please contact your system administrator.")
        return False
    
    # Check if already authenticated
    if st.session_state.authenticated:
        return True
    
    # Render login form
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div class="login-container">
                <div class="login-header">
                    <h2>⚖️ Professional Login</h2>
                    <p>Secure access for Australian legal professionals</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Authentication tabs
            auth_tab, register_tab = st.tabs(["🔐 Login", "📝 Register Firm"])
            
            with auth_tab:
                with st.form("login_form", clear_on_submit=False):
                    st.markdown("### Login to Your Firm")
                    
                    email = st.text_input(
                        "Email Address",
                        placeholder="your.name@lawfirm.com.au",
                        help="Use your firm email address"
                    )
                    
                    password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Enter your secure password"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        login_button = st.form_submit_button("🚀 Login", use_container_width=True)
                    with col2:
                        forgot_password = st.form_submit_button("🔄 Reset Password", use_container_width=True)
                    
                    if login_button and email and password:
                        with st.spinner("Authenticating with secure system..."):
                            try:
                                # Attempt authentication
                                auth_result = st.session_state.auth_system.authenticate_user(email, password)
                                
                                if auth_result["success"]:
                                    # Set session state
                                    st.session_state.authenticated = True
                                    st.session_state.user_info = auth_result["user"]
                                    st.session_state.firm_info = auth_result["firm"]
                                    
                                    st.success(f"✅ Welcome back, {auth_result['user']['full_name']}!")
                                    st.rerun()
                                else:
                                    st.error(f"🚫 Authentication failed: {auth_result['message']}")
                                    
                            except Exception as e:
                                st.error(f"🚫 Login error: {str(e)}")
                    
                    if forgot_password and email:
                        st.info("🔄 Password reset functionality will be implemented in the next phase.")
            
            with register_tab:
                with st.form("firm_registration_form", clear_on_submit=False):
                    st.markdown("### Register Your Law Firm")
                    st.markdown("*Create a new firm account for LegalLLM Professional*")
                    
                    # Firm information
                    firm_name = st.text_input(
                        "Law Firm Name",
                        placeholder="Smith & Associates Legal",
                        help="Official registered name of your law firm"
                    )
                    
                    # Principal lawyer information
                    st.markdown("**Principal Lawyer Details:**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        first_name = st.text_input("First Name", placeholder="John")
                        email = st.text_input("Email Address", placeholder="john.smith@lawfirm.com.au")
                    
                    with col2:
                        last_name = st.text_input("Last Name", placeholder="Smith")
                        phone = st.text_input("Phone Number", placeholder="+61 2 9999 0000")
                    
                    # Australian jurisdiction
                    jurisdiction = st.selectbox(
                        "Primary Jurisdiction",
                        ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                        help="Your primary practicing jurisdiction in Australia"
                    )
                    
                    practitioner_number = st.text_input(
                        "Legal Practitioner Number",
                        placeholder="123456",
                        help="Your Australian legal practitioner registration number"
                    )
                    
                    # Security
                    password = st.text_input("Password", type="password", placeholder="Minimum 8 characters")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    
                    # Terms and conditions
                    terms_accepted = st.checkbox(
                        "I accept the Terms of Service and Privacy Policy",
                        help="Required for firm registration"
                    )
                    
                    register_button = st.form_submit_button("🏛️ Register Firm", use_container_width=True)
                    
                    if register_button:
                        # Validation
                        errors = []
                        if not firm_name or len(firm_name) < 3:
                            errors.append("Firm name must be at least 3 characters")
                        if not first_name or not last_name:
                            errors.append("Both first and last names are required")
                        if not email or "@" not in email:
                            errors.append("Valid email address is required")
                        if not practitioner_number:
                            errors.append("Legal practitioner number is required")
                        if not password or len(password) < 8:
                            errors.append("Password must be at least 8 characters")
                        if password != confirm_password:
                            errors.append("Passwords do not match")
                        if not terms_accepted:
                            errors.append("You must accept the terms and conditions")
                        
                        if errors:
                            for error in errors:
                                st.error(f"❌ {error}")
                        else:
                            with st.spinner("Creating your firm account..."):
                                try:
                                    # Register firm and principal
                                    registration_result = st.session_state.auth_system.register_firm(
                                        firm_name=firm_name,
                                        principal_email=email,
                                        principal_password=password,
                                        principal_first_name=first_name,
                                        principal_last_name=last_name,
                                        principal_phone=phone,
                                        jurisdiction=jurisdiction,
                                        practitioner_number=practitioner_number
                                    )
                                    
                                    if registration_result["success"]:
                                        st.success("🎉 Firm registered successfully! Please login with your credentials.")
                                        st.balloons()
                                    else:
                                        st.error(f"🚫 Registration failed: {registration_result['message']}")
                                        
                                except Exception as e:
                                    st.error(f"🚫 Registration error: {str(e)}")
    
    return False

def main():
    """Main enterprise application function"""
    initialize_enterprise_session()
    render_enterprise_header()
    
    # Handle authentication
    if not handle_authentication():
        return
    
    # Main application interface for authenticated users
    with st.container():
        # Sidebar navigation
        with st.sidebar:
            selected_page = render_sidebar_navigation(
                st.session_state.user_info.get('role', 'user')
            )
            st.session_state.current_page = selected_page
        
        # Main content area
        render_role_dashboard(
            st.session_state.current_page,
            st.session_state.user_info,
            st.session_state.firm_info
        )

if __name__ == "__main__":
    main()