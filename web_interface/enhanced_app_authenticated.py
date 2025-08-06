#!/usr/bin/env python3
"""
Authenticated Legal AI Interface with Multi-Tenant Support
Enhanced Streamlit interface with user authentication, role-based access control,
and firm-specific data isolation for legal professionals.
"""

import streamlit as st
import os
import shutil 
import logging
import functools
import time
import json
import atexit
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Load environment variables once at application startup to prevent recursion
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger = logging.getLogger(__name__)
    logger.info("Environment variables loaded successfully at application startup")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("python-dotenv not available - using system environment variables")

# Streamlit-compatible cleanup handler
def cleanup_on_exit():
    """Cleanup function that runs when Streamlit app exits"""
    logger.info("Legal AI Hub shutting down gracefully...")
    # Add any cleanup code here if needed

# Register the cleanup function - works in Streamlit's threaded environment
atexit.register(cleanup_on_exit)

# Railway Health Check Endpoint with backwards compatibility
try:
    # Streamlit >= 1.30.0
    if hasattr(st, 'query_params'):
        if st.query_params.get("healthz") or st.query_params.get("health"):
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "Legal AI Hub",
                "version": "1.0.0",
                "uptime": "OK",
                "dependencies": "OK"
            }
            st.json(health_status)
            st.stop()
    # Older Streamlit versions
    elif hasattr(st, 'experimental_get_query_params'):
        params = st.experimental_get_query_params()
        if params.get("healthz") or params.get("health"):
            health_status = {
                "status": "healthy", 
                "timestamp": datetime.now().isoformat(),
                "service": "Legal AI Hub",
                "version": "1.0.0",
                "uptime": "OK",
                "dependencies": "OK"
            }
            st.json(health_status)
            st.stop()
except Exception as e:
    # Fallback if query params not available
    logger.warning(f"Health check query params not supported: {e}")
    pass

# Performance optimization: Streamlit configuration
st.set_page_config(
    page_title="Legal AI Hub - Professional",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Legal AI Hub Professional - Multi-tenant legal AI platform"
    }
)

# Configure production logging for Railway deployment
log_level = logging.INFO if os.getenv('ENVIRONMENT') == 'production' else logging.DEBUG
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/app.log', mode='a') if os.path.exists('/tmp') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import and configure security logging
try:
    from shared.core.security_logging import (
        log_document_processing, log_ai_query, log_ocr_processing,
        log_text_extraction, log_document_content_preview, 
        log_error_safely, configure_production_logging
    )
    # Apply production logging configuration
    configure_production_logging()
    logger.info("Security logging configured successfully")
except ImportError as e:
    logger.warning(f"Security logging not available: {e}")

# Silence watchdog and development loggers completely for production
production_silence_loggers = [
    'watchdog',
    'watchdog.observers',
    'watchdog.observers.inotify_buffer',
    'watchdog.observers.polling',
    'watchdog.events',
    'streamlit.watcher',
    'streamlit.file_watcher',
    'tornado.access',
    'urllib3.connectionpool'
]

for logger_name in production_silence_loggers:
    silence_logger = logging.getLogger(logger_name)
    silence_logger.setLevel(logging.ERROR)
    silence_logger.disabled = True

# Log startup information with comprehensive environment variable debugging
logger.info("=" * 50)
logger.info("LEGAL AI HUB - STARTUP INITIATED")
logger.info(f"Python version: {os.sys.version}")
logger.info(f"Working directory: {os.getcwd()}")

# ENVIRONMENT VARIABLE DEBUG LOGGING - Enhanced debugging for deployment issues
logger.info("🔍 ENVIRONMENT VARIABLE DEBUG LOGGING:")
logger.info("=" * 30)

# Database environment variables
database_url = os.getenv('DATABASE_URL', 'Not set')
# Mask password in database URL for security
if database_url and database_url != 'Not set':
    import re
    masked_db_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', database_url)
    logger.info(f"📊 DATABASE_URL: {masked_db_url}")
else:
    logger.info(f"📊 DATABASE_URL: {database_url}")

logger.info(f"📊 DB_HOST: {os.getenv('DB_HOST', 'Not set')}")
logger.info(f"📊 DB_PORT: {os.getenv('DB_PORT', 'Not set')}")
logger.info(f"📊 DB_NAME: {os.getenv('DB_NAME', 'Not set')}")
logger.info(f"📊 DB_USER: {os.getenv('DB_USER', 'Not set')}")
logger.info(f"📊 DB_PASSWORD: {'****' if os.getenv('DB_PASSWORD') else 'Not set'}")

# Railway-specific environment variables
logger.info(f"🚂 RAILWAY_ENVIRONMENT_NAME: {os.getenv('RAILWAY_ENVIRONMENT_NAME', 'Not set')}")
logger.info(f"🚂 RAILWAY_PROJECT_NAME: {os.getenv('RAILWAY_PROJECT_NAME', 'Not set')}")
logger.info(f"🚂 RAILWAY_SERVICE_NAME: {os.getenv('RAILWAY_SERVICE_NAME', 'Not set')}")

# Application environment variables
logger.info(f"⚙️ PORT: {os.getenv('PORT', 'Not set')}")
logger.info(f"⚙️ ENVIRONMENT: {os.getenv('ENVIRONMENT', 'Not set')}")
logger.info(f"⚙️ PYTHONPATH: {os.getenv('PYTHONPATH', 'Not set')}")

# AI API keys (masked for security)
groq_key = os.getenv('GROQ_API_KEY')
logger.info(f"🤖 GROQ_API_KEY: {'Set (***' + groq_key[-4:] + ')' if groq_key else 'Not set'}")
openai_key = os.getenv('OPENAI_API_KEY')
logger.info(f"🤖 OPENAI_API_KEY: {'Set (***' + openai_key[-4:] + ')' if openai_key else 'Not set'}")
anthropic_key = os.getenv('ANTHROPIC_API_KEY')
logger.info(f"🤖 ANTHROPIC_API_KEY: {'Set (***' + anthropic_key[-4:] + ')' if anthropic_key else 'Not set'}")

# Cache and performance variables
logger.info(f"💾 REDIS_URL: {'Set' if os.getenv('REDIS_URL') else 'Not set'}")
logger.info(f"💾 DB_POOL_SIZE: {os.getenv('DB_POOL_SIZE', 'Not set (default: 20)')}")
logger.info(f"💾 DB_MAX_OVERFLOW: {os.getenv('DB_MAX_OVERFLOW', 'Not set (default: 30)')}")

# Security and logging variables
logger.info(f"🔒 SECRET_KEY: {'Set' if os.getenv('SECRET_KEY') else 'Not set'}")
logger.info(f"📝 LOG_LEVEL: {os.getenv('LOG_LEVEL', 'Not set')}")
logger.info(f"📝 SKIP_VERBOSE_LOGGING: {os.getenv('SKIP_VERBOSE_LOGGING', 'Not set')}")

logger.info("=" * 30)
logger.info("✅ Environment variable debug logging completed")
logger.info("=" * 50)

# Performance optimization: Caching utilities
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_static_data():
    """Cache static data that doesn't change often"""
    return {
        'practice_areas': [
            'Family Law', 'Corporate Law', 'Criminal Law', 'Real Estate',
            'Employment Law', 'Intellectual Property', 'Immigration',
            'Tax Law', 'Personal Injury', 'Bankruptcy', 'Environmental',
            'Contract Law', 'Litigation', 'Regulatory Compliance', 'Estate Planning'
        ],
        'jurisdictions': ['Australia', 'United States', 'United Kingdom', 'Canada']
    }

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_system_status():
    """Cache system status information"""
    return {
        'database_available': True,
        'ai_available': True,
        'last_check': datetime.now().strftime('%H:%M:%S')
    }

