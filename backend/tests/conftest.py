"""
Pytest configuration and fixtures
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os

from ..models.base import Base
from ..models import LawFirm, User
from ..models.enums import UserRole, AustralianState, SubscriptionTier
from ..database import get_db

# Test database URL (SQLite in-memory for speed)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(engine):
    """Create database session for each test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        
        # Clean up all tables for next test
        for table in reversed(Base.metadata.sorted_tables):
            engine.execute(table.delete())

@pytest.fixture
def sample_firm(db_session):
    """Create a sample law firm for testing"""
    firm = LawFirm(
        name="Test Legal Firm",
        abn="12345678901",
        phone="(02) 9555-1234",
        email="test@testfirm.com.au",
        address="123 Test Street",
        city="Sydney",
        state=AustralianState.NSW,
        postal_code="2000",
        subscription_tier=SubscriptionTier.PROFESSIONAL,
        principal_practitioner_number="12345678",
        practitioner_state=AustralianState.NSW
    )
    db_session.add(firm)
    db_session.commit()
    db_session.refresh(firm)
    return firm

@pytest.fixture
def sample_user(db_session, sample_firm):
    """Create a sample user for testing"""
    user = User(
        firm_id=sample_firm.id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.LAWYER,
        practitioner_number="87654321",
        practitioner_state=AustralianState.NSW
    )
    user.set_password("TestPassword123!")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def principal_user(db_session, sample_firm):
    """Create a principal user for testing"""
    user = User(
        firm_id=sample_firm.id,
        email="principal@example.com",
        first_name="Principal",
        last_name="User",
        role=UserRole.PRINCIPAL,
        practitioner_number="11111111",
        practitioner_state=AustralianState.NSW
    )
    user.set_password("PrincipalPass123!")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user