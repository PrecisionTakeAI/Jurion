#!/usr/bin/env python3
"""
Authentication Components for LegalLLM Professional Enterprise Interface
Streamlit components for login, registration, and user management
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

def validate_email(email: str) -> bool:
    """Validate email address format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_australian_phone(phone: str) -> bool:
    """Validate Australian phone number format"""
    # Remove spaces and special characters
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    # Check for Australian formats
    patterns = [
        r'^(\+61|0)[2-9]\d{8}$',  # Landline
        r'^(\+61|0)4\d{8}$',       # Mobile
        r'^(\+61|0)1[38]\d{8}$'    # Special numbers
    ]
    return any(re.match(pattern, clean_phone) for pattern in patterns)

def validate_practitioner_number(number: str, jurisdiction: str) -> bool:
    """Validate Australian legal practitioner number format by jurisdiction"""
    # Remove spaces and special characters
    clean_number = re.sub(r'[\s\-]', '', number)
    
    # Basic validation - numbers only, appropriate length
    if not re.match(r'^\d+$', clean_number):
        return False
    
    # Jurisdiction-specific validation
    jurisdiction_patterns = {
        'NSW': r'^\d{4,6}$',
        'VIC': r'^\d{4,6}$',
        'QLD': r'^\d{4,6}$',
        'WA': r'^\d{4,6}$',
        'SA': r'^\d{4,6}$',
        'TAS': r'^\d{4,6}$',
        'ACT': r'^\d{4,6}$',
        'NT': r'^\d{4,6}$'
    }
    
    pattern = jurisdiction_patterns.get(jurisdiction, r'^\d{4,6}$')
    return re.match(pattern, clean_number) is not None

def render_login_form() -> Optional[Dict]:
    """Render professional login form for Australian legal professionals"""
    
    st.markdown("### 🔐 Professional Login")
    st.markdown("*Secure access for Australian legal professionals*")
    
    with st.form("professional_login", clear_on_submit=False):
        # Email input with validation
        email = st.text_input(
            "Email Address",
            placeholder="your.name@lawfirm.com.au",
            help="Use your registered firm email address"
        )
        
        # Password input
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your secure password",
            help="Minimum 8 characters with special characters"
        )
        
        # Login options
        col1, col2 = st.columns(2)
        with col1:
            remember_me = st.checkbox("Remember me", help="Keep me logged in for 30 days")
        with col2:
            show_mfa = st.checkbox("Use MFA", help="Multi-factor authentication")
        
        # MFA input if enabled
        mfa_code = None
        if show_mfa:
            mfa_code = st.text_input(
                "MFA Code",
                placeholder="000000",
                max_chars=6,
                help="Enter 6-digit code from your authenticator app"
            )
        
        # Submit buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            submit_login = st.form_submit_button("🚀 Login", use_container_width=True)
        with col2:
            forgot_password = st.form_submit_button("🔄 Reset", use_container_width=True)
        with col3:
            help_button = st.form_submit_button("❓ Help", use_container_width=True)
        
        # Handle form submission
        if submit_login:
            errors = []
            
            # Validate inputs
            if not email:
                errors.append("Email address is required")
            elif not validate_email(email):
                errors.append("Please enter a valid email address")
            
            if not password:
                errors.append("Password is required")
            elif len(password) < 8:
                errors.append("Password must be at least 8 characters")
            
            if show_mfa and (not mfa_code or len(mfa_code) != 6):
                errors.append("Please enter a valid 6-digit MFA code")
            
            # Display errors or return credentials
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
                return None
            else:
                return {
                    "email": email.lower().strip(),
                    "password": password,
                    "mfa_code": mfa_code,
                    "remember_me": remember_me
                }
        
        if forgot_password:
            st.info("🔄 Password reset functionality will be available in the next release.")
            return None
        
        if help_button:
            render_login_help()
            return None
    
    return None

