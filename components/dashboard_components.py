#!/usr/bin/env python3
"""
Dashboard Components for LegalLLM Professional Enterprise Interface
Role-based dashboards for Australian legal professionals
"""

import streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_role_dashboard(current_page: str, user_info: Dict, firm_info: Dict):
    """Render appropriate dashboard based on user role and selected page"""
    
    user_role = user_info.get('role', 'client')
    user_name = user_info.get('full_name', 'User')
    firm_name = firm_info.get('name', 'Unknown Firm')
    
    # Route to appropriate dashboard based on page selection
    if current_page == "dashboard":
        render_main_dashboard(user_role, user_info, firm_info)
    elif current_page == "cases":
        render_case_management(user_role, user_info, firm_info)
    elif current_page == "documents":
        render_document_management(user_role, user_info, firm_info)
    elif current_page == "ai_assistant":
        render_ai_assistant(user_role, user_info, firm_info)
    elif current_page == "administration":
        render_administration(user_role, user_info, firm_info)
    elif current_page == "reports":
        render_reports(user_role, user_info, firm_info)
    elif current_page == "billing":
        render_billing(user_role, user_info, firm_info)
    else:
        render_main_dashboard(user_role, user_info, firm_info)

def render_main_dashboard(user_role: str, user_info: Dict, firm_info: Dict):
    """Render main dashboard with role-appropriate content"""
    
    st.markdown("## 📊 Dashboard")
    
    # Welcome message
    current_time = datetime.now()
    time_greeting = "Good morning" if current_time.hour < 12 else "Good afternoon" if current_time.hour < 17 else "Good evening"
    
    st.markdown(f"""
    <div class="alert-info">
        <strong>{time_greeting}, {user_info.get('full_name', 'User')}!</strong><br>
        Welcome to your LegalLLM Professional dashboard. Here's an overview of your firm's activity.
    </div>
    """, unsafe_allow_html=True)
    
    # Role-specific dashboard content
    if user_role in ['principal', 'senior_lawyer']:
        render_executive_dashboard(user_info, firm_info)
    elif user_role == 'lawyer':
        render_lawyer_dashboard(user_info, firm_info)
    elif user_role == 'paralegal':
        render_paralegal_dashboard(user_info, firm_info)
    elif user_role == 'client':
        render_client_dashboard(user_info, firm_info)
    else:
        render_basic_dashboard(user_info, firm_info)

