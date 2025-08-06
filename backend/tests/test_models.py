"""
Unit tests for SQLAlchemy models
"""

import pytest
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError
from ..models import LawFirm, User, Case, Document, FinancialInformation, ChildrenInformation
from ..models.enums import (
    UserRole, AustralianState, SubscriptionTier, ComplianceStatus,
    CaseStatus, CasePriority, AustralianFamilyCaseType, CourtSystem,
    DocumentType, ProcessingStatus, PartyType
)

class TestLawFirm:
    """Test LawFirm model"""
    
    def test_create_law_firm(self, db_session):
        """Test creating a law firm"""
        firm = LawFirm(
            name="Smith & Associates",
            abn="12345678901",
            phone="(02) 9555-1234",
            email="admin@smithassociates.com.au",
            address="Level 15, 123 Collins Street",
            city="Melbourne",
            state=AustralianState.VIC,
            postal_code="3000"
        )
        
        db_session.add(firm)
        db_session.commit()
        
        assert firm.id is not None
        assert firm.name == "Smith & Associates"
        assert firm.subscription_tier == SubscriptionTier.PROFESSIONAL
        assert firm.max_users == 15
        assert firm.is_active is True
        assert firm.compliance_status == ComplianceStatus.PENDING
    
    def test_abn_validation(self, db_session):
        """Test ABN validation"""
        # Valid ABN
        firm = LawFirm(
            name="Test Firm",
            abn="12345678901",
            phone="0400000000",
            email="test@example.com"
        )
        db_session.add(firm)
        db_session.commit()
        
        # Invalid ABN (not 11 digits)
        with pytest.raises(ValueError, match="ABN must be 11 digits"):
            invalid_firm = LawFirm(
                name="Invalid Firm",
                abn="123456789",  # Only 9 digits
                phone="0400000000",
                email="invalid@example.com"
            )
            db_session.add(invalid_firm)
            db_session.commit()
    
    def test_email_validation(self, db_session):
        """Test email validation"""
        with pytest.raises(ValueError, match="Invalid email format"):
            firm = LawFirm(
                name="Test Firm",
                phone="0400000000",
                email="invalid-email"  # Invalid format
            )
            db_session.add(firm)
            db_session.commit()
    
    def test_user_limit_methods(self, sample_firm, db_session):
        """Test user limit tracking methods"""
        # Initially no users
        assert sample_firm.get_user_count() == 0
        assert sample_firm.can_add_user() is True
        
        # Add users up to limit
        for i in range(sample_firm.max_users):
            user = User(
                firm_id=sample_firm.id,
                email=f"user{i}@example.com",
                first_name="Test",
                last_name=f"User{i}",
                role=UserRole.LAWYER
            )
            user.set_password("TestPass123!")
            db_session.add(user)
        
        db_session.commit()
        db_session.refresh(sample_firm)
        
        assert sample_firm.get_user_count() == sample_firm.max_users
        assert sample_firm.can_add_user() is False