def render_firm_registration() -> Optional[Dict]:
    """Render comprehensive firm registration form"""
    
    st.markdown("### 🏛️ Register Your Law Firm")
    st.markdown("*Create a new firm account for LegalLLM Professional*")
    
    # Show registration requirements
    with st.expander("📋 Registration Requirements", expanded=False):
        st.markdown("""
        **To register your law firm, you'll need:**
        - Official firm name and ABN (if applicable)
        - Principal lawyer details with valid practitioner number
        - Australian jurisdiction of practice
        - Firm contact information
        - Secure password and terms acceptance
        
        **Supported Jurisdictions:**
        🇦🇺 All Australian states and territories (NSW, VIC, QLD, WA, SA, TAS, ACT, NT)
        """)
    
    with st.form("firm_registration", clear_on_submit=False):
        # Firm Information Section
        st.markdown("#### 🏢 Law Firm Information")
        
        col1, col2 = st.columns(2)
        with col1:
            firm_name = st.text_input(
                "Law Firm Name *",
                placeholder="Smith & Associates Legal",
                help="Official registered name of your law firm"
            )
            
            firm_abn = st.text_input(
                "ABN (Optional)",
                placeholder="12 345 678 901",
                help="Australian Business Number (if applicable)"
            )
        
        with col2:
            firm_type = st.selectbox(
                "Firm Type",
                ["Sole Practitioner", "Partnership", "Incorporated Law Firm", "Multi-National", "In-House Legal", "Government Legal", "Other"],
                help="Type of legal practice"
            )
            
            firm_size = st.selectbox(
                "Firm Size",
                ["1-2 lawyers", "3-10 lawyers", "11-50 lawyers", "51-200 lawyers", "200+ lawyers"],
                help="Number of legal practitioners in your firm"
            )
        
        # Principal Lawyer Information
        st.markdown("#### 👨‍💼 Principal Lawyer Details")
        
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input(
                "First Name *",
                placeholder="John",
                help="Principal lawyer's first name"
            )
            
            last_name = st.text_input(
                "Last Name *",
                placeholder="Smith",
                help="Principal lawyer's last name"
            )
            
            title = st.selectbox(
                "Professional Title",
                ["Mr", "Ms", "Mrs", "Dr", "Prof", "Hon", "QC", "SC"],
                help="Professional title or honorific"
            )
        
        with col2:
            email = st.text_input(
                "Email Address *",
                placeholder="john.smith@lawfirm.com.au",
                help="Principal's professional email address"
            )
            
            phone = st.text_input(
                "Phone Number *",
                placeholder="+61 2 9999 0000",
                help="Direct phone number for the principal lawyer"
            )
            
            position = st.text_input(
                "Position",
                placeholder="Managing Partner",
                help="Role within the firm"
            )
        
        # Australian Legal Practice Information
        st.markdown("#### ⚖️ Australian Legal Practice")
        
        col1, col2 = st.columns(2)
        with col1:
            jurisdiction = st.selectbox(
                "Primary Jurisdiction *",
                ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                help="Your primary practicing jurisdiction in Australia"
            )
            
            practitioner_number = st.text_input(
                f"Legal Practitioner Number ({jurisdiction}) *",
                placeholder="123456",
                help=f"Your legal practitioner registration number in {jurisdiction}"
            )
        
        with col2:
            additional_jurisdictions = st.multiselect(
                "Additional Jurisdictions",
                ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT", "Federal Courts"],
                help="Other jurisdictions where you practice (optional)"
            )
            
            practice_areas = st.multiselect(
                "Primary Practice Areas",
                [
                    "Family Law", "Corporate Law", "Criminal Law", "Property Law",
                    "Employment Law", "Personal Injury", "Commercial Law", "Litigation",
                    "Immigration Law", "Tax Law", "Intellectual Property", "Environmental Law",
                    "Administrative Law", "Construction Law", "Insurance Law", "Other"
                ],
                help="Select your main areas of legal practice"
            )
        
        # Firm Address Information
        st.markdown("#### 📍 Firm Address")
        
        col1, col2 = st.columns(2)
        with col1:
            street_address = st.text_input(
                "Street Address",
                placeholder="Level 10, 123 Collins Street",
                help="Physical address of your firm"
            )
            
            city = st.text_input(
                "City",
                placeholder="Melbourne",
                help="City where your firm is located"
            )
        
        with col2:
            state = st.selectbox(
                "State/Territory",
                ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                help="State or territory of your firm's address"
            )
            
            postcode = st.text_input(
                "Postcode",
                placeholder="3000",
                help="Australian postcode"
            )
        
        # Security Information
        st.markdown("#### 🔐 Account Security")
        
        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input(
                "Password *",
                type="password",
                placeholder="Minimum 8 characters",
                help="Strong password with uppercase, lowercase, numbers, and special characters"
            )
        
        with col2:
            confirm_password = st.text_input(
                "Confirm Password *",
                type="password",
                placeholder="Re-enter your password",
                help="Must match the password above"
            )
        
        # Multi-factor authentication setup
        enable_mfa = st.checkbox(
            "Enable Multi-Factor Authentication (Recommended)",
            help="Adds an extra layer of security to your account"
        )
        
        if enable_mfa:
            st.info("📱 You'll be guided through MFA setup after registration.")
        
        # Terms and Conditions
        st.markdown("#### 📜 Terms and Conditions")
        
        col1, col2 = st.columns(2)
        with col1:
            terms_accepted = st.checkbox(
                "I accept the Terms of Service *",
                help="Required to create an account"
            )
            
            privacy_accepted = st.checkbox(
                "I accept the Privacy Policy *",
                help="Required to create an account"
            )
        
        with col2:
            marketing_consent = st.checkbox(
                "I consent to receive product updates",
                help="Optional - you can change this later"
            )
            
            data_processing_consent = st.checkbox(
                "I consent to data processing for legal AI analysis",
                help="Required for AI functionality"
            )
        
        # Firm verification information
        with st.expander("🔍 Firm Verification (Optional)", expanded=False):
            st.markdown("*Provide additional information to expedite verification:*")
            
            law_society_membership = st.text_input(
                "Law Society Membership Number",
                placeholder="e.g., Law Society of NSW membership",
                help="Your membership number with relevant law society"
            )
            
            firm_website = st.text_input(
                "Firm Website",
                placeholder="https://www.yourfirm.com.au",
                help="Your firm's official website"
            )
            
            verification_documents = st.file_uploader(
                "Verification Documents",
                type=["pdf", "jpg", "png"],
                accept_multiple_files=True,
                help="Upload practising certificate, firm registration, or other verification documents"
            )
        
        # Submit button
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit_registration = st.form_submit_button(
                "🏛️ Register Law Firm",
                use_container_width=True,
                help="Create your firm account"
            )
        
        # Handle registration submission
        if submit_registration:
            errors = []
            
            # Validate required fields
            if not firm_name or len(firm_name) < 3:
                errors.append("Firm name must be at least 3 characters")
            
            if not first_name or not last_name:
                errors.append("Principal lawyer's first and last names are required")
            
            if not email or not validate_email(email):
                errors.append("Valid email address is required")
            
            if not phone or not validate_australian_phone(phone):
                errors.append("Valid Australian phone number is required")
            
            if not practitioner_number or not validate_practitioner_number(practitioner_number, jurisdiction):
                errors.append(f"Valid {jurisdiction} legal practitioner number is required")
            
            if not password or len(password) < 8:
                errors.append("Password must be at least 8 characters")
            
            if password != confirm_password:
                errors.append("Passwords do not match")
            
            if not terms_accepted or not privacy_accepted:
                errors.append("You must accept the Terms of Service and Privacy Policy")
            
            if not data_processing_consent:
                errors.append("Data processing consent is required for AI functionality")
            
            # Display errors or return registration data
            if errors:
                st.error("🚫 **Registration Validation Errors:**")
                for error in errors:
                    st.error(f"• {error}")
                return None
            else:
                # Return registration data
                return {
                    "firm_info": {
                        "name": firm_name.strip(),
                        "abn": firm_abn.strip() if firm_abn else None,
                        "type": firm_type,
                        "size": firm_size,
                        "address": {
                            "street": street_address.strip() if street_address else None,
                            "city": city.strip() if city else None,
                            "state": state,
                            "postcode": postcode.strip() if postcode else None
                        },
                        "website": firm_website.strip() if firm_website else None
                    },
                    "principal_info": {
                        "title": title,
                        "first_name": first_name.strip(),
                        "last_name": last_name.strip(),
                        "email": email.lower().strip(),
                        "phone": phone.strip(),
                        "position": position.strip() if position else "Principal",
                        "jurisdiction": jurisdiction,
                        "practitioner_number": practitioner_number.strip(),
                        "additional_jurisdictions": additional_jurisdictions,
                        "practice_areas": practice_areas,
                        "law_society_membership": law_society_membership.strip() if law_society_membership else None
                    },
                    "security": {
                        "password": password,
                        "enable_mfa": enable_mfa
                    },
                    "consents": {
                        "terms": terms_accepted,
                        "privacy": privacy_accepted,
                        "marketing": marketing_consent,
                        "data_processing": data_processing_consent
                    },
                    "verification_documents": verification_documents if verification_documents else None
                }
    
    return None

