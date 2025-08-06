"""
Database Connection Fallback System for Railway Deployment
Handles PostgreSQL connection issues and provides graceful degradation
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DatabaseConnectionFallback:
    """
    Handles database connection failures with intelligent fallback strategies
    """
    
    def __init__(self):
        self.connection_attempts = 0
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 30.0
        
    def parse_database_url(self, database_url: str) -> Dict[str, str]:
        """Parse DATABASE_URL into components"""
        try:
            parsed = urlparse(database_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'username': parsed.username,
                'password': parsed.password
            }
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")
            return {}
    
    def test_psycopg2_import(self) -> bool:
        """Test if psycopg2 can be imported"""
        try:
            import psycopg2
            logger.info(f"✅ psycopg2 version {psycopg2.__version__} available")
            return True
        except ImportError as e:
            logger.warning(f"⚠️ psycopg2 import failed: {e}")
            
            # Try psycopg2-binary
            try:
                import psycopg2
                logger.info("✅ psycopg2-binary fallback successful")
                return True
            except ImportError:
                logger.error("❌ Neither psycopg2 nor psycopg2-binary available")
                return False
    
    def create_connection_with_retry(self, database_url: str):
        """Create database connection with exponential backoff retry"""
        if not self.test_psycopg2_import():
            raise ImportError("psycopg2 not available")
        
        from sqlalchemy import create_engine
        
        for attempt in range(self.max_retries):
            try:
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                
                if attempt > 0:
                    logger.info(f"🔄 Connection attempt {attempt + 1}/{self.max_retries} after {delay:.1f}s delay...")
                    time.sleep(delay)
                
                # Create engine with Railway-optimized settings
                engine = create_engine(
                    database_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    pool_recycle=300,
                    connect_args={
                        "connect_timeout": 10,
                        "application_name": "Legal AI Hub",
                        "sslmode": "prefer"
                    }
                )
                
                # Test connection
                with engine.connect() as conn:
                    conn.execute("SELECT 1")
                
                logger.info(f"✅ Database connection successful on attempt {attempt + 1}")
                return engine
                
            except Exception as e:
                logger.warning(f"⚠️ Connection attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error("❌ All connection attempts exhausted")
                    raise
        
        raise ConnectionError("Failed to establish database connection")
    
    def get_fallback_database_url(self) -> Optional[str]:
        """Get fallback database URL for development"""
        fallback_urls = [
            os.getenv('LOCAL_DATABASE_URL'),
            os.getenv('FALLBACK_DATABASE_URL'),
            'postgresql://postgres:password@localhost:5432/legalai_dev'
        ]
        
        for url in fallback_urls:
            if url:
                try:
                    # Test if this URL is reachable
                    engine = self.create_connection_with_retry(url)
                    engine.dispose()
                    logger.info(f"✅ Fallback database URL validated: {url[:30]}...")
                    return url
                except:
                    continue
        
        logger.warning("⚠️ No fallback database URLs available")
        return None
    
    def setup_database_connection(self) -> Optional[Any]:
        """
        Main function to setup database connection with fallbacks
        Returns SQLAlchemy engine or None if all attempts fail
        """
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            
            # Try fallback URLs
            fallback_url = self.get_fallback_database_url()
            if fallback_url:
                database_url = fallback_url
            else:
                logger.error("❌ No database connection available")
                return None
        
        try:
            # Attempt primary connection
            engine = self.create_connection_with_retry(database_url)
            logger.info("✅ Database connection established successfully")
            return engine
            
        except Exception as e:
            logger.error(f"❌ Primary database connection failed: {e}")
            
            # Try fallback connection
            fallback_url = self.get_fallback_database_url()
            if fallback_url and fallback_url != database_url:
                try:
                    logger.info("🔄 Attempting fallback database connection...")
                    engine = self.create_connection_with_retry(fallback_url)
                    logger.info("✅ Fallback database connection successful")
                    return engine
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback database connection failed: {fallback_error}")
            
            logger.error("❌ All database connection attempts failed")
            return None
    
    def validate_database_schema(self, engine) -> bool:
        """Validate that required tables exist"""
        try:
            from sqlalchemy import inspect
            
            inspector = inspect(engine)
            required_tables = ['law_firms', 'users', 'cases', 'documents']
            existing_tables = inspector.get_table_names()
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                logger.warning(f"⚠️ Missing database tables: {missing_tables}")
                return False
            
            logger.info("✅ Database schema validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database schema validation failed: {e}")
            return False

# Global instance for easy import
db_fallback = DatabaseConnectionFallback()

def get_database_engine():
    """
    Convenience function to get database engine with fallback handling
    """
    return db_fallback.setup_database_connection()

def test_database_connection():
    """
    Test database connection and return status
    """
    engine = get_database_engine()
    if engine:
        is_valid = db_fallback.validate_database_schema(engine)
        engine.dispose()
        return is_valid
    return False