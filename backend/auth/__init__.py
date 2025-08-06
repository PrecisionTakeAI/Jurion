"""
Authentication system for LegalAI Hub
"""

from .auth_service import AuthService
from .jwt_handler import JWTHandler
from .dependencies import get_current_user, get_current_active_user
from .schemas import LoginRequest, LoginResponse, RegisterFirmRequest, RegisterUserRequest

__all__ = [
    'AuthService',
    'JWTHandler', 
    'get_current_user',
    'get_current_active_user',
    'LoginRequest',
    'LoginResponse',
    'RegisterFirmRequest',
    'RegisterUserRequest'
]