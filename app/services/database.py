import os
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.models.database_models import Base
import asyncpg

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Service for managing PostgreSQL database connections and operations.
    Handles connection pooling, session management, and table creation.
    """
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def _get_database_url(self) -> str:
        """Constructs the PostgreSQL database URL from environment variables."""
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DATABASE")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        
        if not all([host, database, user, password]):
            missing = [var for var, val in {
                "POSTGRES_HOST": host,
                "POSTGRES_DATABASE": database, 
                "POSTGRES_USER": user,
                "POSTGRES_PASSWORD": password
            }.items() if not val]
            raise ValueError(f"Missing required PostgreSQL environment variables: {', '.join(missing)}")
        
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    
    async def initialize(self):
        """Initialize database connection and create tables if they don't exist."""
        if self._initialized:
            return
        
        try:
            database_url = self._get_database_url()
            logger.info("Initializing database connection...")
            
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                database_url,
                poolclass=NullPool,  # Use NullPool for serverless environments
                echo=False,  # Set to True for SQL query logging
                future=True
            )
            
            # Create session factory
            self.SessionLocal = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.run_sync(lambda _: None)  # Simple connection test
            
            logger.info("Database connection established successfully")
            
            # Create tables if they don't exist
            await self.create_tables()
            
            self._initialized = True
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def create_tables(self):
        """Create database tables if they don't exist."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        if not self._initialized:
            await self.initialize()
        
        return self.SessionLocal()
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

# Global database service instance
database_service = DatabaseService()

async def get_db_session() -> AsyncSession:
    """Dependency function to get database session for FastAPI endpoints."""
    async with database_service.get_session() as session:
        try:
            yield session
        finally:
            await session.close()
