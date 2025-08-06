#!/usr/bin/env python3
"""
Client Portal with AI Integration for LegalLLM Professional
Secure client self-service portal with AI-powered assistance and case updates
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
import os
import sys
from enum import Enum

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import existing components
try:
    from shared.database.models import Case, Document, User, ClientMessage
    from core.enhanced_llm_engine import EnhancedLegalLLMEngine
    from components.ai_case_assistant import AICaseContext
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database/AI components not available: {e}")
    DATABASE_AVAILABLE = False

# Client Portal Features
class PortalFeature(Enum):
    CASE_OVERVIEW = "case_overview"
    DOCUMENT_MANAGEMENT = "document_management"
    AI_ASSISTANT = "ai_assistant"
    BILLING_INFORMATION = "billing_information"
    SECURE_MESSAGING = "secure_messaging"
    APPOINTMENT_SCHEDULING = "appointment_scheduling"
    PROGRESS_TRACKING = "progress_tracking"

class MessageType(Enum):
    GENERAL_INQUIRY = "general_inquiry"
    CASE_UPDATE = "case_update"
    DOCUMENT_QUESTION = "document_question"
    BILLING_INQUIRY = "billing_inquiry"
    APPOINTMENT_REQUEST = "appointment_request"
    URGENT_MATTER = "urgent_matter"

class ClientAccessLevel(Enum):
    BASIC = "basic"         # View-only access
    STANDARD = "standard"   # Standard client features
    PREMIUM = "premium"     # Enhanced features with AI
    VIP = "vip"            # Full access with priority support

# AI Assistant Modes for Clients
class ClientAIMode(Enum):
    CASE_GUIDANCE = "case_guidance"       # Case-specific guidance
    LEGAL_EDUCATION = "legal_education"   # General legal information
    DOCUMENT_HELP = "document_help"       # Document assistance
    PROCESS_EXPLANATION = "process_explanation"  # Legal process explanation

def render_client_portal(user_info: Dict, firm_info: Dict):
    """Main client portal interface"""
    
    st.markdown("## 👤 Client Portal")
    st.markdown("*Secure self-service portal with AI-powered legal assistance*")
    
    # Client welcome message
    render_client_welcome(user_info, firm_info)
    
    # Portal navigation
    portal_tab, cases_tab, documents_tab, ai_tab, messages_tab, billing_tab = st.tabs([
        "🏠 Overview", "📋 My Cases", "📄 Documents", "🤖 AI Assistant", "💬 Messages", "💰 Billing"
    ])
    
    with portal_tab:
        render_client_overview(user_info, firm_info)
    
    with cases_tab:
        render_client_cases(user_info, firm_info)
    
    with documents_tab:
        render_client_documents(user_info, firm_info)
    
    with ai_tab:
        render_client_ai_assistant(user_info, firm_info)
    
    with messages_tab:
        render_client_messaging(user_info, firm_info)
    
    with billing_tab:
        render_client_billing(user_info, firm_info)

def render_client_welcome(user_info: Dict, firm_info: Dict):
    """Client welcome section with personalized information"""
    
    client_name = user_info.get('full_name', 'Valued Client')
    firm_name = firm_info.get('name', 'Your Law Firm')
    
    # Welcome banner
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); padding: 2rem; border-radius: 12px; color: white; margin-bottom: 2rem;">
        <h3 style="margin: 0 0 0.5rem 0;">Welcome back, {client_name}! 👋</h3>
        <div style="opacity: 0.9; font-size: 1rem;">
            Your secure portal for legal matters with {firm_name}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick status overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_client_metric_card("Active Matters", "2", "📋")
    
    with col2:
        render_client_metric_card("Unread Messages", "3", "💬")
    
    with col3:
        render_client_metric_card("Documents", "12", "📄")
    
    with col4:
        render_client_metric_card("Next Appointment", "Feb 20", "📅")

def render_client_metric_card(title: str, value: str, icon: str):
    """Render client metric card"""
    
    st.markdown(f"""
    <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 0.25rem;">
            {value}
        </div>
        <div style="font-size: 0.85rem; color: #64748b;">
            {title}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_client_overview(user_info: Dict, firm_info: Dict):
    """Client portal overview dashboard"""
    
    st.markdown("### 📊 Your Legal Matters Overview")
    
    # Recent activity
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 🔔 Recent Activity")
        
        activities = get_client_recent_activity(user_info.get('id', ''))
        
        if activities:
            for activity in activities:
                render_activity_item(activity)
        else:
            st.info("No recent activity to display.")
    
    with col2:
        st.markdown("#### ⚡ Quick Actions")
        
        # Quick action buttons
        if st.button("📄 Upload Document", use_container_width=True):
            st.session_state.client_action = "upload_document"
        
        if st.button("💬 Send Message", use_container_width=True):
            st.session_state.client_action = "send_message"
        
        if st.button("📅 Schedule Meeting", use_container_width=True):
            st.session_state.client_action = "schedule_meeting"
        
        if st.button("🤖 Ask AI Assistant", use_container_width=True):
            st.session_state.client_action = "ai_assistant"
        
        # Portal help
        st.markdown("#### 🆘 Need Help?")
        st.markdown("""
        <div style="padding: 1rem; background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe;">
            <div style="color: #1e40af; font-size: 0.9rem;">
                • Use the AI Assistant for instant help<br>
                • Contact your lawyer via secure messaging<br>
                • Download case documents anytime<br>
                • Track your matter progress in real-time
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Important notices
    render_client_notices(user_info)

def render_activity_item(activity: Dict):
    """Render individual activity item"""
    
    activity_icons = {
        'document_uploaded': '📄',
        'message_received': '💬',
        'case_updated': '📋',
        'appointment_scheduled': '📅',
        'payment_processed': '💰'
    }
    
    icon = activity_icons.get(activity.get('type', ''), '📝')
    
    st.markdown(f"""
    <div style="padding: 0.75rem; border-left: 3px solid #0ea5e9; margin: 0.5rem 0; background: #f8fafc; border-radius: 0 6px 6px 0;">
        <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
            <span style="font-size: 1.2rem; margin-right: 0.5rem;">{icon}</span>
            <span style="font-weight: 600; color: #1e293b;">{activity['title']}</span>
        </div>
        <div style="color: #64748b; font-size: 0.9rem; margin-bottom: 0.25rem;">
            {activity['description']}
        </div>
        <div style="color: #6b7280; font-size: 0.8rem;">
            {activity['timestamp']} • {activity.get('matter', 'General')}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_client_cases(user_info: Dict, firm_info: Dict):
    """Client cases overview with AI-enhanced information"""
    
    st.markdown("### 📋 Your Legal Matters")
    
    # Get client cases
    client_cases = get_client_cases(user_info.get('id', ''))
    
    if not client_cases:
        st.info("You currently have no active legal matters.")
        return
    
    # Cases overview
    for case in client_cases:
        render_client_case_card(case, user_info)

def render_client_case_card(case: Dict, user_info: Dict):
    """Render detailed case card for client"""
    
    case_status_colors = {
        'active': '#16a34a',
        'in_progress': '#0ea5e9',
        'pending': '#f59e0b',
        'completed': '#64748b',
        'on_hold': '#ef4444'
    }
    
    status = case.get('status', 'active')
    status_color = case_status_colors.get(status, '#64748b')
    
    with st.expander(f"📋 {case['title']}", expanded=True):
        
        # Case header
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"**Case Type:** {case.get('case_type', 'Unknown')}")
            st.markdown(f"**Lawyer:** {case.get('lawyer', 'Unknown')}")
        
        with col2:
            st.markdown(f"**Started:** {case.get('start_date', 'Unknown')}")
            st.markdown(f"**Next Action:** {case.get('next_action', 'None scheduled')}")
        
        with col3:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="background: {status_color}; color: white; padding: 0.5rem; border-radius: 20px; font-weight: 600; font-size: 0.85rem;">
                    {status.replace('_', ' ').title()}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Case progress
        progress = case.get('progress', 0)
        st.markdown(f"**Progress:** {progress}% Complete")
        st.progress(progress / 100)
        
        # Case description
        if case.get('description'):
            st.markdown("**Matter Description:**")
            st.markdown(case['description'])
        
        # AI-powered case insights for client
        render_client_case_insights(case, user_info)
        
        # Case actions
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📄 Documents", key=f"docs_{case['id']}", use_container_width=True):
                view_case_documents(case['id'], user_info)
        
        with col2:
            if st.button("📊 Progress", key=f"progress_{case['id']}", use_container_width=True):
                view_case_progress(case['id'], user_info)
        
        with col3:
            if st.button("💬 Message", key=f"message_{case['id']}", use_container_width=True):
                send_case_message(case['id'], user_info)
        
        with col4:
            if st.button("🤖 AI Help", key=f"ai_{case['id']}", use_container_width=True):
                get_case_ai_assistance(case['id'], user_info)

