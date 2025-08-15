import os
import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.algolia import AlgoliaSearchClient
from services.routing_service import RoutingService

def test_algolia_config():
    """Test if Algolia credentials are configured correctly"""
    print("=== Testing Algolia Configuration ===")
    
    app_id = os.getenv("ALGOLIA_APP_ID")
    api_key = os.getenv("ALGOLIA_API_KEY")
    index_name = os.getenv("ALGOLIA_INDEX_NAME", "polkassembly_posts")
    
    print(f"ALGOLIA_APP_ID: {app_id}")
    print(f"ALGOLIA_API_KEY: {'*' * len(api_key) if api_key else 'Not set'}")
    print(f"ALGOLIA_INDEX_NAME: {index_name}")
    
    if not app_id or not api_key:
        print("❌ Algolia credentials missing!")
        return False
    
    print("✅ Algolia credentials configured")
    return True

def test_direct_algolia_search():
    """Test direct Algolia search using our fixed client"""
    print("\n=== Testing Direct Algolia Search ===")
    
    try:
        client = AlgoliaSearchClient()
        results = client.search_posts("clarys", 3)
        print(f"\n\nResults: {results}")
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.get('title', 'Untitled')}")
            print(f"   ID: {result.get('id', result.get('objectID', 'Unknown'))}")
            print(f"   Type: {result.get('proposal_type', result.get('proposalType', 'Unknown'))}")
            print(f"   Content Preview: {result.get('content', '')[:100]}...")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Error in direct search: {str(e)}")
        return False

async def test_routing_service():
    """Test the routing service with Algolia"""
    print("\n=== Testing Routing Service ===")
    
    try:
        routing_service = RoutingService()
        
        # Test a query that should route to Algolia
        test_prompt = "Tell me about clarys proposal"
        result = await routing_service.process_routed_request(test_prompt)
        
        print(f"Routing result for '{test_prompt}':")
        print(f"Data source: {result.get('data_source', 'Unknown')}")
        print(f"Keywords: {result.get('keywords', 'Unknown')}")
        print(f"Results count: {len(result.get('search_results', []))}")
        
        if result.get('search_results'):
            print("\nFirst result:")
            first_result = result['search_results'][0]
            print(f"  Title: {first_result.get('title', 'Untitled')}")
            print(f"  Content: {first_result.get('content', '')[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in routing service: {str(e)}")
        return False

def test_connection():
    """Test basic connection to Algolia"""
    print("\n=== Testing Connection ===")
    
    import requests
    import socket
    import requests.packages.urllib3.util.connection as urllib3_cn

    # Apply the same IPv4 fix
    def allowed_gai_family():
        return socket.AF_INET
    urllib3_cn.allowed_gai_family = allowed_gai_family
    
    app_id = os.getenv("ALGOLIA_APP_ID")
    api_key = os.getenv("ALGOLIA_API_KEY")
    index_name = os.getenv("ALGOLIA_INDEX_NAME", "polkassembly_posts")
    
    if not app_id or not api_key:
        print("❌ Missing credentials")
        return False
    
    try:
        url = f"https://{app_id}-dsn.algolia.net/1/indexes/{index_name}/query"
        headers = {
            "X-Algolia-API-Key": api_key,
            "X-Algolia-Application-Id": app_id,
            "Content-Type": "application/json"
        }
        payload = {"query": "clarys", "hitsPerPage": 1}
        
        print(f"Testing connection to: {url}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        hits = data.get("hits", [])
        
        print(f"✅ Connection successful! Found {len(hits)} results")
        if hits:
            print(f"Sample result: {hits[0].get('title', 'Untitled')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Starting Algolia Debug Tests\n")
    
    # Test 1: Configuration
    config_ok = test_algolia_config()
    
    # Test 2: Basic connection
    connection_ok = test_connection()
    
    # Test 3: Direct search using our client
    search_ok = test_direct_algolia_search()
    
    # Test 4: Routing service
    routing_ok = await test_routing_service()
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"Configuration: {'✅' if config_ok else '❌'}")
    print(f"Connection: {'✅' if connection_ok else '❌'}")
    print(f"Direct Search: {'✅' if search_ok else '❌'}")
    print(f"Routing Service: {'✅' if routing_ok else '❌'}")
    
    if all([config_ok, connection_ok, search_ok, routing_ok]):
        print("\n🎉 All tests passed! Algolia is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())