"""
Authentication API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, AuditLog
from .auth_service import AuthService
from .dependencies import get_current_active_user, require_permission
from .schemas import (
    LoginRequest, LoginResponse, RegisterFirmRequest, RegisterUserRequest,
    MFASetupRequest, MFASetupResponse, PasswordChangeRequest, UserResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()

@router.post("/register-firm", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_firm(
    request: RegisterFirmRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Register a new law firm with principal user
    
    - **firm_name**: Name of the law firm
    - **abn**: Australian Business Number (optional)
    - **phone**: Firm contact phone
    - **email**: Firm contact email
    - **principal_first_name**: Principal user first name
    - **principal_last_name**: Principal user last name
    - **principal_email**: Principal user email
    - **principal_password**: Principal user password (min 8 chars, uppercase, lowercase, digit)
    - **practitioner_number**: Australian legal practitioner number (optional)
    - **practitioner_state**: State where practitioner is registered (optional)
    """
    try:
        firm, principal = await auth_service.register_firm(request, db)
        
        # Log successful registration
        audit_log = AuditLog.log_user_action(
            firm_id=str(firm.id),
            user_id=str(principal.id),
            action='create',
            description=f'Firm registration: {firm.name}',
            entity_type='firm',
            entity_id=str(firm.id),
            ip_address=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get('user-agent') if http_request else None
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "message": "Firm registered successfully",
            "firm_id": str(firm.id),
            "principal_id": str(principal.id),
            "firm_name": firm.name
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )

@router.post("/register-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterUserRequest,
    current_user: User = Depends(require_permission("user.create")),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Register a new user in the current firm
    
    Requires: user.create permission (Principal or Admin role)
    """
    try:
        user = await auth_service.register_user(request, str(current_user.firm_id), db)
        
        # Log user creation
        audit_log = AuditLog.log_user_action(
            firm_id=str(current_user.firm_id),
            user_id=str(current_user.id),
            action='create',
            description=f'User created: {user.email}',
            entity_type='user',
            entity_id=str(user.id),
            ip_address=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get('user-agent') if http_request else None
        )
        db.add(audit_log)
        db.commit()
        
        return UserResponse.from_orm(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Authenticate user and return access token
    
    - **email**: User email address
    - **password**: User password
    - **mfa_code**: Multi-factor authentication code (if MFA enabled)
    """
    try:
        user, requires_mfa = await auth_service.authenticate_user(request, db)
        
        if requires_mfa:
            return LoginResponse(
                access_token="",
                expires_in=0,
                user_id=str(user.id),
                firm_id=str(user.firm_id),
                role=user.role.value,
                requires_mfa=True
            )
        
        # Generate access token
        token_data = auth_service.generate_access_token(user)
        
        # Log successful login
        audit_log = AuditLog.log_security_event(
            firm_id=str(user.firm_id),
            user_id=str(user.id),
            event='login',
            description=f'Successful login: {user.email}',
            severity='info',
            ip_address=http_request.client.host if http_request else None,
            user_agent=http_request.headers.get('user-agent') if http_request else None
        )
        db.add(audit_log)
        db.commit()
        
        return LoginResponse(**token_data)
        
    except ValueError as e:
        # Log failed login attempt
        if http_request:
            audit_log = AuditLog(
                firm_id=None,  # Don't know firm yet
                user_id=None,  # Don't know user yet
                event_type='security_event',
                action='login_failed',
                description=f'Failed login attempt: {request.email}',
                severity='warning',
                ip_address=http_request.client.host,
                user_agent=http_request.headers.get('user-agent')
            )
            db.add(audit_log)
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Logout current user (token will be invalid after expiration)
    """
    # Log logout
    audit_log = AuditLog.log_security_event(
        firm_id=str(current_user.firm_id),
        user_id=str(current_user.id),
        event='logout',
        description=f'User logout: {current_user.email}',
        severity='info',
        ip_address=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get('user-agent') if http_request else None
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Logged out successfully"}

@router.post("/setup-mfa", response_model=MFASetupResponse)
async def setup_mfa(
    request: MFASetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Setup multi-factor authentication for current user
    """
    try:
        if request.enable:
            mfa_data = await auth_service.setup_mfa(current_user, db)
            
            # Log MFA setup
            audit_log = AuditLog.log_security_event(
                firm_id=str(current_user.firm_id),
                user_id=str(current_user.id),
                event='mfa_enabled',
                description='MFA enabled for user',
                severity='info'
            )
            db.add(audit_log)
            db.commit()
            
            return MFASetupResponse(**mfa_data)
        else:
            # Disable MFA
            current_user.mfa_enabled = False
            current_user.mfa_secret = None
            current_user.mfa_backup_codes = None
            db.commit()
            
            # Log MFA disable
            audit_log = AuditLog.log_security_event(
                firm_id=str(current_user.firm_id),
                user_id=str(current_user.id),
                event='mfa_disabled',
                description='MFA disabled for user',
                severity='info'
            )
            db.add(audit_log)
            db.commit()
            
            return MFASetupResponse(qr_code="", backup_codes=[], secret="")
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup failed"
        )

@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password
    """
    try:
        await auth_service.change_password(
            current_user, 
            request.current_password, 
            request.new_password, 
            db
        )
        
        # Log password change
        audit_log = AuditLog.log_security_event(
            firm_id=str(current_user.firm_id),
            user_id=str(current_user.id),
            event='password_change',
            description='Password changed successfully',
            severity='info'
        )
        db.add(audit_log)
        db.commit()
        
        return {"message": "Password changed successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    """
    return UserResponse.from_orm(current_user)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_permission("user.read")),
    db: Session = Depends(get_db)
):
    """
    List all users in current firm
    
    Requires: user.read permission
    """
    users = db.query(User).filter(User.firm_id == current_user.firm_id).all()
    return [UserResponse.from_orm(user) for user in users]

@router.get("/practitioner-requirements")
async def get_practitioner_requirements():
    """
    Get Australian legal practitioner number requirements for all states
    """
    from .australian_validation import AustralianPractitionerValidator
    return AustralianPractitionerValidator.get_all_state_requirements()