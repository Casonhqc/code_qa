#!/usr/bin/env python3
"""
Simple test for the improved retrieval functionality
"""

import requests
import json
import time

def test_single_query():
    """Test a single query to see the improved logging and results"""
    base_url = "http://localhost:5001"
    test_query = "@codebase 用户登录功能"
    
    print("🔍 Testing Improved Retrieval System")
    print("="*50)
    print(f"Query: {test_query}")
    print("-"*50)
    
    try:
        # Test without reranking first
        print("📝 Testing without reranking...")
        response = requests.post(
            base_url,
            json={"query": test_query, "rerank": False},
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('response', '')
            
            print("✅ Request successful!")
            print(f"📊 Response length: {len(result)} characters")
            print("\n📄 Response preview:")
            print("-"*30)
            # Show first 500 characters
            preview = result[:500] + "..." if len(result) > 500 else result
            print(preview)
            print("-"*30)
            
            # Count sections
            method_count = result.count("=== METHOD")
            class_count = result.count("=== CLASS")
            print(f"\n📊 Results summary:")
            print(f"   Methods found: {method_count}")
            print(f"   Classes found: {class_count}")
            
        else:
            print(f"❌ Request failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    print("\n" + "="*50)
    print("🎉 Test completed!")

if __name__ == "__main__":
    test_single_query()
