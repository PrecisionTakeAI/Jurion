"""
Consent Management UI Components
===============================

Streamlit UI components for Privacy Act 1988 compliant consent management
with user-friendly flows and multi-agent processing consent.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

from shared.core.security.consent_manager import (
    ConsentManager, ConsentType, ConsentStatus,
    ConsentRequest, ConsentDecision, get_consent_manager
)
from shared.core.security.compliance_monitor import (
    ComplianceMonitor, get_consent_dashboard
)


def render_consent_banner(user_id: str, db_session):
    """Render consent banner for users without necessary consents"""
    consent_manager = get_consent_manager(db_session)
    
    # Check essential consents
    required_consents = [
        ConsentType.AI_PROCESSING,
        ConsentType.DOCUMENT_ANALYSIS
    ]
    
    consent_status = consent_manager.check_consent(user_id, required_consents)
    
    missing_consents = [ct for ct, granted in consent_status.items() if not granted]
    
    if missing_consents:
        with st.warning("🔒 **Privacy & Consent Required**"):
            st.write("To use LegalLLM Professional, we need your consent for:")
            
            for consent_type in missing_consents:
                if consent_type == ConsentType.AI_PROCESSING:
                    st.write("- **AI Processing**: Use artificial intelligence to analyze your legal queries")
                elif consent_type == ConsentType.DOCUMENT_ANALYSIS:
                    st.write("- **Document Analysis**: Process and analyze your legal documents")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info("Your privacy is protected under the Australian Privacy Act 1988")
            with col2:
                if st.button("Review & Consent", type="primary"):
                    st.session_state.show_consent_form = True


def render_consent_form(user_id: str, db_session, firm_id: str):
    """Render comprehensive consent form"""
    st.markdown("## 🔐 Privacy Consent")
    st.markdown("---")
    
    consent_manager = get_consent_manager(db_session, firm_id)
    
    # Get user context
    context = {
        'ip_address': st.session_state.get('client_ip', 'unknown'),
        'user_agent': st.session_state.get('user_agent', 'Streamlit'),
        'source': 'web_interface'
    }
    
    # AI Processing Consent
    with st.expander("🤖 **AI Processing Consent**", expanded=True):
        st.markdown("""
        ### What we do with your data:
        - Process your legal queries using advanced AI models
        - Analyze case information to provide relevant legal insights
        - Generate document summaries and recommendations
        
        ### How we protect your data:
        - All data is encrypted using AES-256-GCM encryption
        - Data is stored securely in Australian data centers
        - Access is restricted to authorized personnel only
        - You can withdraw consent at any time
        
        ### Data retention:
        - Query data retained for 1 year for quality improvement
        - You can request deletion at any time
        """)
        
        ai_consent = st.checkbox(
            "I consent to AI processing of my legal queries and case data",
            key="ai_processing_consent"
        )
    
    # Document Analysis Consent
    with st.expander("📄 **Document Analysis Consent**"):
        st.markdown("""
        ### What we analyze:
        - Legal documents you upload (contracts, court documents, etc.)
        - Extract key information and dates
        - Identify legal issues and risks
        
        ### Security measures:
        - Documents are scanned for malware before processing
        - Sensitive information is automatically redacted
        - Documents are encrypted at rest and in transit
        
        ### Your rights:
        - You control which documents are analyzed
        - You can delete documents at any time
        - Analysis results are only visible to you and authorized team members
        """)
        
        doc_consent = st.checkbox(
            "I consent to automated analysis of legal documents I upload",
            key="document_analysis_consent"
        )
    
    # Financial Data Consent (if applicable)
    if st.session_state.get('show_financial_consent', False):
        with st.expander("💰 **Financial Data Processing Consent**"):
            st.markdown("""
            ### For property settlements and financial matters:
            - Analyze financial documents (bank statements, tax returns)
            - Calculate asset pools and settlement scenarios
            - Generate financial disclosure summaries
            
            ### Additional protections:
            - Financial data is subject to highest security standards
            - Automated redaction of account numbers
            - Compliance with ATO privacy requirements
            """)
            
            financial_consent = st.checkbox(
                "I consent to processing of financial information for legal matters",
                key="financial_data_consent"
            )
    else:
        financial_consent = False
    
    # Multi-Agent Processing Consent
    with st.expander("🤝 **Multi-Agent AI Collaboration Consent**"):
        st.markdown("""
        ### Enhanced AI capabilities:
        - Multiple specialized AI agents work together on your matter
        - Document Analyzer, Legal Researcher, and Compliance Checker collaborate
        - Faster and more comprehensive analysis
        
        ### How it works:
        - Each agent only accesses data relevant to its function
        - All inter-agent communication is encrypted
        - You receive consolidated results from all agents
        
        ### Benefits:
        - 3x faster document processing
        - More comprehensive legal analysis
        - Better identification of legal issues
        """)
        
        multi_agent_consent = st.checkbox(
            "I consent to multi-agent AI processing for enhanced analysis",
            key="multi_agent_consent"
        )
    
    # Consent summary
    st.markdown("### 📋 Consent Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **Your selections:**
        - AI Processing: {'✅' if ai_consent else '❌'}
        - Document Analysis: {'✅' if doc_consent else '❌'}
        - Financial Processing: {'✅' if financial_consent else '❌'}
        - Multi-Agent Processing: {'✅' if multi_agent_consent else '❌'}
        """)
    
    with col2:
        st.warning("""
        **Important:**
        - You can withdraw consent at any time
        - Your data is protected by Australian law
        - We never share data without your permission
        """)
    
    # Consent actions
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("Cancel", key="cancel_consent"):
            st.session_state.show_consent_form = False
            st.rerun()
    
    with col3:
        if st.button("Submit Consent", type="primary", disabled=not (ai_consent and doc_consent)):
            # Process consents
            decision = ConsentDecision(
                granted=True,
                timestamp=datetime.utcnow(),
                ip_address=context['ip_address'],
                user_agent=context['user_agent'],
                consent_method='explicit_form'
            )
            
            # Record each consent
            results = []
            
            if ai_consent:
                request = ConsentRequest(
                    consent_type=ConsentType.AI_PROCESSING,
                    purpose="Process legal queries and case data using AI",
                    data_categories=['personal_information', 'case_data'],
                    processing_description="Use AI to analyze legal queries and provide insights",
                    retention_period_days=365
                )
                consent_result = consent_manager.request_consent(user_id, request, context)
                if consent_result['status'] == 'pending':
                    consent_manager.record_consent_decision(
                        consent_result['consent_id'],
                        user_id,
                        decision
                    )
                results.append(('AI Processing', True))
            
            if doc_consent:
                request = ConsentRequest(
                    consent_type=ConsentType.DOCUMENT_ANALYSIS,
                    purpose="Analyze uploaded legal documents",
                    data_categories=['legal_documents'],
                    processing_description="Extract information and analyze legal documents",
                    retention_period_days=730
                )
                consent_result = consent_manager.request_consent(user_id, request, context)
                if consent_result['status'] == 'pending':
                    consent_manager.record_consent_decision(
                        consent_result['consent_id'],
                        user_id,
                        decision
                    )
                results.append(('Document Analysis', True))
            
            if financial_consent:
                request = ConsentRequest(
                    consent_type=ConsentType.FINANCIAL_DATA_PROCESSING,
                    purpose="Process financial information for legal matters",
                    data_categories=['financial_records', 'asset_information'],
                    processing_description="Analyze financial data for property settlements",
                    retention_period_days=2555
                )
                consent_result = consent_manager.request_consent(user_id, request, context)
                if consent_result['status'] == 'pending':
                    consent_manager.record_consent_decision(
                        consent_result['consent_id'],
                        user_id,
                        decision
                    )
                results.append(('Financial Processing', True))
            
            if multi_agent_consent:
                consent_result = consent_manager.request_multi_agent_consent(
                    user_id,
                    'comprehensive_analysis',
                    ['document_analyzer', 'legal_researcher', 'compliance_checker'],
                    'provide comprehensive legal analysis',
                    context
                )
                if consent_result['status'] == 'pending':
                    consent_manager.record_consent_decision(
                        consent_result['consent_id'],
                        user_id,
                        decision
                    )
                results.append(('Multi-Agent Processing', True))
            
            # Show success
            st.success("✅ Consent recorded successfully!")
            st.balloons()
            
            # Clear form
            st.session_state.show_consent_form = False
            st.rerun()


