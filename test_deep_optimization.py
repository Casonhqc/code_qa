#!/usr/bin/env python3
"""
Deep optimization performance test for Dify API
测试保留所有核心功能的深度优化效果
"""

import requests
import json
import time
import statistics

# API Configuration
ORIGINAL_API = "http://localhost:5002"
FAST_API = "http://localhost:5003" 
OPTIMIZED_API = "http://localhost:5004"
API_KEY = "codeqa-api-key-2025"
KNOWLEDGE_BASE_ID = "codeqa-java-mall"

def test_api_with_modes(api_url, api_name, test_queries):
    """Test API with different performance modes"""
    print(f"\n🧪 Testing {api_name} API ({api_url})")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Test different performance modes
    if "5004" in api_url:  # Optimized API
        test_modes = {
            "fast": {
                "top_k": 5,
                "score_threshold": 0.3,
                "performance_mode": "fast"
            },
            "balanced": {
                "top_k": 5,
                "score_threshold": 0.3,
                "performance_mode": "balanced"
            },
            "quality": {
                "top_k": 5,
                "score_threshold": 0.3,
                "performance_mode": "quality"
            }
        }
    else:
        # Original or fast API
        test_modes = {
            "default": {
                "top_k": 5,
                "score_threshold": 0.3
            }
        }
    
    results = {}
    
    for mode_name, config in test_modes.items():
        print(f"\n📝 Mode: {mode_name}")
        print(f"   Config: {config}")
        print("-" * 40)
        
        times = []
        success_count = 0
        total_results = 0
        quality_scores = []
        
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
                    timeout=120
                )
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("records", [])
                    times.append(duration)
                    success_count += 1
                    total_results += len(records)
                    
                    # Calculate average quality score
                    if records:
                        avg_score = sum(r.get('score', 0) for r in records) / len(records)
                        quality_scores.append(avg_score)
                    
                    print(f"   Query {i}: {duration:.2f}s ({len(records)} results, avg_score: {avg_score:.3f if records else 0:.3f})")
                else:
                    print(f"   Query {i}: FAILED ({response.status_code})")
                    
            except requests.exceptions.Timeout:
                print(f"   Query {i}: TIMEOUT (>120s)")
            except Exception as e:
                print(f"   Query {i}: ERROR ({e})")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            avg_quality = statistics.mean(quality_scores) if quality_scores else 0
            
            print(f"\n📊 Results for {mode_name}:")
            print(f"   Success rate: {success_count}/{len(test_queries)} ({success_count/len(test_queries)*100:.1f}%)")
            print(f"   Average time: {avg_time:.2f}s")
            print(f"   Time range: {min_time:.2f}s - {max_time:.2f}s")
            print(f"   Total results: {total_results}")
            print(f"   Average quality: {avg_quality:.3f}")
            
            results[mode_name] = {
                'success_rate': success_count/len(test_queries),
                'avg_time': avg_time,
                'min_time': min_time,
                'max_time': max_time,
                'total_results': total_results,
                'avg_quality': avg_quality,
                'times': times
            }
        else:
            print(f"\n❌ No successful requests for {mode_name}")
            results[mode_name] = None
    
    return results

def test_cache_effectiveness(api_url):
    """Test cache effectiveness for repeated queries"""
    print(f"\n💾 Testing Cache Effectiveness ({api_url})")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    test_query = "用户登录功能"
    payload = {
        "knowledge_id": KNOWLEDGE_BASE_ID,
        "query": test_query,
        "retrieval_setting": {
            "top_k": 5,
            "score_threshold": 0.3,
            "performance_mode": "balanced"
        }
    }
    
    print(f"🔍 Test Query: '{test_query}'")
    
    # First request
    print("\n📝 First request (cache miss):")
    start_time = time.time()
    response1 = requests.post(f"{api_url}/retrieval", headers=headers, json=payload, timeout=120)
    duration1 = time.time() - start_time
    
    if response1.status_code == 200:
        data1 = response1.json()
        records1 = data1.get("records", [])
        print(f"   ✅ Success: {duration1:.2f}s ({len(records1)} results)")
    else:
        print(f"   ❌ Failed: {response1.status_code}")
        return
    
    # Second request (should hit cache)
    print("📝 Second request (potential cache hit):")
    start_time = time.time()
    response2 = requests.post(f"{api_url}/retrieval", headers=headers, json=payload, timeout=120)
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
            
            if speedup > 3:
                print("   🚀 Excellent cache performance!")
            elif speedup > 2:
                print("   ✅ Good cache performance")
            elif speedup > 1.5:
                print("   📈 Moderate cache performance")
            else:
                print("   ⚠️ Limited cache benefit")
    else:
        print(f"   ❌ Failed: {response2.status_code}")