def render_client_case_insights(case: Dict, user_info: Dict):
    """AI-powered case insights for clients"""
    
    st.markdown("**🤖 AI Case Insights:**")
    
    # Generate client-appropriate insights
    insights = generate_client_case_insights(case, user_info)
    
    for insight in insights:
        insight_color = {"positive": "#166534", "neutral": "#0ea5e9", "attention": "#ea580c"}
        color = insight_color.get(insight.get('type', 'neutral'), "#64748b")
        
        st.markdown(f"""
        <div style="padding: 0.75rem; border-left: 4px solid {color}; background: #f8fafc; border-radius: 0 6px 6px 0; margin: 0.5rem 0;">
            <div style="color: #1e293b; font-weight: 600; margin-bottom: 0.25rem;">
                {insight['title']}
            </div>
            <div style="color: #64748b; font-size: 0.9rem;">
                {insight['description']}
            </div>
            {insight.get('action') and f'<div style="color: {color}; font-size: 0.85rem; margin-top: 0.25rem; font-weight: 500;">💡 {insight["action"]}</div>' or ''}
        </div>
        """, unsafe_allow_html=True)

def render_client_documents(user_info: Dict, firm_info: Dict):
    """Client document management with AI assistance"""
    
    st.markdown("### 📄 Your Documents")
    
    # Document upload section
    render_client_document_upload(user_info)
    
    # Client documents list
    render_client_document_list(user_info)

