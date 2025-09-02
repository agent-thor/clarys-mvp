#!/usr/bin/env python3
"""
Reset Rate Limit Script

This script allows you to reset the rate limit for a specific user by their email address.
It can be used to unblock users who have hit their rate limit or for administrative purposes.

Usage:
    python reset_user_rate_limit.py user@example.com
    python reset_user_rate_limit.py --all  # Reset all users
    python reset_user_rate_limit.py --list  # List all users and their current limits
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.append('.')

from app.services.database import database_service
from app.models.database_models import UserRateLimit
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

class RateLimitManager:
    """Manager class for rate limit operations"""
    
    async def reset_user_limit(self, user_email: str) -> bool:
        """
        Reset rate limit for a specific user.
        
        Args:
            user_email: Email address of the user
            
        Returns:
            True if user was found and reset, False if user not found
        """
        try:
            async with database_service.get_session() as session:
                # Check if user exists
                stmt = select(UserRateLimit).where(UserRateLimit.user_email == user_email)
                result = await session.execute(stmt)
                user_limit = result.scalar_one_or_none()
                
                if user_limit is None:
                    print(f"❌ User '{user_email}' not found in rate limit table")
                    return False
                
                # Reset the user's rate limit
                update_stmt = update(UserRateLimit).where(
                    UserRateLimit.user_email == user_email
                ).values(
                    request_count=0,
                    reset_time=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                await session.execute(update_stmt)
                await session.commit()
                
                print(f"✅ Rate limit reset for user '{user_email}'")
                print(f"   Request count: {user_limit.request_count} → 0")
                print(f"   Reset time: {user_limit.reset_time} → {datetime.utcnow()}")
                return True
                
        except Exception as e:
            print(f"❌ Error resetting rate limit for '{user_email}': {str(e)}")
            return False
    
    async def reset_all_limits(self) -> int:
        """
        Reset rate limits for all users.
        
        Returns:
            Number of users reset
        """
        try:
            async with database_service.get_session() as session:
                # Get count of users before reset
                count_stmt = select(UserRateLimit)
                result = await session.execute(count_stmt)
                users = result.scalars().all()
                user_count = len(users)
                
                if user_count == 0:
                    print("ℹ️ No users found in rate limit table")
                    return 0
                
                # Reset all users
                update_stmt = update(UserRateLimit).values(
                    request_count=0,
                    reset_time=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                await session.execute(update_stmt)
                await session.commit()
                
                print(f"✅ Rate limits reset for {user_count} users")
                return user_count
                
        except Exception as e:
            print(f"❌ Error resetting all rate limits: {str(e)}")
            return 0
    
    async def list_all_limits(self) -> None:
        """List all users and their current rate limit status"""
        try:
            async with database_service.get_session() as session:
                stmt = select(UserRateLimit).order_by(UserRateLimit.updated_at.desc())
                result = await session.execute(stmt)
                users = result.scalars().all()
                
                if not users:
                    print("ℹ️ No users found in rate limit table")
                    return
                
                print(f"\n📊 Rate Limit Status for {len(users)} users:")
                print("=" * 80)
                print(f"{'Email':<35} {'Requests':<10} {'Reset Time':<25} {'Status'}")
                print("-" * 80)
                
                now = datetime.utcnow()
                for user in users:
                    # Determine status
                    if user.request_count >= 20:
                        if now >= user.reset_time:
                            status = "🟢 Ready (Window Expired)"
                        else:
                            status = "🔴 Rate Limited"
                    else:
                        remaining = 20 - user.request_count
                        status = f"🟢 Active ({remaining} remaining)"
                    
                    print(f"{user.user_email:<35} {user.request_count:<10} {user.reset_time.strftime('%Y-%m-%d %H:%M:%S'):<25} {status}")
                
                print("-" * 80)
                
        except Exception as e:
            print(f"❌ Error listing rate limits: {str(e)}")
    
    async def delete_user_limit(self, user_email: str) -> bool:
        """
        Delete a user's rate limit record entirely.
        
        Args:
            user_email: Email address of the user
            
        Returns:
            True if user was found and deleted, False if user not found
        """
        try:
            async with database_service.get_session() as session:
                # Check if user exists
                stmt = select(UserRateLimit).where(UserRateLimit.user_email == user_email)
                result = await session.execute(stmt)
                user_limit = result.scalar_one_or_none()
                
                if user_limit is None:
                    print(f"❌ User '{user_email}' not found in rate limit table")
                    return False
                
                # Delete the user's rate limit record
                delete_stmt = delete(UserRateLimit).where(
                    UserRateLimit.user_email == user_email
                )
                
                await session.execute(delete_stmt)
                await session.commit()
                
                print(f"✅ Rate limit record deleted for user '{user_email}'")
                print(f"   User will start fresh on next request")
                return True
                
        except Exception as e:
            print(f"❌ Error deleting rate limit for '{user_email}': {str(e)}")
            return False

async def main():
    """Main function to handle command line arguments and execute operations"""
    parser = argparse.ArgumentParser(
        description="Reset user rate limits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reset_user_rate_limit.py user@example.com          # Reset specific user
  python reset_user_rate_limit.py --all                     # Reset all users
  python reset_user_rate_limit.py --list                    # List all users
  python reset_user_rate_limit.py --delete user@example.com # Delete user record
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('email', nargs='?', help='Email address of user to reset')
    group.add_argument('--all', action='store_true', help='Reset all users')
    group.add_argument('--list', action='store_true', help='List all users and their limits')
    group.add_argument('--delete', metavar='EMAIL', help='Delete user rate limit record')
    
    args = parser.parse_args()
    
    print("🔧 Rate Limit Manager")
    print("=" * 50)
    
    try:
        # Initialize database
        print("📊 Connecting to database...")
        await database_service.initialize()
        print("✅ Database connected successfully")
        
        manager = RateLimitManager()
        
        if args.email:
            # Reset specific user
            print(f"\n🔄 Resetting rate limit for: {args.email}")
            success = await manager.reset_user_limit(args.email)
            if success:
                print(f"\n✅ User '{args.email}' can now make 20 new requests")
            else:
                sys.exit(1)
                
        elif args.all:
            # Reset all users
            print("\n🔄 Resetting rate limits for ALL users...")
            print("⚠️  This will reset rate limits for every user in the system")
            
            # Ask for confirmation
            confirm = input("Are you sure? (yes/no): ").lower().strip()
            if confirm not in ['yes', 'y']:
                print("❌ Operation cancelled")
                sys.exit(0)
            
            count = await manager.reset_all_limits()
            if count > 0:
                print(f"\n✅ All {count} users can now make 20 new requests")
            else:
                sys.exit(1)
                
        elif args.list:
            # List all users
            await manager.list_all_limits()
            
        elif args.delete:
            # Delete specific user record
            print(f"\n🗑️  Deleting rate limit record for: {args.delete}")
            success = await manager.delete_user_limit(args.delete)
            if not success:
                sys.exit(1)
        
        print(f"\n🏁 Operation completed successfully!")
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Close database connections
        try:
            await database_service.close()
            print("🔒 Database connections closed")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
