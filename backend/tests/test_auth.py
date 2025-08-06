"""
Unit tests for authentication endpoints and services
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from ..main import app
from ..auth.auth_service import AuthService
from ..auth.australian_validation import AustralianPractitionerValidator
from ..models import User, LawFirm
from ..models.enums import UserRole, AustralianState

client = TestClient(app)

class TestAustralianPractitionerValidator:
    """Test Australian practitioner validation"""
    
    def test_nsw_validation(self):
        """Test NSW practitioner number validation"""
        # Valid NSW number (8 digits)
        result = AustralianPractitionerValidator.validate_practitioner_number(
            "12345678", AustralianState.NSW
        )
        assert result['valid'] is True
        assert result['state'] == 'nsw'
        
        # Invalid NSW number (too short)
        result = AustralianPractitionerValidator.validate_practitioner_number(
            "123456", AustralianState.NSW
        )
        assert result['valid'] is False
        assert 'Invalid format' in result['error']
    
    def test_vic_validation(self):
        """Test VIC practitioner number validation"""
        # Valid VIC number (7 digits)
        result = AustralianPractitionerValidator.validate_practitioner_number(
            "1234567", AustralianState.VIC
        )
        assert result['valid'] is True
        
        # Valid VIC number (8 digits)
        result = AustralianPractitionerValidator.validate_practitioner_number(
            "12345678", AustralianState.VIC
        )
        assert result['valid'] is True
    
    def test_all_states_coverage(self):
        """Test that all Australian states have validation patterns"""
        requirements = AustralianPractitionerValidator.get_all_state_requirements()
        
        expected_states = ['nsw', 'vic', 'qld', 'wa', 'sa', 'tas', 'act', 'nt']
        assert set(requirements.keys()) == set(expected_states)
        
        for state, info in requirements.items():
            assert 'description' in info
            assert 'example' in info
            assert 'pattern' in info
    
    def test_format_validation(self):
        """Test format validation method"""
        # Test valid formats
        assert AustralianPractitionerValidator.is_valid_format("12345678", AustralianState.NSW) is True
        assert AustralianPractitionerValidator.is_valid_format("1234567", AustralianState.VIC) is True
        
        # Test invalid formats
        assert AustralianPractitionerValidator.is_valid_format("123", AustralianState.NSW) is False
        assert AustralianPractitionerValidator.is_valid_format("abcd1234", AustralianState.NSW) is False

class TestAuthService:
    """Test authentication service"""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service instance"""
        return AuthService()
    
    def test_register_firm_success(self, auth_service, db_session):
        """Test successful firm registration"""
        from ..auth.schemas import RegisterFirmRequest
        
        request = RegisterFirmRequest(
            firm_name="Test Legal Firm",
            abn="12345678901",
            phone="(02) 9555-1234",
            email="admin@testfirm.com.au",
            address="123 Test Street",
            city="Sydney",
            state="nsw",
            postal_code="2000",
            principal_first_name="John",
            principal_last_name="Smith",
            principal_email="john@testfirm.com.au",
            principal_password="SecurePass123!",
            practitioner_number="12345678",
            practitioner_state="nsw"
        )
        
        # Use asyncio to run async function
        import asyncio
        firm, principal = asyncio.run(auth_service.register_firm(request, db_session))
        
        assert firm.name == "Test Legal Firm"
        assert firm.abn == "12345678901"
        assert principal.email == "john@testfirm.com.au"
        assert principal.role == UserRole.PRINCIPAL
        assert principal.verify_password("SecurePass123!") is True
    
    def test_register_firm_invalid_practitioner(self, auth_service, db_session):
        """Test firm registration with invalid practitioner number"""
        from ..auth.schemas import RegisterFirmRequest
        
        request = RegisterFirmRequest(
            firm_name="Test Legal Firm",
            phone="(02) 9555-1234",
            email="admin@testfirm.com.au",
            principal_first_name="John",
            principal_last_name="Smith",
            principal_email="john@testfirm.com.au",
            principal_password="SecurePass123!",
            practitioner_number="123",  # Too short for NSW
            practitioner_state="nsw"
        )
        
        import asyncio
        with pytest.raises(ValueError, match="Invalid practitioner number"):
            asyncio.run(auth_service.register_firm(request, db_session))
    
    def test_authenticate_user_success(self, auth_service, sample_user, db_session):
        """Test successful user authentication"""
        from ..auth.schemas import LoginRequest
        
        request = LoginRequest(
            email=sample_user.email,
            password="TestPassword123!"
        )
        
        import asyncio
        user, requires_mfa = asyncio.run(auth_service.authenticate_user(request, db_session))
        
        assert user.id == sample_user.id
        assert requires_mfa is False
        assert sample_user.last_login is not None
        assert sample_user.failed_login_attempts == 0
    
    def test_authenticate_user_wrong_password(self, auth_service, sample_user, db_session):
        """Test authentication with wrong password"""
        from ..auth.schemas import LoginRequest
        
        request = LoginRequest(
            email=sample_user.email,
            password="WrongPassword"
        )
        
        import asyncio
        with pytest.raises(ValueError, match="Invalid email or password"):
            asyncio.run(auth_service.authenticate_user(request, db_session))
        
        # Refresh user to check failed attempts
        db_session.refresh(sample_user)
        assert sample_user.failed_login_attempts == 1
    
    def test_authenticate_user_account_locked(self, auth_service, sample_user, db_session):
        """Test authentication with locked account"""
        from ..auth.schemas import LoginRequest
        
        # Lock the account
        sample_user.lock_account()
        db_session.commit()
        
        request = LoginRequest(
            email=sample_user.email,
            password="TestPassword123!"
        )
        
        import asyncio
        with pytest.raises(ValueError, match="Account is locked"):
            asyncio.run(auth_service.authenticate_user(request, db_session))
    
    def test_authenticate_user_with_mfa(self, auth_service, sample_user, db_session):
        """Test authentication with MFA enabled"""
        from ..auth.schemas import LoginRequest
        
        # Enable MFA for user
        sample_user.setup_mfa()
        sample_user.mfa_enabled = True
        db_session.commit()
        
        # First request without MFA code
        request = LoginRequest(
            email=sample_user.email,
            password="TestPassword123!"
        )
        
        import asyncio
        user, requires_mfa = asyncio.run(auth_service.authenticate_user(request, db_session))
        
        assert user.id == sample_user.id
        assert requires_mfa is True
    
    def test_generate_access_token(self, auth_service, sample_user):
        """Test access token generation"""
        token_data = auth_service.generate_access_token(sample_user)
        
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["user_id"] == str(sample_user.id)
        assert token_data["firm_id"] == str(sample_user.firm_id)
        assert token_data["role"] == sample_user.role.value
        assert "expires_in" in token_data
    
    def test_setup_mfa(self, auth_service, sample_user, db_session):
        """Test MFA setup"""
        import asyncio
        mfa_data = asyncio.run(auth_service.setup_mfa(sample_user, db_session))
        
        assert "qr_code" in mfa_data
        assert "backup_codes" in mfa_data
        assert "secret" in mfa_data
        assert mfa_data["qr_code"].startswith("data:image/png;base64,")
        assert len(mfa_data["backup_codes"]) == 10
        
        # Check user was updated
        db_session.refresh(sample_user)
        assert sample_user.mfa_enabled is True
        assert sample_user.mfa_secret is not None
    
    def test_change_password_success(self, auth_service, sample_user, db_session):
        """Test successful password change"""
        original_hash = sample_user.password_hash
        
        import asyncio
        result = asyncio.run(auth_service.change_password(
            sample_user, 
            "TestPassword123!", 
            "NewPassword123!", 
            db_session
        ))
        
        assert result is True
        db_session.refresh(sample_user)
        assert sample_user.password_hash != original_hash
        assert sample_user.verify_password("NewPassword123!") is True
        assert sample_user.verify_password("TestPassword123!") is False
    
    def test_change_password_wrong_current(self, auth_service, sample_user, db_session):
        """Test password change with wrong current password"""
        import asyncio
        with pytest.raises(ValueError, match="Current password is incorrect"):
            asyncio.run(auth_service.change_password(
                sample_user,
                "WrongPassword",
                "NewPassword123!",
                db_session
            ))

