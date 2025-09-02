#!/usr/bin/env python3
"""
Test API rate limiting by making multiple requests
"""

import asyncio
import aiohttp
import json

async def test_api_rate_limiting():
    """Test API rate limiting with multiple requests"""
    
    base_url = "http://localhost:8000"
    test_email = "test@example.com"
    
    # Test payload
    payload = {
        "prompt": "Test prompt",
        "user_email": test_email
    }
    
    print(f"🧪 Testing rate limiting for {test_email}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        for i in range(5):
            try:
                print(f"\n📤 Request {i+1}:")
                
                async with session.post(
                    f"{base_url}/extract",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        remaining = data.get("remaining_requests", "N/A")
                        print(f"   ✅ Success - Remaining requests: {remaining}")
                        print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                        
                    elif response.status == 429:
                        data = await response.json()
                        print(f"   🔴 Rate limited - {data}")
                        
                    else:
                        text = await response.text()
                        print(f"   ❌ Error: {text[:200]}...")
                        
            except Exception as e:
                print(f"   ❌ Request failed: {str(e)}")
            
            # Small delay between requests
            await asyncio.sleep(0.1)
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    print("🚀 Starting API rate limit test...")
    print("Make sure the API server is running on http://localhost:8000")
    print()
    
    try:
        asyncio.run(test_api_rate_limiting())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
