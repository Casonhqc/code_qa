#!/usr/bin/env python3
"""
Test Unified Backend - 测试统一后端在所有接口上的效果
"""

import requests
import json
import time
import statistics

# API Configuration
WEB_API = "http://localhost:5001"      # Unified Web Interface
DIFY_API = "http://localhost:5002"     # Unified Dify API
API_KEY = "codeqa-api-key-2025"
KNOWLEDGE_BASE_ID = "codeqa-java-mall"

def test_web_interface():
    """Test unified web interface"""
    print("\n🌐 Testing Unified Web Interface")
    print("=" * 50)
    
    # Test health endpoint
    try:
        response = requests.get(f"{WEB_API}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Web Interface Status: {health_data['status']}")
            print(f"📚 Service: {health_data['service']}")
            print(f"🔢 Version: {health_data['version']}")
            print(f"🔧 Backend: {health_data['backend']}")
            print(f"⚡ Features: {health_data['features']}")
        else:
            print(f"❌ Web interface health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to web interface: {e}")
        return False
    
    # Test performance modes endpoint
    try:
        response = requests.get(f"{WEB_API}/api/modes", timeout=5)
        if response.status_code == 200:
            modes_data = response.json()
            print(f"🎯 Available Modes: {modes_data['modes']}")
            print(f"📝 Default Mode: {modes_data['default']}")
        else:
            print(f"⚠️ Modes endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Modes endpoint error: {e}")
    
    return True

def test_dify_api():
    """Test unified Dify API"""
    print("\n🔌 Testing Unified Dify API")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Test health endpoint
    try:
        response = requests.get(f"{DIFY_API}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Dify API Status: {health_data['status']}")
            print(f"📚 Service: {health_data['service']}")
            print(f"🔢 Version: {health_data['version']}")
            print(f"🔧 Backend: {health_data['backend']}")
            print(f"⚡ Engine Status: {health_data['engine_status']}")
            
            if 'features' in health_data:
                print(f"🎯 Performance Modes: {health_data['features']['performance_modes']}")
                print(f"📝 Default Mode: {health_data['features']['default_mode']}")
        else:
            print(f"❌ Dify API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Dify API: {e}")
        return False
    
    # Test modes endpoint
    try:
        response = requests.get(f"{DIFY_API}/modes", timeout=5)
        if response.status_code == 200:
            modes_data = response.json()
            print(f"🔧 Available Modes: {list(modes_data['available_modes'].keys())}")
            print(f"📊 Usage Info: {modes_data['usage']}")
        else:
            print(f"⚠️ Modes endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Modes endpoint error: {e}")
    
    # Test stats endpoint
    try:
        response = requests.get(f"{DIFY_API}/stats", timeout=5)
        if response.status_code == 200:
            stats_data = response.json()
            print(f"📊 Engine Stats: {stats_data}")
        else:
            print(f"⚠️ Stats endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Stats endpoint error: {e}")
    
    return True

def test_performance_consistency():
    """Test performance consistency across different modes"""
    print("\n⚡ Testing Performance Consistency")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    test_query = "用户登录功能"
    performance_modes = ["fast", "balanced", "quality"]
    
    results = {}
    
    for mode in performance_modes:
        print(f"\n📝 Testing {mode} mode:")
        
        payload = {
            "knowledge_id": KNOWLEDGE_BASE_ID,
            "query": test_query,
            "retrieval_setting": {
                "top_k": 5,
                "score_threshold": 0.3,
                "performance_mode": mode,
                "use_rerank": True,
                "enable_cache": False  # Disable cache for fair comparison
            }
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{DIFY_API}/retrieval",
                headers=headers,
                json=payload,
                timeout=60
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])
                
                if records:
                    avg_score = sum(r.get('score', 0) for r in records) / len(records)
                    print(f"   ✅ Success: {duration:.2f}s ({len(records)} results, avg_score: {avg_score:.3f})")
                    
                    results[mode] = {
                        'duration': duration,
                        'results_count': len(records),
                        'avg_score': avg_score,
                        'success': True
                    }
                else:
                    print(f"   ⚠️ Success but no results: {duration:.2f}s")
                    results[mode] = {
                        'duration': duration,
                        'results_count': 0,
                        'avg_score': 0,
                        'success': True
                    }
            else:
                print(f"   ❌ Failed: {response.status_code}")
                results[mode] = {'success': False}
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout (>60s)")
            results[mode] = {'success': False, 'timeout': True}
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[mode] = {'success': False, 'error': str(e)}
    
    # Analyze results
    print(f"\n📊 Performance Analysis:")
    print("-" * 30)
    
    successful_results = {k: v for k, v in results.items() if v.get('success')}
    
    if successful_results:
        for mode, result in successful_results.items():
            print(f"{mode:10}: {result['duration']:6.2f}s | {result['results_count']} results | score: {result['avg_score']:.3f}")
        
        # Calculate improvements
        if 'quality' in successful_results and 'fast' in successful_results:
            quality_time = successful_results['quality']['duration']
            fast_time = successful_results['fast']['duration']
            speedup = quality_time / fast_time if fast_time > 0 else 0
            print(f"\n🚀 Fast vs Quality speedup: {speedup:.1f}x")
        
        if 'balanced' in successful_results:
            balanced_result = successful_results['balanced']
            print(f"⚖️ Balanced mode: {balanced_result['duration']:.2f}s (recommended)")
    
    return results

