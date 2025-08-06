"""
FastAPI dependencies for authentication
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..models import User
from .jwt_handler import JWTHandler
from ..database import get_db

security = HTTPBearer()
jwt_handler = JWTHandler()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: JWT token from Authorization header
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    payload = jwt_handler.verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    # Extract user ID
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (account and firm must be active)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user or firm is deactivated
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    if not current_user.firm.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firm account is deactivated"
        )
    
    return current_user

def require_permission(permission: str):
    """
    Dependency factory to require specific permission
    
    Args:
        permission: Required permission string
        
    Returns:
        Dependency function
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return current_user
    
    return permission_checker

def require_role(required_roles: list):
    """
    Dependency factory to require specific role(s)
    
    Args:
        required_roles: List of required roles
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required one of: {[role.value for role in required_roles]}"
            )
        return current_user
    
    return role_checker

# Common role dependencies
require_principal = require_role([User.UserRole.PRINCIPAL])
require_lawyer = require_role([User.UserRole.PRINCIPAL, User.UserRole.SENIOR_LAWYER, User.UserRole.LAWYER])
require_admin = require_role([User.UserRole.PRINCIPAL, User.UserRole.ADMIN])