def render_consent_management(user_id: str, db_session, firm_id: str):
    """Render consent management interface"""
    st.markdown("## 🔐 Privacy & Consent Management")
    
    consent_manager = get_consent_manager(db_session, firm_id)
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["My Consents", "Consent History", "Privacy Settings"])
    
    with tab1:
        st.markdown("### Current Consents")
        
        # Get all consent types and their status
        all_consent_types = list(ConsentType)
        consent_status = consent_manager.check_consent(user_id, all_consent_types)
        
        # Create consent cards
        cols = st.columns(2)
        for idx, (consent_type, is_granted) in enumerate(consent_status.items()):
            with cols[idx % 2]:
                if is_granted:
                    st.success(f"✅ **{consent_type.value.replace('_', ' ').title()}**")
                    
                    # Get consent details
                    history = consent_manager.get_consent_history(user_id)
                    active_consent = next(
                        (h for h in history 
                         if h['consent_type'] == consent_type.value and 
                         h['status'] == ConsentStatus.GRANTED.value),
                        None
                    )
                    
                    if active_consent:
                        st.caption(f"Granted: {active_consent['granted_at'][:10]}")
                        st.caption(f"Expires: {active_consent['expires_at'][:10]}")
                        
                        if st.button(f"Withdraw", key=f"withdraw_{consent_type.value}"):
                            if st.session_state.get(f'confirm_withdraw_{consent_type.value}', False):
                                # Withdraw consent
                                result = consent_manager.withdraw_consent(
                                    user_id,
                                    consent_type,
                                    "User requested withdrawal",
                                    {
                                        'ip_address': st.session_state.get('client_ip', 'unknown'),
                                        'user_agent': st.session_state.get('user_agent', 'Streamlit'),
                                        'source': 'consent_management_ui'
                                    }
                                )
                                st.warning(f"Consent withdrawn. {result['message']}")
                                st.rerun()
                            else:
                                st.session_state[f'confirm_withdraw_{consent_type.value}'] = True
                                st.warning("Click again to confirm withdrawal")
                else:
                    st.error(f"❌ **{consent_type.value.replace('_', ' ').title()}**")
                    st.caption("Not consented")
                    
                    if st.button(f"Grant Consent", key=f"grant_{consent_type.value}"):
                        st.session_state.show_consent_form = True
                        st.session_state.consent_type_focus = consent_type
                        st.rerun()
    
    with tab2:
        st.markdown("### Consent History")
        
        history = consent_manager.get_consent_history(user_id, include_audit_logs=True)
        
        if history:
            # Convert to DataFrame for display
            history_data = []
            for record in history:
                history_data.append({
                    'Type': record['consent_type'].replace('_', ' ').title(),
                    'Status': record['status'].replace('_', ' ').title(),
                    'Purpose': record['purpose'][:50] + '...' if len(record['purpose']) > 50 else record['purpose'],
                    'Granted': record['granted_at'][:10] if record['granted_at'] else '-',
                    'Withdrawn': record['withdrawn_at'][:10] if record['withdrawn_at'] else '-',
                    'Expires': record['expires_at'][:10] if record['expires_at'] else '-'
                })
            
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)
            
            # Show detailed audit logs
            with st.expander("View Detailed Audit Logs"):
                for record in history:
                    if record.get('audit_logs'):
                        st.markdown(f"**{record['consent_type']}**")
                        for log in record['audit_logs']:
                            st.caption(f"- {log['timestamp']}: {log['action']}")
                            if log.get('reason'):
                                st.caption(f"  Reason: {log['reason']}")
        else:
            st.info("No consent history found")
    
    with tab3:
        st.markdown("### Privacy Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Data Retention")
            st.info("""
            Your data is retained according to legal requirements:
            - AI interactions: 1 year
            - Legal documents: 7 years
            - Financial records: 7 years
            - Court documents: 15 years
            """)
            
            if st.button("Request Data Deletion"):
                st.warning("To request deletion of your data, please contact your firm administrator.")
        
        with col2:
            st.markdown("#### Data Access")
            st.info("""
            You have the right to:
            - Access your personal information
            - Correct inaccurate information
            - Request data portability
            - Lodge a privacy complaint
            """)
            
            if st.button("Download My Data"):
                st.info("Data export functionality coming soon")
        
        st.markdown("---")
        st.markdown("#### Privacy Policy")
        with st.expander("View Full Privacy Policy"):
            st.markdown("""
            **LegalLLM Professional Privacy Policy**
            
            This privacy policy explains how we collect, use, and protect your personal information
            in accordance with the Australian Privacy Act 1988 and the Australian Privacy Principles (APPs).
            
            **Information We Collect:**
            - Personal identification information
            - Legal case information
            - Financial information (with consent)
            - Usage data and analytics
            
            **How We Use Your Information:**
            - Provide legal AI services
            - Improve our services
            - Comply with legal obligations
            - Protect against fraud and security threats
            
            **Your Rights:**
            - Access your personal information (APP 12)
            - Correct inaccurate information (APP 13)
            - Withdraw consent at any time
            - Lodge complaints with the OAIC
            
            **Data Security:**
            - AES-256-GCM encryption for all sensitive data
            - Regular security audits
            - Access controls and monitoring
            - Incident response procedures
            
            **Contact:**
            For privacy inquiries, contact your firm's Privacy Officer.
            """)


