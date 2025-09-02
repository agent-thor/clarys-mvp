#!/usr/bin/env python3
"""
Debug script to test rate limiter database operations
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.append('.')

from app.services.database import database_service
from app.services.rate_limiter import rate_limiter
from app.models.database_models import UserRateLimit
from sqlalchemy import select

async def debug_rate_limiter():
    """Debug rate limiter functionality"""
    print("🔍 Debugging Rate Limiter...")
    
    try:
        # Initialize database
        print("📊 Initializing database...")
        await database_service.initialize()
        print("✅ Database initialized successfully")
        
        test_email = "debug@test.com"
        
        # Check initial state
        print(f"\n1️⃣ Checking initial state for {test_email}")
        async with database_service.get_session() as session:
            stmt = select(UserRateLimit).where(UserRateLimit.user_email == test_email)
            result = await session.execute(stmt)
            user_limit = result.scalar_one_or_none()
            
            if user_limit:
                print(f"   Existing record: count={user_limit.request_count}, reset_time={user_limit.reset_time}")
            else:
                print("   No existing record found")
        
        # Test rate limiting multiple times
        print(f"\n2️⃣ Testing rate limiting for {test_email}")
        for i in range(5):
            print(f"\n   Request {i+1}:")
            is_allowed, remaining = await rate_limiter.check_rate_limit(test_email)
            print(f"   → Allowed: {is_allowed}, Remaining: {remaining}")
            
            # Check database state after each request
            async with database_service.get_session() as session:
                stmt = select(UserRateLimit).where(UserRateLimit.user_email == test_email)
                result = await session.execute(stmt)
                user_limit = result.scalar_one_or_none()
                
                if user_limit:
                    print(f"   → DB State: count={user_limit.request_count}, reset_time={user_limit.reset_time}")
                else:
                    print("   → DB State: No record found!")
        
        # Test get_remaining_requests method
        print(f"\n3️⃣ Testing get_remaining_requests")
        remaining = await rate_limiter.get_remaining_requests(test_email)
        print(f"   Remaining requests: {remaining}")
        
        # Show final database state
        print(f"\n4️⃣ Final database state")
        async with database_service.get_session() as session:
            stmt = select(UserRateLimit)
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            print(f"   Total users in database: {len(users)}")
            for user in users:
                print(f"   → {user.user_email}: count={user.request_count}, reset_time={user.reset_time}")
        
        print("\n✅ Debug completed successfully!")
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connections
        await database_service.close()
        print("🔒 Database connections closed")

if __name__ == "__main__":
    asyncio.run(debug_rate_limiter())
