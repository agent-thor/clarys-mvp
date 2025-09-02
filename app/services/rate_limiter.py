import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from app.models.database_models import UserRateLimit, QueryHistory
from app.services.database import database_service

logger = logging.getLogger(__name__)

class RateLimiterService:
    """
    Rate limiter service using PostgreSQL backend.
    Implements a sliding window rate limiter with configurable requests per time window.
    Default: 20 requests per 24 hours.
    """
    
    def __init__(self, requests_per_window: int = 20):
        # Load window size from environment variable (in hours), default to 24 hours
        window_hours = int(os.getenv("RATE_LIMIT_WINDOW_HOURS", "24"))
        
        self.requests_per_window = requests_per_window
        self.window_size_seconds = window_hours * 3600  # Convert hours to seconds
        self.window_hours = window_hours
        
        logger.info(f"Rate limiter initialized: {requests_per_window} requests per {window_hours} hours")
    
    async def check_rate_limit(self, user_email: str) -> Tuple[bool, int]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_email: User's email address
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        logger.info(f"🔍 Checking rate limit for user: {user_email}")
        session = None
        try:
            session = await database_service.get_session()
            logger.info(f"📊 Database session created for {user_email}")
            
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=self.window_size_seconds)
            
            # Get or create user rate limit record
            stmt = select(UserRateLimit).where(UserRateLimit.user_email == user_email)
            result = await session.execute(stmt)
            user_limit = result.scalar_one_or_none()
            
            logger.info(f"📋 Existing record for {user_email}: {user_limit}")
            
            if user_limit is None:
                # Create new user record
                logger.info(f"🆕 Creating new user record for {user_email}")
                user_limit = UserRateLimit(
                    user_email=user_email,
                    request_count=1,
                    reset_time=now + timedelta(seconds=self.window_size_seconds)
                )
                session.add(user_limit)
                await session.commit()
                
                remaining = self.requests_per_window - 1
                logger.info(f"✅ New user {user_email}: 1 request, {remaining} remaining")
                return True, remaining
            
            # Check if we need to reset the window
            if now >= user_limit.reset_time:
                # Reset the window
                user_limit.request_count = 1
                user_limit.reset_time = now + timedelta(seconds=self.window_size_seconds)
                user_limit.updated_at = now
                
                await session.commit()
                
                remaining = self.requests_per_window - 1
                logger.info(f"Window reset for {user_email}: 1 request, {remaining} remaining")
                return True, remaining
            
            # Check if user has exceeded limit
            if user_limit.request_count >= self.requests_per_window:
                remaining = 0
                logger.warning(f"Rate limit exceeded for {user_email}: {user_limit.request_count} requests")
                return False, remaining
            
            # Increment request count
            old_count = user_limit.request_count
            user_limit.request_count += 1
            user_limit.updated_at = now
            await session.commit()
            
            remaining = self.requests_per_window - user_limit.request_count
            logger.info(f"✅ Request allowed for {user_email}: {old_count} → {user_limit.request_count} requests, {remaining} remaining")
            return True, remaining
                
        except Exception as e:
            logger.error(f"❌ Error checking rate limit for {user_email}: {str(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # In case of database error, allow the request but log the issue
            return True, self.requests_per_window - 1
        finally:
            if session:
                await session.close()
    
    async def get_remaining_requests(self, user_email: str) -> int:
        """
        Get remaining requests for a user without incrementing the counter.
        
        Args:
            user_email: User's email address
            
        Returns:
            Number of remaining requests
        """
        session = None
        try:
            session = await database_service.get_session()
            now = datetime.now(timezone.utc)
            
            stmt = select(UserRateLimit).where(UserRateLimit.user_email == user_email)
            result = await session.execute(stmt)
            user_limit = result.scalar_one_or_none()
            
            if user_limit is None:
                return self.requests_per_window
            
            # Check if window has expired
            if now >= user_limit.reset_time:
                return self.requests_per_window
            
            remaining = max(0, self.requests_per_window - user_limit.request_count)
            return remaining
                
        except Exception as e:
            logger.error(f"Error getting remaining requests for {user_email}: {str(e)}")
            return self.requests_per_window
        finally:
            if session:
                await session.close()
    
    async def log_query(
        self, 
        user_email: str, 
        endpoint: str, 
        prompt: str, 
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> None:
        """
        Log user query to database for analytics and debugging.
        
        Args:
            user_email: User's email address
            endpoint: API endpoint called (e.g., 'general-chat')
            prompt: User's prompt/query
            result: API response (will be JSON serialized)
            success: Whether the request was successful
            error_message: Error message if request failed
            processing_time_ms: Time taken to process the request
        """
        session = None
        try:
            session = await database_service.get_session()
            # Serialize result to JSON string
            result_json = None
            if result is not None:
                try:
                    result_json = json.dumps(result, default=str, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Failed to serialize result for logging: {str(e)}")
                    result_json = str(result)
            
            query_log = QueryHistory(
                user_email=user_email,
                endpoint=endpoint,
                prompt=prompt,
                result=result_json,
                success=success,
                error_message=error_message,
                processing_time_ms=processing_time_ms
            )
            
            session.add(query_log)
            await session.commit()
            
            logger.info(f"Query logged for {user_email} on {endpoint}")
                
        except Exception as e:
            logger.error(f"Failed to log query for {user_email}: {str(e)}")
            # Don't raise exception as logging failure shouldn't break the main flow
        finally:
            if session:
                await session.close()
    
    async def cleanup_old_records(self, days_to_keep: int = 30) -> None:
        """
        Clean up old rate limit and query history records.
        
        Args:
            days_to_keep: Number of days to keep records
        """
        session = None
        try:
            session = await database_service.get_session()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Clean up old query history
            delete_query_stmt = delete(QueryHistory).where(
                QueryHistory.created_at < cutoff_date
            )
            query_result = await session.execute(delete_query_stmt)
            
            # Clean up expired rate limit records
            delete_limit_stmt = delete(UserRateLimit).where(
                UserRateLimit.reset_time < datetime.now(timezone.utc) - timedelta(hours=1)
            )
            limit_result = await session.execute(delete_limit_stmt)
            
            await session.commit()
            
            logger.info(f"Cleaned up {query_result.rowcount} old query records and {limit_result.rowcount} expired rate limit records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {str(e)}")
        finally:
            if session:
                await session.close()

# Global rate limiter instance
rate_limiter = RateLimiterService(requests_per_window=20)
