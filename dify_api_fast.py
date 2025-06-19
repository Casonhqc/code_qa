#!/usr/bin/env python3
"""
Dify External Knowledge Base API - Fast Version
优化版本：大幅减少响应时间
"""

from flask import Flask, request, jsonify
import os
import sys
import time
import logging
import lancedb
from lancedb.rerankers import AnswerdotaiRerankers
from openai import OpenAI
from dotenv import load_dotenv
import hashlib
import json
import redis

# Load environment variables
load_dotenv()

# Import existing functions
from app import (
    setup_logging, setup_database, openai_hyde, 
    enhance_query, CONFIG
)

# Dify API Configuration
DIFY_CONFIG = {
    'API_KEY': os.environ.get('DIFY_API_KEY', 'codeqa-api-key-2025'),
    'KNOWLEDGE_BASE_ID': os.environ.get('KNOWLEDGE_BASE_ID', 'codeqa-java-mall'),
    'DEFAULT_TOP_K': 5,
    'DEFAULT_SCORE_THRESHOLD': 0.3,  # 降低默认阈值
    'MAX_TOP_K': 20,
    'MIN_SCORE_THRESHOLD': 0.0,
    'CACHE_TTL': 3600,  # 缓存1小时
    'USE_HYDE_V2': False,  # 默认关闭HYDE-v2
    'USE_RERANK': False,   # 默认关闭重排序
}

# Create Flask app for Dify API
dify_app = Flask(__name__)
dify_app.config.update(CONFIG)

# Setup logging
logger = setup_logging(CONFIG)

# Global variables
method_table = None
class_table = None
reranker = None
client = None
redis_client = None

def init_dify_api(codebase_path):
    """Initialize the Dify API with codebase"""
    global method_table, class_table, reranker, client, redis_client
    
    logger.info("🚀 Initializing Fast Dify API...")
    
    # Setup database
    method_table, class_table = setup_database(codebase_path)
    logger.info("✅ Database tables loaded")
    
    # Initialize reranker (lazy loading)
    reranker = None  # 延迟加载
    logger.info("✅ Reranker set to lazy loading")
    
    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL")
    )
    logger.info("✅ OpenAI client initialized")
    
    # Initialize Redis for caching
    try:
        redis_config = {
            'host': os.environ.get('REDIS_HOST', 'localhost'),
            'port': int(os.environ.get('REDIS_PORT', 6379)),
            'db': int(os.environ.get('REDIS_DB', 0)),
            'socket_timeout': 5,
            'socket_connect_timeout': 5
        }
        
        if os.environ.get('REDIS_PASSWORD'):
            redis_config['password'] = os.environ.get('REDIS_PASSWORD')
        
        redis_client = redis.Redis(**redis_config)
        redis_client.ping()  # Test connection
        logger.info("✅ Redis cache initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis cache not available: {e}")
        redis_client = None
    
    logger.info("🎉 Fast Dify API initialization completed")

def get_cache_key(query, top_k, score_threshold, use_hyde_v2, use_rerank):
    """Generate cache key for query"""
    key_data = f"{query}:{top_k}:{score_threshold}:{use_hyde_v2}:{use_rerank}"
    return f"dify_cache:{hashlib.md5(key_data.encode()).hexdigest()}"

def get_cached_result(cache_key):
    """Get cached result"""
    if not redis_client:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info("🎯 Cache hit!")
            return json.loads(cached.decode())
    except Exception as e:
        logger.warning(f"⚠️ Cache read error: {e}")
    
    return None

def set_cached_result(cache_key, result):
    """Set cached result"""
    if not redis_client:
        return
    
    try:
        redis_client.setex(
            cache_key, 
            DIFY_CONFIG['CACHE_TTL'], 
            json.dumps(result)
        )
        logger.info("💾 Result cached")
    except Exception as e:
        logger.warning(f"⚠️ Cache write error: {e}")

