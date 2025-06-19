#!/usr/bin/env python3
"""
Test script for Dify External Knowledge API
"""

import requests
import json
import time

# API Configuration
API_BASE_URL = "http://localhost:5002"
API_KEY = "codeqa-api-key-2025"
KNOWLEDGE_BASE_ID = "codeqa-java-mall"

def test_health_check():
    """Test health check endpoint"""
    print("🏥 Testing Health Check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"📝 Service: {data['service']}")
            print(f"🔢 Version: {data['version']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_authentication():
    """Test authentication scenarios"""
    print("\n🔐 Testing Authentication...")
    
    # Test 1: Missing Authorization header
    print("📝 Test 1: Missing Authorization header")
    try:
        response = requests.post(
            f"{API_BASE_URL}/retrieval",
            json={"knowledge_id": KNOWLEDGE_BASE_ID, "query": "test"},
            timeout=10
        )
        if response.status_code == 400:
            print("✅ Correctly rejected missing auth header")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Invalid Authorization format
    print("📝 Test 2: Invalid Authorization format")
    try:
        response = requests.post(
            f"{API_BASE_URL}/retrieval",
            headers={"Authorization": "Invalid format"},
            json={"knowledge_id": KNOWLEDGE_BASE_ID, "query": "test"},
            timeout=10
        )
        if response.status_code == 400:
            print("✅ Correctly rejected invalid auth format")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Wrong API key
    print("📝 Test 3: Wrong API key")
    try:
        response = requests.post(
            f"{API_BASE_URL}/retrieval",
            headers={"Authorization": "Bearer wrong-api-key"},
            json={"knowledge_id": KNOWLEDGE_BASE_ID, "query": "test"},
            timeout=10
        )
        if response.status_code == 403:
            print("✅ Correctly rejected wrong API key")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_retrieval_api():
    """Test the main retrieval API"""
    print("\n🔍 Testing Retrieval API...")
    
    test_cases = [
        {
            "name": "用户登录功能",
            "query": "用户登录功能",
            "top_k": 3,
            "score_threshold": 0.5
        },
        {
            "name": "商品管理",
            "query": "商品管理",
            "top_k": 5,
            "score_threshold": 0.4
        },
        {
            "name": "订单处理",
            "query": "订单处理",
            "top_k": 2,
            "score_threshold": 0.6
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['name']}")
        print("-" * 50)
        
        payload = {
            "knowledge_id": KNOWLEDGE_BASE_ID,
            "query": test_case["query"],
            "retrieval_setting": {
                "top_k": test_case["top_k"],
                "score_threshold": test_case["score_threshold"]
            }
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/retrieval",
                headers=headers,
                json=payload,
                timeout=60
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])
                
                print(f"✅ Request successful!")
                print(f"⏱️ Response time: {duration:.2f}s")
                print(f"📊 Records returned: {len(records)}")
                
                if records:
                    print(f"🎯 Score range: {records[-1]['score']:.3f} - {records[0]['score']:.3f}")
                    
                    # Show first result details
                    first_result = records[0]
                    print(f"\n📄 Top Result:")
                    print(f"   Title: {first_result['title']}")
                    print(f"   Score: {first_result['score']}")
                    print(f"   Type: {first_result['metadata']['type']}")
                    print(f"   File: {first_result['metadata']['file_path'].split('/')[-1]}")
                    
                    # Show content preview
                    content_preview = first_result['content'][:100] + "..." if len(first_result['content']) > 100 else first_result['content']
                    print(f"   Content: {content_preview}")
                else:
                    print("⚠️ No records returned")
                    
            else:
                print(f"❌ Request failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text}")
                    
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\n🧪 Testing Edge Cases...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Test 1: Invalid knowledge_id
    print("📝 Test 1: Invalid knowledge_id")
    try:
        response = requests.post(
            f"{API_BASE_URL}/retrieval",
            headers=headers,
            json={
                "knowledge_id": "invalid-kb-id",
                "query": "test",
                "retrieval_setting": {"top_k": 5, "score_threshold": 0.5}
            },
            timeout=10
        )
        if response.status_code == 404:
            print("✅ Correctly rejected invalid knowledge_id")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Missing required fields
    print("📝 Test 2: Missing query field")
    try:
        response = requests.post(
            f"{API_BASE_URL}/retrieval",
            headers=headers,
            json={
                "knowledge_id": KNOWLEDGE_BASE_ID,
                "retrieval_setting": {"top_k": 5, "score_threshold": 0.5}
            },
            timeout=10
        )
        if response.status_code == 400:
            print("✅ Correctly rejected missing query")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Extreme parameters
    print("📝 Test 3: Extreme parameters")
    try:
        response = requests.post(
            f"{API_BASE_URL}/retrieval",
            headers=headers,
            json={
                "knowledge_id": KNOWLEDGE_BASE_ID,
                "query": "test",
                "retrieval_setting": {"top_k": 100, "score_threshold": -0.5}
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            records = data.get("records", [])
            print(f"✅ Handled extreme parameters, returned {len(records)} records")
        else:
            print(f"❌ Failed with extreme parameters: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run all tests"""
    print("🧪 Dify External Knowledge API Test Suite")
    print("=" * 60)
    
    # Test 1: Health Check
    if not test_health_check():
        print("❌ Health check failed, stopping tests")
        return
    
    # Test 2: Authentication
    test_authentication()
    
    # Test 3: Retrieval API
    test_retrieval_api()
    
    # Test 4: Edge Cases
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("🎉 Test suite completed!")
    print("\n📋 Next Steps:")
    print("1. Configure this API in Dify as external knowledge base")
    print("2. Use the following settings:")
    print(f"   - API Endpoint: {API_BASE_URL}/retrieval")
    print(f"   - API Key: {API_KEY}")
    print(f"   - Knowledge Base ID: {KNOWLEDGE_BASE_ID}")

if __name__ == "__main__":
    main()
