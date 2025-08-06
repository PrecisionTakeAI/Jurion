"""
Database configuration and connection setup for LegalLLM Professional
Multi-tenant PostgreSQL with connection pooling and security
Includes automatic migration checking and schema validation
"""

import os
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, MetaData, text, inspect
from sqlalchemy.engine import Engine, Inspector
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager, asynccontextmanager
import logging
import time
from dataclasses import dataclass

# Try to import async components with graceful fallback
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    import asyncio
    import asyncpg
    ASYNC_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("Async database components available")
except ImportError as e:
    ASYNC_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Async database components not available: {e}")
    logger.info("Database will operate in sync-only mode")

from .models import Base

@dataclass
class DatabasePerformanceMetrics:
    """Performance metrics for database operations"""
    active_connections: int
    idle_connections: int
    total_connections: int
    pool_size: int
    max_overflow: int
    query_count: int
    average_query_time: float
    connection_errors: int
    health_status: bool

logger = logging.getLogger(__name__)

# Performance optimization: Startup caching
_startup_cache = {}
_is_production = os.getenv('ENVIRONMENT', '').lower() == 'production'
_skip_verbose_logging = os.getenv('SKIP_VERBOSE_LOGGING', '').lower() == 'true' or _is_production

class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        # Get database URL with validation
        self.database_url = os.getenv('DATABASE_URL', '').strip()
        
        # Handle Railway's DATABASE_URL format
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
            logger.info("Converted postgres:// to postgresql:// for SQLAlchemy compatibility")
        
        if not self.database_url:
            logger.error("DATABASE_URL environment variable not set!")
            raise ValueError("DATABASE_URL must be set")
        
        # Mask password in logs
        masked_url = self._mask_password(self.database_url)
        logger.info(f"Database URL configured: {masked_url}")
        
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '20'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '30'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        self.echo = os.getenv('DB_ECHO', 'False').lower() == 'true'
    
    def _mask_password(self, url: str) -> str:
        """Mask password in database URL for logging"""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)
    
    def _get_database_url(self) -> str:
        """Get database URL from environment variables with multiple fallbacks"""
        
        # Option 1: Full DATABASE_URL (Railway/Heroku style)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # Handle Railway's postgres:// vs postgresql:// issue
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            # RAILWAY FIX: Replace internal hostname with external if detected
            if 'postgres.railway.internal' in database_url:
                logger.warning("🚨 RAILWAY FIX: Detected internal hostname 'postgres.railway.internal'")
                logger.warning("🔧 This will cause connection failures. Please update DATABASE_URL with external hostname.")
                logger.warning("📖 Run 'python fix_railway_database_url.py' for detailed instructions")
                
                # Try to find external URL from other environment variables
                external_url = (os.getenv('DATABASE_EXTERNAL_URL') or 
                              os.getenv('DATABASE_PUBLIC_URL') or 
                              os.getenv('POSTGRES_URL'))
                
                if external_url and '.railway.app' in external_url:
                    logger.info("✅ Found external Railway URL, using that instead")
                    database_url = external_url
                    if database_url.startswith('postgres://'):
                        database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            return database_url
        
        # Option 2: Individual connection parameters
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'legal_llm_db')
        username = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', '')
        
        if password:
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{username}@{host}:{port}/{database}"


