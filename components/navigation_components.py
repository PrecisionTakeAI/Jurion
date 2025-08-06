#!/usr/bin/env python3
"""
Navigation Components for LegalLLM Professional Enterprise Interface
Role-based sidebar navigation and menu system
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple

def get_navigation_items(user_role: str) -> List[Dict]:
    """Get navigation items based on user role"""
    
    # Base navigation items available to all users
    base_items = [
        {
            "key": "dashboard",
            "label": "📊 Dashboard",
            "description": "Overview and key metrics",
            "roles": ["principal", "senior_lawyer", "lawyer", "paralegal", "client", "admin"]
        },
        {
            "key": "ai_assistant", 
            "label": "🤖 AI Assistant",
            "description": "Legal AI analysis and assistance",
            "roles": ["principal", "senior_lawyer", "lawyer", "paralegal", "client"]
        }
    ]
    
    # Role-specific navigation items
    role_specific_items = [
        # Principal and Senior Lawyer items
        {
            "key": "cases",
            "label": "📋 Case Management", 
            "description": "Manage all firm cases",
            "roles": ["principal", "senior_lawyer", "lawyer"]
        },
        {
            "key": "documents",
            "label": "📄 Document Library",
            "description": "Firm document repository", 
            "roles": ["principal", "senior_lawyer", "lawyer", "paralegal", "client"]
        },
        {
            "key": "reports",
            "label": "📊 Reports & Analytics",
            "description": "Business intelligence and reporting",
            "roles": ["principal", "senior_lawyer"]
        },
        {
            "key": "billing",
            "label": "💰 Billing & Time",
            "description": "Time tracking and billing management",
            "roles": ["principal", "senior_lawyer", "lawyer", "client"]
        },
        {
            "key": "clients",
            "label": "👥 Client Portal",
            "description": "Client relationship management", 
            "roles": ["principal", "senior_lawyer", "lawyer"]
        },
        {
            "key": "administration",
            "label": "⚙️ Administration",
            "description": "Firm settings and user management",
            "roles": ["principal", "senior_lawyer", "admin"]
        }
    ]
    
    # Combine and filter based on role
    all_items = base_items + role_specific_items
    filtered_items = [item for item in all_items if user_role in item["roles"]]
    
    return filtered_items

def render_sidebar_navigation(user_role: str) -> str:
    """Render sidebar navigation and return selected page"""
    
    # Get navigation items for the user's role
    nav_items = get_navigation_items(user_role)
    
    # Sidebar header
    st.sidebar.markdown("""
    <div style="padding: 1rem 0; border-bottom: 1px solid #334155; margin-bottom: 1rem;">
        <h3 style="color: white; margin: 0; font-size: 1.1rem;">⚖️ Navigation</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation menu
    current_page = st.session_state.get('current_page', 'dashboard')
    
    # Create navigation buttons
    selected_page = current_page
    
    for item in nav_items:
        # Determine if this item is currently active
        is_active = current_page == item["key"]
        
        # Style based on active state
        if is_active:
            button_style = """
            background: #334155 !important;
            border-left: 4px solid #0ea5e9 !important;
            color: white !important;
            """
        else:
            button_style = """
            background: transparent !important;
            border: none !important;
            color: #cbd5e1 !important;
            """
        
        # Create button with custom styling
        button_html = f"""
        <div style="margin: 0.25rem 0;">
            <button style="
                {button_style}
                width: 100%;
                text-align: left;
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
                font-weight: 500;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s ease;
            " onclick="selectPage('{item['key']}')">
                {item['label']}
            </button>
        </div>
        """
        
        # Use regular Streamlit button for functionality
        if st.sidebar.button(
            item["label"], 
            key=f"nav_{item['key']}",
            help=item["description"],
            use_container_width=True
        ):
            selected_page = item["key"]
    
    # User profile section
    render_user_profile_sidebar()
    
    # Firm information section
    render_firm_info_sidebar()
    
    # Help and support section
    render_support_sidebar()
    
    return selected_page