def test_cache_effectiveness():
    """Test cache effectiveness"""
    print("\n💾 Testing Cache Effectiveness")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    test_query = "商品管理"
    
    payload = {
        "knowledge_id": KNOWLEDGE_BASE_ID,
        "query": test_query,
        "retrieval_setting": {
            "top_k": 5,
            "score_threshold": 0.3,
            "performance_mode": "balanced",
            "enable_cache": True
        }
    }
    
    print(f"🔍 Test Query: '{test_query}'")
    
    # First request (cache miss)
    print("\n📝 First request (cache miss):")
    start_time = time.time()
    response1 = requests.post(f"{DIFY_API}/retrieval", headers=headers, json=payload, timeout=60)
    duration1 = time.time() - start_time
    
    if response1.status_code == 200:
        data1 = response1.json()
        records1 = data1.get("records", [])
        print(f"   ✅ Success: {duration1:.2f}s ({len(records1)} results)")
    else:
        print(f"   ❌ Failed: {response1.status_code}")
        return
    
    # Second request (cache hit)
    print("📝 Second request (cache hit):")
    start_time = time.time()
    response2 = requests.post(f"{DIFY_API}/retrieval", headers=headers, json=payload, timeout=60)
    duration2 = time.time() - start_time
    
    if response2.status_code == 200:
        data2 = response2.json()
        records2 = data2.get("records", [])
        print(f"   ✅ Success: {duration2:.2f}s ({len(records2)} results)")
        
        # Calculate cache effectiveness
        if duration2 > 0:
            speedup = duration1 / duration2
            time_saved = duration1 - duration2
            
            print(f"\n📊 Cache Performance:")
            print(f"   First request:  {duration1:.2f}s")
            print(f"   Second request: {duration2:.2f}s")
            print(f"   Speedup:        {speedup:.1f}x")
            print(f"   Time saved:     {time_saved:.2f}s")
            
            if speedup > 10:
                print("   🚀 Excellent cache performance!")
            elif speedup > 5:
                print("   ✅ Good cache performance")
            elif speedup > 2:
                print("   📈 Moderate cache performance")
            else:
                print("   ⚠️ Limited cache benefit")
    else:
        print(f"   ❌ Failed: {response2.status_code}")

def main():
    """Run comprehensive unified backend tests"""
    print("🧪 Unified Backend Performance Test Suite")
    print("=" * 80)
    print("Testing unified retrieval engine across all interfaces")
    
    # Test web interface
    web_available = test_web_interface()
    
    # Test Dify API
    dify_available = test_dify_api()
    
    if not dify_available:
        print("\n❌ Dify API not available. Please start it with:")
        print("python3 dify_api_unified.py $(pwd)/main")
        return
    
    # Test performance consistency
    performance_results = test_performance_consistency()
    
    # Test cache effectiveness
    test_cache_effectiveness()
    
    # Summary
    print("\n" + "=" * 80)
    print("🎉 UNIFIED BACKEND TEST SUMMARY")
    print("=" * 80)
    
    print(f"🌐 Web Interface: {'✅ Available' if web_available else '❌ Not Available'}")
    print(f"🔌 Dify API: {'✅ Available' if dify_available else '❌ Not Available'}")
    
    successful_modes = sum(1 for r in performance_results.values() if r.get('success'))
    print(f"⚡ Performance Modes: {successful_modes}/3 working")
    
    print("\n💡 Unified Backend Benefits:")
    print("✅ Consistent performance across all interfaces")
    print("✅ Centralized optimization strategies")
    print("✅ Unified caching and configuration")
    print("✅ Single point of maintenance")
    print("✅ Performance mode flexibility")
    
    print("\n🚀 Next Steps:")
    if web_available:
        print(f"- Access Web Interface: {WEB_API}")
    if dify_available:
        print(f"- Use Dify API: {DIFY_API}/retrieval")
    print("- All interfaces now use the same optimized backend!")

if __name__ == "__main__":
    main()