class DatabaseManager:
    """Enhanced database manager with async support and performance monitoring"""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.engine: Optional[Engine] = None
        self.async_engine = None
        self.SessionLocal: Optional[sessionmaker] = None
        self.AsyncSessionLocal = None
        self.scoped_session_factory: Optional[scoped_session] = None
        self.migration_applied = False
        self._async_available = ASYNC_AVAILABLE
        self._initialized = False
        
        # Performance tracking
        self.query_count = 0
        self.total_query_time = 0.0
        self.connection_errors = 0
        self.last_health_check = 0
        self.health_check_interval = 60  # seconds
        
    def is_database_initialized(self) -> bool:
        """Quick check if database is already initialized (performance optimization)"""
        cache_key = f'db_initialized_{id(self)}'
        if cache_key in _startup_cache:
            logger.info("⚡ Using cached database initialization status")
            return _startup_cache[cache_key]
        
        try:
            if self.engine is None:
                _startup_cache[cache_key] = False
                return False
            
            # Quick connectivity test
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Cache successful initialization
            _startup_cache[cache_key] = True
            logger.info("✅ Database initialization status cached")
            return True
            
        except Exception as e:
            logger.warning(f"Database initialization check failed: {e}")
            _startup_cache[cache_key] = False
            return False
    
    def quick_table_exists_check(self) -> bool:
        """Fast check for required tables without full inspection"""
        cache_key = 'required_tables_exist'
        if cache_key in _startup_cache:
            return _startup_cache[cache_key]
        
        try:
            if not self.engine:
                return False
                
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('law_firms', 'users')
                """))
                required_count = result.scalar()
                
                exists = required_count >= 2
                _startup_cache[cache_key] = exists
                
                if exists:
                    logger.info("⚡ Required tables exist (cached)")
                else:
                    logger.info("📋 Required tables missing, will create")
                
                return exists
                
        except Exception as e:
            logger.warning(f"Quick table check failed: {e}")
            return False
    
    def initialize_database(self) -> None:
        """Initialize database engine and session factory with async support"""
        try:
            # Create sync engine with enhanced connection pooling
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=True,  # Validate connections before use
                echo=self.config.echo,
                # Security and performance settings
                connect_args={
                    "sslmode": os.getenv('DB_SSL_MODE', 'prefer'),
                    "application_name": "LegalLLM_Professional",
                }
            )
            
            # Create session factories
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Create scoped session for thread safety
            self.scoped_session_factory = scoped_session(self.SessionLocal)
            
            # Try to create async engine if async components are available
            if self._async_available:
                try:
                    async_url = self.config.database_url.replace('postgresql://', 'postgresql+asyncpg://')
                    self.async_engine = create_async_engine(
                        async_url,
                        poolclass=QueuePool,
                        pool_size=self.config.pool_size,
                        max_overflow=self.config.max_overflow,
                        pool_timeout=self.config.pool_timeout,
                        pool_recycle=self.config.pool_recycle,
                        pool_pre_ping=True,
                        echo=self.config.echo,
                        future=True,
                        connect_args={
                            "server_settings": {
                                "application_name": "LegalLLM_Professional_Async",
                                "jit": "off"  # Disable JIT for faster startup
                            }
                        }
                    )
                    
                    self.AsyncSessionLocal = async_sessionmaker(
                        bind=self.async_engine,
                        class_=AsyncSession,
                        expire_on_commit=False
                    )
                    logger.info("Database initialized successfully with async support")
                    
                except Exception as async_error:
                    logger.warning(f"Async database initialization failed: {async_error}")
                    logger.info("Falling back to sync-only database operations")
                    self._async_available = False
                    self.async_engine = None
                    self.AsyncSessionLocal = None
            else:
                logger.info("Database initialized successfully (sync-only mode)")
            
            # Mark as initialized
            self._initialized = True
            
        except Exception as e:
            self.connection_errors += 1
            self._initialized = False
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def check_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a specific column exists in a table"""
        if not self.engine:
            logger.error("Database engine not initialized")
            return False
        
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            column_names = [col['name'] for col in columns]
            exists = column_name in column_names
            
            logger.info(f"Column check: {table_name}.{column_name} exists = {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Error checking column {table_name}.{column_name}: {e}")
            return False
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        if not self.engine:
            logger.error("Database engine not initialized")
            return False
        
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            exists = table_name in tables
            
            logger.info(f"Table check: {table_name} exists = {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Error checking table {table_name}: {e}")
            return False
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get the current schema for a table"""
        if not self.engine:
            logger.error("Database engine not initialized")
            return {}
        
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            
            schema = {
                'table_name': table_name,
                'columns': {col['name']: {
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                    'default': col['default']
                } for col in columns}
            }
            
            logger.info(f"Retrieved schema for {table_name}: {len(columns)} columns")
            return schema
            
        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            return {}
    
    def apply_missing_columns_migration(self) -> bool:
        """Automatically apply migration for missing columns"""
        if not self.engine:
            logger.error("Database engine not initialized - cannot apply migration")
            return False
        
        if self.migration_applied:
            logger.info("Migration already applied in this session")
            return True
        
        try:
            logger.info("🔍 Checking for missing database columns...")
            
            # Check if law_firms table exists
            if not self.check_table_exists('law_firms'):
                logger.info("law_firms table doesn't exist yet - will be created normally")
                return True
            
            # Define required columns for law_firms table
            required_law_firm_columns = {
                'phone': 'VARCHAR(20)',
                'jurisdiction': 'VARCHAR(50) DEFAULT \'australia\''
            }
            
            # Check and add missing columns to law_firms
            migrations_needed = []
            
            for column_name, column_def in required_law_firm_columns.items():
                if not self.check_column_exists('law_firms', column_name):
                    migrations_needed.append(f"ALTER TABLE law_firms ADD COLUMN {column_name} {column_def}")
                    logger.info(f"📋 Missing column detected: law_firms.{column_name}")
            
            # Check users table if it exists
            if self.check_table_exists('users'):
                required_user_columns = {
                    'password_salt': 'VARCHAR(255) NOT NULL DEFAULT \'\'',
                    'name': 'VARCHAR(255) NOT NULL DEFAULT \'\'',
                    'practitioner_number': 'VARCHAR(50)',
                    'practitioner_jurisdiction': 'VARCHAR(10)',
                    'mfa_secret_pending': 'VARCHAR(255)'
                }
                
                for column_name, column_def in required_user_columns.items():
                    if not self.check_column_exists('users', column_name):
                        migrations_needed.append(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}")
                        logger.info(f"📋 Missing column detected: users.{column_name}")
            
            # Apply migrations if needed
            if migrations_needed:
                logger.info(f"🚀 Applying {len(migrations_needed)} automatic migrations...")
                
                with self.engine.begin() as conn:
                    for migration_sql in migrations_needed:
                        try:
                            logger.info(f"⚡ Executing: {migration_sql}")
                            conn.execute(text(migration_sql))
                            logger.info("✅ Migration executed successfully")
                        except Exception as e:
                            logger.error(f"❌ Migration failed: {migration_sql} - {e}")
                            # Continue with other migrations even if one fails
                            continue
                
                # Verify migrations
                verification_passed = True
                if 'law_firms' in [m for m in migrations_needed if 'law_firms' in m]:
                    for column_name in required_law_firm_columns.keys():
                        if not self.check_column_exists('law_firms', column_name):
                            logger.error(f"❌ Verification failed: law_firms.{column_name} still missing")
                            verification_passed = False
                
                if verification_passed:
                    logger.info("✅ All automatic migrations completed and verified successfully")
                    self.migration_applied = True
                else:
                    logger.warning("⚠️ Some migrations may have failed verification")
                
                return verification_passed
            else:
                logger.info("✅ All required columns present - no migration needed")
                self.migration_applied = True
                return True
                
        except Exception as e:
            logger.error(f"❌ Automatic migration failed: {e}")
            return False
    
    def log_database_schema(self):
        """Log current database schema for debugging (production-optimized)"""
        try:
            # Skip verbose logging in production unless explicitly enabled
            if _skip_verbose_logging:
                logger.info("✅ Database schema validated (verbose logging disabled)")
                return
            
            # Cache schema info to avoid repeated queries
            schema_cache_key = 'schema_logged'
            if schema_cache_key in _startup_cache:
                logger.info("⚡ Schema already logged (cached)")
                return
            
            if self.check_table_exists('law_firms'):
                schema = self.get_table_schema('law_firms')
                logger.info(f"📋 law_firms schema: {len(schema.get('columns', {}))} columns")
                if not _is_production:  # Only show details in development
                    for col_name, col_info in schema.get('columns', {}).items():
                        logger.info(f"   - {col_name}: {col_info['type']} {'NULL' if col_info['nullable'] else 'NOT NULL'}")
            
            if self.check_table_exists('users'):
                schema = self.get_table_schema('users')
                logger.info(f"📋 users schema: {len(schema.get('columns', {}))} columns")
                if not _is_production:  # Only show details in development
                    for col_name, col_info in schema.get('columns', {}).items():
                        logger.info(f"   - {col_name}: {col_info['type']} {'NULL' if col_info['nullable'] else 'NOT NULL'}")
            
            # Cache that we've logged schema
            _startup_cache[schema_cache_key] = True
                    
        except Exception as e:
            logger.error(f"Error logging database schema: {e}")
    
    def _create_enums_safely(self, conn, enum_types):
        """Create enum types with robust error handling and transaction management"""
        logger.info("🔧 Creating PostgreSQL ENUM types...")
        
        enum_names = [
            'user_role_enum', 'au_family_case_type', 'case_status_enum', 
            'document_category', 'document_subcategory'
        ]
        
        for i, (enum_name, enum_sql) in enumerate(zip(enum_names, enum_types)):
            try:
                # Check if enum already exists first
                check_sql = text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type 
                        WHERE typname = :enum_name
                    )
                """)
                
                result = conn.execute(check_sql, {"enum_name": enum_name})
                exists = result.scalar()
                
                if exists:
                    logger.info(f"✅ ENUM {enum_name} already exists, skipping")
                    continue
                
                # Create the enum in its own transaction
                trans = conn.begin()
                try:
                    conn.execute(text(enum_sql))
                    trans.commit()
                    logger.info(f"✅ Created ENUM {enum_name}")
                except Exception as create_error:
                    trans.rollback()
                    if "already exists" in str(create_error).lower():
                        logger.info(f"✅ ENUM {enum_name} already exists (concurrent creation)")
                    else:
                        logger.warning(f"⚠️ Could not create ENUM {enum_name}: {create_error}")
                        logger.info(f"📝 Will use VARCHAR fallback for {enum_name}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Error checking/creating ENUM {enum_name}: {e}")
                logger.info(f"📝 Will use VARCHAR fallback for {enum_name}")
    
    def create_optional_features(self) -> None:
        """Create optional database features with separate transaction handling"""
        if not self.engine:
            return
        
        # Skip optional features in production for faster startup
        if _is_production:
            logger.info("⚡ Skipping optional database features in production for performance")
            return
        
        logger.info("🔧 Creating optional database features...")
        
        # Full-text search index (separate transaction)
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_ocr_search 
                    USING gin(to_tsvector('english', ocr_text))
                """))
            logger.info("✅ Full-text search index created")
        except Exception as e:
            logger.warning(f"⚠️ Could not create full-text search index: {e}")
        
        # Materialized view (separate transaction)
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS case_summary_stats AS
                    SELECT 
                        firm_id,
                        case_type,
                        status,
                        COUNT(*) as case_count,
                        AVG(EXTRACT(days FROM (COALESCE(archived_at, NOW()) - created_at))) as avg_duration_days,
                        SUM(estimated_asset_pool) as total_asset_pool
                    FROM cases 
                    GROUP BY firm_id, case_type, status
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ON case_summary_stats(firm_id, case_type)"))
            logger.info("✅ Materialized view and indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Could not create materialized view: {e}")
    
    def create_all_tables(self) -> None:
        """Create all database tables and types with automatic migration checking (performance optimized)"""
        # Performance optimization: Check if already initialized
        if self.is_database_initialized() and self.quick_table_exists_check():
            logger.info("⚡ Database already initialized and tables exist - skipping creation")
            
            # Still run migration check in case of schema updates
            if not self.migration_applied:
                logger.info("🔍 Running migration check for existing database...")
                self.apply_missing_columns_migration()
            
            return
        
        # EMERGENCY BYPASS: Initialize engine if not already done
        if not self.engine:
            logger.info("🔧 Initializing database engine...")
            try:
                self.initialize_database()
            except Exception as e:
                logger.error(f"Emergency database initialization failed: {e}")
                return  # Don't crash, just skip table creation
        
        try:
            # First create custom ENUM types with robust error handling
            with self.engine.connect() as conn:
                # Enable UUID extensions
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                    logger.info("✅ PostgreSQL extensions enabled")
                except Exception as e:
                    logger.warning(f"Extension creation warning: {e}")
                
                # Create ENUM types with individual error handling
                enum_types = [
                    """CREATE TYPE user_role_enum AS ENUM (
                        'principal', 'senior_lawyer', 'lawyer', 'paralegal', 
                        'law_clerk', 'admin', 'client', 'read_only'
                    )""",
                    """CREATE TYPE au_family_case_type AS ENUM (
                        'divorce', 'property_settlement', 'child_custody', 'parenting_orders',
                        'spousal_maintenance', 'child_support', 'domestic_violence',
                        'adoption', 'surrogacy', 'defacto_separation', 'consent_orders'
                    )""",
                    """CREATE TYPE case_status_enum AS ENUM (
                        'initial_consultation', 'case_preparation', 'negotiation',
                        'mediation', 'court_proceedings', 'settlement', 'completed',
                        'on_hold', 'archived'
                    )""",
                    """CREATE TYPE document_category AS ENUM (
                        'court_documents', 'financial_documents', 'correspondence',
                        'affidavits', 'expert_reports', 'property_valuations',
                        'bank_statements', 'tax_returns', 'superannuation_statements',
                        'business_documents', 'parenting_plans', 'consent_orders',
                        'medical_reports', 'child_assessments', 'other'
                    )""",
                    """CREATE TYPE document_subcategory AS ENUM (
                        'application', 'response', 'reply', 'court_orders', 'judgment',
                        'subpoena', 'notice_to_produce', 'interim_orders',
                        'asset_statement', 'liability_statement', 'income_statement',
                        'form_13', 'form_13a', 'property_valuation', 'business_valuation',
                        'letter_to_court', 'letter_to_opposing_party', 'internal_memo',
                        'email_correspondence', 'file_note',
                        'contract', 'agreement', 'certificate', 'statutory_declaration'
                    )"""
                ]
                
                # Create each enum type with separate transactions to avoid transaction abort
                self._create_enums_safely(conn, enum_types)
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            # Apply automatic migrations for missing columns
            logger.info("🔍 Checking for missing columns and applying automatic migrations...")
            migration_success = self.apply_missing_columns_migration()
            if migration_success:
                logger.info("✅ Automatic migration check completed successfully")
            else:
                logger.warning("⚠️ Some automatic migrations may have failed - check logs")
            
            # Log current database schema for debugging
            self.log_database_schema()
            
            # Create optional database features (indexes, views) with separate transactions
            self.create_optional_features()
            
            logger.info("✅ All database tables and indexes created successfully")
            
            # Verify table creation and provide status
            with self.engine.connect() as conn:
                try:
                    result = conn.execute(text("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        ORDER BY table_name
                    """))
                    tables = [row[0] for row in result.fetchall()]
                    logger.info(f"📋 Created {len(tables)} database tables: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
                    
                    # Check if main tables exist for firm registration
                    required_tables = ['law_firms', 'users']
                    missing_tables = [table for table in required_tables if table not in tables]
                    
                    if missing_tables:
                        logger.warning(f"⚠️ Missing required tables: {missing_tables}")
                    else:
                        logger.info("🎯 FIRM REGISTRATION READY: All required tables created successfully")
                        
                except Exception as verify_error:
                    logger.warning(f"Could not verify table creation: {verify_error}")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Get a database session with automatic cleanup"""
        # Check if database is initialized
        if not self._initialized:
            logger.error("Database not initialized - calling initialize_database()")
            try:
                self.initialize_database()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise RuntimeError("Could not initialize database session")
        
        if not self.SessionLocal:
            logger.error("SessionLocal is None - database not properly initialized")
            raise Exception("Database not initialized")
        
        session = None
        try:
            session = self.SessionLocal()
            # Test the connection
            session.execute(text("SELECT 1"))
            yield session
            session.commit()
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            if session:
                session.close()
    
    def get_session_direct(self):
        """Get database session directly with proper error handling"""
        if not self._initialized:
            logger.error("Database not initialized - calling initialize_database()")
            self.initialize_database()
            self._initialized = True
        
        if not self.SessionLocal:
            logger.error("SessionLocal is None - database not properly initialized")
            raise Exception("Database not initialized")
        
        try:
            session = self.SessionLocal()
            # Test the connection
            session.execute(text("SELECT 1"))
            return session
        except Exception as e:
            logger.error(f"Failed to create database session: {str(e)}")
            if 'session' in locals() and session:
                session.close()
            raise
    
    def get_scoped_session(self) -> scoped_session:
        """Get a scoped session for thread-safe operations"""
        # EMERGENCY BYPASS: Initialize if not already done
        if not self.scoped_session_factory:
            logger.warning("⚠️ EMERGENCY BYPASS: Auto-initializing database for scoped session")
            try:
                self.initialize_database()
            except Exception as e:
                logger.error(f"Emergency scoped session initialization failed: {e}")
                raise RuntimeError("Could not initialize scoped database session")
        return self.scoped_session_factory()
    
    @asynccontextmanager
    async def get_async_session(self):
        """Get an async database session with automatic cleanup"""
        if not self._async_available:
            raise RuntimeError("Async database operations not available. Use sync sessions instead.")
        
        # Initialize async engine if not already done
        if not self.AsyncSessionLocal:
            logger.warning("⚠️ EMERGENCY BYPASS: Auto-initializing async database")
            try:
                self.initialize_database()
            except Exception as e:
                logger.error(f"Emergency async session initialization failed: {e}")
                raise RuntimeError("Could not initialize async database session")
        
        start_time = time.time()
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
                
                # Track performance
                self.query_count += 1
                self.total_query_time += time.time() - start_time
                
            except Exception as e:
                await session.rollback()
                self.connection_errors += 1
                logger.error(f"Async database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def close_connections(self) -> None:
        """Close all database connections including async connections"""
        if self.scoped_session_factory:
            self.scoped_session_factory.remove()
        if self.engine:
            self.engine.dispose()
        if self.async_engine and self._async_available:
            await self.async_engine.dispose()
    
    def is_async_available(self) -> bool:
        """Check if async database operations are available"""
        return self._async_available and self.async_engine is not None
            
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            session = self.get_session_direct()
            result = session.execute(text("SELECT 1")).scalar()
            session.close()
            return result == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    async def test_async_connection(self) -> bool:
        """Test async database connectivity"""
        if not self._async_available or not self.async_engine:
            logger.warning("Async database not available for connection test")
            return False
        
        start_time = time.time()
        try:
            async with self.async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            self.query_count += 1
            self.total_query_time += time.time() - start_time
            return True
        except Exception as e:
            self.connection_errors += 1
            logger.error(f"Async database connection test failed: {e}")
            return False
    
    def get_performance_metrics(self) -> DatabasePerformanceMetrics:
        """Get comprehensive database performance metrics"""
        pool = self.engine.pool if self.engine else None
        
        if pool:
            active_connections = pool.checkedout()
            idle_connections = pool.checkedin()
            total_connections = pool.size()
        else:
            active_connections = idle_connections = total_connections = 0
        
        average_query_time = (
            self.total_query_time / self.query_count 
            if self.query_count > 0 else 0.0
        )
        
        # Perform health check if needed
        current_time = time.time()
        health_status = True
        if current_time - self.last_health_check > self.health_check_interval:
            health_status = self.test_connection()
            self.last_health_check = current_time
        
        return DatabasePerformanceMetrics(
            active_connections=active_connections,
            idle_connections=idle_connections,
            total_connections=total_connections,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            query_count=self.query_count,
            average_query_time=average_query_time,
            connection_errors=self.connection_errors,
            health_status=health_status
        )
    
    async def get_async_performance_metrics(self) -> DatabasePerformanceMetrics:
        """Get async database performance metrics"""
        async_pool = self.async_engine.pool if self.async_engine else None
        
        if async_pool:
            active_connections = async_pool.checkedout()
            idle_connections = async_pool.checkedin()
            total_connections = async_pool.size()
        else:
            active_connections = idle_connections = total_connections = 0
        
        average_query_time = (
            self.total_query_time / self.query_count 
            if self.query_count > 0 else 0.0
        )
        
        # Perform async health check if needed
        current_time = time.time()
        health_status = True
        if current_time - self.last_health_check > self.health_check_interval:
            health_status = await self.test_async_connection()
            self.last_health_check = current_time
        
        return DatabasePerformanceMetrics(
            active_connections=active_connections,
            idle_connections=idle_connections,
            total_connections=total_connections,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            query_count=self.query_count,
            average_query_time=average_query_time,
            connection_errors=self.connection_errors,
            health_status=health_status
        )
    
    def reset_performance_counters(self):
        """Reset performance tracking counters"""
        self.query_count = 0
        self.total_query_time = 0.0
        self.connection_errors = 0
        logger.info("Database performance counters reset")
    
    def setup_row_level_security(self, firm_id: str) -> None:
        """Setup row-level security for multi-tenant isolation"""
        if not self.engine:
            raise RuntimeError("Database not initialized.")
        
        try:
            with self.engine.connect() as conn:
                # Enable RLS on tables
                rls_tables = ['cases', 'documents', 'ai_interactions']
                for table in rls_tables:
                    conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
                
                # Set current firm context
                conn.execute(text(f"SET app.current_firm_id = '{firm_id}'"))
                
                # Create policies (example for cases table)
                conn.execute(text("""
                    CREATE POLICY IF NOT EXISTS firm_isolation ON cases 
                    FOR ALL TO current_user 
                    USING (firm_id = current_setting('app.current_firm_id')::UUID)
                """))
                
                conn.commit()
                logger.info(f"Row-level security setup for firm: {firm_id}")
                
        except Exception as e:
            logger.error(f"Failed to setup RLS: {e}")
            raise


# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def init_database():
    """Initialize the database"""
    db_manager.initialize_database()

def create_tables():
    """Create all database tables"""
    db_manager.create_all_tables()

def get_session():
    """Get a database session"""
    return db_manager.get_session()

def get_scoped_session():
    """Get a scoped session"""
    return db_manager.get_scoped_session()

def test_connection():
    """Test database connection"""
    return db_manager.test_connection()

async def close_connections():
    """Close all connections"""
    await db_manager.close_connections()

def get_async_session():
    """Get an async database session"""
    return db_manager.get_async_session()

def get_performance_metrics():
    """Get database performance metrics"""
    return db_manager.get_performance_metrics()

async def get_async_performance_metrics():
    """Get async database performance metrics"""
    return await db_manager.get_async_performance_metrics()

async def test_async_connection():
    """Test async database connection"""
    return await db_manager.test_async_connection()