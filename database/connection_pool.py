#!/usr/bin/env python3
"""
Production Database Connection Pool for Legal AI Hub - Railway Optimized
Optimized for 15+ concurrent users with connection management and monitoring
"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.engine import Engine
import time
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ConnectionPoolConfig:
    """Configuration for database connection pool"""
    
    # Basic connection settings
    database_url: str = ""
    
    # Pool configuration for production
    pool_size: int = 20  # Base pool size for 15+ concurrent users
    max_overflow: int = 30  # Additional connections during peak load
    pool_timeout: int = 30  # Seconds to wait for available connection
    pool_recycle: int = 3600  # Recycle connections every hour
    
    # Connection validation
    pool_pre_ping: bool = True  # Test connections before use
    echo: bool = False  # SQL logging (disable in production)
    
    # Performance optimization
    connect_args: Dict[str, Any] = field(default_factory=lambda: {
        "connect_timeout": 10,
        "application_name": "LegalLLM_Professional",
        "options": "-c default_transaction_isolation=read_committed"
    })

class ProductionConnectionPool:
    """
    Production-grade database connection pool with monitoring and optimization
    Designed for Australian legal firm enterprise deployment
    """
    
    def __init__(self, config: Optional[ConnectionPoolConfig] = None):
        """Initialize production connection pool"""
        self.config = config or self._load_config()
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._stats_lock = threading.Lock()
        self._connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'pool_hits': 0,
            'pool_misses': 0,
            'connection_errors': 0,
            'avg_connection_time': 0.0,
            'last_error': None
        }
        
    def _load_config(self) -> ConnectionPoolConfig:
        """Load configuration from environment variables"""
        config = ConnectionPoolConfig()
        
        # Database URL from environment
        config.database_url = (
            os.getenv('DATABASE_URL') or 
            f"postgresql://{os.getenv('DB_USER', 'legalllm_user')}:"
            f"{os.getenv('DB_PASSWORD', 'secure_password')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '5432')}/"
            f"{os.getenv('DB_NAME', 'legalllm')}"
        )
        
        # Production pool settings
        config.pool_size = int(os.getenv('DB_POOL_SIZE', '20'))
        config.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '30'))
        config.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        config.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        config.echo = os.getenv('DB_ECHO', 'false').lower() == 'true'
        
        return config
    
    def initialize(self) -> None:
        """Initialize database engine and connection pool"""
        try:
            # Create engine with optimized pool settings
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=self.config.pool_pre_ping,
                echo=self.config.echo,
                connect_args=self.config.connect_args,
                future=True  # Use SQLAlchemy 2.0 style
            )
            
            # Set up connection event listeners for monitoring
            self._setup_connection_monitoring()
            
            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Test initial connection
            self._test_connection()
            
            logger.info(
                f"Database connection pool initialized: "
                f"pool_size={self.config.pool_size}, "
                f"max_overflow={self.config.max_overflow}, "
                f"timeout={self.config.pool_timeout}s"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    def _setup_connection_monitoring(self) -> None:
        """Set up connection monitoring and statistics collection"""
        
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Track new connections"""
            with self._stats_lock:
                self._connection_stats['total_connections'] += 1
                connection_record.info['connect_time'] = time.time()
        
        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Track connection checkout from pool"""
            start_time = time.time()
            connection_record.info['checkout_time'] = start_time
            
            with self._stats_lock:
                self._connection_stats['active_connections'] += 1
                self._connection_stats['pool_hits'] += 1
        
        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Track connection return to pool"""
            checkout_time = connection_record.info.get('checkout_time')
            if checkout_time:
                connection_duration = time.time() - checkout_time
                with self._stats_lock:
                    self._connection_stats['active_connections'] -= 1
                    # Update average connection time
                    current_avg = self._connection_stats['avg_connection_time']
                    total_hits = self._connection_stats['pool_hits']
                    self._connection_stats['avg_connection_time'] = (
                        (current_avg * (total_hits - 1) + connection_duration) / total_hits
                    )
        
        @event.listens_for(self.engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Track connection errors"""
            with self._stats_lock:
                self._connection_stats['connection_errors'] += 1
                self._connection_stats['last_error'] = str(exception) if exception else "Unknown error"
            
            logger.warning(f"Database connection invalidated: {exception}")
    
    def _test_connection(self) -> None:
        """Test initial database connection"""
        try:
            with self.get_session() as session:
                result = session.execute("SELECT 1 as test").fetchone()
                if result[0] != 1:
                    raise Exception("Connection test failed")
                    
            logger.info("Database connection test successful")
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Get database session with automatic cleanup
        
        Usage:
            with connection_pool.get_session() as session:
                # Use session for database operations
                result = session.query(User).all()
        """
        if not self.session_factory:
            raise RuntimeError("Connection pool not initialized. Call initialize() first.")
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """
        Get database session for synchronous use (manual cleanup required)
        Note: Caller must handle session.close()
        """
        if not self.session_factory:
            raise RuntimeError("Connection pool not initialized. Call initialize() first.")
        
        return self.session_factory()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics"""
        with self._stats_lock:
            stats = self._connection_stats.copy()
        
        # Add current pool status
        if self.engine:
            pool = self.engine.pool
            stats.update({
                'pool_size': pool.size(),
                'checked_in_connections': pool.checkedin(),
                'checked_out_connections': pool.checkedout(),
                'overflow_connections': pool.overflow(),
                'invalid_connections': pool.invalid()
            })
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of connection pool"""
        health_status = {
            'healthy': True,
            'timestamp': time.time(),
            'checks': {}
        }
        
        try:
            # Test database connectivity
            start_time = time.time()
            with self.get_session() as session:
                session.execute("SELECT 1").fetchone()
            response_time = time.time() - start_time
            
            health_status['checks']['database_connectivity'] = {
                'status': 'healthy',
                'response_time_ms': round(response_time * 1000, 2)
            }
            
        except Exception as e:
            health_status['healthy'] = False
            health_status['checks']['database_connectivity'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        # Check pool status
        try:
            stats = self.get_connection_stats()
            pool_utilization = (
                stats.get('checked_out_connections', 0) / 
                max(stats.get('pool_size', 1), 1) * 100
            )
            
            health_status['checks']['connection_pool'] = {
                'status': 'healthy' if pool_utilization < 90 else 'warning',
                'utilization_percent': round(pool_utilization, 1),
                'active_connections': stats.get('active_connections', 0),
                'total_connections': stats.get('total_connections', 0)
            }
            
        except Exception as e:
            health_status['healthy'] = False
            health_status['checks']['connection_pool'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        return health_status
    
    def close(self) -> None:
        """Close connection pool and cleanup resources"""
        try:
            if self.engine:
                self.engine.dispose()
                logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")

# Global connection pool instance
_connection_pool: Optional[ProductionConnectionPool] = None

def get_connection_pool() -> ProductionConnectionPool:
    """Get global connection pool instance"""
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = ProductionConnectionPool()
        _connection_pool.initialize()
    
    return _connection_pool

def initialize_connection_pool(config: Optional[ConnectionPoolConfig] = None) -> ProductionConnectionPool:
    """Initialize global connection pool with custom configuration"""
    global _connection_pool
    
    if _connection_pool is not None:
        _connection_pool.close()
    
    _connection_pool = ProductionConnectionPool(config)
    _connection_pool.initialize()
    
    return _connection_pool

# Convenience functions for common database operations
@contextmanager
def get_db_session():
    """Convenient context manager for database sessions"""
    pool = get_connection_pool()
    with pool.get_session() as session:
        yield session

def get_db_stats() -> Dict[str, Any]:
    """Get database connection statistics"""
    pool = get_connection_pool()
    return pool.get_connection_stats()

def perform_db_health_check() -> Dict[str, Any]:
    """Perform database health check"""
    pool = get_connection_pool()
    return pool.health_check()