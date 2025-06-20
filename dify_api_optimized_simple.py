#!/usr/bin/env python3
"""
Dify External Knowledge Base API - Simplified Deep Optimization
保留所有核心功能的深度性能优化版本（简化依赖）
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
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Import existing functions
from app import setup_logging, setup_database, enhance_query, CONFIG

# Optimized Dify API Configuration
DIFY_CONFIG = {
    'API_KEY': os.environ.get('DIFY_API_KEY', 'codeqa-api-key-2025'),
    'KNOWLEDGE_BASE_ID': os.environ.get('KNOWLEDGE_BASE_ID', 'codeqa-java-mall'),
    'DEFAULT_TOP_K': 5,
    'DEFAULT_SCORE_THRESHOLD': 0.3,
    'MAX_TOP_K': 20,
    'MIN_SCORE_THRESHOLD': 0.0,
    'ENABLE_CACHE': True,
    'CACHE_TTL': 1800,  # 30 minutes
}

# Performance modes with optimized settings
PERFORMANCE_MODES = {
    "fast": {
        "hyde_model": "gpt-3.5-turbo",
        "hyde_v2_model": "gpt-3.5-turbo",
        "max_tokens_hyde": 150,
        "max_tokens_hyde_v2": 100,
        "search_limit": 10,
        "context_size": 2,
        "target_time": "6-8s"
    },
    "balanced": {
        "hyde_model": "gpt-4o-mini",
        "hyde_v2_model": "gpt-3.5-turbo",
        "max_tokens_hyde": 200,
        "max_tokens_hyde_v2": 150,
        "search_limit": 15,
        "context_size": 3,
        "target_time": "8-12s"
    },
    "quality": {
        "hyde_model": "gpt-4o-mini",
        "hyde_v2_model": "gpt-4o-mini",
        "max_tokens_hyde": 250,
        "max_tokens_hyde_v2": 200,
        "search_limit": 20,
        "context_size": 4,
        "target_time": "10-15s"
    }
}

# Optimized prompts
OPTIMIZED_PROMPTS = {
    "hyde_fast": "Generate code for: {query}\nInclude method names, class names, key concepts.\nOutput code only.",
    "hyde_balanced": "Generate relevant code for the query. Focus on method names, class names, and key programming concepts. Output only the code snippet.",
    "hyde_v2_fast": "Enhance query: {query}\nUsing context: {context}\nOutput enhanced query only.",
    "hyde_v2_balanced": "Enhance the query using the provided context. Query: {query}\nContext: {context}\nOutput the enhanced query only."
}

# Create Flask app
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
executor = None

def init_optimized_api(codebase_path):
    """Initialize the optimized API"""
    global method_table, class_table, reranker, client, redis_client, executor
    
    logger.info("🚀 Initializing Simplified Optimized Dify API...")
    
    # Setup database
    method_table, class_table = setup_database(codebase_path)
    logger.info("✅ Database tables loaded")
    
    # Initialize thread pool
    executor = ThreadPoolExecutor(max_workers=2)
    logger.info("✅ Thread pool initialized")
    
    # Initialize reranker (lazy loading)
    reranker = None
    logger.info("✅ Reranker set to lazy loading")
    
    # Initialize optimized OpenAI client
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        max_retries=2,
        timeout=15.0
    )
    logger.info("✅ Optimized OpenAI client initialized")
    
    # Initialize Redis cache
    try:
        redis_config = {
            'host': os.environ.get('REDIS_HOST', 'localhost'),
            'port': int(os.environ.get('REDIS_PORT', 6379)),
            'db': int(os.environ.get('REDIS_DB', 0)),
            'socket_timeout': 3,
            'socket_connect_timeout': 3
        }
        
        if os.environ.get('REDIS_PASSWORD'):
            redis_config['password'] = os.environ.get('REDIS_PASSWORD')
        
        redis_client = redis.Redis(**redis_config)
        redis_client.ping()
        logger.info("✅ Redis cache initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis cache not available: {e}")
        redis_client = None
    
    logger.info("🎉 Simplified Optimized API initialization completed")

def get_cache_key(query, mode, top_k, threshold):
    """Generate cache key"""
    key_data = f"{query}:{mode}:{top_k}:{threshold}"
    return f"opt_cache:{hashlib.md5(key_data.encode()).hexdigest()}"

def optimized_hyde(query, mode_config):
    """Optimized HYDE with reduced tokens"""
    try:
        model = mode_config['hyde_model']
        max_tokens = mode_config['max_tokens_hyde']
        
        if mode_config.get('target_time') == "6-8s":
            prompt = OPTIMIZED_PROMPTS['hyde_fast'].format(query=query)
        else:
            prompt = OPTIMIZED_PROMPTS['hyde_balanced'].format(query=query)
        
        chat_completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.1
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ Optimized HYDE error: {e}")
        return query

def optimized_hyde_v2(query, context, hyde_result, mode_config):
    """Optimized HYDE-v2 with context truncation"""
    try:
        model = mode_config['hyde_v2_model']
        max_tokens = mode_config['max_tokens_hyde_v2']
        
        # Truncate context based on mode
        max_context = 800 if mode_config.get('target_time') == "6-8s" else 1200
        truncated_context = context[:max_context] if len(context) > max_context else context
        
        if mode_config.get('target_time') == "6-8s":
            prompt = OPTIMIZED_PROMPTS['hyde_v2_fast'].format(query=query, context=truncated_context)
        else:
            prompt = OPTIMIZED_PROMPTS['hyde_v2_balanced'].format(query=query, context=truncated_context)
        
        chat_completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"HYDE result: {hyde_result}"}
            ],
            max_tokens=max_tokens,
            temperature=0.1
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ Optimized HYDE-v2 error: {e}")
        return hyde_result

def deep_optimized_retrieval(query, top_k=5, score_threshold=0.3, performance_mode="balanced"):
    """Deep optimized retrieval with all core functions preserved"""
    start_time = time.time()
    mode_config = PERFORMANCE_MODES.get(performance_mode, PERFORMANCE_MODES["balanced"])
    
    logger.info(f"🚀 Deep optimized retrieval: '{query}' (mode={performance_mode})")
    
    try:
        # Step 1: Check cache
        cache_key = get_cache_key(query, performance_mode, top_k, score_threshold)
        if DIFY_CONFIG['ENABLE_CACHE'] and redis_client:
            try:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    data = json.loads(cached_result.decode())
                    logger.info(f"🎯 Cache hit! Returned in {time.time() - start_time:.2f}s")
                    return data, None
            except Exception:
                pass
        
        # Step 2: Enhanced query
        enhanced_query = enhance_query(query)
        logger.info(f"🔧 Enhanced query: '{enhanced_query}'")
        
        # Step 3: Optimized HYDE
        hyde_start = time.time()
        hyde_result = optimized_hyde(enhanced_query, mode_config)
        hyde_time = time.time() - hyde_start
        logger.info(f"✅ Optimized HYDE completed in {hyde_time:.2f}s")
        
        # Step 4: Initial search with adaptive limits
        search_limit = mode_config['search_limit']
        method_search_initial = method_table.search(hyde_result).limit(search_limit)
        class_search_initial = class_table.search(hyde_result).limit(search_limit)
        
        method_docs_initial = method_search_initial.to_pandas()
        class_docs_initial = class_search_initial.to_pandas()
        
        logger.info(f"📊 Initial search: {len(method_docs_initial)} methods, {len(class_docs_initial)} classes")
        
        # Step 5: Optimized context building
        context_size = mode_config['context_size']
        if len(method_docs_initial) > 0 and len(class_docs_initial) > 0:
            temp_context = '\n'.join(
                method_docs_initial['code'][:context_size].tolist() + 
                class_docs_initial['source_code'][:context_size].tolist()
            )
        elif len(method_docs_initial) > 0:
            temp_context = '\n'.join(method_docs_initial['code'][:context_size*2].tolist())
        elif len(class_docs_initial) > 0:
            temp_context = '\n'.join(class_docs_initial['source_code'][:context_size*2].tolist())
        else:
            temp_context = ""
        
        # Step 6: Optimized HYDE-v2
        hyde_v2_start = time.time()
        hyde_v2_result = optimized_hyde_v2(enhanced_query, temp_context, hyde_result, mode_config)
        hyde_v2_time = time.time() - hyde_v2_start
        logger.info(f"✅ Optimized HYDE-v2 completed in {hyde_v2_time:.2f}s")
        
        # Step 7: Final search
        method_search = method_table.search(hyde_v2_result).limit(search_limit)
        class_search = class_table.search(hyde_v2_result).limit(search_limit)
        
        # Step 8: Optimized reranking
        rerank_start = time.time()
        global reranker
        if reranker is None:
            logger.info("🔄 Loading reranker...")
            reranker = AnswerdotaiRerankers(column="source_code")
        
        method_search_reranked = method_search.rerank(reranker)
        class_search_reranked = class_search.rerank(reranker)
        rerank_time = time.time() - rerank_start
        logger.info(f"✅ Optimized reranking completed in {rerank_time:.2f}s")
        
        # Step 9: Results processing
        method_docs = method_search_reranked.to_list()
        class_docs = class_search_reranked.to_list()
        
        # Format results
        all_results = []
        
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
        
        all_results.sort(key=lambda x: x['score'], reverse=True)
        final_results = all_results[:top_k]
        
        total_time = time.time() - start_time
        logger.info(f"✅ Deep optimized retrieval completed in {total_time:.2f}s")
        logger.info(f"   HYDE: {hyde_time:.2f}s, HYDE-v2: {hyde_v2_time:.2f}s, Rerank: {rerank_time:.2f}s")
        logger.info(f"   Returned {len(final_results)} results")
        
        # Cache results
        if DIFY_CONFIG['ENABLE_CACHE'] and redis_client:
            try:
                redis_client.setex(cache_key, DIFY_CONFIG['CACHE_TTL'], json.dumps(final_results))
                logger.info("💾 Results cached")
            except Exception as e:
                logger.warning(f"⚠️ Cache error: {e}")
        
        return final_results, None
        
    except Exception as e:
        logger.error(f"❌ Deep optimized retrieval error: {str(e)}")
        return None, {"error_code": 500, "error_msg": f"Internal server error: {str(e)}"}

def authenticate_request():
    """Authenticate API request"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False, {"error_code": 1001, "error_msg": "Invalid authorization"}
    
    api_key = auth_header[7:]
    if api_key != DIFY_CONFIG['API_KEY']:
        return False, {"error_code": 1002, "error_msg": "Authorization failed"}
    
    return True, None