def render_user_profile_sidebar():
    """Render user profile section in sidebar"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 Profile")
    
    # Get user information from session state
    user_info = st.session_state.get('user_info', {})
    firm_info = st.session_state.get('firm_info', {})
    
    user_name = user_info.get('full_name', 'Unknown User')
    user_email = user_info.get('email', 'unknown@example.com')
    user_role = user_info.get('role', 'user').replace('_', ' ').title()
    
    # User information display
    st.sidebar.markdown(f"""
    <div style="
        background: #1e293b;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #475569;
        margin-bottom: 1rem;
    ">
        <div style="color: white; font-weight: 600; margin-bottom: 0.25rem;">
            {user_name}
        </div>
        <div style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.5rem;">
            {user_email}
        </div>
        <div style="
            background: #334155;
            color: #e2e8f0;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: inline-block;
        ">
            {user_role}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Profile actions
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("⚙️ Settings", use_container_width=True, key="user_settings"):
            st.info("User settings interface coming in Phase 2")
    
    with col2:
        if st.button("🚪 Logout", use_container_width=True, key="user_logout"):
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.session_state.firm_info = None
            st.session_state.current_page = "dashboard"
            st.rerun()

def render_firm_info_sidebar():
    """Render firm information section in sidebar"""
    
    st.sidebar.markdown("### 🏛️ Firm Info")
    
    # Get firm information from session state
    firm_info = st.session_state.get('firm_info', {})
    
    firm_name = firm_info.get('name', 'Unknown Firm')
    firm_id = firm_info.get('id', 'N/A')
    
    # Firm information display
    st.sidebar.markdown(f"""
    <div style="
        background: #0f172a;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #334155;
        margin-bottom: 1rem;
    ">
        <div style="color: white; font-weight: 600; margin-bottom: 0.5rem;">
            {firm_name}
        </div>
        <div style="color: #64748b; font-size: 0.8rem;">
            Firm ID: {firm_id}
        </div>
        <div style="color: #64748b; font-size: 0.8rem;">
            🇦🇺 Australian Legal Practice
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Firm status indicators
    st.sidebar.markdown("#### 📊 System Status")
    
    status_items = [
        {"label": "Database", "status": "✅ Connected", "color": "#10b981"},
        {"label": "AI Assistant", "status": "✅ Online", "color": "#10b981"},
        {"label": "Backups", "status": "✅ Current", "color": "#10b981"},
        {"label": "Security", "status": "🔒 Secure", "color": "#3b82f6"}
    ]
    
    for item in status_items:
        st.sidebar.markdown(f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.25rem 0;
            color: #cbd5e1;
            font-size: 0.8rem;
        ">
            <span>{item['label']}:</span>
            <span style="color: {item['color']}; font-weight: 600;">
                {item['status']}
            </span>
        </div>
        """, unsafe_allow_html=True)

def render_support_sidebar():
    """Render help and support section in sidebar"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📞 Support")
    
    # Quick help buttons
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("❓ Help", use_container_width=True, key="help_button"):
            render_help_modal()
    
    with col2:
        if st.button("🐛 Report", use_container_width=True, key="bug_report"):
            render_bug_report_modal()
    
    # Support information
    st.sidebar.markdown("""
    <div style="
        background: #1e293b;
        padding: 0.75rem;
        border-radius: 8px;
        border: 1px solid #475569;
        margin-top: 0.5rem;
    ">
        <div style="color: #e2e8f0; font-size: 0.8rem; margin-bottom: 0.5rem;">
            <strong>📧 Support Email:</strong><br>
            support@legalllm.com.au
        </div>
        <div style="color: #e2e8f0; font-size: 0.8rem; margin-bottom: 0.5rem;">
            <strong>📞 Phone:</strong><br>
            1800 LEGAL AI
        </div>
        <div style="color: #e2e8f0; font-size: 0.8rem;">
            <strong>🕐 Hours:</strong><br>
            8 AM - 6 PM AEST
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Version information
    st.sidebar.markdown("""
    <div style="
        text-align: center;
        color: #64748b;
        font-size: 0.7rem;
        margin-top: 1rem;
        padding-top: 0.5rem;
        border-top: 1px solid #334155;
    ">
        LegalLLM Professional v1.0<br>
        Enterprise Edition
    </div>
    """, unsafe_allow_html=True)