def compare_optimization_results(original_results, fast_results, optimized_results):
    """Compare results across different optimization approaches"""
    print("\n" + "=" * 80)
    print("📊 DEEP OPTIMIZATION COMPARISON")
    print("=" * 80)
    
    # Compare default/balanced modes
    orig_default = original_results.get('default') if original_results else None
    fast_default = fast_results.get('fast_mode') if fast_results else None
    opt_fast = optimized_results.get('fast') if optimized_results else None
    opt_balanced = optimized_results.get('balanced') if optimized_results else None
    opt_quality = optimized_results.get('quality') if optimized_results else None
    
    print("\n🔍 Performance Comparison:")
    print("-" * 50)
    
    if orig_default:
        print(f"Original API (full):     {orig_default['avg_time']:.2f}s (quality: {orig_default['avg_quality']:.3f})")
    
    if fast_default:
        print(f"Fast API (no HYDE):      {fast_default['avg_time']:.2f}s (quality: {fast_default['avg_quality']:.3f})")
    
    if opt_fast:
        print(f"Optimized Fast:          {opt_fast['avg_time']:.2f}s (quality: {opt_fast['avg_quality']:.3f})")
    
    if opt_balanced:
        print(f"Optimized Balanced:      {opt_balanced['avg_time']:.2f}s (quality: {opt_balanced['avg_quality']:.3f})")
    
    if opt_quality:
        print(f"Optimized Quality:       {opt_quality['avg_time']:.2f}s (quality: {opt_quality['avg_quality']:.3f})")
    
    print("\n🎯 Key Insights:")
    print("-" * 30)
    
    if orig_default and opt_balanced:
        speedup = orig_default['avg_time'] / opt_balanced['avg_time']
        quality_retention = (opt_balanced['avg_quality'] / orig_default['avg_quality']) * 100 if orig_default['avg_quality'] > 0 else 100
        
        print(f"✅ Balanced mode achieves {speedup:.1f}x speedup")
        print(f"✅ Quality retention: {quality_retention:.1f}%")
        
        if speedup >= 2 and quality_retention >= 90:
            print("🚀 Excellent optimization: Significant speedup with quality preservation!")
        elif speedup >= 1.5 and quality_retention >= 85:
            print("✅ Good optimization: Notable improvement with acceptable quality")
        else:
            print("📈 Moderate optimization: Some improvement achieved")
    
    if opt_fast and opt_quality:
        speed_range = f"{opt_fast['avg_time']:.1f}s - {opt_quality['avg_time']:.1f}s"
        quality_range = f"{opt_fast['avg_quality']:.3f} - {opt_quality['avg_quality']:.3f}"
        print(f"🎛️ Performance range: {speed_range} (quality: {quality_range})")

def main():
    """Run comprehensive deep optimization tests"""
    print("🧪 Deep Optimization Performance Test Suite")
    print("=" * 80)
    
    # Test queries
    test_queries = [
        "用户登录功能",
        "商品管理",
        "订单处理",
        "支付功能"
    ]
    
    print(f"📝 Test queries: {test_queries}")
    
    # Check API availability
    apis_to_test = [
        (ORIGINAL_API, "Original"),
        (FAST_API, "Fast"),
        (OPTIMIZED_API, "Deep Optimized")
    ]
    
    available_apis = []
    for api_url, api_name in apis_to_test:
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                available_apis.append((api_url, api_name))
                print(f"✅ {api_name} API available at {api_url}")
            else:
                print(f"❌ {api_name} API not responding at {api_url}")
        except:
            print(f"❌ {api_name} API not available at {api_url}")
    
    if not available_apis:
        print("\n❌ No APIs available for testing!")
        return
    
    # Test each available API
    all_results = {}
    for api_url, api_name in available_apis:
        results = test_api_with_modes(api_url, api_name, test_queries)
        all_results[api_name] = results
        
        # Test cache effectiveness for optimized API
        if "5004" in api_url:
            test_cache_effectiveness(api_url)
    
    # Compare results
    original_results = all_results.get("Original")
    fast_results = all_results.get("Fast")
    optimized_results = all_results.get("Deep Optimized")
    
    if optimized_results:
        compare_optimization_results(original_results, fast_results, optimized_results)
    
    print("\n🎉 Deep optimization testing completed!")
    print("\n💡 Recommendations:")
    print("- Use 'fast' mode for real-time applications requiring <10s response")
    print("- Use 'balanced' mode for optimal speed/quality trade-off")
    print("- Use 'quality' mode when highest accuracy is critical")
    print("- Smart caching provides significant benefits for repeated queries")

if __name__ == "__main__":
    main()
