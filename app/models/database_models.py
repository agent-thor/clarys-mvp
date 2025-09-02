from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class UserRateLimit(Base):
    """
    Table to track user rate limits.
    Stores current request count and reset time for each user.
    """
    __tablename__ = "user_rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), unique=True, index=True, nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    reset_time = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Add index for efficient lookups
    __table_args__ = (
        Index('ix_user_email_reset_time', 'user_email', 'reset_time'),
    )

class QueryHistory(Base):
    """
    Table to store user query history with prompts and results.
    Tracks all API interactions for analytics and debugging.
    """
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), index=True, nullable=False)
    endpoint = Column(String(100), nullable=False)  # e.g., 'general-chat', 'accountability-check'
    prompt = Column(Text, nullable=False)
    result = Column(Text, nullable=True)  # JSON string of the response
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)  # Time taken to process request
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Add indexes for efficient queries
    __table_args__ = (
        Index('ix_user_email_created_at', 'user_email', 'created_at'),
        Index('ix_endpoint_created_at', 'endpoint', 'created_at'),
    )
