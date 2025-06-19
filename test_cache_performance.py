#!/usr/bin/env python3
"""
Test cache performance for Fast Dify API
"""

import requests
import json
import time

# API Configuration
FAST_API = "http://localhost:5003"
API_KEY = "codeqa-api-key-2025"
KNOWLEDGE_BASE_ID = "codeqa-java-mall"

def test_cache_performance():
    """Test cache performance"""
    print("💾 Testing Cache Performance")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Test query
    test_query = "用户登录功能"
    
    payload = {
        "knowledge_id": KNOWLEDGE_BASE_ID,
        "query": test_query,
        "retrieval_setting": {
            "top_k": 5,
            "score_threshold": 0.3,
            "use_hyde_v2": False,
            "use_rerank": False
        }
    }
    
    print(f"🔍 Test Query: '{test_query}'")
    print(f"⚙️ Mode: Fast mode (no HYDE-v2, no rerank)")
    print()
    
    # First request (should be slow)
    print("📝 First request (cache miss):")
    start_time = time.time()
    response1 = requests.post(
        f"{FAST_API}/retrieval",
        headers=headers,
        json=payload,
        timeout=30
    )
    duration1 = time.time() - start_time
    
    if response1.status_code == 200:
        data1 = response1.json()
        records1 = data1.get("records", [])
        print(f"   ✅ Success: {duration1:.2f}s ({len(records1)} results)")
    else:
        print(f"   ❌ Failed: {response1.status_code}")
        return
    
    # Second request (should be fast due to cache)
    print("📝 Second request (cache hit):")
    start_time = time.time()
    response2 = requests.post(
        f"{FAST_API}/retrieval",
        headers=headers,
        json=payload,
        timeout=30
    )
    duration2 = time.time() - start_time
    
    if response2.status_code == 200:
        data2 = response2.json()
        records2 = data2.get("records", [])
        print(f"   ✅ Success: {duration2:.2f}s ({len(records2)} results)")
    else:
        print(f"   ❌ Failed: {response2.status_code}")
        return
    
    # Calculate speedup
    if duration2 > 0:
        speedup = duration1 / duration2
        time_saved = duration1 - duration2
        
        print("\n📊 Cache Performance:")
        print(f"   First request:  {duration1:.2f}s")
        print(f"   Second request: {duration2:.2f}s")
        print(f"   Speedup:        {speedup:.1f}x faster")
        print(f"   Time saved:     {time_saved:.2f}s")
        
        if speedup > 10:
            print("   🚀 Excellent cache performance!")
        elif speedup > 5:
            print("   ✅ Good cache performance")
        elif speedup > 2:
            print("   📈 Moderate cache performance")
        else:
            print("   ⚠️ Cache may not be working properly")

def test_different_modes():
    """Test performance of different modes"""
    print("\n⚡ Testing Different Performance Modes")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    test_query = "商品管理"
    
    modes = {
        "Ultra Fast": {
            "top_k": 3,
            "score_threshold": 0.2,
            "use_hyde_v2": False,
            "use_rerank": False
        },
        "Fast": {
            "top_k": 5,
            "score_threshold": 0.3,
            "use_hyde_v2": False,
            "use_rerank": False
        },
        "Balanced": {
            "top_k": 5,
            "score_threshold": 0.4,
            "use_hyde_v2": True,
            "use_rerank": False
        }
    }
    
    print(f"🔍 Test Query: '{test_query}'")
    print()
    
    for mode_name, config in modes.items():
        print(f"📝 Testing {mode_name} Mode:")
        print(f"   Config: {config}")
        
        payload = {
            "knowledge_id": KNOWLEDGE_BASE_ID,
            "query": test_query,
            "retrieval_setting": config
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{FAST_API}/retrieval",
                headers=headers,
                json=payload,
                timeout=60
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])
                print(f"   ✅ Success: {duration:.2f}s ({len(records)} results)")
                
                if records:
                    avg_score = sum(r['score'] for r in records) / len(records)
                    print(f"   📊 Average score: {avg_score:.3f}")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout (>60s)")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()

def main():
    """Run cache performance tests"""
    print("🧪 Fast Dify API Cache & Performance Test")
    print("=" * 60)
    
    # Check API availability
    try:
        response = requests.get(f"{FAST_API}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API Status: {health_data['status']}")
            print(f"📚 Service: {health_data['service']}")
            print(f"🔢 Version: {health_data['version']}")
            
            features = health_data.get('features', {})
            print(f"💾 Cache: {'Enabled' if features.get('cache') else 'Disabled'}")
            print()
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return
    
    # Test cache performance
    test_cache_performance()
    
    # Test different modes
    test_different_modes()
    
    print("🎉 Performance testing completed!")
    print("\n💡 Recommendations:")
    print("- Use Ultra Fast mode for real-time applications")
    print("- Use Fast mode for good balance of speed and quality")
    print("- Use Balanced mode when higher quality is needed")
    print("- Cache provides significant speedup for repeated queries")

if __name__ == "__main__":
    main()