class TestUser:
    """Test User model"""
    
    def test_create_user(self, sample_firm, db_session):
        """Test creating a user"""
        user = User(
            firm_id=sample_firm.id,
            email="lawyer@example.com",
            first_name="Jane",
            last_name="Doe",
            role=UserRole.LAWYER,
            practitioner_number="87654321",
            practitioner_state=AustralianState.NSW
        )
        user.set_password("SecurePass123!")
        
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == "lawyer@example.com"
        assert user.role == UserRole.LAWYER
        assert user.is_active is True
        assert user.mfa_enabled is False
        assert user.failed_login_attempts == 0
        assert user.get_full_name() == "Jane Doe"
    
    def test_password_hashing(self, sample_user):
        """Test password hashing and verification"""
        password = "TestPassword123!"
        
        # Password should be hashed, not stored in plain text
        assert sample_user.password_hash != password
        assert len(sample_user.password_hash) > 50  # PBKDF2 hash is long
        
        # Should verify correct password
        assert sample_user.verify_password(password) is True
        
        # Should reject incorrect password
        assert sample_user.verify_password("WrongPassword") is False
    
    def test_email_validation(self, sample_firm, db_session):
        """Test email validation and normalization"""
        user = User(
            firm_id=sample_firm.id,
            email="TEST@EXAMPLE.COM",  # Uppercase
            first_name="Test",
            last_name="User",
            role=UserRole.LAWYER
        )
        user.set_password("TestPass123!")
        
        db_session.add(user)
        db_session.commit()
        
        # Email should be normalized to lowercase
        assert user.email == "test@example.com"
    
    def test_practitioner_number_validation(self, sample_firm, db_session):
        """Test practitioner number validation"""
        user = User(
            firm_id=sample_firm.id,
            email="lawyer@example.com",
            first_name="Test",
            last_name="Lawyer",
            role=UserRole.LAWYER,
            practitioner_number="abc123",  # Mixed case
            practitioner_state=AustralianState.NSW
        )
        user.set_password("TestPass123!")
        
        db_session.add(user)
        db_session.commit()
        
        # Should be normalized to uppercase
        assert user.practitioner_number == "ABC123"
    
    def test_mfa_setup(self, sample_user, db_session):
        """Test MFA setup"""
        # Setup MFA
        qr_data = sample_user.setup_mfa()
        
        assert sample_user.mfa_secret is not None
        assert len(sample_user.mfa_secret) == 32  # Base32 encoded
        assert sample_user.mfa_backup_codes is not None
        assert len(sample_user.mfa_backup_codes) == 10
        assert qr_data.startswith("otpauth://totp/")
    
    def test_account_locking(self, sample_user, db_session):
        """Test account locking mechanism"""
        # Initially not locked
        assert sample_user.is_account_locked() is False
        
        # Record failed login attempts
        for i in range(4):
            sample_user.record_failed_login()
            assert sample_user.is_account_locked() is False
        
        # 5th failed attempt should lock account
        sample_user.record_failed_login()
        db_session.commit()
        
        assert sample_user.is_account_locked() is True
        assert sample_user.failed_login_attempts == 0  # Reset after locking
        
        # Unlock account
        sample_user.unlock_account()
        db_session.commit()
        
        assert sample_user.is_account_locked() is False
    
    def test_permissions(self, db_session, sample_firm):
        """Test role-based permissions"""
        # Create users with different roles
        principal = User(
            firm_id=sample_firm.id,
            email="principal@example.com",
            first_name="Principal",
            last_name="User",
            role=UserRole.PRINCIPAL
        )
        
        lawyer = User(
            firm_id=sample_firm.id,
            email="lawyer@example.com",
            first_name="Lawyer",
            last_name="User",
            role=UserRole.LAWYER
        )
        
        client = User(
            firm_id=sample_firm.id,
            email="client@example.com",
            first_name="Client",
            last_name="User",
            role=UserRole.CLIENT
        )
        
        # Principal has all permissions
        assert principal.has_permission("case.create") is True
        assert principal.has_permission("user.delete") is True
        
        # Lawyer has case permissions but not user management
        assert lawyer.has_permission("case.create") is True
        assert lawyer.has_permission("user.delete") is False
        
        # Client has limited permissions
        assert client.has_permission("case.read") is True
        assert client.has_permission("case.create") is False