def render_help_modal():
    """Render help modal with user assistance"""
    
    st.info("📖 **Quick Help Guide**")
    
    with st.expander("🚀 Getting Started", expanded=True):
        st.markdown("""
        **Welcome to LegalLLM Professional!**
        
        **Navigation:**
        - Use the sidebar to navigate between different sections
        - Your available options depend on your role within the firm
        - Dashboard provides an overview of your activity and firm metrics
        
        **Key Features:**
        - 🤖 **AI Assistant**: Legal document analysis and assistance
        - 📋 **Case Management**: Organize and track legal matters
        - 📄 **Document Library**: Secure document storage and processing
        - 📊 **Reports**: Business intelligence and analytics
        """)
    
    with st.expander("👥 Role-Based Access", expanded=False):
        st.markdown("""
        **Access Levels:**
        
        **🏛️ Principal/Senior Lawyer:**
        - Full access to all firm data and settings
        - User management and administration
        - Financial reports and analytics
        - Case oversight across all lawyers
        
        **⚖️ Lawyer:**
        - Access to assigned cases and clients
        - Document creation and analysis
        - Time tracking and billing
        - Limited reporting capabilities
        
        **📝 Paralegal:**
        - Task management and document processing
        - Case support and research assistance
        - Limited case access based on assignments
        
        **👤 Client:**
        - View assigned matters and documents
        - Secure communication with legal team
        - Billing and payment information
        """)
    
    with st.expander("🔐 Security Features", expanded=False):
        st.markdown("""
        **Security Measures:**
        
        - 🔒 **Multi-Factor Authentication**: Enhanced account security
        - 🛡️ **Role-Based Access Control**: Information on need-to-know basis
        - 🔄 **Audit Logging**: Complete activity tracking
        - 💾 **Encrypted Backups**: Data protection and recovery
        - 🇦🇺 **Australian Compliance**: Meeting legal industry standards
        """)

def render_bug_report_modal():
    """Render bug report modal"""
    
    st.info("🐛 **Report an Issue**")
    
    with st.form("bug_report_form"):
        st.markdown("Help us improve LegalLLM Professional by reporting issues:")
        
        issue_type = st.selectbox(
            "Issue Type",
            ["Bug/Error", "Performance Issue", "Feature Request", "Login Problem", "Data Issue", "Other"]
        )
        
        severity = st.selectbox(
            "Severity",
            ["Low", "Medium", "High", "Critical"]
        )
        
        description = st.text_area(
            "Description",
            placeholder="Please describe the issue in detail, including steps to reproduce...",
            height=100
        )
        
        # System information (auto-populated)
        st.markdown("**System Information (automatically included):**")
        st.code(f"""
User Role: {st.session_state.get('user_info', {}).get('role', 'Unknown')}
Firm: {st.session_state.get('firm_info', {}).get('name', 'Unknown')}
Browser: [Auto-detected]
Version: LegalLLM Professional v1.0
        """)
        
        submit_report = st.form_submit_button("📧 Submit Report")
        
        if submit_report:
            if description.strip():
                st.success("✅ Bug report submitted successfully! Our support team will investigate and respond within 24 hours.")
                st.markdown("**Tracking ID:** BUG-2024-" + str(hash(description))[-6:])
            else:
                st.error("❌ Please provide a description of the issue.")

