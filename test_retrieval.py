#!/usr/bin/env python3
"""
Test script for the retrieval-only functionality
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_config():
    """Test that environment variables are properly configured"""
    print("Testing environment configuration...")

    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    redis_host = os.environ.get("REDIS_HOST")
    redis_port = os.environ.get("REDIS_PORT")
    redis_password = os.environ.get("REDIS_PASSWORD")

    print(f"OPENAI_BASE_URL: {base_url}")
    print(f"OPENAI_API_KEY: {'*' * 20 + api_key[-10:] if api_key else 'Not set'}")
    print(f"REDIS_HOST: {redis_host}")
    print(f"REDIS_PORT: {redis_port}")
    print(f"REDIS_PASSWORD: {'*' * 6 if redis_password else 'Not set'}")

    if not base_url:
        print("❌ OPENAI_BASE_URL not set")
        return False

    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return False

    if not redis_host:
        print("❌ REDIS_HOST not set")
        return False

    print("✅ Environment configuration looks good")
    return True

def test_imports():
    """Test that all required modules can be imported"""
    print("\nTesting imports...")
    
    try:
        from openai import OpenAI
        print("✅ OpenAI imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import OpenAI: {e}")
        return False
    
    try:
        import lancedb
        print("✅ LanceDB imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import LanceDB: {e}")
        return False
    
    try:
        from lancedb.rerankers import AnswerdotaiRerankers
        print("✅ Rerankers imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Rerankers: {e}")
        return False
    
    try:
        from flask import Flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Flask: {e}")
        return False

    try:
        import redis
        print("✅ Redis imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Redis: {e}")
        return False

    return True

def test_openai_client():
    """Test OpenAI client initialization"""
    print("\nTesting OpenAI client initialization...")

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL")
        )
        print("✅ OpenAI client initialized successfully")
        print(f"Base URL: {client.base_url}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")
        return False

def test_redis_connection():
    """Test Redis connection"""
    print("\nTesting Redis connection...")

    try:
        import redis

        redis_config = {
            'host': os.environ.get('REDIS_HOST', 'localhost'),
            'port': int(os.environ.get('REDIS_PORT', 6379)),
            'db': int(os.environ.get('REDIS_DB', 0)),
            'socket_timeout': 5,
            'socket_connect_timeout': 5
        }

        # Add password if provided
        if os.environ.get('REDIS_PASSWORD'):
            redis_config['password'] = os.environ.get('REDIS_PASSWORD')

        client = redis.Redis(**redis_config)

        # Test connection
        client.ping()
        print("✅ Redis connection successful")
        print(f"Redis info: {redis_config['host']}:{redis_config['port']}")

        # Test basic operations
        client.set('test_key', 'test_value', ex=10)
        value = client.get('test_key')
        if value and value.decode() == 'test_value':
            print("✅ Redis read/write operations working")
            client.delete('test_key')
        else:
            print("⚠️ Redis read/write test failed")

        return True
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 Testing CodeQA Retrieval-Only Setup\n")
    
    tests = [
        test_env_config,
        test_imports,
        test_openai_client,
        test_redis_connection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The retrieval-only setup looks good.")
        print("\n📝 Next steps:")
        print("1. Index your Java codebase: ./index_codebase.sh $(pwd)/main")
        print("2. Start the app: python3 app.py $(pwd)/main")
        print("3. Open browser: http://localhost:5001")
        print("4. Try queries like: '@codebase 用户登录功能' or '@codebase 商品管理'")
    else:
        print("❌ Some tests failed. Please check the configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
