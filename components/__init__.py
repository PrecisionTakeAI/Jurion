#!/usr/bin/env python3
"""
LegalLLM Professional - Enterprise UI Components Package
Streamlit components for multi-tenant legal AI platform
"""

# Component imports for easy access
from .auth_components import (
    render_login_form,
    render_firm_registration,
    render_login_help,
    render_password_strength_indicator,
    validate_email,
    validate_australian_phone,
    validate_practitioner_number
)

from .dashboard_components import (
    render_role_dashboard,
    render_main_dashboard,
    render_executive_dashboard,
    render_lawyer_dashboard,
    render_paralegal_dashboard,
    render_client_dashboard,
    render_case_management,
    render_document_management,
    render_ai_assistant,
    render_administration,
    render_reports,
    render_billing
)

from .navigation_components import (
    render_sidebar_navigation,
    render_user_profile_sidebar,
    render_firm_info_sidebar,
    render_support_sidebar,
    render_help_modal,
    render_bug_report_modal,
    render_breadcrumb_navigation,
    render_quick_actions_menu,
    get_navigation_items
)

from .case_management_components import (
    render_case_management_dashboard,
    render_australian_family_law_case_wizard,
    render_executive_case_dashboard,
    render_lawyer_case_dashboard,
    render_paralegal_case_dashboard,
    render_client_case_dashboard
)

from .workflow_components import (
    render_workflow_dashboard,
    render_workflow_overview,
    render_workflow_progress,
    render_workflow_steps,
    render_compliance_tracking,
    render_workflow_automation_setup,
    WorkflowType,
    WorkflowStepStatus
)

from .document_case_integration import (
    render_case_document_dashboard,
    render_case_document_upload,
    render_case_document_list,
    render_document_ai_analysis,
    DocumentCategory,
    PrivilegeLevel
)

from .ai_case_assistant import (
    render_ai_case_assistant,
    AICaseContext,
    AIMode,
    AIConfidenceLevel
)

from .ai_document_generation import (
    render_ai_document_generation,
    render_contextual_document_generator,
    render_template_document_generator,
    DocumentTemplate,
    GenerationConfidence
)

from .advanced_workflow_automation import (
    render_advanced_workflow_automation,
    render_contextual_workflow_automation,
    render_general_workflow_automation,
    AutomationMode,
    AutomationTrigger,
    TaskPriority,
    TaskStatus,
    WorkflowIntelligence
)

from .enterprise_analytics import (
    render_enterprise_analytics,
    render_analytics_overview,
    render_performance_analytics,
    render_financial_analytics,
    render_ai_insights_analytics,
    AnalyticsScope,
    AnalyticsTimeframe,
    AnalyticsCategory,
    InsightType,
    InsightPriority
)

from .client_portal import (
    render_client_portal,
    render_client_overview,
    render_client_cases,
    render_client_documents,
    render_client_ai_assistant,
    render_client_messaging,
    render_client_billing,
    PortalFeature,
    MessageType,
    ClientAccessLevel,
    ClientAIMode
)

__version__ = "1.0.0"
__author__ = "LegalLLM Professional Team"
__description__ = "Enterprise UI components for Australian legal AI platform"

# Component categories for organization
AUTH_COMPONENTS = [
    "render_login_form",
    "render_firm_registration", 
    "render_login_help",
    "render_password_strength_indicator"
]

DASHBOARD_COMPONENTS = [
    "render_role_dashboard",
    "render_main_dashboard",
    "render_executive_dashboard",
    "render_lawyer_dashboard",
    "render_paralegal_dashboard",
    "render_client_dashboard"
]

NAVIGATION_COMPONENTS = [
    "render_sidebar_navigation",
    "render_user_profile_sidebar",
    "render_firm_info_sidebar",
    "render_support_sidebar"
]

UTILITY_FUNCTIONS = [
    "validate_email",
    "validate_australian_phone",
    "validate_practitioner_number",
    "get_navigation_items"
]

# Export all components
__all__ = AUTH_COMPONENTS + DASHBOARD_COMPONENTS + NAVIGATION_COMPONENTS + UTILITY_FUNCTIONS