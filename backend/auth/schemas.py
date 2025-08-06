"""
Authentication schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from enum import Enum

class UserRoleSchema(str, Enum):
    PRINCIPAL = "principal"
    SENIOR_LAWYER = "senior_lawyer"
    LAWYER = "lawyer"
    PARALEGAL = "paralegal"
    ADMIN = "admin"
    CLIENT = "client"

class AustralianStateSchema(str, Enum):
    NSW = "nsw"
    VIC = "vic"
    QLD = "qld"
    WA = "wa"
    SA = "sa"
    TAS = "tas"
    ACT = "act"
    NT = "nt"

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "email": "lawyer@example.com",
                "password": "SecurePassword123!",
                "mfa_code": "123456"
            }
        }

class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    firm_id: str
    role: UserRoleSchema
    requires_mfa: bool = False
    mfa_qr_code: Optional[str] = None  # Only for MFA setup

class RegisterFirmRequest(BaseModel):
    """Firm registration request schema"""
    # Firm details
    firm_name: str
    abn: Optional[str] = None
    phone: str
    email: EmailStr
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[AustralianStateSchema] = None
    postal_code: Optional[str] = None
    
    # Principal user details
    principal_first_name: str
    principal_last_name: str
    principal_email: EmailStr
    principal_password: str
    principal_phone: Optional[str] = None
    practitioner_number: Optional[str] = None
    practitioner_state: Optional[AustralianStateSchema] = None
    
    @validator('principal_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('abn')
    def validate_abn(cls, v):
        """Validate Australian Business Number"""
        if v and not v.isdigit() or len(v) != 11:
            raise ValueError('ABN must be 11 digits')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "firm_name": "Smith & Associates Legal",
                "abn": "12345678901",
                "phone": "(02) 9555-1234",
                "email": "admin@smithassociates.com.au",
                "address": "Level 15, 123 Collins Street",
                "city": "Melbourne",
                "state": "vic",
                "postal_code": "3000",
                "principal_first_name": "John",
                "principal_last_name": "Smith",
                "principal_email": "john.smith@smithassociates.com.au",
                "principal_password": "SecurePassword123!",
                "practitioner_number": "12345678",
                "practitioner_state": "vic"
            }
        }

class RegisterUserRequest(BaseModel):
    """User registration request schema"""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRoleSchema
    practitioner_number: Optional[str] = None
    practitioner_state: Optional[AustralianStateSchema] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "lawyer@example.com",
                "password": "SecurePassword123!",
                "first_name": "Jane",
                "last_name": "Doe",
                "role": "lawyer",
                "practitioner_number": "87654321",
                "practitioner_state": "nsw"
            }
        }

class MFASetupRequest(BaseModel):
    """MFA setup request schema"""
    enable: bool = True

class MFASetupResponse(BaseModel):
    """MFA setup response schema"""
    qr_code: str
    backup_codes: list[str]
    secret: str

class PasswordChangeRequest(BaseModel):
    """Password change request schema"""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserResponse(BaseModel):
    """User response schema"""
    id: str
    email: str
    first_name: str
    last_name: str
    role: UserRoleSchema
    is_active: bool
    mfa_enabled: bool
    last_login: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True