def render_compliance_dashboard(db_session, firm_id: str):
    """Render compliance monitoring dashboard"""
    st.markdown("## 📊 Compliance Dashboard")
    
    monitor = ComplianceMonitor(db_session, firm_id)
    
    # Get consent dashboard data
    consent_data = monitor.get_consent_dashboard()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Users",
            consent_data['total_users'],
            help="Active users in the firm"
        )
    
    with col2:
        st.metric(
            "Overall Compliance",
            f"{consent_data['overall_compliance_rate']:.1f}%",
            help="Average consent rate across all types"
        )
    
    with col3:
        st.metric(
            "Expiring Soon",
            consent_data['expiring_soon'],
            help="Consents expiring in next 30 days"
        )
    
    with col4:
        compliance_score = consent_data['overall_compliance_rate']
        if compliance_score >= 95:
            st.success("✅ Compliant")
        elif compliance_score >= 80:
            st.warning("⚠️ Review Needed")
        else:
            st.error("❌ Action Required")
    
    # Consent breakdown
    st.markdown("### Consent Coverage by Type")
    
    consent_df = pd.DataFrame([
        {
            'Consent Type': consent_type.replace('_', ' ').title(),
            'Users Consented': stats['granted'],
            'Coverage %': stats['percentage']
        }
        for consent_type, stats in consent_data['consent_statistics'].items()
    ])
    
    if not consent_df.empty:
        st.dataframe(consent_df, use_container_width=True)
        
        # Visualize consent coverage
        st.bar_chart(
            consent_df.set_index('Consent Type')['Coverage %'],
            height=300
        )
    
    # Generate full compliance report
    if st.button("Generate Full Compliance Report"):
        with st.spinner("Generating comprehensive compliance report..."):
            report = monitor.generate_compliance_report()
            
            st.markdown("### Compliance Report Summary")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Compliance Score", f"{report.compliance_score:.1f}/100")
                st.metric("Checks Performed", report.checks_performed)
            
            with col2:
                st.metric("Issues Found", report.issues_found)
                st.metric("Critical Issues", report.critical_issues)
            
            # Show issues by category
            if report.issues_found > 0:
                st.markdown("### Issues by Category")
                
                issues_by_category = {}
                for check in report.detailed_checks:
                    if check.status != 'compliant':
                        category = check.category.value
                        if category not in issues_by_category:
                            issues_by_category[category] = []
                        issues_by_category[category].append(check)
                
                for category, issues in issues_by_category.items():
                    with st.expander(f"{category.replace('_', ' ').title()} ({len(issues)} issues)"):
                        for issue in issues:
                            severity_color = {
                                'critical': '🔴',
                                'high': '🟠',
                                'medium': '🟡',
                                'low': '🟢'
                            }
                            st.markdown(f"{severity_color.get(issue.severity, '⚪')} **{issue.check_name}**")
                            st.caption(issue.details)
                            if issue.recommendations:
                                st.info("Recommendations: " + ", ".join(issue.recommendations))
            
            # Show recommendations
            if report.recommendations:
                st.markdown("### Recommendations")
                for rec in report.recommendations:
                    st.write(rec)


# Integration helpers
def check_and_request_consent(user_id: str, consent_types: List[ConsentType], db_session) -> bool:
    """Check if user has required consents and request if missing"""
    consent_manager = get_consent_manager(db_session)
    consent_status = consent_manager.check_consent(user_id, consent_types)
    
    missing_consents = [ct for ct, granted in consent_status.items() if not granted]
    
    if missing_consents:
        st.session_state.show_consent_form = True
        st.session_state.required_consents = missing_consents
        return False
    
    return True