def fast_retrieval(query, top_k=5, score_threshold=0.3, use_hyde_v2=False, use_rerank=False):
    """
    Fast retrieval function optimized for speed
    """
    start_time = time.time()
    logger.info(f"🚀 Fast retrieval for query: '{query}' (top_k={top_k}, threshold={score_threshold})")
    
    # Check cache first
    cache_key = get_cache_key(query, top_k, score_threshold, use_hyde_v2, use_rerank)
    cached_result = get_cached_result(cache_key)
    if cached_result:
        logger.info(f"✅ Cache hit! Returned in {time.time() - start_time:.2f}s")
        return cached_result, None
    
    try:
        # Step 1: Enhance query (fast)
        enhanced_query_text = enhance_query(query)
        logger.info(f"🔧 Enhanced query: '{enhanced_query_text}'")
        
        # Step 2: Choose retrieval strategy
        if use_hyde_v2:
            # Full HYDE pipeline (slower but better quality)
            hyde_query = openai_hyde(enhanced_query_text)
            logger.info(f"✅ HYDE query generated")
            
            # Initial search for HYDE-v2 context
            method_search_initial = method_table.search(hyde_query).limit(top_k * 2)
            class_search_initial = class_table.search(hyde_query).limit(top_k * 2)
            
            method_docs_initial = method_search_initial.to_pandas()
            class_docs_initial = class_search_initial.to_pandas()
            
            # Generate context for HYDE v2
            if len(method_docs_initial) > 0 and len(class_docs_initial) > 0:
                temp_context = '\n'.join(method_docs_initial['code'][:2].tolist() + 
                                       class_docs_initial['source_code'][:2].tolist())
            elif len(method_docs_initial) > 0:
                temp_context = '\n'.join(method_docs_initial['code'][:3].tolist())
            elif len(class_docs_initial) > 0:
                temp_context = '\n'.join(class_docs_initial['source_code'][:3].tolist())
            else:
                temp_context = ""
            
            # HYDE v2 query generation
            from app import openai_hyde_v2
            final_query = openai_hyde_v2(enhanced_query_text, temp_context, hyde_query)
            logger.info(f"✅ HYDE v2 query generated")
        else:
            # Direct search (much faster)
            final_query = enhanced_query_text
            logger.info(f"⚡ Using direct search (no HYDE)")
        
        # Step 3: Final search
        search_limit = min(top_k * 3, 15)  # 限制搜索范围
        method_search = method_table.search(final_query).limit(search_limit)
        class_search = class_table.search(final_query).limit(search_limit)
        
        # Step 4: Apply reranking if requested
        if use_rerank:
            global reranker
            if reranker is None:
                logger.info("🔄 Loading reranker...")
                reranker = AnswerdotaiRerankers(column="source_code")
            
            method_search = method_search.rerank(reranker)
            class_search = class_search.rerank(reranker)
            logger.info("✅ Reranking applied")
        
        # Step 5: Get results and format
        method_docs = method_search.to_list()
        class_docs = class_search.to_list()
        
        # Combine and sort by score
        all_results = []
        
        # Process method results
        for doc in method_docs:
            score = 1.0 - doc.get('_distance', 0.5)
            if score >= score_threshold:
                all_results.append({
                    'content': doc['code'],
                    'score': round(score, 4),
                    'title': f"Method in {os.path.basename(doc['file_path'])}",
                    'metadata': {
                        'file_path': doc['file_path'],
                        'type': 'method',
                        'method_name': doc.get('method_name', 'Unknown'),
                        'class_name': doc.get('class_name', 'Unknown')
                    }
                })
        
        # Process class results
        for doc in class_docs:
            score = 1.0 - doc.get('_distance', 0.5)
            if score >= score_threshold:
                all_results.append({
                    'content': doc['source_code'],
                    'score': round(score, 4),
                    'title': f"Class in {os.path.basename(doc['file_path'])}",
                    'metadata': {
                        'file_path': doc['file_path'],
                        'type': 'class',
                        'class_name': doc.get('class_name', 'Unknown'),
                        'references': doc.get('references', 'N/A')
                    }
                })
        
        # Sort by score and limit
        all_results.sort(key=lambda x: x['score'], reverse=True)
        final_results = all_results[:top_k]
        
        duration = time.time() - start_time
        logger.info(f"✅ Fast retrieval completed in {duration:.2f}s, returned {len(final_results)} results")
        
        # Cache the result
        set_cached_result(cache_key, final_results)
        
        return final_results, None
        
    except Exception as e:
        logger.error(f"❌ Error in fast retrieval: {str(e)}")
        return None, {
            "error_code": 500,
            "error_msg": f"Internal server error: {str(e)}"
        }