def render_login_help():
    """Render login help information"""
    st.markdown("### ❓ Login Help")
    
    with st.expander("🔐 Forgot Password", expanded=True):
        st.markdown("""
        **To reset your password:**
        1. Click the "Reset" button on the login form
        2. Enter your registered email address
        3. Check your email for reset instructions
        4. Follow the secure link to create a new password
        
        *Note: Password reset functionality will be available in the next release.*
        """)
    
    with st.expander("📱 Multi-Factor Authentication (MFA)", expanded=False):
        st.markdown("""
        **Setting up MFA:**
        1. Install an authenticator app (Google Authenticator, Authy, Microsoft Authenticator)
        2. Enable MFA in your account settings after first login
        3. Scan the QR code with your authenticator app
        4. Enter the 6-digit code when logging in
        
        **MFA Benefits:**
        - Enhanced security for sensitive legal data
        - Required for partners and administrators
        - Compliance with Australian legal security standards
        """)
    
    with st.expander("🏛️ Firm Registration", expanded=False):
        st.markdown("""
        **New to LegalLLM Professional?**
        
        **Requirements for firm registration:**
        - Valid Australian legal practitioner registration
        - Firm email address (not personal email)
        - Principal lawyer authorization
        - Terms of service acceptance
        
        **Verification process:**
        1. Submit registration form
        2. Email verification
        3. Practitioner number validation
        4. Account activation (usually within 24 hours)
        
        **Need help?** Contact support at support@legalllm.com.au
        """)
    
    with st.expander("🔧 Technical Support", expanded=False):
        st.markdown("""
        **Common login issues:**
        
        **Browser compatibility:**
        - Use latest version of Chrome, Firefox, Safari, or Edge
        - Enable JavaScript and cookies
        - Clear browser cache if experiencing issues
        
        **Network requirements:**
        - Stable internet connection required
        - Ports 80 and 443 must be accessible
        - Corporate firewalls may need configuration
        
        **Security features:**
        - Account lockout after 5 failed attempts
        - Session timeout after 8 hours of inactivity
        - Secure HTTPS connection required
        
        **Contact support:**
        - Email: support@legalllm.com.au
        - Phone: 1800 LEGAL AI (1800 534 252)
        - Business hours: 8 AM - 6 PM AEST
        """)

def render_password_strength_indicator(password: str) -> None:
    """Render password strength indicator"""
    if not password:
        return
    
    # Calculate password strength
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("At least 8 characters")
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Uppercase letter")
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Lowercase letter")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Number")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append("Special character")
    
    # Display strength
    strength_colors = ["🔴", "🟠", "🟡", "🟢", "🟢"]
    strength_labels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
    
    if score > 0:
        color = strength_colors[min(score-1, 4)]
        label = strength_labels[min(score-1, 4)]
        
        st.markdown(f"**Password Strength:** {color} {label}")
        
        if feedback:
            st.markdown(f"**Missing:** {', '.join(feedback)}")