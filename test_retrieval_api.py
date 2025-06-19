#!/usr/bin/env python3
"""
Test script for the retrieval API functionality
"""

import requests
import json
import time

def test_retrieval_api():
    """Test the retrieval API with various queries"""
    base_url = "http://localhost:5001"
    
    # Test queries for the Java mall project
    test_queries = [
        "@codebase 用户登录功能",
        "@codebase 商品管理",
        "@codebase 订单处理",
        "@codebase 秒杀功能",
        "@codebase 优惠券系统",
        "@codebase Redis缓存",
        "@codebase 支付功能",
        "@codebase 购物车",
        "@codebase 用户注册",
        "@codebase 商品搜索",
        "@codebase 数据库配置",
        "@codebase 异常处理",
        "@codebase 文件上传",
        "@codebase 权限验证",
        "@codebase 定时任务"
    ]
    
    print("🔍 Testing CodeQA Retrieval API\n")
    
    # Wait for server to be ready
    print("Waiting for server to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(base_url, timeout=5)
            if response.status_code == 200:
                print("✅ Server is ready!")
                break
        except requests.exceptions.RequestException:
            pass
        
        if i == max_retries - 1:
            print("❌ Server is not responding after 30 attempts")
            return False
        
        print(f"Attempt {i+1}/{max_retries}...")
        time.sleep(2)
    
    print("\n" + "="*60)
    print("Testing Retrieval Queries")
    print("="*60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Query {i}: {query}")
        print("-" * 50)
        
        try:
            # Test with reranking disabled
            response = requests.post(
                base_url,
                json={"query": query, "rerank": False},
                headers={
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                retrieved_context = data.get('response', '')
                
                if retrieved_context:
                    print("✅ Retrieval successful!")
                    print(f"📄 Context length: {len(retrieved_context)} characters")
                    
                    # Show first 200 characters of retrieved context
                    preview = retrieved_context[:200] + "..." if len(retrieved_context) > 200 else retrieved_context
                    print(f"📝 Preview: {preview}")
                    
                    # Count number of files mentioned
                    file_count = retrieved_context.count("File:")
                    print(f"📁 Files referenced: {file_count}")
                else:
                    print("⚠️ No context retrieved")
            else:
                print(f"❌ Request failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        
        # Small delay between requests
        time.sleep(1)
    
    print("\n" + "="*60)
    print("Testing with Reranking")
    print("="*60)
    
    # Test one query with reranking enabled
    test_query = "@codebase 用户登录功能"
    print(f"\n🔍 Query with reranking: {test_query}")
    print("-" * 50)
    
    try:
        response = requests.post(
            base_url,
            json={"query": test_query, "rerank": True},
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            retrieved_context = data.get('response', '')
            
            if retrieved_context:
                print("✅ Reranked retrieval successful!")
                print(f"📄 Context length: {len(retrieved_context)} characters")
                
                # Show first 200 characters
                preview = retrieved_context[:200] + "..." if len(retrieved_context) > 200 else retrieved_context
                print(f"📝 Preview: {preview}")
                
                file_count = retrieved_context.count("File:")
                print(f"📁 Files referenced: {file_count}")
            else:
                print("⚠️ No context retrieved")
        else:
            print(f"❌ Request failed with status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    print("\n" + "="*60)
    print("🎉 Retrieval API testing completed!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    test_retrieval_api()
