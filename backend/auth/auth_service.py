"""
Authentication service for LegalAI Hub
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import qrcode
import io
import base64

from ..models import User, LawFirm
from ..models.enums import UserRole, AustralianState, SubscriptionTier
from .jwt_handler import JWTHandler
from .australian_validation import AustralianPractitionerValidator
from .schemas import RegisterFirmRequest, RegisterUserRequest, LoginRequest

class AuthService:
    """Handle authentication operations"""
    
    def __init__(self):
        self.jwt_handler = JWTHandler()
        self.practitioner_validator = AustralianPractitionerValidator()
    
    async def register_firm(self, request: RegisterFirmRequest, db: Session) -> Tuple[LawFirm, User]:
        """
        Register a new law firm with principal user
        
        Args:
            request: Firm registration request
            db: Database session
            
        Returns:
            Tuple of created firm and principal user
            
        Raises:
            ValueError: If validation fails
            IntegrityError: If firm/user already exists
        """
        # Validate Australian practitioner number if provided
        if request.practitioner_number and request.practitioner_state:
            validation_result = self.practitioner_validator.validate_practitioner_number(
                request.practitioner_number, 
                AustralianState(request.practitioner_state)
            )
            if not validation_result['valid']:
                raise ValueError(f"Invalid practitioner number: {validation_result['error']}")
        
        try:
            # Create law firm
            firm = LawFirm(
                name=request.firm_name,
                abn=request.abn,
                phone=request.phone,
                email=request.email,
                address=request.address,
                city=request.city,
                state=AustralianState(request.state) if request.state else None,
                postal_code=request.postal_code,
                subscription_tier=SubscriptionTier.PROFESSIONAL,
                principal_practitioner_number=request.practitioner_number,
                practitioner_state=AustralianState(request.practitioner_state) if request.practitioner_state else None
            )
            
            db.add(firm)
            db.flush()  # Get firm ID without committing
            
            # Create principal user
            principal = User(
                firm_id=firm.id,
                email=request.principal_email,
                first_name=request.principal_first_name,
                last_name=request.principal_last_name,
                role=UserRole.PRINCIPAL,
                practitioner_number=request.practitioner_number,
                practitioner_state=AustralianState(request.practitioner_state) if request.practitioner_state else None
            )
            principal.set_password(request.principal_password)
            
            db.add(principal)
            db.commit()
            
            return firm, principal
            
        except IntegrityError as e:
            db.rollback()
            if "abn" in str(e.orig):
                raise ValueError("A firm with this ABN already exists")
            elif "email" in str(e.orig):
                raise ValueError("A user with this email already exists")
            else:
                raise ValueError("Registration failed due to data conflict")
    
    async def register_user(self, request: RegisterUserRequest, firm_id: str, db: Session) -> User:
        """
        Register a new user in existing firm
        
        Args:
            request: User registration request
            firm_id: ID of the firm to add user to
            db: Database session
            
        Returns:
            Created user
            
        Raises:
            ValueError: If validation fails
            IntegrityError: If user already exists
        """
        # Check if firm exists and can add more users
        firm = db.query(LawFirm).filter(LawFirm.id == firm_id).first()
        if not firm:
            raise ValueError("Firm not found")
        
        if not firm.can_add_user():
            raise ValueError(f"Firm has reached maximum user limit of {firm.max_users}")
        
        # Validate Australian practitioner number if provided
        if request.practitioner_number and request.practitioner_state:
            validation_result = self.practitioner_validator.validate_practitioner_number(
                request.practitioner_number,
                AustralianState(request.practitioner_state)
            )
            if not validation_result['valid']:
                raise ValueError(f"Invalid practitioner number: {validation_result['error']}")
        
        try:
            user = User(
                firm_id=firm_id,
                email=request.email,
                first_name=request.first_name,
                last_name=request.last_name,
                role=UserRole(request.role),
                practitioner_number=request.practitioner_number,
                practitioner_state=AustralianState(request.practitioner_state) if request.practitioner_state else None
            )
            user.set_password(request.password)
            
            db.add(user)
            db.commit()
            
            return user
            
        except IntegrityError:
            db.rollback()
            raise ValueError("A user with this email already exists")
    
    async def authenticate_user(self, request: LoginRequest, db: Session) -> Tuple[Optional[User], bool]:
        """
        Authenticate user login
        
        Args:
            request: Login request
            db: Database session
            
        Returns:
            Tuple of (user, requires_mfa)
            
        Raises:
            ValueError: If authentication fails
        """
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise ValueError("Invalid email or password")
        
        # Check if account is locked
        if user.is_account_locked():
            lock_time = user.account_locked_until.strftime("%Y-%m-%d %H:%M:%S")
            raise ValueError(f"Account is locked until {lock_time}")
        
        # Verify password
        if not user.verify_password(request.password):
            user.record_failed_login()
            db.commit()
            raise ValueError("Invalid email or password")
        
        # Check if account is active
        if not user.is_active:
            raise ValueError("Account is deactivated")
        
        # Check if firm is active
        if not user.firm.is_active:
            raise ValueError("Firm account is deactivated")
        
        # Handle MFA if enabled
        if user.mfa_enabled:
            if not request.mfa_code:
                return user, True  # Requires MFA code
            
            if not user.verify_mfa_token(request.mfa_code):
                user.record_failed_login()
                db.commit()
                raise ValueError("Invalid MFA code")
        
        # Successful login
        user.record_successful_login()
        db.commit()
        
        return user, False
    
    def generate_access_token(self, user: User) -> dict:
        """Generate JWT access token for user"""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "firm_id": str(user.firm_id),
            "role": user.role.value,
            "type": "access"
        }
        
        access_token = self.jwt_handler.create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.jwt_handler.access_token_expire_minutes * 60,
            "user_id": str(user.id),
            "firm_id": str(user.firm_id),
            "role": user.role.value
        }
    
    async def setup_mfa(self, user: User, db: Session) -> dict:
        """
        Setup MFA for user
        
        Args:
            user: User to setup MFA for
            db: Database session
            
        Returns:
            Dict with QR code and backup codes
        """
        qr_data = user.setup_mfa()
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        user.mfa_enabled = True
        db.commit()
        
        return {
            "qr_code": f"data:image/png;base64,{img_base64}",
            "backup_codes": user.mfa_backup_codes,
            "secret": user.mfa_secret
        }
    
    async def change_password(self, user: User, current_password: str, new_password: str, db: Session) -> bool:
        """
        Change user password
        
        Args:
            user: User to change password for
            current_password: Current password
            new_password: New password
            db: Database session
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If current password is incorrect
        """
        if not user.verify_password(current_password):
            raise ValueError("Current password is incorrect")
        
        user.set_password(new_password)
        db.commit()
        
        return True
    
    async def reset_password(self, email: str, db: Session) -> bool:
        """
        Initiate password reset process
        
        Args:
            email: User email
            db: Database session
            
        Returns:
            True if reset email sent (always returns True for security)
        """
        user = db.query(User).filter(User.email == email).first()
        if user:
            # In production, this would send a reset email
            # For now, just update the last_password_reset timestamp
            user.last_password_reset = datetime.utcnow()
            db.commit()
        
        # Always return True to prevent email enumeration
        return True