@dify_app.route('/retrieval', methods=['POST'])
def optimized_retrieval_endpoint():
    """Optimized Dify retrieval endpoint"""
    try:
        # Authentication
        is_authenticated, auth_error = authenticate_request()
        if not is_authenticated:
            return jsonify(auth_error), 403 if auth_error['error_code'] == 1002 else 400
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error_code": 1001, "error_msg": "Invalid JSON"}), 400
        
        knowledge_id = data.get('knowledge_id')
        query = data.get('query')
        retrieval_setting = data.get('retrieval_setting', {})
        
        if not knowledge_id or not query:
            return jsonify({"error_code": 1001, "error_msg": "Missing required fields"}), 400
        
        if knowledge_id != DIFY_CONFIG['KNOWLEDGE_BASE_ID']:
            return jsonify({"error_code": 2001, "error_msg": "Knowledge base not found"}), 404
        
        # Extract settings
        top_k = max(1, min(retrieval_setting.get('top_k', 5), 20))
        score_threshold = max(0.0, min(retrieval_setting.get('score_threshold', 0.3), 1.0))
        performance_mode = retrieval_setting.get('performance_mode', 'balanced')
        
        if performance_mode not in PERFORMANCE_MODES:
            performance_mode = 'balanced'
        
        logger.info(f"📝 Request: query='{query}', mode={performance_mode}")
        
        # Perform retrieval
        results, error = deep_optimized_retrieval(query, top_k, score_threshold, performance_mode)
        
        if error:
            return jsonify(error), 500
        
        return jsonify({"records": results}), 200
        
    except Exception as e:
        logger.error(f"❌ API error: {str(e)}")
        return jsonify({"error_code": 500, "error_msg": str(e)}), 500

@dify_app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "CodeQA Simplified Deep Optimized API",
        "version": "3.1.0",
        "features": {
            "cache": redis_client is not None,
            "performance_modes": list(PERFORMANCE_MODES.keys())
        }
    }), 200

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dify_api_optimized_simple.py <codebase_path>")
        sys.exit(1)
    
    codebase_path = sys.argv[1]
    init_optimized_api(codebase_path)
    
    print("🚀 Starting Simplified Deep Optimized Dify API...")
    print(f"📚 Knowledge Base: {DIFY_CONFIG['KNOWLEDGE_BASE_ID']}")
    print(f"💾 Cache: {'Enabled' if redis_client else 'Disabled'}")
    print(f"🎯 Modes: {', '.join(PERFORMANCE_MODES.keys())}")
    print("🌐 Server: http://0.0.0.0:5004")
    
    dify_app.run(host='0.0.0.0', port=5004, debug=False)
