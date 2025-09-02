#!/usr/bin/env python3
"""
Test script for rate limiter functionality.
This script tests the rate limiter without running the full API.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.append('.')

from app.services.database import database_service
from app.services.rate_limiter import rate_limiter

async def test_rate_limiter():
    """Test the rate limiter functionality"""
    print("🧪 Testing Rate Limiter...")
    
    try:
        # Initialize database
        print("📊 Initializing database...")
        await database_service.initialize()
        print("✅ Database initialized successfully")
        
        test_email = "test@example.com"
        
        # Test rate limiting
        print(f"\n🔄 Testing rate limiting for {test_email}")
        
        # Make several requests quickly
        for i in range(5):
            is_allowed, remaining = await rate_limiter.check_rate_limit(test_email)
            print(f"Request {i+1}: Allowed={is_allowed}, Remaining={remaining}")
            
            if not is_allowed:
                print("❌ Rate limit exceeded as expected")
                break
        
        # Test query logging
        print(f"\n📝 Testing query logging...")
        await rate_limiter.log_query(
            user_email=test_email,
            endpoint="test",
            prompt="Test prompt",
            result={"test": "data"},
            success=True,
            processing_time_ms=100
        )
        print("✅ Query logged successfully")
        
        # Test getting remaining requests
        remaining = await rate_limiter.get_remaining_requests(test_email)
        print(f"📊 Remaining requests for {test_email}: {remaining}")
        
        print("\n✅ All rate limiter tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connections
        await database_service.close()
        print("🔒 Database connections closed")

if __name__ == "__main__":
    asyncio.run(test_rate_limiter())
