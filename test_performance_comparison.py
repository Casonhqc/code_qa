#!/usr/bin/env python3
"""
Performance comparison test between original and fast Dify API
"""

import requests
import json
import time
import statistics

# API Configuration
ORIGINAL_API = "http://localhost:5002"
FAST_API = "http://localhost:5003"
API_KEY = "codeqa-api-key-2025"
KNOWLEDGE_BASE_ID = "codeqa-java-mall"

def test_api_performance(api_url, api_name, test_queries, test_configs):
    """Test API performance with different configurations"""
    print(f"\n🧪 Testing {api_name} API ({api_url})")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    results = {}
    
    for config_name, config in test_configs.items():
        print(f"\n📝 Configuration: {config_name}")
        print(f"   Settings: {config}")
        print("-" * 40)
        
        times = []
        success_count = 0
        
        for i, query in enumerate(test_queries, 1):
            payload = {
                "knowledge_id": KNOWLEDGE_BASE_ID,
                "query": query,
                "retrieval_setting": config
            }
            
            try:
                start_time = time.time()
                response = requests.post(
                    f"{api_url}/retrieval",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("records", [])
                    times.append(duration)
                    success_count += 1
                    
                    print(f"   Query {i}: {duration:.2f}s ({len(records)} results)")
                else:
                    print(f"   Query {i}: FAILED ({response.status_code})")
                    
            except requests.exceptions.Timeout:
                print(f"   Query {i}: TIMEOUT")
            except Exception as e:
                print(f"   Query {i}: ERROR ({e})")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"\n📊 Results for {config_name}:")
            print(f"   Success rate: {success_count}/{len(test_queries)} ({success_count/len(test_queries)*100:.1f}%)")
            print(f"   Average time: {avg_time:.2f}s")
            print(f"   Min time: {min_time:.2f}s")
            print(f"   Max time: {max_time:.2f}s")
            
            results[config_name] = {
                'success_rate': success_count/len(test_queries),
                'avg_time': avg_time,
                'min_time': min_time,
                'max_time': max_time,
                'times': times
            }
        else:
            print(f"\n❌ No successful requests for {config_name}")
            results[config_name] = None
    
    return results

def compare_results(original_results, fast_results):
    """Compare performance results"""
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE COMPARISON")
    print("=" * 80)
    
    for config_name in original_results.keys():
        print(f"\n🔍 Configuration: {config_name}")
        print("-" * 50)
        
        orig = original_results.get(config_name)
        fast = fast_results.get(config_name)
        
        if orig and fast:
            speedup = orig['avg_time'] / fast['avg_time']
            time_saved = orig['avg_time'] - fast['avg_time']
            
            print(f"Original API:  {orig['avg_time']:.2f}s (range: {orig['min_time']:.2f}-{orig['max_time']:.2f}s)")
            print(f"Fast API:      {fast['avg_time']:.2f}s (range: {fast['min_time']:.2f}-{fast['max_time']:.2f}s)")
            print(f"Speedup:       {speedup:.1f}x faster")
            print(f"Time saved:    {time_saved:.2f}s per request")
            
            if speedup > 2:
                print("🚀 Significant improvement!")
            elif speedup > 1.5:
                print("✅ Good improvement")
            elif speedup > 1.1:
                print("📈 Moderate improvement")
            else:
                print("⚠️ Minimal improvement")
        else:
            print("❌ Cannot compare - missing data")

def main():
    """Run performance comparison tests"""
    print("⚡ Dify API Performance Comparison Test")
    print("=" * 80)
    
    # Test queries
    test_queries = [
        "用户登录功能",
        "商品管理",
        "订单处理"
    ]
    
    # Test configurations
    test_configs = {
        "fast_mode": {
            "top_k": 5,
            "score_threshold": 0.3,
            "use_hyde_v2": False,
            "use_rerank": False
        },
        "balanced_mode": {
            "top_k": 5,
            "score_threshold": 0.3,
            "use_hyde_v2": True,
            "use_rerank": False
        },
        "quality_mode": {
            "top_k": 5,
            "score_threshold": 0.3,
            "use_hyde_v2": True,
            "use_rerank": True
        }
    }
    
    # Test original API (if available)
    print("🔍 Checking API availability...")
    
    original_available = False
    fast_available = False
    
    try:
        response = requests.get(f"{ORIGINAL_API}/health", timeout=5)
        if response.status_code == 200:
            original_available = True
            print(f"✅ Original API available at {ORIGINAL_API}")
    except:
        print(f"❌ Original API not available at {ORIGINAL_API}")
    
    try:
        response = requests.get(f"{FAST_API}/health", timeout=5)
        if response.status_code == 200:
            fast_available = True
            print(f"✅ Fast API available at {FAST_API}")
    except:
        print(f"❌ Fast API not available at {FAST_API}")
    
    if not fast_available:
        print("\n❌ Fast API is not available. Please start it with:")
        print("python3 dify_api_fast.py $(pwd)/main")
        return
    
    # Test Fast API
    fast_results = test_api_performance(FAST_API, "Fast", test_queries, test_configs)
    
    # Test Original API if available
    if original_available:
        # Only test basic mode for original API (to avoid long waits)
        original_test_configs = {
            "quality_mode": {
                "top_k": 5,
                "score_threshold": 0.5
            }
        }
        original_results = test_api_performance(ORIGINAL_API, "Original", test_queries[:1], original_test_configs)
        
        # Compare results
        if original_results and fast_results:
            # Map fast balanced_mode to original quality_mode for comparison
            comparison_fast = {"quality_mode": fast_results.get("balanced_mode")}
            compare_results(original_results, comparison_fast)
    else:
        print("\n📊 Fast API Performance Summary:")
        print("=" * 50)
        
        for config_name, result in fast_results.items():
            if result:
                print(f"{config_name:15}: {result['avg_time']:.2f}s average")
        
        print("\n💡 Recommendations:")
        print("- Use 'fast_mode' for real-time applications (< 5s)")
        print("- Use 'balanced_mode' for good quality with reasonable speed")
        print("- Use 'quality_mode' only when highest accuracy is needed")
    
    print("\n🎉 Performance testing completed!")

if __name__ == "__main__":
    main()
