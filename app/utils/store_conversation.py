#!/usr/bin/env python3
"""
Simple API Conversation Monitor

Monitors API requests and responses, storing only query and response data
in a simple JSON structure organized by endpoint.

Usage:
    python app/utils/store_conversation.py --monitor
    python app/utils/store_conversation.py --export

Data is saved to: data/conversations.json
"""

import asyncio
import json
import argparse
import signal
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.database import database_service
from app.models.database_models import QueryHistory
from sqlalchemy import select, and_

class SimpleConversationMonitor:
    """Simple monitor for API conversations - stores only query and response"""
    
    def __init__(self, start_fresh=False):
        # Data folder path
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        self.output_file = os.path.join(self.data_dir, 'conversations.json')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.conversations = {}
        self.last_check = datetime.now(timezone.utc)
        self.running = False
        
        # Load existing conversations only if not starting fresh
        if not start_fresh:
            self.load_conversations()
    
    def load_conversations(self):
        """Load existing conversations from JSON file"""
        try:
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.conversations = json.load(f)
                print(f"📂 Loaded existing conversations from {self.output_file}")
                self.print_stats()
        except Exception as e:
            print(f"⚠️  Error loading conversations: {str(e)}")
            self.conversations = {}
    
    def save_conversations(self):
        """Save conversations to JSON file"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved to {self.output_file}")
            self.print_stats()
        except Exception as e:
            print(f"❌ Error saving: {str(e)}")
    
    def print_stats(self):
        """Print simple statistics"""
        total = sum(len(convs) for convs in self.conversations.values())
        print(f"📊 Total: {total} conversations")
        for endpoint, convs in self.conversations.items():
            print(f"   - {endpoint}: {len(convs)}")
    
    def filter_response_by_endpoint(self, endpoint: str, response_data: Dict) -> Dict:
        """Filter response data to keep only relevant fields for each endpoint"""
        if not response_data:
            return None
        
        if endpoint == "extract-with-proposals":
            # Only keep prompt and analysis
            return {
                "analysis": response_data.get("analysis")
            }
        elif endpoint == "accountability-check":
            # Only keep prompt and accountability_analysis
            return {
                "accountability_analysis": response_data.get("accountability_analysis")
            }
        elif endpoint == "general-chat":
            # Only keep prompt and answer
            return {
                "answer": response_data.get("answer")
            }
        else:
            # For other endpoints (extract, etc.), return the full response
            return response_data
    
    async def fetch_new_conversations(self):
        """Fetch new conversations from database"""
        try:
            session = await database_service.get_session()
            try:
                print(f"🔍 Looking for conversations after: {self.last_check}")
                
                stmt = select(QueryHistory).where(
                    and_(
                        QueryHistory.created_at > self.last_check,
                        QueryHistory.success == True
                    )
                ).order_by(QueryHistory.created_at.asc())
                
                result = await session.execute(stmt)
                query_logs = result.scalars().all()
                
                print(f"📊 Found {len(query_logs)} records in database query")
                
                new_conversations = []
                for log in query_logs:
                    try:
                        # Parse response JSON
                        response_data = None
                        if log.result:
                            response_data = json.loads(log.result)
                        
                        # Extract only relevant fields based on endpoint
                        filtered_response = self.filter_response_by_endpoint(log.endpoint, response_data)
                        
                        # Simple conversation structure - only query and filtered response
                        conversation = {
                            "query": log.prompt,
                            "response": filtered_response
                        }
                        
                        new_conversations.append((log.endpoint, conversation))
                        
                    except json.JSONDecodeError:
                        continue  # Skip invalid JSON
                
                # Update last check time
                if query_logs:
                    self.last_check = max(log.created_at for log in query_logs)
                    print(f"🕒 Updated last check time to: {self.last_check}")
                else:
                    self.last_check = datetime.now(timezone.utc)
                
                return new_conversations
                
            finally:
                await session.close()
                
        except Exception as e:
            print(f"❌ Database error: {str(e)}")
            return []
    
    def add_conversations(self, conversations):
        """Add new conversations"""
        for endpoint, conversation in conversations:
            if endpoint not in self.conversations:
                self.conversations[endpoint] = []
            self.conversations[endpoint].append(conversation)
        
        if conversations:
            print(f"➕ Added {len(conversations)} new conversations")
    
    async def monitor(self, interval=10):
        """Monitor continuously - only capture NEW API calls"""
        print(f"🔍 Starting fresh monitoring of NEW API calls (every {interval}s)")
        print("Press Ctrl+C to stop")
        print(f"📅 Monitoring started at: {self.last_check}")
        
        # Clear existing conversations to start fresh
        self.conversations = {}
        self.running = True
        
        def stop_handler(signum, frame):
            print("\n🛑 Stopping...")
            self.running = False
        
        signal.signal(signal.SIGINT, stop_handler)
        
        try:
            while self.running:
                new_conversations = await self.fetch_new_conversations()
                
                if new_conversations:
                    self.add_conversations(new_conversations)
                    self.save_conversations()
                else:
                    print(f"⏱️  No new calls ({datetime.now().strftime('%H:%M:%S')})")
                
                # Wait
                for _ in range(interval):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
        
        except Exception as e:
            print(f"❌ Monitor error: {str(e)}")
        
        finally:
            self.save_conversations()
            print("✅ Stopped")
    
    async def export_all(self):
        """Export all conversations from database"""
        print("📤 Exporting all conversations...")
        
        try:
            session = await database_service.get_session()
            try:
                stmt = select(QueryHistory).where(
                    QueryHistory.success == True
                ).order_by(QueryHistory.created_at.asc())
                
                result = await session.execute(stmt)
                query_logs = result.scalars().all()
                
                print(f"📊 Found {len(query_logs)} conversations")
                
                # Clear and rebuild
                self.conversations = {}
                
                for log in query_logs:
                    try:
                        response_data = None
                        if log.result:
                            response_data = json.loads(log.result)
                        
                        # Extract only relevant fields based on endpoint
                        filtered_response = self.filter_response_by_endpoint(log.endpoint, response_data)
                        
                        conversation = {
                            "query": log.prompt,
                            "response": filtered_response
                        }
                        
                        if log.endpoint not in self.conversations:
                            self.conversations[log.endpoint] = []
                        
                        self.conversations[log.endpoint].append(conversation)
                        
                    except json.JSONDecodeError:
                        continue
                
                self.save_conversations()
                print("✅ Export completed")
                
            finally:
                await session.close()
                
        except Exception as e:
            print(f"❌ Export error: {str(e)}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Simple API conversation monitor")
    parser.add_argument('--monitor', '-m', action='store_true', help='Start monitoring NEW API calls only')
    parser.add_argument('--export', '-e', action='store_true', help='Export all conversations from database')
    parser.add_argument('--clear', '-c', action='store_true', help='Clear existing conversations file')
    parser.add_argument('--interval', '-i', type=int, default=10, help='Monitor interval (default: 10s)')
    
    args = parser.parse_args()
    
    if not args.monitor and not args.export and not args.clear:
        parser.print_help()
        return
    
    print("🚀 Simple API Conversation Monitor")
    print("=" * 40)
    
    try:
        # Connect to database
        print("📊 Connecting to database...")
        await database_service.initialize()
        print("✅ Connected")
        
        # Handle different modes
        if args.clear:
            # Clear existing conversations file
            monitor = SimpleConversationMonitor(start_fresh=True)
            monitor.conversations = {}
            monitor.save_conversations()
            print("🗑️  Cleared existing conversations file")
            return
        
        # Initialize monitor
        if args.monitor:
            # Start fresh monitoring - don't load existing conversations
            monitor = SimpleConversationMonitor(start_fresh=True)
            await monitor.monitor(args.interval)
        elif args.export:
            # Export mode - load existing conversations
            monitor = SimpleConversationMonitor(start_fresh=False)
            await monitor.export_all()
        
    except KeyboardInterrupt:
        print("\n❌ Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        try:
            await database_service.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
