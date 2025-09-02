#!/usr/bin/env python3
"""
Test database connection and basic operations
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.append('.')

async def test_database_connection():
    """Test database connection and operations"""
    print("🔗 Testing Database Connection...")
    print("=" * 50)
    
    try:
        # Check environment variables
        print("1️⃣ Checking environment variables:")
        env_vars = [
            "POSTGRES_HOST",
            "POSTGRES_PORT", 
            "POSTGRES_DATABASE",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD"
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # Mask password
                display_value = "***" if "PASSWORD" in var else value
                print(f"   ✅ {var}: {display_value}")
            else:
                print(f"   ❌ {var}: Not set")
        
        # Test database service initialization
        print(f"\n2️⃣ Testing database service initialization:")
        from app.services.database import database_service
        
        await database_service.initialize()
        print("   ✅ Database service initialized successfully")
        
        # Test session creation
        print(f"\n3️⃣ Testing session creation:")
        session = await database_service.get_session()
        try:
            print("   ✅ Database session created successfully")
            
            # Test a simple query
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"   ✅ Simple query result: {row}")
        finally:
            await session.close()
        
        # Test table creation/existence
        print(f"\n4️⃣ Testing table operations:")
        from app.models.database_models import UserRateLimit
        from sqlalchemy import select
        
        session = await database_service.get_session()
        try:
            # Try to query the user_rate_limits table
            stmt = select(UserRateLimit).limit(1)
            result = await session.execute(stmt)
            users = result.scalars().all()
            print(f"   ✅ user_rate_limits table exists, found {len(users)} records")
        finally:
            await session.close()
        
        print(f"\n✅ All database tests passed!")
        
    except Exception as e:
        print(f"\n❌ Database test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await database_service.close()
            print("🔒 Database connections closed")
        except:
            pass
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    if not success:
        sys.exit(1)