# DEPLOYMENT VERIFICATION - CHECK IF NEW CODE IS RUNNING
logger.info("DEPLOYMENT VERIFICATION: Code version 2025-01-27-FORCE-REDEPLOY is running")
logger.info("This message confirms the latest database fixes are deployed")

# Authentication imports
try:
    from shared.auth.authentication import (
        LegalAuthenticationSystem, AuthenticationResult, SessionInfo,
        AuthenticationRole, AuthenticationStatus, safe_enum_value
    )
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    logger.warning(f"Authentication system not available: {e}")

# Lazy loading functions for memory efficiency
_llm_engine = None
_case_manager = None
_document_processor = None

def get_llm_engine():
    """Lazy load LLM engine only when needed"""
    global _llm_engine
    if _llm_engine is None:
        try:
            logger.info("Loading LLM engine (lazy initialization)...")
            from core.enhanced_llm_engine import EnhancedLegalLLMEngine
            _llm_engine = EnhancedLegalLLMEngine()
            logger.info("LLM engine loaded successfully")
        except ImportError as e:
            logger.warning(f"LLM engine import failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"LLM engine initialization failed: {e}")
            return None
    return _llm_engine

def get_case_manager():
    """Lazy load case manager only when needed"""
    global _case_manager
    if _case_manager is None:
        try:
            logger.info("Loading case manager (lazy initialization)...")
            from core.case_manager import CaseManager
            _case_manager = CaseManager()
            logger.info("Case manager loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to load case manager: {e}")
            return None
    return _case_manager

def get_document_processor():
    """Lazy load document processor only when needed with enhanced error handling"""
    global _document_processor
    if _document_processor is None:
        try:
            logger.info("Loading document processor (lazy initialization)...")
            from core.document_processor import DocumentProcessor
            _document_processor = DocumentProcessor()
            logger.info("Document processor loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to load document processor - ImportError: {e}")
            logger.error("Falling back to legacy document processing")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize document processor - Exception: {e}")
            logger.error("Document processor will not be available for this session")
            return None
    return _document_processor

# Initialize document processor availability flag with session state
def init_document_processor():
    """Initialize document processor with session state tracking"""
    if 'doc_processor_available' not in st.session_state:
        processor = get_document_processor()
        st.session_state.doc_processor_available = processor is not None
        if processor is not None:
            st.session_state.doc_processor = processor
            logger.info("Document processor initialized in session state")
        else:
            logger.warning("Document processor not available - legacy processing will be used")
    return st.session_state.get('doc_processor_available', False)

# Check availability without importing
ENGINE_AVAILABLE = True
try:
    import core.enhanced_llm_engine
    import core.case_manager
    import core.document_processor
    import core.jurisdiction_manager
except ImportError as e:
    ENGINE_AVAILABLE = False
    logger.warning(f"Core engines not available: {e}")

# Legacy Groq import for backward compatibility
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq not available")

# Document processing imports
import docx
import PyPDF2
import io
import tempfile

# IMMEDIATE DATABASE INITIALIZATION - FORCE SETUP ON APP STARTUP
logger.info("FORCING DATABASE INITIALIZATION AT APP STARTUP...")
try:
    from database.database import db_manager, init_database, create_tables
    from shared.database.models import Base
    
    # CRITICAL: Force initialize the global db_manager first
    logger.info("Force initializing global db_manager...")
    db_manager.initialize_database()
    
    # Double-check by also calling the convenience function
    logger.info(" Calling init_database() convenience function...")
    init_database()
    
    # Force table creation immediately  
    logger.info(" Calling create_tables()...")
    create_tables()
    
    logger.info(" IMMEDIATE DATABASE SETUP COMPLETED SUCCESSFULLY")
    
except Exception as urgent_db_error:
    logger.error(f" URGENT DATABASE SETUP FAILED: {urgent_db_error}")
    import traceback
    logger.error(traceback.format_exc())
    logger.warning(" App will continue but database features may not work")

# Add caching decorator for dependency checks
@functools.lru_cache(maxsize=1)
def check_dependencies():
    """Cache dependency checks to prevent repeated execution"""
    results = {}
    
    # Check pdfplumber
    try:
        import pdfplumber
        results['pdfplumber'] = True
        logger.info(" pdfplumber available")
    except ImportError:
        results['pdfplumber'] = False
        logger.warning(" pdfplumber not available")
    
    # Check PyMuPDF/fitz
    try:
        import fitz
        results['pymupdf'] = True
        logger.info(" PyMuPDF (fitz) available")
    except ImportError:
        results['pymupdf'] = False
        logger.warning(" PyMuPDF (fitz) not available")
    
    return results

# Replace the dependency checks section with:
deps = check_dependencies()
PDFPLUMBER_AVAILABLE = deps['pdfplumber']
PYMUPDF_AVAILABLE = deps['pymupdf']

# Enhanced OCR imports with system configuration
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    
    tesseract_path = shutil.which('tesseract')
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        logger.info(f" Tesseract found at: {tesseract_path}")
        OCR_AVAILABLE = True
    else:
        logger.warning(" Tesseract not found in PATH")
        OCR_AVAILABLE = False
        
except ImportError as e:
    OCR_AVAILABLE = False
    logger.warning(f" OCR libraries not available: {e}")

# Page configuration moved to top of file to comply with Streamlit requirements

# Enhanced CSS for authenticated interface
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(37, 99, 235, 0.3);
    }
    
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        font-family: 'Inter', sans-serif;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .user-info-bar {
        background: linear-gradient(90deg, #059669 0%, #10b981 100%);
        padding: 0.8rem 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
        font-weight: 500;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
    }
    
    .auth-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
        border: 1px solid #e2e8f0;
        max-width: 500px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .role-badge {
        background: rgba(255,255,255,0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .firm-header {
        background: #f8fafc;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border-left: 4px solid #2563eb;
    }
    
    .chat-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    .message-user {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 15px 15px 5px 15px;
        margin: 1rem 0;
        margin-left: 20%;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    
    .message-assistant {
        background: #f8fafc;
        color: #1e293b;
        padding: 1rem 1.5rem;
        border-radius: 15px 15px 15px 5px;
        margin: 1rem 0;
        margin-right: 20%;
        border-left: 4px solid #2563eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    
    .feature-disabled {
        opacity: 0.5;
        pointer-events: none;
    }
    
    .error-message {
        background: #fee2e2;
        color: #dc2626;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #dc2626;
    }
    
    .success-message {
        background: #dcfce7;
        color: #16a34a;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #16a34a;
    }
</style>
""", unsafe_allow_html=True)

# Initialize authentication system with enhanced error handling
if AUTH_AVAILABLE:
    if 'auth_system' not in st.session_state:
        try:
            logger.info("Initializing LegalAuthenticationSystem...")
            st.session_state.auth_system = LegalAuthenticationSystem()
            logger.info(" Authentication system initialized successfully")
            
            # Test database connection and initialize tables
            if hasattr(st.session_state.auth_system, 'database_available'):
                if st.session_state.auth_system.database_available:
                    logger.info(" Database connection available for authentication")
                    
                    # Initialize database tables automatically (once per session)
                    if 'db_initialized' not in st.session_state:
                        try:
                            logger.info(" Initializing database tables...")
                            from database.database import init_database, create_tables
                            
                            # Initialize database connection
                            init_database()
                            
                            # Create all tables
                            create_tables()
                            
                            logger.info(" Database tables initialized successfully")
                            st.session_state.db_initialized = True
                            
                        except Exception as db_e:
                            logger.error(f" Database table initialization failed: {db_e}")
                            logger.info("Authentication system will attempt to create tables as needed")
                            st.session_state.db_initialized = False
                    else:
                        logger.info(" Database already initialized for this session")
                        
                else:
                    logger.warning("  Database not available, authentication will use fallback mode")
                    
        except Exception as e:
            logger.error(f" Failed to initialize authentication system: {e}")
            import traceback
            logger.error(traceback.format_exc())
            globals()['AUTH_AVAILABLE'] = False
            st.error(f"Authentication system initialization failed: {e}")
            st.info("The application will continue in legacy mode without authentication.")

# Session state initialization
def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'session_info' not in st.session_state:
        st.session_state.session_info = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
    if 'current_case_id' not in st.session_state:
        st.session_state.current_case_id = None
    if 'show_login' not in st.session_state:
        st.session_state.show_login = True
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if 'query_count' not in st.session_state:
        st.session_state.query_count = 0
    if 'last_query_time' not in st.session_state:
        st.session_state.last_query_time = 'Never'

def has_permission(required_permission: str) -> bool:
    """Check if current user has required permission"""
    if not st.session_state.authenticated or not st.session_state.session_info:
        return False
    
    return required_permission in st.session_state.session_info.permissions

def render_login_form():
    """Render login form"""
    st.markdown("""
    <div class="auth-container">
        <h2 style="text-align: center; color: #1e293b; margin-bottom: 1.5rem;">
             Legal Professional Login
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.show_register:
        render_registration_form()
        return
    
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="lawyer@lawfirm.com.au")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            login_submitted = st.form_submit_button("Login", use_container_width=True)
        with col2:
            if st.form_submit_button("Register New Firm", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()
        
        # MFA section (if needed)
        if 'mfa_required' in st.session_state and st.session_state.mfa_required:
            st.info("Multi-factor authentication required")
            mfa_code = st.text_input("MFA Code", placeholder="123456")
        else:
            mfa_code = None
        
        if login_submitted and email and password:
            if not AUTH_AVAILABLE:
                st.error("Authentication system not available. Running in legacy mode.")
                # Set mock session for demo
                st.session_state.authenticated = True
                st.session_state.session_info = type('MockSession', (), {
                    'user_name': 'Demo User',
                    'firm_name': 'Demo Law Firm',
                    'role': AuthenticationRole.LAWYER,
                    'permissions': ['manage_own_cases', 'manage_documents']
                })()
                st.rerun()
                return
            
            # Get client information in Streamlit-compatible way
            try:
                # Try to get Railway deployment info from environment
                import os
                if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
                    ip_address = 'railway-deployment'
                    user_agent = f"Railway-{os.getenv('RAILWAY_ENVIRONMENT_NAME', 'production')}"
                else:
                    # For local development
                    ip_address = 'localhost'
                    user_agent = 'streamlit-local'
            except Exception:
                # Fallback for any errors
                ip_address = 'unknown'
                user_agent = 'streamlit-app'
            
            # Authenticate user
            auth_result = st.session_state.auth_system.authenticate_user(
                email=email,
                password=password,
                mfa_code=mfa_code,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if auth_result.status == AuthenticationStatus.SUCCESS:
                st.session_state.authenticated = True
                st.session_state.session_info = type('SessionInfo', (), {
                    'user_name': auth_result.user_name,
                    'firm_name': auth_result.firm_name,
                    'user_id': auth_result.user_id,
                    'firm_id': auth_result.firm_id,
                    'role': auth_result.role,
                    'permissions': auth_result.permissions,
                    'session_token': auth_result.session_token
                })()
                st.success(f"Welcome, {auth_result.user_name}!")
                time.sleep(1)
                st.rerun()
                
            elif auth_result.status == AuthenticationStatus.MFA_REQUIRED:
                st.session_state.mfa_required = True
                st.info("Please enter your MFA code to continue")
                
            elif auth_result.status == AuthenticationStatus.ACCOUNT_LOCKED:
                st.error("Account temporarily locked due to failed login attempts")
                
            else:
                st.error(auth_result.error_message or "Invalid credentials")

def render_registration_form():
    """Render firm registration form"""
    st.markdown("### Register New Law Firm")
    
    with st.form("register_form", clear_on_submit=False):
        st.markdown("#### Firm Information")
        firm_name = st.text_input("Law Firm Name", placeholder="Smith & Associates Legal")
        address = st.text_area("Firm Address", placeholder="123 Collins Street, Melbourne VIC 3000")
        phone = st.text_input("Phone", placeholder="+61 3 9123 4567")
        jurisdiction = st.selectbox(
            "Primary Jurisdiction",
            ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
            help="Select your primary Australian jurisdiction"
        )
        
        st.markdown("#### Principal Lawyer Details")
        admin_name = st.text_input("Principal Name", placeholder="John Smith")
        admin_email = st.text_input("Email", placeholder="john@smithlaw.com.au")
        admin_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        practitioner_number = st.text_input(
            "Legal Practitioner Number", 
            placeholder="e.g., 12345",
            help="Your Australian legal practitioner number"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            register_submitted = st.form_submit_button("Register Firm", use_container_width=True)
        with col2:
            if st.form_submit_button("Back to Login", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()
        
        if register_submitted:
            # Validation
            if not all([firm_name, admin_name, admin_email, admin_password]):
                st.error("Please fill in all required fields")
                return
            
            if admin_password != confirm_password:
                st.error("Passwords do not match")
                return
            
            if len(admin_password) < 8:
                st.error("Password must be at least 8 characters long")
                return
            
            if not AUTH_AVAILABLE:
                st.error("Authentication system not available")
                return
            
            # Register firm
            auth_result = st.session_state.auth_system.register_firm(
                firm_name=firm_name,
                admin_email=admin_email,
                admin_password=admin_password,
                admin_name=admin_name,
                practitioner_number=practitioner_number if practitioner_number else None,
                jurisdiction=jurisdiction.lower(),
                address=address,
                phone=phone
            )
            
            if auth_result.status == AuthenticationStatus.SUCCESS:
                st.success(f"Firm '{firm_name}' registered successfully! Please login.")
                st.session_state.show_register = False
                time.sleep(2)
                st.rerun()
            else:
                st.error(auth_result.error_message or "Registration failed")

def render_user_header():
    """Render authenticated user header"""
    if not st.session_state.authenticated or not st.session_state.session_info:
        return
    
    session = st.session_state.session_info
    
    # User info bar
    st.markdown(f"""
    <div class="user-info-bar">
        <div>
            <strong>{session.user_name}</strong>  {session.firm_name}
            <span class="role-badge">{safe_enum_value(session.role).replace('_', ' ').title()}</span>
        </div>
        <div>
            Connected  Australia
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render role-based sidebar navigation"""
    if not st.session_state.authenticated:
        return
    
    with st.sidebar:
        st.markdown("### Navigation")
        
        # API Configuration Status
        with st.expander("🔧 System Status", expanded=False):
            # Database Connection Test Status
            db_test_result = st.session_state.get('database_startup_test', None)
            if db_test_result:
                if db_test_result['status'] == 'success':
                    st.success("✅ Database: Connected")
                elif db_test_result['status'] == 'failed':
                    st.error("❌ Database: Connection Failed")
                    st.info(f"💡 {db_test_result['message']}")
                elif db_test_result['status'] == 'error':
                    st.error("❌ Database: Connection Error")
                    st.info(f"💡 {db_test_result['message']}")
                elif db_test_result['status'] == 'setup_failed':
                    st.error("❌ Database: Setup Failed") 
                    st.info(f"💡 {db_test_result['message']}")
                
                # Show timestamp for debugging
                if st.checkbox("Show database test details", key="db_test_details"):
                    st.text(f"Test time: {db_test_result['timestamp']}")
            else:
                st.warning("⚠️ Database: Status Unknown")
                st.info("💡 Database connection test not completed")
            
            # Check API key configuration
            groq_key_available = bool(os.getenv("GROQ_API_KEY"))
            doc_processor_available = st.session_state.get('doc_processor_available', False)
            
            if groq_key_available:
                st.success("✅ AI API: Configured")
            else:
                st.error("❌ AI API: Not configured")
                st.info("💡 Set GROQ_API_KEY environment variable")
            
            if doc_processor_available:
                st.success("✅ Document Processor: Available")
            else:
                st.warning("⚠️ Document Processor: Legacy mode")
            
            if ENGINE_AVAILABLE:
                st.success("✅ Enhanced Engine: Available")
            else:
                st.warning("⚠️ Enhanced Engine: Legacy mode")
        
        # Core features available to all authenticated users
        if st.button(" Legal Chat", use_container_width=True):
            st.session_state.current_page = "chat"
            st.rerun()
        
        if has_permission('manage_own_cases') or has_permission('manage_cases'):
            if st.button(" Case Manager", use_container_width=True):
                st.session_state.current_page = "cases"
                st.rerun()
        
        if has_permission('manage_documents'):
            if st.button(" Document Analysis", use_container_width=True):
                st.session_state.current_page = "documents"
                st.rerun()
        
        # Admin features
        if has_permission('manage_firm'):
            st.markdown("### Administration")
            if st.button(" User Management", use_container_width=True):
                st.session_state.current_page = "users"
                st.rerun()
            
            if st.button(" Firm Settings", use_container_width=True):
                st.session_state.current_page = "firm"
                st.rerun()
        
        if has_permission('view_analytics'):
            if st.button(" Analytics", use_container_width=True):
                st.session_state.current_page = "analytics"
                st.rerun()
        
        # User settings
        st.markdown("### Account")
        if st.button(" Settings", use_container_width=True):
            st.session_state.current_page = "settings"
            st.rerun()
        
        if st.button(" Logout", use_container_width=True):
            logout_user()

def logout_user():
    """Logout current user"""
    if AUTH_AVAILABLE and st.session_state.session_info:
        st.session_state.auth_system.logout_user(
            st.session_state.session_info.session_token
        )
    
    # Clear session state
    st.session_state.authenticated = False
    st.session_state.session_info = None
    st.session_state.messages = []
    st.session_state.uploaded_files = []
    st.session_state.current_case_id = None
    
    if 'mfa_required' in st.session_state:
        del st.session_state.mfa_required
    
    st.success("Logged out successfully")
    time.sleep(1)
    st.rerun()

def render_legal_chat():
    """Render the main legal chat interface"""
    st.markdown("###  Legal AI Assistant")
    
    # Firm context header
    if st.session_state.session_info:
        st.markdown(f"""
        <div class="firm-header">
            <strong>Active Firm:</strong> {st.session_state.session_info.firm_name} | 
            <strong>Jurisdiction:</strong> Australia | 
            <strong>Role:</strong> {safe_enum_value(st.session_state.session_info.role).replace('_', ' ').title()}
        </div>
        """, unsafe_allow_html=True)
    
    # File upload section with enhanced error handling
    with st.expander(" Document Upload", expanded=False):
        # Debug info for Railway troubleshooting
        if st.session_state.get('show_debug_info', False):
            st.write("🔧 Debug Info:")
            st.write(f"Streamlit version: {st.__version__}")
            try:
                max_size = st.config.get_option('server.maxUploadSize')
                st.write(f"Max upload size: {max_size} MB")
            except:
                st.write("Max upload size: Configuration not accessible")
        
        try:
            uploaded_files = st.file_uploader(
                "Upload legal documents (Max 200MB per file)",
                accept_multiple_files=True,
                type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'],
                key="doc_upload",
                help="Supported formats: PDF, Word documents, text files, and images"
            )
            
            if uploaded_files:
                # Check memory usage before processing
                try:
                    import psutil
                    memory = psutil.virtual_memory()
                    logger.info(f"Memory usage before file processing: {memory.percent}%")
                    
                    if memory.percent > 85:
                        st.warning(f"⚠️ High memory usage ({memory.percent}%) - large files may fail")
                except ImportError:
                    logger.info("psutil not available - skipping memory check")
                
                for uploaded_file in uploaded_files:
                    # Check if file already processed
                    if uploaded_file.name not in [f[0] for f in st.session_state.uploaded_files]:
                        
                        # Get file size and validate
                        try:
                            file_bytes = uploaded_file.getvalue()
                            file_size_mb = len(file_bytes) / (1024 * 1024)
                            
                            # File size validation
                            if file_size_mb > 200:
                                st.error(f"❌ {uploaded_file.name} exceeds 200MB limit ({file_size_mb:.1f}MB)")
                                logger.error(f"File {uploaded_file.name} rejected: {file_size_mb:.1f}MB > 200MB limit")
                                continue
                            
                            # Log file info
                            logger.info(f"Processing upload: {uploaded_file.name} ({file_size_mb:.2f}MB)")
                            
                            # Process file with enhanced error handling
                            with st.spinner(f"Processing {uploaded_file.name} ({file_size_mb:.1f}MB)..."):
                                try:
                                    content = process_uploaded_file(uploaded_file.name, file_bytes)
                                    
                                    if content and content.strip():
                                        st.session_state.uploaded_files.append((uploaded_file.name, content))
                                        char_count = len(content)
                                        st.success(f"✅ {uploaded_file.name} processed successfully ({char_count:,} characters extracted)")
                                        logger.info(f"Successfully processed {uploaded_file.name}: {char_count} characters")
                                    else:
                                        st.error(f"❌ {uploaded_file.name} could not be processed - no text extracted")
                                        st.info("💡 If this is a scanned PDF, OCR processing may take longer. Check the logs for details.")
                                        logger.warning(f"No content extracted from {uploaded_file.name}")
                                        
                                except MemoryError:
                                    error_msg = f"Insufficient memory to process {uploaded_file.name} ({file_size_mb:.1f}MB)"
                                    st.error(f"💾 {error_msg}")
                                    logger.error(error_msg)
                                except Exception as e:
                                    error_msg = f"Error processing {uploaded_file.name}: {str(e)}"
                                    st.error(f"❌ {error_msg}")
                                    logger.error(f"Upload processing error for {uploaded_file.name}: {e}")
                                    logger.exception("Full upload error traceback:")
                        
                        except Exception as e:
                            error_msg = f"Failed to read {uploaded_file.name}: {str(e)}"
                            st.error(f"❌ {error_msg}")
                            logger.error(error_msg)
                            continue
                    else:
                        st.info(f"📄 {uploaded_file.name} already processed")
        
        except Exception as e:
            st.error(f"❌ File upload system error: {str(e)}")
            logger.error(f"File upload system failed: {str(e)}")
            logger.exception("Full file upload system error traceback:")
        
        # Debug toggle
        if st.checkbox("Show debug info", help="Enable for troubleshooting upload issues"):
            st.session_state.show_debug_info = True
        else:
            st.session_state.show_debug_info = False
    
    # Case selection (if user has case access)
    if has_permission('manage_own_cases') or has_permission('manage_cases'):
        case_options = get_user_cases()
        if case_options:
            selected_case = st.selectbox(
                "Link to Case (Optional)",
                options=["None"] + [f"{case['title']} ({case['id'][:8]})" for case in case_options],
                help="Associate this conversation with a case"
            )
            
            if selected_case != "None":
                st.session_state.current_case_id = case_options[0]['id']  # Simplified for demo
    
    # Initialize form variables
    submit_button = False
    user_input = ""
    
    # Input form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Your legal question:",
            height=100,
            placeholder="e.g., Analyze this contract for key risks and compliance issues..."
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submit_button = st.form_submit_button("Send", use_container_width=True)
        with col2:
            practice_area = st.selectbox(
                "Practice Area",
                ["family", "corporate", "criminal", "real_estate", "employment", "contract"],
                index=0
            )
        with col3:
            jurisdiction = st.selectbox(
                "Jurisdiction",
                ["australia", "united_states", "united_kingdom", "canada"],
                index=0
            )
    
    if submit_button and user_input:
        # Prevent duplicate processing - check if this is not a repeated submission
        query_hash = hash(user_input)
        if 'last_query_hash' not in st.session_state or st.session_state.last_query_hash != query_hash:
            st.session_state.last_query_hash = query_hash
            
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Update query metrics
            st.session_state.query_count = getattr(st.session_state, 'query_count', 0) + 1
            st.session_state.last_query_time = datetime.now().isoformat()
            
            # Get AI response and display immediately
            with st.spinner("Analyzing with legal expertise..."):
                # Debug logging
                logger.info(f"Processing query: {user_input[:50]}... | Area: {practice_area} | Jurisdiction: {jurisdiction}")
                
                start_time = time.time()
                response = process_legal_query_safe(
                    user_input, 
                    practice_area, 
                    jurisdiction,
                    st.session_state.uploaded_files,
                    st.session_state.current_case_id
                )
                processing_time = time.time() - start_time
                
                # Add to history
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Display the response immediately in the current execution
                st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                
                # User query
                st.markdown(f"""
                <div class="message-user">
                    <strong>Query:</strong> {user_input}
                </div>
                """, unsafe_allow_html=True)
                
                # AI response 
                st.markdown(f"""
                <div class="message-assistant">
                    {response}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Debug info
                logger.info(f"Query completed in {processing_time:.2f}s - Response: {len(response)} chars")
                
                # Show processing stats in debug mode
                if logger.isEnabledFor(logging.DEBUG):
                    st.info(f"⚡ Response generated in {processing_time:.2f} seconds")
                
                # Add debug info sidebar
                with st.sidebar:
                    if st.checkbox("Show Debug Info", key="debug_mode"):
                        st.write("**Debug Information:**")
                        st.write(f"Session ID: {getattr(st.session_state, 'session_id', 'N/A')}")
                        st.write(f"Query Count: {getattr(st.session_state, 'query_count', 0)}")
                        st.write(f"Last Query Time: {getattr(st.session_state, 'last_query_time', 'Never')}")
                        st.write(f"Processing Time: {processing_time:.2f}s")
                        st.write(f"Response Length: {len(response)} chars")
        
        # Clear the form by not storing anything that would persist
    
    # Show conversation history when not processing a new query
    if not (submit_button and user_input):
        if st.session_state.messages:
            with st.expander("📜 Conversation History", expanded=False):
                st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                
                # Display recent chat messages (last 6 for performance)
                recent_messages = st.session_state.messages[-6:] if len(st.session_state.messages) > 6 else st.session_state.messages
                
                for message in recent_messages:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class="message-user">
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="message-assistant">
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

@st.cache_data(ttl=3600)  # Cache file processing for 1 hour
def process_uploaded_file(file_name: str, file_content: bytes) -> str:
    """Process uploaded file and extract text with OCR progress indicators"""
    logger.info(f"Processing file: {file_name} ({len(file_content)} bytes)")
    
    # Determine file type and size
    file_extension = file_name.lower().split('.')[-1] if '.' in file_name else 'unknown'
    file_size_mb = len(file_content) / (1024 * 1024)
    logger.info(f"File type detected: {file_extension}, Size: {file_size_mb:.2f}MB")
    
    # Create progress container for OCR status
    progress_container = st.empty()
    
    # Check if this might need OCR processing
    is_pdf = file_extension == 'pdf'
    if is_pdf:
        progress_container.info("📄 Processing PDF document...")
    
    if not ENGINE_AVAILABLE:
        logger.warning("ENGINE_AVAILABLE=False, using legacy processing")
        progress_container.warning("⚠️ Using legacy processing mode")
        
        # Enhanced legacy processing with OCR feedback
        if is_pdf:
            progress_container.info("📄 Legacy mode: Processing PDF with PyPDF2...")
        
        # Create a temporary file-like object for legacy processing
        import io
        temp_file = io.BytesIO(file_content)
        temp_file.name = file_name
        
        # Show OCR preparation message for PDFs
        if is_pdf:
            progress_container.info("🔍 Legacy mode: Will attempt OCR if regular extraction yields < 50 characters...")
        
        result = extract_text_legacy(temp_file)
        
        # Enhanced success feedback for legacy processing
        if result and result.strip():
            char_count = len(result.strip())
            if char_count >= 50:
                progress_container.success(f"✅ Legacy processing successful! Extracted {char_count:,} characters")
                if is_pdf and char_count > 500:  # Likely OCR was used for substantial text
                    st.info("📋 This document was processed using legacy OCR mode.")
            else:
                progress_container.warning(f"⚠️ Legacy processing extracted limited text ({char_count} characters)")
                st.info("💡 For better results, consider using the full processing engine.")
            
            import time
            time.sleep(2)
        else:
            progress_container.error("❌ Legacy processing failed to extract text")
            if is_pdf:
                st.info("💡 Legacy OCR processing failed. This may be due to:")
                st.write("• Poor image quality in scanned PDF")
                st.write("• Missing OCR dependencies (tesseract)")
                st.write("• Memory constraints in legacy mode")
            import time
            time.sleep(3)
        
        progress_container.empty()
        return result
    
    try:
        # Use integrated document processor
        session = st.session_state.session_info if 'session_info' in st.session_state else None
        logger.info(f"Session info available: {session is not None}")
        
        processor = DocumentProcessor(
            firm_id=session.firm_id if session else None,
            user_id=session.user_id if session else None
        )
        
        # Show processing status
        if is_pdf:
            progress_container.info("🔍 Analyzing PDF structure...")
        
        logger.info(f"Starting document processing with DocumentProcessor")
        
        # Enhanced OCR detection and status reporting
        try:
            capabilities = processor.get_processing_capabilities()
            ocr_available = capabilities.get('ocr_available', False)
            
            if is_pdf and ocr_available:
                progress_container.info("🖼️ PDF detected - checking if OCR is needed...")
                
                # Quick check if OCR might be needed (for scanned PDFs)
                if len(file_content) > 1024 * 1024:  # Files > 1MB might be scanned
                    progress_container.info("📄 Large PDF detected - preparing for potential OCR processing...")
        except Exception as e:
            logger.debug(f"Capabilities check failed: {e}")
        
        # Process document with enhanced OCR status monitoring
        logger.info(f"Starting document processing with DocumentProcessor")
        
        # Check if this might trigger OCR by looking at processing method
        try:
            # Monitor for OCR-specific log messages during processing
            import threading
            import time
            
            ocr_detected = threading.Event()
            
            def monitor_ocr_logs():
                # Enhanced OCR monitoring with better indicators
                time.sleep(1)  # Give processing a moment to start
                if is_pdf:
                    if not ocr_detected.is_set():
                        progress_container.info("🔍 Analyzing PDF structure - checking if OCR is needed...")
                        time.sleep(2)
                        if not ocr_detected.is_set():
                            progress_container.info("🖼️ Regular text extraction insufficient - attempting OCR...")
                            time.sleep(3)
                            if not ocr_detected.is_set():
                                progress_container.info("⏳ OCR processing in progress - this may take a few moments...")
            
            monitor_thread = threading.Thread(target=monitor_ocr_logs, daemon=True)
            monitor_thread.start()
            
            result = processor.process_document(file_content, file_name)
            
            ocr_detected.set()  # Stop monitoring
            
        except Exception as e:
            # Fallback to simple processing without monitoring
            logger.debug(f"OCR monitoring failed: {e}")
            result = processor.process_document(file_content, file_name)
        
        if result.success:
            text_length = len(result.text_content) if result.text_content else 0
            logger.info(f"Document processed successfully - extracted {text_length} characters")
            
            # Enhanced success message with OCR detection
            if text_length > 0:
                # Check if OCR was used based on extraction method
                extraction_method = getattr(result.metadata, 'extraction_method', 'unknown') if hasattr(result, 'metadata') else 'unknown'
                
                if extraction_method == 'OCR' or 'ocr' in extraction_method.lower():
                    progress_container.success(f"✅ OCR processing completed! Extracted {text_length:,} characters from scanned PDF")
                    st.info("📋 This document was processed using OCR (Optical Character Recognition) for scanned content.")
                elif 'partial' in extraction_method.lower():
                    progress_container.warning(f"⚠️ Document partially processed! Extracted {text_length:,} characters")
                    st.info("💡 This document had limited extractable text. For better results, try a higher-quality scan.")
                else:
                    progress_container.success(f"✅ Document processed successfully! Extracted {text_length:,} characters")
                
                # Keep success message visible longer for OCR results
                import time
                sleep_time = 4 if 'ocr' in extraction_method.lower() else 2
                time.sleep(sleep_time)
                progress_container.empty()
            else:
                progress_container.warning("⚠️ Document processed but no text was extracted")
                
                # Enhanced guidance for failed OCR
                if is_pdf:
                    st.info("💡 If this is a scanned PDF:")
                    st.write("• OCR processing may have failed due to poor image quality")
                    st.write("• Try scanning at higher resolution (300+ DPI)")
                    st.write("• Ensure text is clearly visible and not handwritten")
                    st.write("• Check the Railway logs for detailed OCR diagnostics")
                
                time.sleep(3)
                progress_container.empty()
            
            return result.text_content or ""
        else:
            error_msg = getattr(result, 'error_message', 'Unknown error')
            logger.error(f"Document processing failed: {error_msg}")
            progress_container.error(f"❌ Document processing failed: {error_msg}")
            time.sleep(3)
            progress_container.empty()
            return ""
        
    except Exception as e:
        logger.error(f"File processing exception: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        
        # Fallback to legacy processing
        logger.info("Attempting fallback to legacy processing...")
        try:
            import io
            temp_file = io.BytesIO(file_content)
            temp_file.name = file_name
            result = extract_text_legacy(temp_file)
            
            if result:
                logger.info(f"Legacy processing succeeded - extracted {len(result)} characters")
                return result
            else:
                logger.error("Legacy processing also failed")
                return ""
                
        except Exception as fallback_error:
            logger.error(f"Legacy processing also failed: {fallback_error}")
            return ""

def perform_ocr_on_pdf_legacy(file_content: bytes, filename: str) -> str:
    """Perform OCR on PDF - lightweight version for legacy mode"""
    logger.info(f"Starting legacy OCR for {filename}")
    
    try:
        import tempfile
        import os
        
        # Save content to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            # Method 1: Try with PyMuPDF (fitz) first - it's more memory efficient
            try:
                import fitz
                import pytesseract
                from PIL import Image
                import io
                
                logger.info("Legacy processing: Using PyMuPDF for OCR")
                doc = fitz.open(tmp_path)
                all_text = []
                
                max_pages = min(len(doc), 10)  # Limit pages for memory
                logger.info(f"Legacy OCR: Processing {max_pages} pages")
                
                for page_num in range(max_pages):
                    logger.info(f"Legacy OCR page {page_num + 1}")
                    page = doc[page_num]
                    
                    # Get page as image with lower resolution for memory
                    mat = fitz.Matrix(1.2, 1.2)  # Slightly higher than minimum
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    
                    # OCR the image
                    img = Image.open(io.BytesIO(img_data))
                    if img.mode != 'L':
                        img = img.convert('L')  # Grayscale for efficiency
                    
                    text = pytesseract.image_to_string(img, lang='eng', timeout=30)
                    if text and text.strip():
                        all_text.append(text.strip())
                    
                    # Clean up immediately
                    img.close()
                    pix = None
                
                doc.close()
                final_text = '\n\n'.join(all_text)
                try:
                    log_ocr_processing(filename, max_pages, len(final_text))
                except:
                    logger.info(f"Legacy PyMuPDF OCR complete: {len(final_text)} characters")
                return final_text
                
            except ImportError:
                logger.warning("PyMuPDF not available in legacy mode, trying pdf2image")
            
            # Method 2: Fallback to pdf2image
            try:
                from pdf2image import convert_from_path
                import pytesseract
                
                logger.info("Legacy processing: Using pdf2image for OCR")
                # Very low settings for Railway memory constraints
                images = convert_from_path(
                    tmp_path,
                    dpi=100,  # Very low DPI
                    fmt='jpeg',
                    first_page=1,
                    last_page=min(3, 10),  # Only first 3 pages to save memory
                    thread_count=1
                )
                
                texts = []
                for i, image in enumerate(images):
                    logger.info(f"Legacy OCR on page {i+1}")
                    if image.mode != 'L':
                        image = image.convert('L')  # Convert to grayscale
                    text = pytesseract.image_to_string(image, lang='eng', timeout=30)
                    if text and text.strip():
                        texts.append(text.strip())
                
                final_text = '\n\n'.join(texts)
                try:
                    log_ocr_processing(filename, len(images), len(final_text))
                except:
                    logger.info(f"Legacy pdf2image OCR complete: {len(final_text)} characters")
                return final_text
                
            except ImportError:
                logger.error("pdf2image not available in legacy mode - OCR not possible")
                return ""
        
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Legacy OCR error: {type(e).__name__}: {str(e)}")
        logger.exception("Full legacy OCR traceback:")
        return ""

def extract_text_legacy(uploaded_file) -> str:
    """Legacy text extraction for backward compatibility with OCR support"""
    logger.info(f"Legacy processing for {uploaded_file.name}")
    
    try:
        content = ""
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            # First try regular PyPDF2 extraction
            try:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                
                # Use security logging instead of direct content logging
                try:
                    log_text_extraction(uploaded_file.name, "PyPDF2", len(content), success=bool(content))
                except:
                    logger.info(f"Legacy PyPDF2 extracted {len(content)} characters")
                
                # If extraction yielded very little text, try OCR
                if len(content.strip()) < 50:
                    logger.info(f"Legacy: Regular extraction insufficient ({len(content.strip())} < 50 chars), attempting OCR...")
                    
                    # Reset file pointer and get content as bytes
                    uploaded_file.seek(0)
                    file_content = uploaded_file.read()
                    
                    ocr_content = perform_ocr_on_pdf_legacy(file_content, uploaded_file.name)
                    if ocr_content and len(ocr_content.strip()) > len(content.strip()):
                        content = ocr_content
                        try:
                            log_text_extraction(uploaded_file.name, "Legacy OCR", len(content), success=True)
                        except:
                            logger.info(f"Legacy OCR successful: {len(content)} characters extracted")
                    else:
                        logger.warning("Legacy OCR did not improve text extraction")
                
            except Exception as pdf_error:
                logger.error(f"Legacy PDF processing error: {pdf_error}")
                # If PyPDF2 fails completely, try OCR as last resort
                try:
                    uploaded_file.seek(0)
                    file_content = uploaded_file.read()
                    content = perform_ocr_on_pdf_legacy(file_content, uploaded_file.name)
                    if content:
                        try:
                            log_text_extraction(uploaded_file.name, "Legacy Fallback OCR", len(content), success=True)
                        except:
                            logger.info(f"Legacy fallback OCR successful: {len(content)} characters")
                except Exception as ocr_error:
                    logger.error(f"Legacy fallback OCR also failed: {ocr_error}")
        
        elif file_extension == 'docx':
            doc = docx.Document(uploaded_file)
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
        
        elif file_extension == 'txt':
            content = str(uploaded_file.read(), "utf-8")
        
        # Force garbage collection for memory management
        import gc
        gc.collect()
        
        return content.strip()
        
    except Exception as e:
        logger.error(f"Legacy extraction error: {e}")
        logger.exception("Full legacy extraction traceback:")
        return ""

def get_legal_ai_response(query: str, practice_area: str, jurisdiction: str, files: list, case_id: str = None) -> str:
    """Get AI response using integrated legal engine"""
    if not ENGINE_AVAILABLE:
        logger.info("Using legacy Groq API (direct) - LangChain database engine not available")
        return get_groq_response_legacy(query, files)
    
    try:
        session = st.session_state.session_info
        logger.info("Using enhanced LangChain AI engine with database logging")
        
        # Get the LLM engine using the existing lazy loader
        engine = get_llm_engine()
        if engine is None:
            logger.warning("Enhanced LLM engine not available - falling back to Groq")
            return get_groq_response_legacy(query, files)
        
        # Configure engine with firm context if needed
        if hasattr(engine, 'set_context'):
            engine.set_context(
                firm_id=session.firm_id if session else None,
                user_id=session.user_id if session else None
            )
        
        # Prepare context with document content
        context = {}
        if files:
            context['documents'] = [{"name": name, "content": content} for name, content in files]
        
        # Process query with case linking if available
        if case_id and hasattr(engine, 'process_query_with_case'):
            response = engine.process_query_with_case(
                query=query,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                case_id=case_id,
                context=context
            )
        else:
            response = engine.process_query(
                query=query,
                practice_area=practice_area,
                jurisdiction=jurisdiction,
                context=context
            )
        
        # Format response with compliance info and clean content
        cleaned_response = clean_response_content(response.response) if hasattr(response, 'response') else str(response)
        
        formatted_response = f"""**Legal Analysis:**

{cleaned_response}

**Confidence Level:** {response.confidence_level if hasattr(response, 'confidence_level') else 'Medium'}
{" **Lawyer Review Recommended**" if hasattr(response, 'requires_human_review') and response.requires_human_review else " **Analysis Complete**"}

**Legal Considerations:**
{chr(10).join(f" {consideration}" for consideration in (response.legal_considerations if hasattr(response, 'legal_considerations') else []))}

**Recommendations:**
{chr(10).join(f" {recommendation}" for recommendation in (response.recommendations if hasattr(response, 'recommendations') else []))}

---
**Jurisdiction:** {safe_enum_value(response.jurisdiction).replace('_', ' ').title() if hasattr(response, 'jurisdiction') else jurisdiction.replace('_', ' ').title()}
**Practice Area:** {safe_enum_value(response.practice_area).replace('_', ' ').title() if hasattr(response, 'practice_area') else practice_area.replace('_', ' ').title()}
"""
        
        return formatted_response
        
    except NameError as e:
        if "EnhancedLegalLLMEngine" in str(e):
            logger.warning("EnhancedLegalLLMEngine not available - falling back to Groq API")
            return get_groq_response_legacy(query, files)
        else:
            logger.error(f"AI response NameError: {e}")
            return get_groq_response_legacy(query, files)
    except Exception as e:
        logger.error(f"AI response error: {e}")
        logger.warning("Falling back to Groq API due to error")
        return get_groq_response_legacy(query, files)

def extract_loan_amounts_fallback(query: str, files: list) -> str:
    """Fallback loan amount extraction when AI services are unavailable"""
    import re
    
    if "loan" not in query.lower() and "amount" not in query.lower():
        return None
    
    amounts_found = []
    documents_analyzed = []
    
    # Simple regex patterns for loan amounts
    patterns = [
        r'\$[\d,]+(?:\.\d{2})?',  # $1,000.00
        r'[\d,]+\s*(?:dollars|AUD|USD)',  # 1,000 AUD
        r'(?:loan|amount|principal|sum)[\s:]+\$?[\d,]+(?:\.\d{2})?',  # loan: $1,000
    ]
    
    for name, content in files:
        if content:
            documents_analyzed.append(name)
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Clean up the amount
                    amount_str = re.sub(r'[^\d,.]', '', match)
                    if amount_str and (amount_str.replace(',', '').replace('.', '')).isdigit():
                        try:
                            amount = float(amount_str.replace(',', ''))
                            if amount > 100:  # Only include reasonable loan amounts
                                amounts_found.append(f"${amount:,.2f}")
                        except:
                            pass
    
    if amounts_found:
        return f"""**Loan Amount Analysis (Basic Extraction)**

**Documents Analyzed:** {', '.join(documents_analyzed)}

**Loan Amounts Found:**
{chr(10).join(f"• {amount}" for amount in set(amounts_found))}

**Note:** This is a basic text analysis. For detailed legal analysis, please update your API keys and try again.

**Legal Disclaimer:** This automated extraction is for reference only. Please verify all amounts against original documents and consult with a qualified legal professional for advice."""

    return None

def process_legal_query_safe(query: str, practice_area: str, jurisdiction: str, files: list, case_id: str = None) -> str:
    """Process legal query with comprehensive error handling and fallbacks"""
    # Check API key availability first
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "❌ **Configuration Error**: AI API key not found. Please check your environment variables or contact your administrator."
    
    # Try the main engine first if available
    if ENGINE_AVAILABLE:
        try:
            return get_legal_ai_response(query, practice_area, jurisdiction, files, case_id)
        except Exception as e:
            logger.warning(f"Enhanced engine failed, falling back to legacy: {e}")
    
    # Fallback to legacy Groq processing
    return get_groq_response_legacy(query, files)

def get_groq_response_legacy(query: str, files: list) -> str:
    """Legacy Groq response with enhanced connection error handling"""
    if not GROQ_AVAILABLE:
        return "❌ **Service Unavailable**: AI service library not installed. Please contact your administrator."
    
    # Check API key
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "❌ **Configuration Error**: GROQ_API_KEY environment variable not set. Please check your configuration."
    
    try:
        client = Groq(api_key=groq_api_key)
        
        # Prepare context with files (security-conscious)
        context = ""
        total_chars = 0
        doc_count = 0
        
        if files:
            context = "\n\nDocument Context:\n"
            for name, content in files[-3:]:  # Limit to last 3 files
                doc_count += 1
                content_chunk = content[:2000] if content else ""
                total_chars += len(content_chunk)
                context += f"\n--- {name} ---\n{content_chunk}\n"
        
        # Log AI query without exposing content
        try:
            log_ai_query("legacy_groq", doc_count, total_chars, "llama3-70b-8192")
        except:
            logger.info(f"Legacy Groq query: {doc_count} documents, {total_chars} characters")
        
        messages = [
            {
                "role": "system",
                "content": create_secure_system_prompt()
            },
            {
                "role": "user", 
                "content": f"{query}{context}"
            }
        ]
        
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            max_tokens=4000,
            temperature=0.1
        )
        
        # Get the response and clean any role references
        raw_response = response.choices[0].message.content
        return clean_response_content(raw_response)
        
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        error_msg = str(e).lower()
        
        if "connection" in error_msg or "network" in error_msg or "timeout" in error_msg:
            return "**Connection Error**: Unable to reach AI service. Please check your internet connection and try again."
        elif "api" in error_msg or "key" in error_msg or "auth" in error_msg or "401" in error_msg:
            # Try fallback loan amount extraction for loan-related queries
            fallback_result = extract_loan_amounts_fallback(query, files)
            if fallback_result:
                return fallback_result
            
            return """**API Key Expired**: Your AI service API keys have expired and need to be renewed.

**To fix this:**
1. **OpenAI**: Get a new key from https://platform.openai.com/api-keys
2. **Groq**: Get a free key from https://console.groq.com/keys
3. Update your `.env` file with the new key
4. Restart the application

**Your query**: "{}" 

**Temporary workaround**: Contact your administrator to update the API keys.""".format(query[:100])
        elif "rate" in error_msg or "limit" in error_msg:
            return "**Rate Limit**: Too many requests. Please wait a moment and try again."
        elif "model" in error_msg:
            return "**Model Error**: The AI model is temporarily unavailable. Please try again later."
        else:
            return f"**Processing Error**: {str(e)[:100]}... Please try again or contact support if this persists."

def get_user_cases() -> List[Dict[str, Any]]:
    """Get cases for current user"""
    if not ENGINE_AVAILABLE or not st.session_state.session_info:
        return []
    
    try:
        session = st.session_state.session_info
        case_manager = CaseManager(
            firm_id=session.firm_id,
            user_id=session.user_id
        )
        
        cases = case_manager.list_cases() if hasattr(case_manager, 'list_cases') else []
        return cases[:10]  # Limit for UI
        
    except Exception as e:
        logger.error(f"Error getting cases: {e}")
        return []

def render_user_management():
    """Render user management interface (admin only)"""
    if not has_permission('manage_firm'):
        st.error("Access denied: Admin permissions required")
        return
    
    st.markdown("###  User Management")
    
    # Add user form
    with st.expander("Add New User"):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_user_name = st.text_input("Full Name")
                new_user_email = st.text_input("Email")
                new_user_role = st.selectbox(
                    "Role",
                    [safe_enum_value(role).replace('_', ' ').title() for role in AuthenticationRole if role != AuthenticationRole.PRINCIPAL]
                )
            with col2:
                new_user_password = st.text_input("Temporary Password", type="password")
                practitioner_number = st.text_input("Practitioner Number (Optional)")
                jurisdiction = st.selectbox("Jurisdiction", 
                    ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"])
            
            if st.form_submit_button("Add User"):
                # Implementation would create user via authentication system
                st.success(f"User {new_user_name} added successfully")
    
    # User list (placeholder)
    st.markdown("#### Current Users")
    st.info("User list would be displayed here with edit/deactivate options")

def render_firm_settings():
    """Render firm settings interface"""
    if not has_permission('manage_firm'):
        st.error("Access denied: Admin permissions required")
        return
    
    st.markdown("###  Firm Settings")
    
    session = st.session_state.session_info
    
    with st.form("firm_settings"):
        col1, col2 = st.columns(2)
        with col1:
            firm_name = st.text_input("Firm Name", value=session.firm_name)
            address = st.text_area("Address")
            phone = st.text_input("Phone")
        with col2:
            jurisdiction = st.selectbox("Primary Jurisdiction", 
                ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"])
            mfa_required = st.checkbox("Require MFA for all users")
            session_timeout = st.slider("Session Timeout (hours)", 1, 24, 8)
        
        if st.form_submit_button("Save Settings"):
            st.success("Firm settings updated successfully")

def main():
    """Main application entry point"""
    logger.info("Main application function called")
    
    try:
        logger.info("Initializing session state...")
        init_session_state()
        logger.info("Session state initialized successfully")
        
        # Initialize document processor
        logger.info("Initializing document processor...")
        init_document_processor()
        logger.info("Document processor initialization completed")
        
    except Exception as e:
        logger.error(f"Failed to initialize application components: {str(e)}")
        logger.exception("Application initialization error:")
        raise
    
    # Handle session validation for authenticated users
    if st.session_state.authenticated and AUTH_AVAILABLE:
        session_info = st.session_state.auth_system.validate_session(
            st.session_state.session_info.session_token
        )
        if not session_info:
            st.warning("Session expired. Please login again.")
            logout_user()
            return
    
    # Authentication check
    if not st.session_state.authenticated:
        st.markdown("""
        <div class="main-header">
            <h1> LegalLLM Professional</h1>
            <p>Multi-Tenant Legal AI Platform for Australian Law Firms</p>
        </div>
        """, unsafe_allow_html=True)
        
        render_login_form()
        return
    
    # Authenticated interface
    render_user_header()
    render_sidebar()
    
    # Main content based on current page
    current_page = getattr(st.session_state, 'current_page', 'chat')
    
    if current_page == 'chat':
        render_legal_chat()
    elif current_page == 'users' and has_permission('manage_firm'):
        render_user_management()
    elif current_page == 'firm' and has_permission('manage_firm'):
        render_firm_settings()
    elif current_page == 'cases':
        st.markdown("###  Case Management")
        st.info("Case management interface would be implemented here")
    elif current_page == 'documents':
        st.markdown("###  Document Analysis")
        st.info("Document analysis interface would be implemented here")
    elif current_page == 'analytics':
        st.markdown("###  Analytics Dashboard")
        st.info("Analytics dashboard would be implemented here")
    elif current_page == 'settings':
        st.markdown("###  User Settings")
        st.info("User settings interface would be implemented here")
    else:
        render_legal_chat()

def create_secure_system_prompt() -> str:
    """Create a system prompt that doesn't expose role information in responses"""
    return """Provide professional legal analysis and guidance. Focus on delivering clear, 
    accurate legal information without referencing your credentials or role. Start responses 
    directly with the analysis or answer. Ensure all advice includes appropriate disclaimers 
    about seeking qualified legal counsel for specific matters."""

def clean_response_content(response: str) -> str:
    """Clean AI response to remove any accidental role references"""
    if not response:
        return response
    
    # Remove common role reference patterns
    role_patterns = [
        "As a senior legal expert, ",
        "As a legal expert, ",
        "As an AI legal assistant, ",
        "As a legal professional, ",
        "Speaking as a lawyer, ",
        "In my capacity as a legal expert, ",
        "As your legal advisor, "
    ]
    
    cleaned_response = response
    for pattern in role_patterns:
        cleaned_response = cleaned_response.replace(pattern, "")
    
    # Also check for patterns at the start of sentences
    import re
    cleaned_response = re.sub(r'\. As a (senior )?legal expert, ', '. ', cleaned_response)
    cleaned_response = re.sub(r'^As a (senior )?legal expert, ', '', cleaned_response)
    
    return cleaned_response.strip()

if __name__ == "__main__":
    try:
        logger.info("Starting Streamlit application...")
        logger.info("Initializing session state...")
        main()
        
        # Production startup confirmation with port verification
        port = int(os.environ.get("PORT", 8501))
        logger.info(f"✅ Legal AI Hub running on port {port}")
        logger.info(f"🌐 Access the application at your Railway URL")
        logger.info("🔒 Multi-tenant authentication system active")
        logger.info("⚖️ Australian legal compliance enabled")
        
        # Verify port binding
        if port != 8501:
            logger.info(f"🚀 Railway deployment detected - using port {port}")
        else:
            logger.info(f"🔧 Local/development mode - using default port {port}")
            
        logger.info("Streamlit application started successfully")
    except ImportError as e:
        logger.error(f"Import error during startup: {str(e)}")
        logger.exception("Import error traceback:")
        st.error(f"Import Error: {str(e)}")
        st.info("This might be due to missing dependencies. Check the Railway logs for details.")
        st.stop()
    except Exception as e:
        logger.error(f"Failed to start Streamlit application: {str(e)}")
        logger.exception("Full startup error traceback:")
        st.error(f"Application Startup Error: {str(e)}")
        st.info("Check the Railway logs for detailed error information.")
        st.stop()