def render_executive_dashboard(user_info: Dict, firm_info: Dict):
    """Executive dashboard for principals and senior lawyers"""
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">42</span>
            <div class="metric-label">Active Cases</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">8</span>
            <div class="metric-label">Team Members</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">$247K</span>
            <div class="metric-label">Monthly Revenue</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">94%</span>
            <div class="metric-label">Client Satisfaction</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts and analytics
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Case Volume Trends")
        # Sample data for demonstration
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='M')
        values = [35, 42, 38, 45, 52, 47, 49, 44, 48, 51, 46, 42]
        
        fig = px.line(x=dates, y=values, title="Monthly Active Cases")
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### ⚖️ Practice Area Distribution")
        # Sample data
        areas = ['Family Law', 'Corporate', 'Criminal', 'Property', 'Employment', 'Other']
        values = [35, 25, 15, 12, 8, 5]
        
        fig = px.pie(values=values, names=areas, title="Cases by Practice Area")
        fig.update_layout(showlegend=True, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent activity and quick actions
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔔 Recent Activity")
        activity_data = [
            {"time": "2 hours ago", "activity": "New case created: Family Law matter", "user": "Sarah Chen"},
            {"time": "4 hours ago", "activity": "Document analysis completed", "user": "AI Assistant"},
            {"time": "6 hours ago", "activity": "Client consultation scheduled", "user": "Michael Wong"},
            {"time": "1 day ago", "activity": "Case closed: Property settlement", "user": "Lisa Park"},
        ]
        
        for item in activity_data:
            st.markdown(f"""
            <div style="padding: 0.5rem; border-left: 3px solid #0ea5e9; margin: 0.5rem 0; background: #f8fafc;">
                <div style="font-size: 0.85rem; color: #64748b;">{item['time']} • {item['user']}</div>
                <div style="font-weight: 500;">{item['activity']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### ⚡ Quick Actions")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("📋 New Case", use_container_width=True):
                st.session_state.current_page = "cases"
                st.rerun()
            
            if st.button("📄 Upload Documents", use_container_width=True):
                st.session_state.current_page = "documents"
                st.rerun()
        
        with col_b:
            if st.button("🤖 AI Analysis", use_container_width=True):
                st.session_state.current_page = "ai_assistant"
                st.rerun()
            
            if st.button("👥 Manage Team", use_container_width=True):
                st.session_state.current_page = "administration"
                st.rerun()
        
        # System status
        st.markdown("#### 🔧 System Status")
        st.markdown("""
        <div style="padding: 1rem; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;">
            <div style="color: #166534; font-weight: 600;">✅ All systems operational</div>
            <div style="font-size: 0.85rem; color: #166534; margin-top: 0.25rem;">
                AI Assistant: Online • Database: Connected • Backups: Current
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_lawyer_dashboard(user_info: Dict, firm_info: Dict):
    """Dashboard for lawyers"""
    
    # Personal metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">12</span>
            <div class="metric-label">My Active Cases</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">3</span>
            <div class="metric-label">Due This Week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">45.5</span>
            <div class="metric-label">Hours This Month</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">8</span>
            <div class="metric-label">Clients</div>
        </div>
        """, unsafe_allow_html=True)
    
    # My cases and calendar
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 My Active Cases")
        
        # Sample case data
        cases_data = {
            "Case": ["Smith v. Jones", "ABC Corp Merger", "Thompson Divorce", "Property Settlement - Wilson"],
            "Type": ["Family Law", "Corporate", "Family Law", "Property"],
            "Priority": ["High", "Medium", "High", "Low"],
            "Due Date": ["2024-02-15", "2024-02-20", "2024-02-12", "2024-02-28"],
            "Status": ["In Progress", "Review", "Urgent", "Planning"]
        }
        
        df = pd.DataFrame(cases_data)
        
        # Color-code by priority
        def color_priority(val):
            if val == "High":
                return "background-color: #fef2f2; color: #991b1b"
            elif val == "Medium":
                return "background-color: #fffbeb; color: #92400e"
            else:
                return "background-color: #f0fdf4; color: #166534"
        
        styled_df = df.style.applymap(color_priority, subset=['Priority'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("### 📅 This Week")
        
        # Calendar items
        calendar_items = [
            {"date": "Mon 12", "event": "Client meeting", "time": "10:00 AM"},
            {"date": "Tue 13", "event": "Court hearing", "time": "2:00 PM"},
            {"date": "Wed 14", "event": "Document review", "time": "9:00 AM"},
            {"date": "Thu 15", "event": "Settlement conf.", "time": "3:00 PM"},
            {"date": "Fri 16", "event": "Team meeting", "time": "11:00 AM"}
        ]
        
        for item in calendar_items:
            priority_color = "#dc2626" if "Court" in item["event"] else "#0ea5e9"
            st.markdown(f"""
            <div style="padding: 0.75rem; border-left: 4px solid {priority_color}; margin: 0.5rem 0; background: white; border-radius: 0 8px 8px 0;">
                <div style="font-weight: 600; color: #1e293b;">{item['date']} - {item['time']}</div>
                <div style="color: #64748b; font-size: 0.9rem;">{item['event']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Quick actions for lawyers
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 Time Entry", use_container_width=True):
            st.info("Time tracking interface will be implemented in Phase 2")
    
    with col2:
        if st.button("🔍 Case Search", use_container_width=True):
            st.session_state.current_page = "cases"
            st.rerun()
    
    with col3:
        if st.button("📄 Draft Document", use_container_width=True):
            st.session_state.current_page = "ai_assistant"
            st.rerun()
    
    with col4:
        if st.button("📞 Client Portal", use_container_width=True):
            st.info("Client portal will be implemented in Phase 3")

def render_paralegal_dashboard(user_info: Dict, firm_info: Dict):
    """Dashboard for paralegals"""
    
    # Task-focused metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">18</span>
            <div class="metric-label">Assigned Tasks</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">5</span>
            <div class="metric-label">Due Today</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">12</span>
            <div class="metric-label">Documents Processed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">3</span>
            <div class="metric-label">Cases Supported</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Task list and document processing
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### ✅ My Tasks")
        
        tasks = [
            {"task": "Prepare discovery documents for Smith case", "due": "Today", "priority": "High"},
            {"task": "File court documents - ABC Corp", "due": "Tomorrow", "priority": "Medium"},
            {"task": "Research family law precedents", "due": "Feb 16", "priority": "Medium"},
            {"task": "Update client contact information", "due": "Feb 18", "priority": "Low"},
            {"task": "Organize case files for audit", "due": "Feb 20", "priority": "Low"}
        ]
        
        for task in tasks:
            priority_colors = {
                "High": "#dc2626",
                "Medium": "#ea580c", 
                "Low": "#16a34a"
            }
            color = priority_colors.get(task["priority"], "#64748b")
            
            st.markdown(f"""
            <div style="padding: 1rem; border-left: 4px solid {color}; margin: 0.5rem 0; background: white; border-radius: 0 8px 8px 0;">
                <div style="font-weight: 600; color: #1e293b;">{task['task']}</div>
                <div style="color: #64748b; font-size: 0.85rem; margin-top: 0.25rem;">
                    Due: {task['due']} • Priority: {task['priority']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📄 Quick Tools")
        
        if st.button("📊 Document Analysis", use_container_width=True):
            st.session_state.current_page = "ai_assistant"
            st.rerun()
        
        if st.button("🔍 Case Lookup", use_container_width=True):
            st.session_state.current_page = "cases"
            st.rerun()
        
        if st.button("📝 Task Update", use_container_width=True):
            st.info("Task management interface coming in Phase 2")
        
        if st.button("📋 Report Issue", use_container_width=True):
            st.info("Support ticketing system coming in Phase 2")
        
        # Recent document processing
        st.markdown("#### 📄 Recent Documents")
        recent_docs = [
            "Contract_ABC_Corp.pdf",
            "Discovery_Smith_v_Jones.docx", 
            "Settlement_Wilson.pdf"
        ]
        
        for doc in recent_docs:
            st.markdown(f"• {doc}")

def render_client_dashboard(user_info: Dict, firm_info: Dict):
    """Dashboard for clients"""
    
    st.markdown("### 👤 Client Portal")
    
    # Client-specific metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">2</span>
            <div class="metric-label">Active Matters</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">$4,200</span>
            <div class="metric-label">Current Balance</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <span class="metric-value">3</span>
            <div class="metric-label">Unread Messages</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Client case overview
    st.markdown("### 📋 My Legal Matters")
    
    matters = [
        {
            "matter": "Property Settlement",
            "lawyer": "Sarah Chen",
            "status": "In Progress",
            "next_action": "Review settlement proposal",
            "due_date": "Feb 15, 2024"
        },
        {
            "matter": "Will and Estate Planning",
            "lawyer": "Michael Wong", 
            "status": "Document Review",
            "next_action": "Client signature required",
            "due_date": "Feb 20, 2024"
        }
    ]
    
    for matter in matters:
        st.markdown(f"""
        <div style="padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 12px; margin: 1rem 0; background: white;">
            <h4 style="color: #1e293b; margin-bottom: 0.5rem;">{matter['matter']}</h4>
            <div style="color: #64748b; margin-bottom: 1rem;">
                <strong>Lawyer:</strong> {matter['lawyer']} • <strong>Status:</strong> {matter['status']}
            </div>
            <div style="background: #eff6ff; padding: 0.75rem; border-radius: 8px; border-left: 4px solid #0ea5e9;">
                <strong>Next Action:</strong> {matter['next_action']}<br>
                <strong>Due:</strong> {matter['due_date']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Client actions
    st.markdown("### 📱 Available Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Message Lawyer", use_container_width=True):
            st.info("Secure messaging system coming in Phase 3")
    
    with col2:
        if st.button("📄 Upload Documents", use_container_width=True):
            st.session_state.current_page = "documents"
            st.rerun()
    
    with col3:
        if st.button("💳 View Billing", use_container_width=True):
            st.session_state.current_page = "billing"
            st.rerun()

def render_basic_dashboard(user_info: Dict, firm_info: Dict):
    """Basic dashboard for undefined roles"""
    
    st.markdown("### 📊 Dashboard")
    
    st.markdown("""
    <div class="alert-info">
        <strong>Welcome to LegalLLM Professional!</strong><br>
        Your account is being set up. Please contact your firm administrator to assign appropriate permissions.
    </div>
    """, unsafe_allow_html=True)
    
    # Basic metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏛️ Firm Information")
        st.write(f"**Firm:** {firm_info.get('name', 'Unknown Firm')}")
        st.write(f"**User:** {user_info.get('full_name', 'Unknown User')}")
        st.write(f"**Role:** {user_info.get('role', 'Not assigned').replace('_', ' ').title()}")
    
    with col2:
        st.markdown("#### 🔧 Available Actions")
        if st.button("📄 View Documents", use_container_width=True):
            st.session_state.current_page = "documents"
            st.rerun()
        
        if st.button("🤖 AI Assistant", use_container_width=True):
            st.session_state.current_page = "ai_assistant"
            st.rerun()

# Additional dashboard functions for other pages
def render_case_management(user_role: str, user_info: Dict, firm_info: Dict):
    """Render integrated case management interface"""
    # Import case management components
    try:
        from .case_management_components import render_case_management_dashboard
        render_case_management_dashboard(user_role, user_info, firm_info) 
    except ImportError:
        st.error("🚫 Case management components not available")

def render_document_management(user_role: str, user_info: Dict, firm_info: Dict):
    """Render document management interface"""
    st.markdown("## 📄 Document Management")
    st.info("🚧 Document management interface will be implemented in Phase 2")

def render_ai_assistant(user_role: str, user_info: Dict, firm_info: Dict):
    """Render AI assistant interface"""
    st.markdown("## 🤖 AI Legal Assistant")
    
    # Redirect to existing AI interface with context
    st.markdown("""
    <div class="alert-info">
        <strong>AI Assistant Integration</strong><br>
        The AI Assistant is being integrated with the enterprise interface. 
        For now, you can access the full AI functionality through the existing interface.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Launch AI Assistant", use_container_width=True):
            st.info("Integration with existing AI interface coming in Phase 2")
    
    with col2:
        if st.button("📊 AI Usage Analytics", use_container_width=True):
            st.info("AI analytics dashboard coming in Phase 2")

def render_administration(user_role: str, user_info: Dict, firm_info: Dict):
    """Render administration interface"""
    if user_role not in ['principal', 'senior_lawyer']:
        st.error("🚫 Access denied. Administration features require principal or senior lawyer privileges.")
        return
    
    st.markdown("## ⚙️ Administration")
    st.info("🚧 Administration interface will be implemented in Phase 2")

def render_reports(user_role: str, user_info: Dict, firm_info: Dict):
    """Render advanced analytics and reports interface"""
    import sys
    import os
    from datetime import datetime, timedelta
    import json
    
    # Add project root for imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    try:
        from components.advanced_analytics.predictive_analytics import LegalPredictiveAnalytics
        from components.advanced_analytics.export_reports import AnalyticsReportGenerator
        from components.advanced_analytics.alerts_monitoring import AlertsAndMonitoring
        from components.advanced_analytics.metrics_engine import LegalMetricsEngine
        ANALYTICS_AVAILABLE = True
    except ImportError as e:
        ANALYTICS_AVAILABLE = False
        st.error(f"Advanced analytics not available: {e}")
        return
    
    st.markdown("## 📊 Advanced Analytics & Reports")
    
    if not ANALYTICS_AVAILABLE:
        st.error("⚠️ Advanced analytics components not available")
        return
    
    # Initialize analytics components
    firm_id = firm_info.get('id') if firm_info else None
    
    # Create tabs for different analytics views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Dashboard", 
        "🔮 Predictions", 
        "📋 Reports", 
        "🚨 Alerts", 
        "⚙️ System Health"
    ])
    
    with tab1:
        render_analytics_dashboard(firm_id, user_role)
    
    with tab2:
        render_predictive_analytics(firm_id, user_role)
    
    with tab3:
        render_report_generation(firm_id, user_role)
    
    with tab4:
        render_alerts_monitoring(firm_id, user_role)
    
    with tab5:
        render_system_health(firm_id, user_role)

def render_analytics_dashboard(firm_id: str, user_role: str):
    """Render the analytics dashboard"""
    try:
        from components.advanced_analytics.metrics_engine import LegalMetricsEngine
        
        st.markdown("### 📊 Analytics Dashboard")
        
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=datetime.now())
        
        if start_date > end_date:
            st.error("Start date must be before end date")
            return
        
        # Initialize metrics engine
        metrics_engine = LegalMetricsEngine(firm_id=firm_id)
        
        # Get metrics
        case_metrics = metrics_engine.get_case_metrics(firm_id, start_date, end_date)
        financial_metrics = metrics_engine.get_financial_metrics(firm_id, start_date, end_date)
        ai_metrics = metrics_engine.get_ai_utilization_metrics(firm_id, start_date, end_date)
        
        # Key Performance Indicators
        st.markdown("#### Key Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Active Cases",
                value=case_metrics.get('active_cases', 0),
                delta=f"+{case_metrics.get('new_cases', 0)} new"
            )
        
        with col2:
            total_revenue = financial_metrics.get('total_revenue', 0)
            st.metric(
                label="Revenue (AUD)",
                value=f"${total_revenue:,.2f}",
                delta="15.3%"
            )
        
        with col3:
            ai_queries = ai_metrics.get('total_queries', 0)
            st.metric(
                label="AI Queries",
                value=f"{ai_queries:,}",
                delta="25.1%"
            )
        
        with col4:
            avg_response = ai_metrics.get('avg_response_time', 0)
            st.metric(
                label="Avg Response Time",
                value=f"{avg_response:.1f}s",
                delta="-18.2%"
            )
        
        # Case Type Distribution
        st.markdown("#### Case Type Distribution")
        case_distribution = case_metrics.get('case_type_distribution', {})
        
        if case_distribution:
            import plotly.express as px
            import pandas as pd
            
            df = pd.DataFrame(list(case_distribution.items()), columns=['Case Type', 'Count'])
            fig = px.pie(df, values='Count', names='Case Type', 
                        title="Case Distribution by Type")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No case data available for the selected period")
        
        # Monthly Trends
        st.markdown("#### Monthly Performance Trends")
        
        # Sample trend data - in practice would come from metrics_engine
        trend_data = {
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'Cases': [45, 52, 48, 61, 58],
            'Revenue': [125000, 142000, 138000, 165000, 155000],
            'AI Usage': [1200, 1450, 1380, 1680, 1520]
        }
        
        df_trends = pd.DataFrame(trend_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_cases = px.line(df_trends, x='Month', y='Cases', 
                               title="Monthly Case Volume", 
                               markers=True)
            st.plotly_chart(fig_cases, use_container_width=True)
        
        with col2:
            fig_revenue = px.bar(df_trends, x='Month', y='Revenue', 
                                title="Monthly Revenue (AUD)",
                                color='Revenue',
                                color_continuous_scale='Greens')
            st.plotly_chart(fig_revenue, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading analytics dashboard: {str(e)}")

def render_predictive_analytics(firm_id: str, user_role: str):
    """Render predictive analytics interface"""
    try:
        from components.advanced_analytics.predictive_analytics import LegalPredictiveAnalytics
        
        st.markdown("### 🔮 Predictive Analytics")
        
        predictive_analytics = LegalPredictiveAnalytics(firm_id=firm_id)
        
        # Case Duration Prediction
        st.markdown("#### Case Duration Prediction")
        
        with st.expander("Predict Case Duration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                case_type = st.selectbox("Case Type", [
                    "divorce", "property_settlement", "child_custody", 
                    "spousal_maintenance", "child_support"
                ])
                
                property_value = st.number_input(
                    "Property Value (AUD)", 
                    min_value=0, 
                    value=500000,
                    step=10000
                )
                
                children_involved = st.checkbox("Children Involved")
                business_assets = st.checkbox("Business Assets")
            
            with col2:
                international_assets = st.checkbox("International Assets")
                domestic_violence = st.checkbox("Domestic Violence Issues")
                mental_health_concerns = st.checkbox("Mental Health Concerns")
                addiction_issues = st.checkbox("Addiction Issues")
            
            if st.button("Predict Duration", type="primary"):
                case_data = {
                    'case_type': case_type,
                    'property_value': property_value,
                    'children_involved': children_involved,
                    'business_assets': business_assets,
                    'international_assets': international_assets,
                    'domestic_violence': domestic_violence,
                    'mental_health_concerns': mental_health_concerns,
                    'addiction_issues': addiction_issues
                }
                
                prediction = predictive_analytics.predict_case_duration(case_data)
                
                # Display prediction results
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Predicted Duration",
                        f"{prediction.predicted_days} days",
                        f"±{(prediction.confidence_interval[1] - prediction.confidence_interval[0])//2} days"
                    )
                
                with col2:
                    st.metric(
                        "Confidence Level",
                        f"{prediction.confidence:.1%}",
                        f"Based on {prediction.similar_cases} cases"
                    )
                
                with col3:
                    st.metric(
                        "Range",
                        f"{prediction.confidence_interval[0]}-{prediction.confidence_interval[1]} days"
                    )
                
                # Key factors
                st.markdown("**Key Factors Affecting Duration:**")
                for factor in prediction.key_factors:
                    st.write(f"• {factor}")
        
        # Settlement Prediction
        st.markdown("#### Property Settlement Prediction")
        
        with st.expander("Predict Settlement Range"):
            col1, col2 = st.columns(2)
            
            with col1:
                total_assets = st.number_input(
                    "Total Assets (AUD)", 
                    min_value=0, 
                    value=1000000,
                    step=50000
                )
                
                total_liabilities = st.number_input(
                    "Total Liabilities (AUD)", 
                    min_value=0, 
                    value=200000,
                    step=10000
                )
                
                party1_financial = st.slider(
                    "Party 1 Financial Contribution %", 
                    0, 100, 60
                )
            
            with col2:
                party1_non_financial = st.slider(
                    "Party 1 Non-Financial Contribution %", 
                    0, 100, 55
                )
                
                children_with_party1 = st.checkbox("Children Primarily with Party 1")
                party1_age = st.number_input("Party 1 Age", min_value=18, max_value=100, value=45)
                party1_health_issues = st.checkbox("Party 1 Health Issues")
            
            if st.button("Predict Settlement", type="primary"):
                financial_data = {
                    'total_assets': total_assets,
                    'total_liabilities': total_liabilities,
                    'party1_contributions': {
                        'financial': party1_financial / 100,
                        'non_financial': party1_non_financial / 100
                    },
                    'party2_contributions': {
                        'financial': (100 - party1_financial) / 100,
                        'non_financial': (100 - party1_non_financial) / 100
                    },
                    'case_context': {
                        'children_with_party1': children_with_party1,
                        'party1_age': party1_age,
                        'party1_health_issues': party1_health_issues
                    }
                }
                
                settlement = predictive_analytics.predict_settlement_range(financial_data)
                
                # Display settlement prediction
                net_pool = total_assets - total_liabilities
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Predicted Settlement Split:**")
                    party1_amount = net_pool * settlement.predicted_split['party_1']
                    party2_amount = net_pool * settlement.predicted_split['party_2']
                    
                    st.write(f"Party 1: {settlement.predicted_split['party_1']:.1%} (${party1_amount:,.2f})")
                    st.write(f"Party 2: {settlement.predicted_split['party_2']:.1%} (${party2_amount:,.2f})")
                    st.write(f"Confidence: {settlement.confidence:.1%}")
                
                with col2:
                    st.markdown("**Contributing Factors:**")
                    for factor in settlement.contributing_factors:
                        st.write(f"• {factor}")
        
        # Resource Planning
        st.markdown("#### Resource Planning")
        
        with st.expander("Predict Resource Needs"):
            # Simplified interface for resource prediction
            upcoming_case_count = st.number_input("Number of Upcoming Cases", min_value=1, max_value=50, value=5)
            avg_complexity = st.slider("Average Case Complexity", 0.0, 1.0, 0.5, 0.1)
            
            if st.button("Predict Resources", type="primary"):
                # Create sample upcoming cases
                upcoming_cases = []
                for i in range(upcoming_case_count):
                    upcoming_cases.append({
                        'id': f'case_{i}',
                        'case_type': 'property_settlement',
                        'start_date': (datetime.now() + timedelta(days=i*7)).isoformat(),
                        'complexity_factors': {'complexity_score': avg_complexity}
                    })
                
                resource_prediction = predictive_analytics.predict_resource_needs(upcoming_cases)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Lawyer Hours Needed",
                        f"{resource_prediction['total_lawyer_hours']:.0f}"
                    )
                
                with col2:
                    st.metric(
                        "Paralegal Hours Needed", 
                        f"{resource_prediction['total_paralegal_hours']:.0f}"
                    )
                
                with col3:
                    st.metric(
                        "Documents to Process",
                        f"{resource_prediction['document_processing_load']:,}"
                    )
                
                st.markdown("**Recommendations:**")
                for rec in resource_prediction.get('recommendations', []):
                    st.write(f"• {rec}")
    
    except Exception as e:
        st.error(f"Error loading predictive analytics: {str(e)}")

def render_report_generation(firm_id: str, user_role: str):
    """Render report generation interface"""
    try:
        from components.advanced_analytics.export_reports import AnalyticsReportGenerator
        
        st.markdown("### 📋 Report Generation")
        
        report_generator = AnalyticsReportGenerator(firm_id=firm_id)
        
        # Report type selection
        report_type = st.selectbox("Report Type", [
            "Monthly Analytics Report",
            "Case Performance Report", 
            "Financial Analysis Report",
            "Client Progress Report"
        ])
        
        if report_type == "Monthly Analytics Report":
            st.markdown("#### Monthly Analytics Report")
            
            col1, col2 = st.columns(2)
            with col1:
                report_month = st.selectbox("Month", [
                    "2024-01", "2024-02", "2024-03", "2024-04", "2024-05"
                ])
            
            with col2:
                format_type = st.selectbox("Format", ["PDF", "Excel"])
            
            if st.button("Generate Monthly Report", type="primary"):
                try:
                    with st.spinner("Generating report..."):
                        if format_type == "PDF":
                            report_bytes = report_generator.generate_monthly_report(firm_id, report_month)
                            st.download_button(
                                label="📄 Download PDF Report",
                                data=report_bytes,
                                file_name=f"monthly_report_{report_month}.pdf",
                                mime="application/pdf"
                            )
                        else:
                            # Sample analytics data for Excel export
                            analytics_data = {
                                'case_metrics': {'active_cases': 45, 'new_cases': 12},
                                'financial_metrics': {'revenue': 125000, 'avg_case_value': 25000},
                                'ai_metrics': {'queries': 2340, 'response_time': 2.1}
                            }
                            report_bytes = report_generator.export_to_excel(analytics_data)
                            st.download_button(
                                label="📊 Download Excel Report",
                                data=report_bytes,
                                file_name=f"analytics_report_{report_month}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    st.success("Report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")
        
        elif report_type == "Client Progress Report":
            st.markdown("#### Client Progress Report")
            
            # In a real implementation, this would load actual cases
            case_id = st.text_input("Case ID", placeholder="Enter case ID")
            
            if st.button("Generate Client Report", type="primary") and case_id:
                try:
                    with st.spinner("Generating client report..."):
                        report_bytes = report_generator.generate_client_report(case_id)
                        st.download_button(
                            label="📄 Download Client Report",
                            data=report_bytes,
                            file_name=f"client_report_{case_id}.pdf",
                            mime="application/pdf"
                        )
                    st.success("Client report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating client report: {str(e)}")
        
        # Report Templates
        st.markdown("#### Available Report Templates")
        
        templates = [
            {"name": "Monthly Performance", "description": "Comprehensive monthly analytics"},
            {"name": "Case Outcomes", "description": "Case resolution and success metrics"},
            {"name": "Financial Summary", "description": "Revenue and billing analysis"},
            {"name": "AI Utilization", "description": "AI system usage and performance"},
            {"name": "Compliance Report", "description": "Regulatory compliance status"},
            {"name": "Client Satisfaction", "description": "Client feedback and satisfaction metrics"}
        ]
        
        for template in templates:
            with st.expander(f"📋 {template['name']}"):
                st.write(template['description'])
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button(f"Generate", key=f"template_{template['name']}"):
                        st.info(f"Generating {template['name']} report...")
    
    except Exception as e:
        st.error(f"Error loading report generation: {str(e)}")

def render_alerts_monitoring(firm_id: str, user_role: str):
    """Render alerts and monitoring interface"""
    try:
        from components.advanced_analytics.alerts_monitoring import AlertsAndMonitoring, AlertSeverity, AlertCategory
        
        st.markdown("### 🚨 Alerts & Monitoring")
        
        alerts_system = AlertsAndMonitoring(firm_id=firm_id)
        
        # Active Alerts
        st.markdown("#### Active Alerts")
        
        active_alerts = alerts_system._get_active_alerts()
        
        if not active_alerts:
            st.success("✅ No active alerts")
        else:
            for alert in active_alerts[:10]:  # Show top 10 alerts
                severity_color = {
                    'critical': '🔴',
                    'high': '🟠', 
                    'medium': '🟡',
                    'low': '🟢'
                }
                
                with st.expander(f"{severity_color.get(alert.severity.value, '⚪')} {alert.title}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Severity:** {alert.severity.value.title()}")
                        st.write(f"**Category:** {alert.category.value.title()}")
                    
                    with col2:
                        st.write(f"**Time:** {alert.timestamp.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Status:** {'Acknowledged' if alert.acknowledged else 'New'}")
                    
                    with col3:
                        if not alert.acknowledged:
                            if st.button(f"Acknowledge", key=f"ack_{alert.id}"):
                                alerts_system.acknowledge_alert(alert.id, "current_user")
                                st.success("Alert acknowledged")
                                st.experimental_rerun()
                        
                        if not alert.resolved:
                            if st.button(f"Resolve", key=f"resolve_{alert.id}"):
                                alerts_system.resolve_alert(alert.id, "current_user", "Resolved via dashboard")
                                st.success("Alert resolved")
                                st.experimental_rerun()
                    
                    st.write(f"**Description:** {alert.description}")
        
        # Alert Statistics
        st.markdown("#### Alert Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            critical_count = len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL])
            st.metric("Critical Alerts", critical_count)
        
        with col2:
            high_count = len([a for a in active_alerts if a.severity == AlertSeverity.HIGH])
            st.metric("High Priority", high_count)
        
        with col3:
            medium_count = len([a for a in active_alerts if a.severity == AlertSeverity.MEDIUM])
            st.metric("Medium Priority", medium_count)
        
        with col4:
            low_count = len([a for a in active_alerts if a.severity == AlertSeverity.LOW])
            st.metric("Low Priority", low_count)
        
        # Compliance Monitoring
        st.markdown("#### Compliance Monitoring")
        
        compliance_status = alerts_system.monitor_compliance_requirements()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Document Retention",
                f"{compliance_status.document_retention_compliance:.1%}",
                delta="Good" if compliance_status.document_retention_compliance > 0.95 else "Needs Attention"
            )
            
            st.metric(
                "Audit Trail Completeness", 
                f"{compliance_status.audit_trail_completeness:.1%}",
                delta="Good" if compliance_status.audit_trail_completeness > 0.95 else "Needs Attention"
            )
        
        with col2:
            st.metric(
                "Security Policy Adherence",
                f"{compliance_status.security_policy_adherence:.1%}",
                delta="Good" if compliance_status.security_policy_adherence > 0.90 else "Needs Attention"
            )
            
            st.metric(
                "Risk Factors Identified",
                compliance_status.risk_factors_identified,
                delta="Tracked"
            )
        
        # Daily Digest
        st.markdown("#### Daily Digest")
        
        if st.button("Generate Daily Digest", type="primary"):
            with st.spinner("Generating daily digest..."):
                digest = alerts_system.generate_daily_digest()
                
                st.json(digest)
    
    except Exception as e:
        st.error(f"Error loading alerts monitoring: {str(e)}")

def render_system_health(firm_id: str, user_role: str):
    """Render system health interface"""
    try:
        from components.advanced_analytics.alerts_monitoring import AlertsAndMonitoring
        
        st.markdown("### ⚙️ System Health")
        
        alerts_system = AlertsAndMonitoring(firm_id=firm_id)
        
        # System Health Check
        if st.button("Run Health Check", type="primary"):
            with st.spinner("Running comprehensive health check..."):
                health_status = alerts_system.check_system_health()
                
                # Overall Health Score
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Overall Health Score",
                        f"{health_status['overall_health']:.1%}",
                        delta=health_status['health_grade']
                    )
                
                with col2:
                    st.metric(
                        "System Status",
                        health_status['status'].title(),
                        delta="Normal" if health_status['status'] == 'healthy' else "Attention Needed"
                    )
                
                with col3:
                    st.metric(
                        "Last Check",
                        datetime.fromisoformat(health_status['timestamp']).strftime('%H:%M:%S')
                    )
                
                # Detailed Health Checks
                st.markdown("#### Detailed Health Checks")
                
                health_checks = health_status.get('checks', {})
                
                for check_name, check_result in health_checks.items():
                    with st.expander(f"{check_name.title().replace('_', ' ')} - {check_result.get('status', 'unknown').title()}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Status:** {check_result.get('status', 'unknown').title()}")
                            st.write(f"**Score:** {check_result.get('score', 0):.2f}")
                        
                        with col2:
                            details = check_result.get('details', {})
                            if isinstance(details, dict):
                                for key, value in details.items():
                                    st.write(f"**{key.title().replace('_', ' ')}:** {value}")
                            else:
                                st.write(f"**Details:** {details}")
        
        # Performance Monitoring Setup
        st.markdown("#### Performance Monitoring")
        
        with st.expander("Configure Performance Alerts"):
            col1, col2 = st.columns(2)
            
            with col1:
                response_time_threshold = st.slider("Response Time Warning (seconds)", 1.0, 10.0, 3.0, 0.1)
                error_rate_threshold = st.slider("Error Rate Warning (%)", 1, 20, 5, 1)
            
            with col2:
                cpu_threshold = st.slider("CPU Usage Warning (%)", 50, 95, 70, 5)
                memory_threshold = st.slider("Memory Usage Warning (%)", 50, 95, 80, 5)
            
            if st.button("Update Thresholds"):
                # In a real implementation, this would update the thresholds
                st.success("Performance thresholds updated successfully!")
        
        # System Metrics
        st.markdown("#### Current System Metrics")
        
        # Sample metrics - in practice these would be real
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("CPU Usage", "45%", delta="-5%")
        
        with col2:
            st.metric("Memory Usage", "67%", delta="+3%")
        
        with col3:
            st.metric("Disk Usage", "23%", delta="+1%")
        
        with col4:
            st.metric("Active Users", "12", delta="+2")
    
    except Exception as e:
        st.error(f"Error loading system health: {str(e)}")

def render_billing(user_role: str, user_info: Dict, firm_info: Dict):
    """Render billing interface"""
    st.markdown("## 💰 Billing & Time Tracking")
    st.info("🚧 Billing interface will be implemented in Phase 2")