def authenticate_request():
    """Authenticate API request using Bearer token"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return False, {"error_code": 1001, "error_msg": "Missing Authorization header"}
    
    if not auth_header.startswith('Bearer '):
        return False, {"error_code": 1001, "error_msg": "Invalid Authorization header format"}
    
    api_key = auth_header[7:]
    
    if api_key != DIFY_CONFIG['API_KEY']:
        return False, {"error_code": 1002, "error_msg": "Authorization failed"}
    
    return True, None

def validate_knowledge_id(knowledge_id):
    """Validate knowledge base ID"""
    if knowledge_id != DIFY_CONFIG['KNOWLEDGE_BASE_ID']:
        return False, {"error_code": 2001, "error_msg": "Knowledge base does not exist"}
    return True, None

@dify_app.route('/retrieval', methods=['POST'])
def dify_retrieval():
    """Fast Dify External Knowledge Base API endpoint"""
    try:
        # Authentication
        is_authenticated, auth_error = authenticate_request()
        if not is_authenticated:
            return jsonify(auth_error), 403 if auth_error['error_code'] == 1002 else 400
        
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"error_code": 1001, "error_msg": "Invalid JSON data"}), 400
        
        # Validate required fields
        knowledge_id = data.get('knowledge_id')
        query = data.get('query')
        retrieval_setting = data.get('retrieval_setting', {})
        
        if not knowledge_id:
            return jsonify({"error_code": 1001, "error_msg": "Missing required field: knowledge_id"}), 400
        
        if not query:
            return jsonify({"error_code": 1001, "error_msg": "Missing required field: query"}), 400
        
        # Validate knowledge base ID
        is_valid_kb, kb_error = validate_knowledge_id(knowledge_id)
        if not is_valid_kb:
            return jsonify(kb_error), 404
        
        # Extract retrieval settings
        top_k = retrieval_setting.get('top_k', DIFY_CONFIG['DEFAULT_TOP_K'])
        score_threshold = retrieval_setting.get('score_threshold', DIFY_CONFIG['DEFAULT_SCORE_THRESHOLD'])
        
        # Advanced settings (optional)
        use_hyde_v2 = retrieval_setting.get('use_hyde_v2', DIFY_CONFIG['USE_HYDE_V2'])
        use_rerank = retrieval_setting.get('use_rerank', DIFY_CONFIG['USE_RERANK'])
        
        # Validate parameters
        top_k = max(1, min(top_k, DIFY_CONFIG['MAX_TOP_K']))
        score_threshold = max(DIFY_CONFIG['MIN_SCORE_THRESHOLD'], min(score_threshold, 1.0))
        
        logger.info(f"📝 Fast API request: query='{query}', top_k={top_k}, threshold={score_threshold}, hyde_v2={use_hyde_v2}, rerank={use_rerank}")
        
        # Perform fast retrieval
        results, error = fast_retrieval(query, top_k, score_threshold, use_hyde_v2, use_rerank)
        
        if error:
            return jsonify(error), 500
        
        # Return results
        response = {"records": results}
        logger.info(f"✅ Fast API response: {len(results)} records returned")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Fast API error: {str(e)}")
        return jsonify({"error_code": 500, "error_msg": f"Internal server error: {str(e)}"}), 500

@dify_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "CodeQA Fast Dify External Knowledge API",
        "version": "2.0.0",
        "features": {
            "cache": redis_client is not None,
            "hyde_v2": "optional",
            "rerank": "optional"
        }
    }), 200

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dify_api_fast.py <codebase_path>")
        sys.exit(1)
    
    codebase_path = sys.argv[1]
    
    # Initialize the API
    init_dify_api(codebase_path)
    
    # Run the Fast Dify API server
    print("⚡ Starting Fast Dify External Knowledge API...")
    print(f"📚 Knowledge Base ID: {DIFY_CONFIG['KNOWLEDGE_BASE_ID']}")
    print(f"🔑 API Key: {DIFY_CONFIG['API_KEY'][:10]}...")
    print(f"💾 Cache: {'Enabled' if redis_client else 'Disabled'}")
    print(f"🔧 HYDE-v2: {'Optional' if not DIFY_CONFIG['USE_HYDE_V2'] else 'Default'}")
    print(f"🔄 Rerank: {'Optional' if not DIFY_CONFIG['USE_RERANK'] else 'Default'}")
    print("🌐 Server running on http://0.0.0.0:5003")
    
    dify_app.run(host='0.0.0.0', port=5003, debug=False)