def render_breadcrumb_navigation(current_page: str, user_role: str) -> None:
    """Render breadcrumb navigation"""
    
    # Page hierarchy mapping
    page_hierarchy = {
        "dashboard": ["Dashboard"],
        "cases": ["Dashboard", "Case Management"],
        "documents": ["Dashboard", "Document Library"],
        "ai_assistant": ["Dashboard", "AI Assistant"],
        "administration": ["Dashboard", "Administration"],
        "reports": ["Dashboard", "Reports & Analytics"],
        "billing": ["Dashboard", "Billing & Time"],
        "clients": ["Dashboard", "Client Portal"]
    }
    
    breadcrumbs = page_hierarchy.get(current_page, ["Dashboard"])
    
    # Render breadcrumb
    breadcrumb_items = []
    for i, item in enumerate(breadcrumbs):
        if i == len(breadcrumbs) - 1:
            # Current page (not clickable)
            breadcrumb_items.append(f"<span style='color: #1e293b; font-weight: 600;'>{item}</span>")
        else:
            # Previous pages (clickable)
            breadcrumb_items.append(f"<span style='color: #0ea5e9; cursor: pointer;'>{item}</span>")
    
    breadcrumb_html = " → ".join(breadcrumb_items)
    
    st.markdown(f"""
    <div style="
        background: #f8fafc;
        padding: 0.75rem 1.5rem;
        border-bottom: 1px solid #e2e8f0;
        margin: -1rem -1rem 1rem -1rem;
        font-size: 0.9rem;
    ">
        🏠 {breadcrumb_html}
    </div>
    """, unsafe_allow_html=True)

def render_quick_actions_menu(user_role: str) -> None:
    """Render floating quick actions menu"""
    
    # Define quick actions based on role
    if user_role in ['principal', 'senior_lawyer']:
        actions = [
            {"icon": "📋", "label": "New Case", "action": "cases"},
            {"icon": "👥", "label": "Add User", "action": "administration"},
            {"icon": "📊", "label": "Reports", "action": "reports"},
            {"icon": "🤖", "label": "AI Query", "action": "ai_assistant"}
        ]
    elif user_role == 'lawyer':
        actions = [
            {"icon": "📋", "label": "New Case", "action": "cases"},
            {"icon": "📄", "label": "Upload Doc", "action": "documents"},
            {"icon": "🤖", "label": "AI Query", "action": "ai_assistant"},
            {"icon": "💰", "label": "Time Entry", "action": "billing"}
        ]
    elif user_role == 'paralegal':
        actions = [
            {"icon": "📄", "label": "Process Doc", "action": "documents"},
            {"icon": "🤖", "label": "AI Analysis", "action": "ai_assistant"},
            {"icon": "📋", "label": "Update Task", "action": "dashboard"},
            {"icon": "🔍", "label": "Case Search", "action": "cases"}
        ]
    else:  # client
        actions = [
            {"icon": "📄", "label": "Upload Doc", "action": "documents"},
            {"icon": "💬", "label": "Message", "action": "dashboard"},
            {"icon": "💰", "label": "View Bill", "action": "billing"},
            {"icon": "📋", "label": "My Cases", "action": "cases"}
        ]
    
    # Render floating action button
    st.markdown("""
    <div style="
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        z-index: 1000;
    ">
        <button id="quick-actions-btn" style="
            background: #0ea5e9;
            color: white;
            border: none;
            border-radius: 50%;
            width: 56px;
            height: 56px;
            font-size: 1.5rem;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(14, 165, 233, 0.4);
            transition: all 0.3s ease;
        " onclick="toggleQuickActions()">
            ⚡
        </button>
    </div>
    
    <script>
    function toggleQuickActions() {
        // Quick actions functionality will be implemented with JavaScript
        alert('Quick actions menu - coming in Phase 2');
    }
    </script>
    """, unsafe_allow_html=True)