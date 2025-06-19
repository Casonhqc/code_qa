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
    
    print(f"OPENAI_BASE_URL: {base_url}")
    print(f"OPENAI_API_KEY: {'*' * 20 + api_key[-10:] if api_key else 'Not set'}")
    
    if not base_url:
        print("❌ OPENAI_BASE_URL not set")
        return False
    
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
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

def main():
    """Run all tests"""
    print("🔍 Testing CodeQA Retrieval-Only Setup\n")
    
    tests = [
        test_env_config,
        test_imports,
        test_openai_client
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
        print("1. Make sure Redis is running: redis-server")
        print("2. Index your codebase: ./index_codebase.sh <path_to_codebase>")
        print("3. Start the app: python app.py <path_to_codebase>")
    else:
        print("❌ Some tests failed. Please check the configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