class TestCase:
    """Test Case model"""
    
    def test_create_case(self, sample_user, db_session):
        """Test creating a case"""
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-001",
            case_type=AustralianFamilyCaseType.DIVORCE,
            title="Smith vs Smith - Divorce Proceedings",
            description="Uncontested divorce proceedings",
            created_by=sample_user.id,
            assigned_lawyer=sample_user.id,
            court_level=CourtSystem.FEDERAL_CIRCUIT_FAMILY_COURT,
            estimated_value=50000.00
        )
        
        db_session.add(case)
        db_session.commit()
        
        assert case.id is not None
        assert case.case_number == "FAM-2024-001"
        assert case.case_type == AustralianFamilyCaseType.DIVORCE
        assert case.status == CaseStatus.ACTIVE
        assert case.priority == CasePriority.MEDIUM
    
    def test_case_number_validation(self, sample_user, db_session):
        """Test case number validation"""
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="fam-2024-001",  # Lowercase
            case_type=AustralianFamilyCaseType.DIVORCE,
            title="Test Case",
            created_by=sample_user.id
        )
        
        db_session.add(case)
        db_session.commit()
        
        # Should be normalized to uppercase
        assert case.case_number == "FAM-2024-001"
    
    def test_compliance_checklist(self, sample_user, db_session):
        """Test compliance checklist functionality"""
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-002",
            case_type=AustralianFamilyCaseType.PROPERTY_SETTLEMENT,
            title="Property Settlement Case",
            created_by=sample_user.id
        )
        
        db_session.add(case)
        db_session.commit()
        
        # Initially no checklist items
        assert case.get_compliance_progress() == 0
        
        # Add checklist items
        case.update_compliance_checklist("financial_disclosure", True)
        case.update_compliance_checklist("property_valuation", False)
        
        # 50% completion (1 of 2 items completed)
        assert case.get_compliance_progress() == 50.0

class TestDocument:
    """Test Document model"""
    
    def test_create_document(self, sample_user, db_session):
        """Test creating a document"""
        # Create a case first
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-003",
            case_type=AustralianFamilyCaseType.CHILD_CUSTODY,
            title="Child Custody Case",
            created_by=sample_user.id
        )
        db_session.add(case)
        db_session.commit()
        
        # Create document
        file_content = b"Test document content"
        document = Document(
            firm_id=sample_user.firm_id,
            case_id=case.id,
            filename="test_document.pdf",
            original_filename="test_document.pdf",
            file_size=len(file_content),
            mime_type="application/pdf",
            file_hash=Document.calculate_file_hash(file_content),
            storage_path="/documents/test_document.pdf",
            document_type=DocumentType.AFFIDAVIT,
            uploaded_by=sample_user.id
        )
        
        db_session.add(document)
        db_session.commit()
        
        assert document.id is not None
        assert document.processing_status == ProcessingStatus.PENDING
        assert document.is_confidential is True
        assert document.version == 1
    
    def test_file_hash_calculation(self):
        """Test file hash calculation"""
        content1 = b"Test content"
        content2 = b"Different content"
        
        hash1 = Document.calculate_file_hash(content1)
        hash2 = Document.calculate_file_hash(content2)
        
        assert len(hash1) == 64  # SHA-256 hex digest
        assert len(hash2) == 64
        assert hash1 != hash2
        
        # Same content should produce same hash
        hash1_repeat = Document.calculate_file_hash(content1)
        assert hash1 == hash1_repeat
    
    def test_document_versioning(self, sample_user, db_session):
        """Test document versioning"""
        # Create original document
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-004",
            case_type=AustralianFamilyCaseType.DIVORCE,
            title="Divorce Case",
            created_by=sample_user.id
        )
        db_session.add(case)
        db_session.commit()
        
        original_content = b"Original document content"
        original_doc = Document(
            firm_id=sample_user.firm_id,
            case_id=case.id,
            filename="contract_v1.pdf",
            original_filename="contract.pdf",
            file_size=len(original_content),
            mime_type="application/pdf",
            file_hash=Document.calculate_file_hash(original_content),
            storage_path="/documents/contract_v1.pdf",
            document_type=DocumentType.CONTRACT,
            uploaded_by=sample_user.id
        )
        
        db_session.add(original_doc)
        db_session.commit()
        
        # Create new version
        new_content = b"Updated document content"
        new_version = original_doc.create_new_version(
            new_content,
            "contract_v2.pdf",
            str(sample_user.id)
        )
        
        assert new_version.version == 2
        assert new_version.parent_document_id == original_doc.id
        assert new_version.file_hash != original_doc.file_hash

