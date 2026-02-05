# FILE: app/core/database.py
# Database Connection and Session Management
# =====================================================

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import contextmanager
from typing import Generator
from urllib.parse import quote_plus
import logging

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ALWAYS build database URL from components (ignore DATABASE_URL from .env)
# URL-encode the password to handle special characters like @ # $ etc.
encoded_password = quote_plus(settings.DB_PASSWORD)
DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{encoded_password}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

logger.info(f" Connecting to: {settings.DB_USER}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

# Database engine configuration
engine_args = {
    "pool_pre_ping": settings.DB_POOL_PRE_PING,
    "echo": settings.DB_ECHO,
}

# Use appropriate connection pool based on environment
if settings.DEBUG:
    # Use NullPool for development (no connection pooling)
    engine_args["poolclass"] = NullPool
else:
    # Use QueuePool for production
    engine_args["pool_size"] = settings.DB_POOL_SIZE
    engine_args["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_args["poolclass"] = QueuePool

# Create database engine
try:
    engine = create_engine(
        DATABASE_URL,
        **engine_args
    )
    logger.info(f" Database engine created successfully for {settings.DB_NAME}")
except Exception as e:
    logger.error(f" Failed to create database engine: {str(e)}")
    raise

# Create SessionLocal class
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Create Base class for models
Base = declarative_base()

# Metadata instance for database operations
metadata = MetaData()

# Dependency to get DB session
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f" Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

# Context manager for database sessions
@contextmanager
def get_db_session():
    """
    Context manager for database operations outside of FastAPI requests
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f" Database operation failed: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

# Test database connection
def test_connection():
    """
    Test database connection
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info(" Database connection test successful")
            return True
    except Exception as e:
        logger.error(f" Database connection test failed: {str(e)}")
        return False

# Initialize database tables
def init_db():
    """
    Create all tables in the database with proper dependency ordering
    """
    try:
        # Only import the models you actually need
        from app.models.user import Company, User
        from app.models.contract import Contract
        from app.models.workflow import Workflow, WorkflowStep
        from app.models.audit import AuditLog
        from app.models.notification import Notification
        
        # Use raw SQL to disable foreign key checks for MySQL
        with engine.begin() as conn:
            # Disable foreign key checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            
            # Don't drop existing tables to preserve data
            Base.metadata.create_all(bind=conn, checkfirst=True)
            
            # Re-enable foreign key checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        
        logger.info(" Database tables created successfully")
    except Exception as e:
        logger.error(f" Failed to create database tables: {str(e)}")
        raise

# Drop all tables (use with caution!)
def drop_all_tables():
    """
    Drop all tables from the database
    WARNING: This will delete all data!
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info(" All database tables dropped successfully")
    except Exception as e:
        logger.error(f" Failed to drop database tables: {str(e)}")
        raise