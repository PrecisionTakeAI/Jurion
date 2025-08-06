#!/usr/bin/env python3
"""
Database initialization script for LegalLLM Professional
Creates tables, indexes, and initial data for Australian Family Law
"""

import os
import sys
import logging
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import db_manager, init_database, create_tables, test_connection
from shared.database.models import (
    LawFirm, User, Case, Document, AIInteraction, AUFamilyLawRequirements,
    WorkflowTemplate, user_role_enum, au_family_case_type
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment() -> bool:
    """Check if required environment variables are set"""
    # Railway PostgreSQL provides these variables
    railway_db_vars = ['PGHOST', 'PGDATABASE', 'PGUSER', 'PGPASSWORD']
    standard_vars = ['DATABASE_URL']
    custom_vars = ['DB_HOST', 'DB_NAME', 'DB_USER']
    
    # Check for DATABASE_URL first
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        logger.info("Found DATABASE_URL environment variable")
        # Log the connection details without password
        import re
        safe_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', database_url)
        logger.info(f"Database URL: {safe_url}")
        return True
    
    # Check for Railway PostgreSQL variables
    railway_vars_present = all(os.getenv(var) for var in railway_db_vars)
    if railway_vars_present:
        logger.info("Found Railway PostgreSQL environment variables")
        # Create DATABASE_URL from Railway variables
        pghost = os.getenv('PGHOST')
        pgdatabase = os.getenv('PGDATABASE')
        pguser = os.getenv('PGUSER')
        pgpassword = os.getenv('PGPASSWORD')
        pgport = os.getenv('PGPORT', '5432')
        
        database_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
        os.environ['DATABASE_URL'] = database_url
        logger.info(f"Created DATABASE_URL from Railway variables: postgresql://{pguser}:***@{pghost}:{pgport}/{pgdatabase}")
        return True
    
    # Check for custom variables
    custom_vars_present = all(os.getenv(var) for var in custom_vars)
    if custom_vars_present:
        logger.info("Found custom database environment variables")
        return True
    
    # Print all available environment variables for debugging
    logger.error("No suitable database environment variables found")
    logger.info("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if any(db_term in key.lower() for db_term in ['database', 'db', 'pg', 'postgres', 'sql']):
            value = os.environ[key]
            if 'password' in key.lower() or 'pass' in key.lower():
                value = '***'
            logger.info(f"  {key} = {value}")
    
    logger.error("Please ensure PostgreSQL service is connected in Railway dashboard")
    return False


def create_sample_workflow_templates():
    """Create sample workflow templates for Australian family law"""
    try:
        with db_manager.get_session() as session:
            # Check if templates already exist
            existing = session.query(WorkflowTemplate).count()
            if existing > 0:
                logger.info(f"Found {existing} existing workflow templates, skipping creation")
                return
            
            templates = [
                {
                    'name': 'Standard Divorce Proceedings',
                    'case_type': 'divorce',
                    'description': 'Standard workflow for uncontested divorce proceedings',
                    'estimated_duration_days': 90,
                    'steps': [
                        {'step': 1, 'name': 'Initial consultation', 'description': 'Meet with client to gather information'},
                        {'step': 2, 'name': 'Prepare divorce application', 'description': 'Draft and review divorce application'},
                        {'step': 3, 'name': 'File with court', 'description': 'Submit application to Federal Circuit Court'},
                        {'step': 4, 'name': 'Serve respondent', 'description': 'Serve divorce papers on respondent'},
                        {'step': 5, 'name': 'Wait for response', 'description': '28-day waiting period for response'},
                        {'step': 6, 'name': 'Court hearing', 'description': 'Attend court hearing if required'},
                        {'step': 7, 'name': 'Divorce order', 'description': 'Obtain final divorce order'}
                    ],
                    'relevant_legislation': [
                        'Family Law Act 1975 (Cth)',
                        'Federal Circuit Court Rules 2021'
                    ],
                    'required_forms': ['Application for Divorce']
                },
                {
                    'name': 'Property Settlement - Simple',
                    'case_type': 'property_settlement',
                    'description': 'Property settlement for cases with assets under $500k',
                    'estimated_duration_days': 120,
                    'steps': [
                        {'step': 1, 'name': 'Asset identification', 'description': 'Identify and value all assets and liabilities'},
                        {'step': 2, 'name': 'Financial disclosure', 'description': 'Complete Form 13 and Form 13A'},
                        {'step': 3, 'name': 'Negotiate settlement', 'description': 'Negotiate property split with other party'},
                        {'step': 4, 'name': 'Draft consent orders', 'description': 'Prepare consent orders for court approval'},
                        {'step': 5, 'name': 'File with court', 'description': 'Submit consent orders to court'},
                        {'step': 6, 'name': 'Court approval', 'description': 'Obtain court approval of settlement'}
                    ],
                    'relevant_legislation': [
                        'Family Law Act 1975 (Cth) Part VIIIAA',
                        'Family Law Regulations 1984'
                    ],
                    'required_forms': ['Form 13', 'Form 13A', 'Consent Orders']
                },
                {
                    'name': 'Parenting Orders Application',
                    'case_type': 'parenting_orders',
                    'description': 'Application for parenting orders involving children',
                    'estimated_duration_days': 150,
                    'steps': [
                        {'step': 1, 'name': 'Section 60I certificate', 'description': 'Attend family dispute resolution or obtain exemption'},
                        {'step': 2, 'name': 'Best interests assessment', 'description': 'Assess best interests of children'},
                        {'step': 3, 'name': 'Prepare application', 'description': 'Draft parenting orders application'},
                        {'step': 4, 'name': 'File with court', 'description': 'Submit application to Family Court'},
                        {'step': 5, 'name': 'Family report', 'description': 'Court may order family report'},
                        {'step': 6, 'name': 'Conciliation conference', 'description': 'Attend court-ordered conciliation'},
                        {'step': 7, 'name': 'Final hearing', 'description': 'Final court hearing if no agreement reached'}
                    ],
                    'relevant_legislation': [
                        'Family Law Act 1975 (Cth) Part VII',
                        'Family Law Act 1975 (Cth) s 60I'
                    ],
                    'required_forms': ['Application for Parenting Orders', 'Section 60I Certificate']
                }
            ]
            
            for template_data in templates:
                template = WorkflowTemplate(**template_data)
                session.add(template)
            
            session.commit()
            logger.info(f"Created {len(templates)} workflow templates")
            
    except Exception as e:
        logger.error(f"Failed to create workflow templates: {e}")
        raise


def create_sample_law_firm():
    """Create a sample law firm for testing"""
    try:
        with db_manager.get_session() as session:
            # Check if sample firm already exists
            existing_firm = session.query(LawFirm).filter_by(name="Sample Family Law Firm").first()
            if existing_firm:
                logger.info("Sample law firm already exists")
                return existing_firm
            
            # Create sample law firm
            sample_firm = LawFirm(
                name="Sample Family Law Firm",
                abn="12345678901",
                address={
                    "street": "123 Collins Street",
                    "city": "Melbourne",
                    "state": "VIC",
                    "postcode": "3000",
                    "country": "Australia"
                },
                subscription_tier="professional",
                settings={
                    "default_jurisdiction": "australia",
                    "practice_areas": ["family_law"],
                    "court_locations": ["Melbourne", "Sydney"]
                }
            )
            
            session.add(sample_firm)
            session.commit()
            logger.info("Created sample law firm")
            return sample_firm
            
    except Exception as e:
        logger.error(f"Failed to create sample law firm: {e}")
        raise


def create_sample_users(firm: LawFirm):
    """Create sample users for the law firm"""
    try:
        with db_manager.get_session() as session:
            # Check if users already exist
            existing_users = session.query(User).filter_by(firm_id=firm.id).count()
            if existing_users > 0:
                logger.info(f"Found {existing_users} existing users for firm")
                return
            
            # Create sample users
            users = [
                {
                    'email': 'principal@samplelaw.com.au',
                    'password_hash': 'hashed_password_here',  # In real use, properly hash passwords
                    'first_name': 'Sarah',
                    'last_name': 'Johnson',
                    'role': 'principal',
                    'australian_lawyer_number': 'NSW12345'
                },
                {
                    'email': 'senior@samplelaw.com.au',
                    'password_hash': 'hashed_password_here',
                    'first_name': 'Michael',
                    'last_name': 'Chen',
                    'role': 'senior_lawyer',
                    'australian_lawyer_number': 'VIC67890'
                },
                {
                    'email': 'lawyer@samplelaw.com.au',
                    'password_hash': 'hashed_password_here',
                    'first_name': 'Emma',
                    'last_name': 'Williams',
                    'role': 'lawyer',
                    'australian_lawyer_number': 'QLD11111'
                },
                {
                    'email': 'paralegal@samplelaw.com.au',
                    'password_hash': 'hashed_password_here',
                    'first_name': 'James',
                    'last_name': 'Brown',
                    'role': 'paralegal'
                }
            ]
            
            for user_data in users:
                user_data['firm_id'] = firm.id
                user = User(**user_data)
                session.add(user)
            
            session.commit()
            logger.info(f"Created {len(users)} sample users")
            
    except Exception as e:
        logger.error(f"Failed to create sample users: {e}")
        raise


def main():
    """Main initialization function"""
    logger.info("Starting database initialization...")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    try:
        # Initialize database connection
        logger.info("Initializing database connection...")
        init_database()
        
        # Test connection with retry for Railway networking
        max_retries = 3
        for attempt in range(max_retries):
            if test_connection():
                logger.info("Database connection successful")
                break
            elif attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed, retrying...")
                import time
                time.sleep(2)
            else:
                logger.error("Database connection test failed after multiple attempts")
                logger.error("This might be due to:")
                logger.error("1. PostgreSQL service not connected in Railway dashboard")
                logger.error("2. Network connectivity issues")
                logger.error("3. Database credentials incorrect")
                logger.info("Application will continue without database features")
                return  # Don't exit, just return to allow app to continue
        
        # Create all tables and indexes
        logger.info("Creating database tables and indexes...")
        create_tables()
        
        # Create sample data
        logger.info("Creating sample data...")
        sample_firm = create_sample_law_firm()
        create_sample_users(sample_firm)
        create_sample_workflow_templates()
        
        logger.info("Database initialization completed successfully!")
        logger.info(f"Sample law firm created: {sample_firm.name}")
        logger.info("You can now start the application")
        
    except SQLAlchemyError as e:
        logger.error(f"Database error during initialization: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}")
        sys.exit(1)
    finally:
        # Clean up connections
        db_manager.close_connections()


if __name__ == "__main__":
    main()