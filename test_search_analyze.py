#!/usr/bin/env python3
"""
Test script for the new /search-and-analyze endpoint
This demonstrates the complete workflow: Algolia search -> Polkassembly fetch -> Gemini analysis
"""

import asyncio
import httpx
import json
from typing import Dict, Any

class SearchAnalyzeAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def test_search_and_analyze(self, query: str, num_results: int = 3) -> Dict[str, Any]:
        """
        Test the complete search and analyze workflow
        
        Args:
            query: The search query
            num_results: Number of results to analyze
            
        Returns:
            API response with analysis
        """
        endpoint = f"{self.base_url}/search-and-analyze"
        payload = {
            "query": query,
            "num_results": num_results
        }
        
        print(f"🔍 Testing search and analyze with query: '{query}'")
        print(f"📡 Making request to: {endpoint}")
        print(f"📝 Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            print(f"\n✅ Success! Status Code: {response.status_code}")
            print(f"📊 Results Summary:")
            print(f"   - Query: {data.get('query', 'N/A')}")
            print(f"   - Algolia Results: {len(data.get('algolia_results', []))}")
            print(f"   - Proposals Fetched: {len(data.get('proposals', []))}")
            print(f"   - Analysis Generated: {'Yes' if data.get('analysis') else 'No'}")
            
            # Show proposal details
            proposals = data.get('proposals', [])
            if proposals:
                print(f"\n📋 Proposals Found:")
                for i, proposal in enumerate(proposals, 1):
                    print(f"   {i}. ID: {proposal.get('id', 'N/A')}")
                    print(f"      Title: {proposal.get('title', 'N/A')}")
                    print(f"      Status: {proposal.get('status', 'N/A')}")
            
            # Show analysis
            analysis = data.get('analysis', '')
            if analysis:
                print(f"\n🤖 Gemini Analysis:")
                print("=" * 60)
                print(analysis)
                print("=" * 60)
            
            return data
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            return {}
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {}
    
    async def test_health_check(self) -> bool:
        """Test if the API is running"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            print(f"✅ Health Check: {data.get('status', 'unknown')}")
            return True
        except Exception as e:
            print(f"❌ Health Check Failed: {str(e)}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

async def main():
    """Run test scenarios"""
    tester = SearchAnalyzeAPITester()
    
    try:
        print("🚀 Starting Search & Analyze API Tests\n")
        
        # Health check first
        print("1. Health Check")
        print("-" * 30)
        health_ok = await tester.test_health_check()
        
        if not health_ok:
            print("❌ API is not running. Please start the server first.")
            return
        
        print("\n" + "=" * 60)
        
        # Test scenarios
        test_queries = [
            "Tell me about clarys proposal",
            "What proposals are related to SubWallet development?",
            "Show me treasury proposals",
            "Find proposals about bounties"
        ]
        
        for i, query in enumerate(test_queries, 2):
            print(f"\n{i}. Testing Query: '{query}'")
            print("-" * 60)
            
            result = await tester.test_search_and_analyze(query, num_results=2)
            
            if result:
                print(f"✅ Test {i-1} completed successfully")
            else:
                print(f"❌ Test {i-1} failed")
            
            print("\n" + "=" * 60)
        
        print("\n🎉 All tests completed!")
        
    finally:
        await tester.close()

if __name__ == "__main__":
    print("Search & Analyze API Tester")
    print("=" * 40)
    print("This script tests the complete workflow:")
    print("1. Search Algolia for relevant proposals")
    print("2. Extract proposal IDs and types")
    print("3. Fetch detailed data from Polkassembly API")
    print("4. Analyze with Gemini AI")
    print("=" * 40)
    
    asyncio.run(main()) 