class TestAuthEndpoints:
    """Test authentication API endpoints"""
    
    def test_register_firm_endpoint(self, db_session):
        """Test firm registration endpoint"""
        # Mock database dependency
        def override_get_db():
            try:
                yield db_session
            finally:
                pass
        
        app.dependency_overrides[f"{__name__.split('.')[0]}.database.get_db"] = override_get_db
        
        registration_data = {
            "firm_name": "API Test Firm",
            "abn": "98765432109",
            "phone": "(03) 9555-5678",
            "email": "admin@apitestfirm.com.au",
            "address": "456 API Street",
            "city": "Melbourne",
            "state": "vic",
            "postal_code": "3000",
            "principal_first_name": "Jane",
            "principal_last_name": "Admin",
            "principal_email": "jane@apitestfirm.com.au",
            "principal_password": "APITestPass123!",
            "practitioner_number": "1234567",  # Valid VIC format
            "practitioner_state": "vic"
        }
        
        response = client.post("/auth/register-firm", json=registration_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "firm_id" in data
        assert "principal_id" in data
        assert data["firm_name"] == "API Test Firm"
    
    def test_register_firm_invalid_data(self):
        """Test firm registration with invalid data"""
        invalid_data = {
            "firm_name": "Test Firm",
            "phone": "invalid-phone",
            "email": "invalid-email",
            "principal_first_name": "Test",
            "principal_last_name": "User",
            "principal_email": "invalid-email",
            "principal_password": "weak"  # Too weak password
        }
        
        response = client.post("/auth/register-firm", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_login_endpoint_success(self, sample_user, db_session):
        """Test successful login endpoint"""
        def override_get_db():
            try:
                yield db_session
            finally:
                pass
        
        app.dependency_overrides[f"{__name__.split('.')[0]}.database.get_db"] = override_get_db
        
        login_data = {
            "email": sample_user.email,
            "password": "TestPassword123!"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == str(sample_user.id)
        assert data["role"] == sample_user.role.value
    
    def test_login_endpoint_invalid_credentials(self, sample_user, db_session):
        """Test login with invalid credentials"""
        def override_get_db():
            try:
                yield db_session
            finally:
                pass
        
        app.dependency_overrides[f"{__name__.split('.')[0]}.database.get_db"] = override_get_db
        
        login_data = {
            "email": sample_user.email,
            "password": "WrongPassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
    
    def test_get_current_user_info(self, sample_user, db_session):
        """Test getting current user information"""
        def override_get_db():
            try:
                yield db_session
            finally:
                pass
        
        # Mock current user dependency
        def override_get_current_user():
            return sample_user
        
        app.dependency_overrides[f"{__name__.split('.')[0]}.database.get_db"] = override_get_db
        app.dependency_overrides[f"{__name__.split('.')[0]}.auth.dependencies.get_current_active_user"] = override_get_current_user
        
        response = client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user.email
        assert data["first_name"] == sample_user.first_name
        assert data["role"] == sample_user.role.value
    
    def test_practitioner_requirements_endpoint(self):
        """Test practitioner requirements endpoint"""
        response = client.get("/auth/practitioner-requirements")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have all Australian states
        expected_states = ['nsw', 'vic', 'qld', 'wa', 'sa', 'tas', 'act', 'nt']
        assert set(data.keys()) == set(expected_states)
        
        # Each state should have required fields
        for state, info in data.items():
            assert 'description' in info
            assert 'example' in info
            assert 'pattern' in info
    
    def test_unauthorized_access(self):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_health_check_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code in [200, 503]  # May fail if no real DB
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data
    
    def teardown_method(self):
        """Clean up dependency overrides after each test"""
        app.dependency_overrides.clear()