def render_client_document_upload(user_info: Dict):
    """Secure document upload for clients"""
    
    st.markdown("#### 📎 Upload Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File upload
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=['pdf', 'docx', 'txt', 'jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
            help="Upload documents related to your legal matters"
        )
        
        if uploaded_files:
            # Document categorization
            document_type = st.selectbox(
                "Document Type:",
                ["Financial Records", "Correspondence", "Legal Documents", "Evidence", "Personal Documents", "Other"],
                help="Select the type of documents you're uploading"
            )
            
            # Case association
            client_cases = get_client_cases(user_info.get('id', ''))
            case_options = ["General/Not case-specific"] + [f"{case['title']}" for case in client_cases]
            
            associated_case = st.selectbox(
                "Associate with Matter:",
                case_options,
                help="Link documents to a specific legal matter"
            )
            
            # Document description
            description = st.text_area(
                "Description (Optional):",
                placeholder="Brief description of the documents...",
                help="Provide context for your legal team"
            )
    
    with col2:
        st.markdown("**📋 Upload Guidelines**")
        st.markdown("""
        <div style="padding: 1rem; background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe;">
            <div style="color: #1e40af; font-size: 0.9rem;">
                ✅ <strong>Accepted formats:</strong><br>
                • PDF, Word documents<br>
                • Images (JPG, PNG)<br>
                • Text files<br><br>
                
                📏 <strong>File size limit:</strong> 50MB<br><br>
                
                🔒 <strong>Security:</strong><br>
                • All uploads are encrypted<br>
                • Only your legal team can access<br>
                • Automatic backup and storage
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Upload processing
    if uploaded_files and st.button("📤 Upload Documents", type="primary"):
        process_client_document_upload(uploaded_files, document_type, associated_case, description, user_info)

def render_client_document_list(user_info: Dict):
    """List of client's documents with AI categorization"""
    
    st.markdown("#### 📋 Your Document Library")
    
    # Document filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        doc_filter = st.selectbox(
            "Filter by Type:",
            ["All Documents", "Financial Records", "Legal Documents", "Correspondence", "Evidence", "Other"]
        )
    
    with col2:
        case_filter = st.selectbox(
            "Filter by Matter:",
            ["All Matters"] + [case['title'] for case in get_client_cases(user_info.get('id', ''))]
        )
    
    with col3:
        sort_order = st.selectbox(
            "Sort by:",
            ["Upload Date (Newest)", "Upload Date (Oldest)", "Name (A-Z)", "Name (Z-A)"]
        )
    
    # Get filtered documents
    client_documents = get_client_documents(user_info.get('id', ''), doc_filter, case_filter, sort_order)
    
    if not client_documents:
        st.info("No documents found. Upload documents to get started.")
        return
    
    # Document list
    for doc in client_documents:
        render_client_document_item(doc, user_info)

def render_client_document_item(document: Dict, user_info: Dict):
    """Render individual document item for client"""
    
    st.markdown(f"""
    <div style="padding: 1rem; border: 1px solid #e2e8f0; border-radius: 8px; margin: 0.5rem 0; background: white;">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
            <div style="flex: 1;">
                <h6 style="color: #1e293b; margin: 0 0 0.25rem 0;">📄 {document['name']}</h6>
                <div style="color: #64748b; font-size: 0.9rem; margin-bottom: 0.5rem;">
                    {document.get('description', 'No description provided')}
                </div>
                <div style="font-size: 0.85rem; color: #475569;">
                    <strong>Type:</strong> {document.get('type', 'Unknown')} • 
                    <strong>Matter:</strong> {document.get('case', 'General')} • 
                    <strong>Uploaded:</strong> {document.get('upload_date', 'Unknown')}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Document actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👁️ View", key=f"view_doc_{document['id']}", use_container_width=True):
            view_client_document(document, user_info)
    
    with col2:
        if st.button("📥 Download", key=f"download_doc_{document['id']}", use_container_width=True):
            download_client_document(document, user_info)
    
    with col3:
        if st.button("🤖 AI Analysis", key=f"ai_doc_{document['id']}", use_container_width=True):
            get_document_ai_analysis(document, user_info)

def render_client_ai_assistant(user_info: Dict, firm_info: Dict):
    """AI assistant specifically designed for clients"""
    
    st.markdown("### 🤖 Your AI Legal Assistant")
    st.markdown("*Get instant answers to your legal questions with AI-powered assistance*")
    
    # AI assistant modes
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # AI conversation interface
        render_client_ai_chat(user_info, firm_info)
    
    with col2:
        # AI assistant features
        st.markdown("#### 🎯 What I Can Help With")
        
        ai_capabilities = [
            {"title": "Case Updates", "description": "Get status updates on your legal matters", "icon": "📋"},
            {"title": "Legal Education", "description": "Understand legal processes and terminology", "icon": "📚"},
            {"title": "Document Questions", "description": "Ask about documents in your case", "icon": "📄"},
            {"title": "Process Guidance", "description": "Learn about next steps in your matter", "icon": "🛤️"},
            {"title": "General Inquiries", "description": "Ask general legal questions", "icon": "❓"}
        ]
        
        for capability in ai_capabilities:
            if st.button(f"{capability['icon']} {capability['title']}", key=f"ai_cap_{capability['title']}", use_container_width=True):
                st.session_state.ai_topic = capability['title']
                st.rerun()
        
        # AI disclaimer
        st.markdown("---")
        st.markdown("**⚠️ Important Disclaimer**")
        st.markdown("""
        <div style="padding: 0.75rem; background: #fef3c7; border-radius: 6px; border: 1px solid #fed7aa;">
            <div style="color: #92400e; font-size: 0.85rem;">
                The AI assistant provides general information only and is not a substitute for professional legal advice. 
                For specific legal questions, please contact your lawyer directly.
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_client_ai_chat(user_info: Dict, firm_info: Dict):
    """AI chat interface for clients"""
    
    # Chat history
    if 'client_chat_history' not in st.session_state:
        st.session_state.client_chat_history = [
            {
                'role': 'assistant',
                'content': f"Hello {user_info.get('first_name', 'there')}! I'm your AI legal assistant. I can help you understand your case, explain legal processes, and answer general questions about your matters with {firm_info.get('name', 'your law firm')}. What would you like to know?",
                'timestamp': datetime.now()
            }
        ]
    
    # Display chat history
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.client_chat_history:
            if message['role'] == 'user':
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin: 1rem 0;">
                    <div style="background: #0ea5e9; color: white; padding: 0.75rem 1rem; border-radius: 18px 18px 4px 18px; max-width: 80%;">
                        {message['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin: 1rem 0;">
                    <div style="background: #f1f5f9; color: #1e293b; padding: 0.75rem 1rem; border-radius: 18px 18px 18px 4px; max-width: 80%; border: 1px solid #e2e8f0;">
                        🤖 {message['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    user_input = st.text_input(
        "Ask your AI assistant:",
        placeholder="Type your question here...",
        key="client_ai_input"
    )
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        send_message = st.button("Send Message", type="primary", use_container_width=True)
    
    with col2:
        clear_chat = st.button("Clear Chat", use_container_width=True)
    
    # Handle user input
    if send_message and user_input:
        # Add user message
        st.session_state.client_chat_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now()
        })
        
        # Generate AI response
        ai_response = generate_client_ai_response(user_input, user_info, firm_info)
        
        # Add AI response
        st.session_state.client_chat_history.append({
            'role': 'assistant',
            'content': ai_response,
            'timestamp': datetime.now()
        })
        
        st.rerun()
    
    if clear_chat:
        st.session_state.client_chat_history = []
        st.rerun()

def render_client_messaging(user_info: Dict, firm_info: Dict):
    """Secure messaging system for clients"""
    
    st.markdown("### 💬 Secure Messaging")
    st.markdown("*Communicate securely with your legal team*")
    
    # Message composition
    render_client_message_composer(user_info, firm_info)
    
    # Message history
    render_client_message_history(user_info, firm_info)

def render_client_message_composer(user_info: Dict, firm_info: Dict):
    """Message composition interface"""
    
    st.markdown("#### ✏️ Send New Message")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Message form
        message_type = st.selectbox(
            "Message Type:",
            ["General Inquiry", "Case Update Request", "Document Question", "Billing Inquiry", "Appointment Request", "Urgent Matter"],
            help="Select the type of message for proper routing"
        )
        
        # Case association
        client_cases = get_client_cases(user_info.get('id', ''))
        case_options = ["General/Not case-specific"] + [case['title'] for case in client_cases]
        
        associated_case = st.selectbox(
            "Related Matter:",
            case_options,
            help="Associate message with a specific legal matter"
        )
        
        subject = st.text_input(
            "Subject:",
            placeholder="Brief subject line...",
            help="Provide a clear subject for your message"
        )
        
        message_content = st.text_area(
            "Message:",
            placeholder="Type your message here...",
            height=150,
            help="Provide details about your inquiry or request"
        )
    
    with col2:
        st.markdown("**📋 Messaging Guidelines**")
        st.markdown("""
        <div style="padding: 1rem; background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe;">
            <div style="color: #1e40af; font-size: 0.9rem;">
                ✅ <strong>Response Times:</strong><br>
                • General inquiries: 24-48 hours<br>
                • Urgent matters: Within 4 hours<br>
                • Emergency: Call office directly<br><br>
                
                🔒 <strong>Security:</strong><br>
                • All messages are encrypted<br>
                • Attorney-client privilege protected<br>
                • Secure file attachments supported<br><br>
                
                💡 <strong>Tips:</strong><br>
                • Be specific in your subject line<br>
                • Include relevant case details<br>
                • Use urgent type only when necessary
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Send message
    if st.button("📤 Send Message", type="primary", use_container_width=True):
        if subject and message_content:
            send_client_message(message_type, associated_case, subject, message_content, user_info)
            st.success("✅ Message sent successfully! Your legal team will respond within the expected timeframe.")
        else:
            st.error("❌ Please provide both a subject and message content.")

def render_client_billing(user_info: Dict, firm_info: Dict):
    """Client billing information and payment portal"""
    
    st.markdown("### 💰 Billing & Payments")
    st.markdown("*View your billing information and make secure payments*")
    
    # Billing overview
    render_client_billing_overview(user_info)
    
    # Billing details
    col1, col2 = st.columns(2)
    
    with col1:
        render_billing_statements(user_info)
    
    with col2:
        render_payment_options(user_info)

def render_client_billing_overview(user_info: Dict):
    """Client billing overview"""
    
    st.markdown("#### 💼 Account Summary")
    
    # Billing metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Balance", "$4,250.00", "-$750")
    
    with col2:
        st.metric("Last Payment", "$2,500.00", "Feb 1, 2024")
    
    with col3:
        st.metric("Total Paid", "$12,750.00", "+$2,500")
    
    with col4:
        st.metric("Outstanding", "$1,750.00", "Due Feb 28")

def render_client_notices(user_info: Dict):
    """Important client notices and alerts"""
    
    notices = get_client_notices(user_info.get('id', ''))
    
    if notices:
        st.markdown("---")
        st.markdown("### 📢 Important Notices")
        
        for notice in notices:
            notice_type_colors = {
                'info': '#0ea5e9',
                'warning': '#f59e0b', 
                'urgent': '#ef4444',
                'success': '#10b981'
            }
            
            color = notice_type_colors.get(notice.get('type', 'info'), '#64748b')
            
            st.markdown(f"""
            <div style="padding: 1rem; border-left: 4px solid {color}; background: #f8fafc; border-radius: 0 8px 8px 0; margin: 0.5rem 0;">
                <div style="font-weight: 600; color: #1e293b; margin-bottom: 0.5rem;">
                    {notice['title']}
                </div>
                <div style="color: #64748b; font-size: 0.9rem; margin-bottom: 0.5rem;">
                    {notice['message']}
                </div>
                <div style="color: #6b7280; font-size: 0.8rem;">
                    {notice['date']}
                </div>
            </div>
            """, unsafe_allow_html=True)

# Helper functions for client portal

def get_client_recent_activity(client_id: str) -> List[Dict]:
    """Get recent activity for client"""
    return [
        {
            'type': 'message_received',
            'title': 'Message from Sarah Chen',
            'description': 'Update on property settlement negotiations',
            'timestamp': '2 hours ago',
            'matter': 'Property Settlement'
        },
        {
            'type': 'document_uploaded',
            'title': 'Document Analysis Complete', 
            'description': 'AI analysis of financial statements completed',
            'timestamp': '1 day ago',
            'matter': 'Divorce Proceedings'
        },
        {
            'type': 'case_updated',
            'title': 'Case Progress Update',
            'description': 'Mediation scheduled for February 25th',
            'timestamp': '2 days ago',
            'matter': 'Family Law Matter'
        }
    ]

def get_client_cases(client_id: str) -> List[Dict]:
    """Get cases for client"""
    return [
        {
            'id': 'case_1',
            'title': 'Property Settlement - Wilson',
            'case_type': 'Family Law - Property',
            'lawyer': 'Sarah Chen',
            'status': 'in_progress',
            'start_date': '2024-01-15',
            'progress': 65,
            'next_action': 'Review property valuations',
            'description': 'Property settlement following separation, including family home and investment properties.'
        },
        {
            'id': 'case_2',
            'title': 'Estate Planning & Wills',
            'case_type': 'Estate Planning',
            'lawyer': 'Michael Wong',
            'status': 'active',
            'start_date': '2024-02-01',
            'progress': 30,
            'next_action': 'Client to provide asset details',
            'description': 'Comprehensive estate planning including will preparation and family trust establishment.'
        }
    ]

def generate_client_case_insights(case: Dict, user_info: Dict) -> List[Dict]:
    """Generate AI insights appropriate for clients"""
    return [
        {
            'type': 'positive',
            'title': 'Strong Settlement Position',
            'description': 'Based on similar cases, you have a favorable position for settlement negotiations.',
            'action': 'Continue cooperating with document requests for best outcome.'
        },
        {
            'type': 'neutral',
            'title': 'Timeline on Track',
            'description': 'Your case is progressing normally compared to similar matters.',
            'action': None
        },
        {
            'type': 'attention',
            'title': 'Outstanding Documents',
            'description': 'Some requested financial documents are still pending.',
            'action': 'Upload missing bank statements to avoid delays.'
        }
    ]

def get_client_documents(client_id: str, doc_filter: str, case_filter: str, sort_order: str) -> List[Dict]:
    """Get filtered client documents"""
    return [
        {
            'id': 'doc_1',
            'name': 'Property Valuation Report.pdf',
            'type': 'Financial Records',
            'case': 'Property Settlement - Wilson',
            'upload_date': '2024-02-10',
            'description': 'Independent valuation of family home'
        },
        {
            'id': 'doc_2',
            'name': 'Bank Statements Jan-Dec 2023.pdf',
            'type': 'Financial Records', 
            'case': 'Property Settlement - Wilson',
            'upload_date': '2024-02-08',
            'description': 'Complete bank statements for financial disclosure'
        }
    ]

def generate_client_ai_response(user_input: str, user_info: Dict, firm_info: Dict) -> str:
    """Generate AI response appropriate for clients"""
    # Mock AI response - would integrate with actual AI system
    responses = {
        'case': "Based on your case information, I can see that your property settlement is progressing well. The current phase involves property valuations, which is normal at this stage. Your lawyer Sarah Chen is handling negotiations professionally.",
        'documents': "I can help you understand the documents in your case. You have uploaded property valuations and financial statements, which are essential for your property settlement. If you need to upload additional documents, use the Documents tab.",
        'process': "The family law process in Australia typically involves several stages: initial consultation, document gathering, negotiation or mediation, and final settlement. You're currently in the negotiation phase, which is positive progress.",
        'billing': "Your current account shows a balance of $4,250. This includes work completed on your property settlement matter. If you have specific billing questions, I recommend contacting your lawyer directly or using the secure messaging system."
    }
    
    # Simple keyword matching for demo
    user_lower = user_input.lower()
    if any(word in user_lower for word in ['case', 'progress', 'status']):
        return responses['case']
    elif any(word in user_lower for word in ['document', 'upload', 'file']):
        return responses['documents']
    elif any(word in user_lower for word in ['process', 'next', 'what happens']):
        return responses['process']
    elif any(word in user_lower for word in ['bill', 'cost', 'payment', 'money']):
        return responses['billing']
    else:
        return f"I understand you're asking about: '{user_input}'. While I can provide general information, for specific legal advice about your matters, please contact your lawyer directly through our secure messaging system. Is there a particular aspect of your case or the legal process you'd like me to explain?"

def get_client_notices(client_id: str) -> List[Dict]:
    """Get important notices for client"""
    return [
        {
            'type': 'warning',
            'title': 'Document Request',
            'message': 'Please upload your 2023 tax return by February 20th to avoid delays in your property settlement.',
            'date': 'February 12, 2024'
        },
        {
            'type': 'info',
            'title': 'Mediation Scheduled',
            'message': 'Mediation session has been scheduled for February 25th at 10:00 AM. Location details will be sent separately.',
            'date': 'February 10, 2024'
        }
    ]

# Placeholder functions for client portal actions
def process_client_document_upload(files, doc_type: str, case: str, description: str, user_info: Dict):
    """Process client document upload"""
    st.success(f"✅ {len(files)} document(s) uploaded successfully! Your legal team will review them shortly.")

def send_client_message(msg_type: str, case: str, subject: str, content: str, user_info: Dict):
    """Send message from client"""
    # Would integrate with secure messaging system
    pass

def view_case_documents(case_id: str, user_info: Dict):
    """View case-specific documents"""
    st.info("📄 Case document viewer will open in a new interface")

def view_case_progress(case_id: str, user_info: Dict):
    """View detailed case progress"""
    st.info("📊 Detailed progress tracking will be shown in expanded view")

def send_case_message(case_id: str, user_info: Dict):
    """Send message about specific case"""
    st.info("💬 Case-specific messaging interface will open")

def get_case_ai_assistance(case_id: str, user_info: Dict):
    """Get AI assistance for specific case"""
    st.info("🤖 Case-specific AI assistant will be activated")

def view_client_document(document: Dict, user_info: Dict):
    """View document in secure viewer"""
    st.info("👁️ Secure document viewer will be implemented in the next phase")

def download_client_document(document: Dict, user_info: Dict):
    """Download document securely"""
    st.info("📥 Secure document download will be implemented in the next phase")

def get_document_ai_analysis(document: Dict, user_info: Dict):
    """Get AI analysis of document"""
    st.info("🤖 Document AI analysis will be implemented in the next phase")

def render_billing_statements(user_info: Dict):
    """Render billing statements"""
    st.info("📋 Detailed billing statements will be implemented in the next phase")

def render_payment_options(user_info: Dict):
    """Render payment options"""
    st.info("💳 Secure payment processing will be implemented in the next phase")

def render_client_message_history(user_info: Dict, firm_info: Dict):
    """Render message history"""
    st.info("📜 Message history interface will be implemented in the next phase")