class TestFinancialInformation:
    """Test FinancialInformation model"""
    
    def test_create_financial_info(self, sample_user, db_session):
        """Test creating financial information"""
        # Create case first
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-005",
            case_type=AustralianFamilyCaseType.PROPERTY_SETTLEMENT,
            title="Property Settlement",
            created_by=sample_user.id
        )
        db_session.add(case)
        db_session.commit()
        
        # Create financial information
        financial_info = FinancialInformation(
            case_id=case.id,
            party_type=PartyType.APPLICANT,
            real_estate=[
                {"property": "Family Home", "value": 800000},
                {"property": "Investment Property", "value": 500000}
            ],
            bank_accounts=[
                {"bank": "Commonwealth Bank", "balance": 50000}
            ],
            debts_liabilities=[
                {"creditor": "Home Loan", "amount": 400000}
            ]
        )
        
        db_session.add(financial_info)
        db_session.commit()
        
        assert financial_info.id is not None
        assert financial_info.party_type == PartyType.APPLICANT
        assert len(financial_info.real_estate) == 2
        assert len(financial_info.bank_accounts) == 1
    
    def test_calculate_totals(self, sample_user, db_session):
        """Test financial totals calculation"""
        # Create case
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-006",
            case_type=AustralianFamilyCaseType.PROPERTY_SETTLEMENT,
            title="Property Settlement",
            created_by=sample_user.id
        )
        db_session.add(case)
        db_session.commit()
        
        # Create financial info with known values
        financial_info = FinancialInformation(
            case_id=case.id,
            party_type=PartyType.APPLICANT,
            real_estate=[{"property": "Home", "value": 500000}],
            bank_accounts=[{"account": "Savings", "value": 50000}],
            debts_liabilities=[{"debt": "Mortgage", "amount": 300000}]
        )
        
        financial_info.calculate_totals()
        
        assert financial_info.total_assets == 550000
        assert financial_info.total_liabilities == 300000
        assert financial_info.net_worth == 250000

class TestChildrenInformation:
    """Test ChildrenInformation model"""
    
    def test_create_children_info(self, sample_user, db_session):
        """Test creating children information"""
        # Create case
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-007",
            case_type=AustralianFamilyCaseType.CHILD_CUSTODY,
            title="Child Custody Case",
            created_by=sample_user.id
        )
        db_session.add(case)
        db_session.commit()
        
        # Create child information
        child_info = ChildrenInformation(
            case_id=case.id,
            first_name="Emma",
            last_name="Smith",
            date_of_birth=date(2015, 5, 15),  # 8-9 years old
            school_name="Primary School",
            school_year="Year 3",
            special_needs=False
        )
        
        db_session.add(child_info)
        db_session.commit()
        
        assert child_info.id is not None
        assert child_info.get_full_name() == "Emma Smith"
        assert child_info.is_school_age() is True
        assert 8 <= child_info.get_age() <= 9  # Age calculation
    
    def test_age_calculation(self, sample_user, db_session):
        """Test age calculation"""
        case = Case(
            firm_id=sample_user.firm_id,
            case_number="FAM-2024-008",
            case_type=AustralianFamilyCaseType.CHILD_CUSTODY,
            title="Child Custody Case",
            created_by=sample_user.id
        )
        db_session.add(case)
        db_session.commit()
        
        # Create child born 10 years ago
        ten_years_ago = date(date.today().year - 10, 1, 1)
        child_info = ChildrenInformation(
            case_id=case.id,
            first_name="Test",
            last_name="Child",
            date_of_birth=ten_years_ago
        )
        
        # Age should be approximately 10
        age = child_info.get_age()
        assert 9 <= age <= 10  # Account for date variations