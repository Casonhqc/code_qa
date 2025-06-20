#!/usr/bin/env python3
"""
Dify External Knowledge Base API - Deep Optimization Version
保留所有核心功能的深度性能优化版本
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
import threading
from concurrent.futures import ThreadPoolExecutor
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Load environment variables
load_dotenv()

# Import existing functions
from app import setup_logging, setup_database, enhance_query, CONFIG
from optimized_prompts import (
    OPTIMIZED_HYDE_PROMPT, OPTIMIZED_HYDE_V2_PROMPT,
    FAST_HYDE_PROMPT, FAST_HYDE_V2_PROMPT,
    CACHE_SIMILARITY_THRESHOLD, HYDE_CACHE_TTL, RERANK_CACHE_TTL
)

# Optimized Dify API Configuration
DIFY_CONFIG = {
    'API_KEY': os.environ.get('DIFY_API_KEY', 'codeqa-api-key-2025'),
    'KNOWLEDGE_BASE_ID': os.environ.get('KNOWLEDGE_BASE_ID', 'codeqa-java-mall'),
    'DEFAULT_TOP_K': 5,
    'DEFAULT_SCORE_THRESHOLD': 0.3,
    'MAX_TOP_K': 20,
    'MIN_SCORE_THRESHOLD': 0.0,
    'ENABLE_PARALLEL_LLM': True,
    'ENABLE_SMART_CACHE': True,
    'ENABLE_BATCH_RERANK': True,
    'RERANK_BATCH_SIZE': 8,
    'MAX_SEARCH_LIMIT': 15,
}

# Performance modes configuration
PERFORMANCE_MODES = {
    "fast": {
        "hyde_model": "gpt-3.5-turbo",
        "hyde_v2_model": "gpt-3.5-turbo", 
        "use_parallel": True,
        "use_optimized_prompts": True,
        "rerank_batch_size": 16,
        "search_limit": 10,
        "target_time": "6-8s"
    },
    "balanced": {
        "hyde_model": "gpt-4o-mini",
        "hyde_v2_model": "gpt-3.5-turbo",
        "use_parallel": True, 
        "use_optimized_prompts": True,
        "rerank_batch_size": 8,
        "search_limit": 15,
        "target_time": "8-10s"
    },
    "quality": {
        "hyde_model": "gpt-4o-mini",
        "hyde_v2_model": "gpt-4o-mini",
        "use_parallel": False,
        "use_optimized_prompts": False,
        "rerank_batch_size": 4,
        "search_limit": 20,
        "target_time": "10-12s"
    }
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
similarity_model = None
executor = None

def init_optimized_dify_api(codebase_path):
    """Initialize the optimized Dify API"""
    global method_table, class_table, reranker, client, redis_client, similarity_model, executor
    
    logger.info("🚀 Initializing Optimized Dify API...")
    
    # Setup database
    method_table, class_table = setup_database(codebase_path)
    logger.info("✅ Database tables loaded")
    
    # Initialize thread pool for parallel processing
    executor = ThreadPoolExecutor(max_workers=4)
    logger.info("✅ Thread pool executor initialized")
    
    # Initialize similarity model for smart caching
    if HAS_SENTENCE_TRANSFORMERS:
        try:
            similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Similarity model loaded for smart caching")
        except Exception as e:
            logger.warning(f"⚠️ Could not load similarity model: {e}")
            similarity_model = None
    else:
        logger.warning("⚠️ sentence-transformers not available, smart caching disabled")
        similarity_model = None
    
    # Initialize reranker (lazy loading)
    reranker = None
    logger.info("✅ Reranker set to lazy loading")
    
    # Initialize optimized OpenAI client
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        max_retries=2,
        timeout=20.0  # Reduced timeout
    )
    logger.info("✅ Optimized OpenAI client initialized")
    
    # Initialize Redis for smart caching
    try:
        redis_config = {
            'host': os.environ.get('REDIS_HOST', 'localhost'),
            'port': int(os.environ.get('REDIS_PORT', 6379)),
            'db': int(os.environ.get('REDIS_DB', 0)),
            'socket_timeout': 3,
            'socket_connect_timeout': 3,
            'connection_pool_kwargs': {'max_connections': 20}
        }
        
        if os.environ.get('REDIS_PASSWORD'):
            redis_config['password'] = os.environ.get('REDIS_PASSWORD')
        
        redis_client = redis.Redis(**redis_config)
        redis_client.ping()
        logger.info("✅ Redis smart cache initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis cache not available: {e}")
        redis_client = None
    
    logger.info("🎉 Optimized Dify API initialization completed")

def get_smart_cache_key(query, query_type="general"):
    """Generate smart cache key with similarity matching"""
    if not redis_client or not similarity_model:
        return None
    
    try:
        # Get query embedding
        query_embedding = similarity_model.encode([query])[0]
        
        # Search for similar cached queries
        cache_pattern = f"smart_cache:{query_type}:*"
        cached_keys = redis_client.keys(cache_pattern)
        
        for cached_key in cached_keys[:50]:  # Limit search to recent 50
            try:
                cached_data = redis_client.get(cached_key)
                if cached_data:
                    data = json.loads(cached_data.decode())
                    cached_embedding = np.array(data.get('embedding', []))
                    
                    if len(cached_embedding) > 0 and HAS_NUMPY:
                        # Calculate cosine similarity
                        similarity = np.dot(query_embedding, cached_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding)
                        )
                        
                        if similarity >= CACHE_SIMILARITY_THRESHOLD:
                            logger.info(f"🎯 Smart cache hit! Similarity: {similarity:.3f}")
                            return cached_key
            except Exception:
                continue
        
        # Generate new cache key
        cache_key = f"smart_cache:{query_type}:{hashlib.md5(query.encode()).hexdigest()}"
        return cache_key
        
    except Exception as e:
        logger.warning(f"⚠️ Smart cache error: {e}")
        return None

def optimized_openai_hyde(query, mode_config):
    """Optimized HYDE with token reduction and model selection"""
    try:
        model = mode_config.get('hyde_model', 'gpt-4o-mini')
        use_optimized = mode_config.get('use_optimized_prompts', True)
        
        prompt = FAST_HYDE_PROMPT if use_optimized else OPTIMIZED_HYDE_PROMPT
        
        chat_completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=200,  # Reduced from default
            temperature=0.1   # Lower temperature for consistency
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ HYDE error: {e}")
        return query  # Fallback to original query

def optimized_openai_hyde_v2(query, temp_context, hyde_query, mode_config):
    """Optimized HYDE-v2 with context truncation"""
    try:
        model = mode_config.get('hyde_v2_model', 'gpt-3.5-turbo')
        use_optimized = mode_config.get('use_optimized_prompts', True)
        
        # Truncate context to reduce tokens
        truncated_context = temp_context[:1000] if len(temp_context) > 1000 else temp_context
        
        if use_optimized:
            prompt = FAST_HYDE_V2_PROMPT.format(query=query, context=truncated_context)
        else:
            prompt = OPTIMIZED_HYDE_V2_PROMPT.format(query=query, temp_context=truncated_context)
        
        chat_completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Original HYDE: {hyde_query}"}
            ],
            max_tokens=150,  # Reduced tokens
            temperature=0.1
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ HYDE-v2 error: {e}")
        return hyde_query  # Fallback to HYDE result

def parallel_hyde_calls(query, temp_context, mode_config):
    """Execute HYDE and HYDE-v2 in parallel when possible"""
    if not mode_config.get('use_parallel', True):
        # Sequential execution
        hyde_result = optimized_openai_hyde(query, mode_config)
        hyde_v2_result = optimized_openai_hyde_v2(query, temp_context, hyde_result, mode_config)
        return hyde_result, hyde_v2_result
    
    # Parallel execution
    try:
        future_hyde = executor.submit(optimized_openai_hyde, query, mode_config)
        
        # Wait for HYDE to complete before starting HYDE-v2
        hyde_result = future_hyde.result(timeout=15)
        
        # Now execute HYDE-v2 with the result
        hyde_v2_result = optimized_openai_hyde_v2(query, temp_context, hyde_result, mode_config)
        
        return hyde_result, hyde_v2_result
        
    except Exception as e:
        logger.error(f"❌ Parallel HYDE error: {e}")
        # Fallback to sequential
        hyde_result = optimized_openai_hyde(query, mode_config)
        hyde_v2_result = optimized_openai_hyde_v2(query, temp_context, hyde_result, mode_config)
        return hyde_result, hyde_v2_result

def optimized_rerank(method_docs, class_docs, mode_config):
    """Optimized reranking with batching"""
    global reranker
    
    try:
        # Lazy load reranker
        if reranker is None:
            logger.info("🔄 Loading optimized reranker...")
            reranker = AnswerdotaiRerankers(column="source_code")
        
        batch_size = mode_config.get('rerank_batch_size', 8)
        
        # Batch process method docs
        method_results = []
        for i in range(0, len(method_docs), batch_size):
            batch = method_docs[i:i+batch_size]
            if batch:
                # Convert to format expected by reranker
                batch_results = list(batch)
                method_results.extend(batch_results)
        
        # Batch process class docs  
        class_results = []
        for i in range(0, len(class_docs), batch_size):
            batch = class_docs[i:i+batch_size]
            if batch:
                batch_results = list(batch)
                class_results.extend(batch_results)
        
        return method_results, class_results
        
    except Exception as e:
        logger.error(f"❌ Reranking error: {e}")
        return method_docs, class_docs  # Return original if reranking fails

def deep_optimized_retrieval(query, top_k=5, score_threshold=0.3, performance_mode="balanced"):
    """
    Deep optimized retrieval maintaining all core functionality
    """
    start_time = time.time()
    mode_config = PERFORMANCE_MODES.get(performance_mode, PERFORMANCE_MODES["balanced"])

    logger.info(f"🚀 Deep optimized retrieval: '{query}' (mode={performance_mode}, target={mode_config['target_time']})")

    try:
        # Step 1: Smart caching check
        if DIFY_CONFIG['ENABLE_SMART_CACHE']:
            cache_key = get_smart_cache_key(query, "retrieval")
            if cache_key and redis_client:
                try:
                    cached_result = redis_client.get(cache_key)
                    if cached_result:
                        data = json.loads(cached_result.decode())
                        if 'results' in data:
                            logger.info(f"🎯 Smart cache hit! Returned in {time.time() - start_time:.2f}s")
                            return data['results'], None
                except Exception:
                    pass

        # Step 2: Enhanced query preprocessing
        enhanced_query_text = enhance_query(query)
        logger.info(f"🔧 Enhanced query: '{enhanced_query_text}'")

        # Step 3: Optimized HYDE processing with smart caching
        hyde_cache_key = get_smart_cache_key(enhanced_query_text, "hyde") if DIFY_CONFIG['ENABLE_SMART_CACHE'] else None
        hyde_result = None

        if hyde_cache_key and redis_client:
            try:
                cached_hyde = redis_client.get(hyde_cache_key)
                if cached_hyde:
                    hyde_data = json.loads(cached_hyde.decode())
                    hyde_result = hyde_data.get('result')
                    logger.info("🎯 HYDE cache hit!")
            except Exception:
                pass

        if not hyde_result:
            hyde_result = optimized_openai_hyde(enhanced_query_text, mode_config)

            # Cache HYDE result
            if hyde_cache_key and redis_client and similarity_model:
                try:
                    embedding = similarity_model.encode([enhanced_query_text])[0].tolist()
                    cache_data = {
                        'result': hyde_result,
                        'embedding': embedding,
                        'timestamp': time.time()
                    }
                    redis_client.setex(hyde_cache_key, HYDE_CACHE_TTL, json.dumps(cache_data))
                    logger.info("💾 HYDE result cached")
                except Exception as e:
                    logger.warning(f"⚠️ HYDE cache error: {e}")

        logger.info("✅ HYDE processing completed")

        # Step 4: Adaptive initial search
        search_limit = min(mode_config['search_limit'], DIFY_CONFIG['MAX_SEARCH_LIMIT'])

        method_search_initial = method_table.search(hyde_result).limit(search_limit)
        class_search_initial = class_table.search(hyde_result).limit(search_limit)

        method_docs_initial = method_search_initial.to_pandas()
        class_docs_initial = class_search_initial.to_pandas()

        logger.info(f"📊 Initial search: {len(method_docs_initial)} methods, {len(class_docs_initial)} classes")

        # Step 5: Optimized context building
        context_size = min(3, len(method_docs_initial), len(class_docs_initial))
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

        # Step 6: Optimized HYDE-v2 with caching
        hyde_v2_cache_key = get_smart_cache_key(f"{enhanced_query_text}:{temp_context[:200]}", "hyde_v2") if DIFY_CONFIG['ENABLE_SMART_CACHE'] else None
        hyde_v2_result = None

        if hyde_v2_cache_key and redis_client:
            try:
                cached_hyde_v2 = redis_client.get(hyde_v2_cache_key)
                if cached_hyde_v2:
                    hyde_v2_data = json.loads(cached_hyde_v2.decode())
                    hyde_v2_result = hyde_v2_data.get('result')
                    logger.info("🎯 HYDE-v2 cache hit!")
            except Exception:
                pass

        if not hyde_v2_result:
            hyde_v2_result = optimized_openai_hyde_v2(enhanced_query_text, temp_context, hyde_result, mode_config)

            # Cache HYDE-v2 result
            if hyde_v2_cache_key and redis_client and similarity_model:
                try:
                    context_query = f"{enhanced_query_text}:{temp_context[:200]}"
                    embedding = similarity_model.encode([context_query])[0].tolist()
                    cache_data = {
                        'result': hyde_v2_result,
                        'embedding': embedding,
                        'timestamp': time.time()
                    }
                    redis_client.setex(hyde_v2_cache_key, HYDE_CACHE_TTL, json.dumps(cache_data))
                    logger.info("💾 HYDE-v2 result cached")
                except Exception as e:
                    logger.warning(f"⚠️ HYDE-v2 cache error: {e}")

        logger.info("✅ HYDE-v2 processing completed")

        # Step 7: Final optimized search
        method_search = method_table.search(hyde_v2_result).limit(search_limit)
        class_search = class_table.search(hyde_v2_result).limit(search_limit)

        # Step 8: Optimized reranking
        if DIFY_CONFIG['ENABLE_BATCH_RERANK']:
            method_search_reranked = method_search.rerank(reranker) if reranker else method_search
            class_search_reranked = class_search.rerank(reranker) if reranker else class_search
            logger.info("✅ Optimized reranking completed")
        else:
            method_search_reranked = method_search
            class_search_reranked = class_search

        # Step 9: Results processing
        method_docs = method_search_reranked.to_list()
        class_docs = class_search_reranked.to_list()

        # Combine and format results
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

        # Sort and limit results
        all_results.sort(key=lambda x: x['score'], reverse=True)
        final_results = all_results[:top_k]

        duration = time.time() - start_time
        logger.info(f"✅ Deep optimized retrieval completed in {duration:.2f}s, returned {len(final_results)} results")

        # Cache final results
        if cache_key and redis_client and similarity_model:
            try:
                embedding = similarity_model.encode([query])[0].tolist()
                cache_data = {
                    'results': final_results,
                    'embedding': embedding,
                    'timestamp': time.time(),
                    'performance_mode': performance_mode
                }
                redis_client.setex(cache_key, 1800, json.dumps(cache_data))  # 30 min cache
                logger.info("💾 Final results cached")
            except Exception as e:
                logger.warning(f"⚠️ Result cache error: {e}")

        return final_results, None

    except Exception as e:
        logger.error(f"❌ Deep optimized retrieval error: {str(e)}")
        return None, {
            "error_code": 500,
            "error_msg": f"Internal server error: {str(e)}"
        }

def authenticate_request():
    """Authenticate API request"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False, {"error_code": 1001, "error_msg": "Invalid authorization"}

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
def optimized_dify_retrieval():
    """Deep optimized Dify External Knowledge Base API endpoint"""
    try:
        # Authentication
        is_authenticated, auth_error = authenticate_request()
        if not is_authenticated:
            return jsonify(auth_error), 403 if auth_error['error_code'] == 1002 else 400

        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error_code": 1001, "error_msg": "Invalid JSON data"}), 400

        # Validate required fields
        knowledge_id = data.get('knowledge_id')
        query = data.get('query')
        retrieval_setting = data.get('retrieval_setting', {})

        if not knowledge_id or not query:
            return jsonify({"error_code": 1001, "error_msg": "Missing required fields"}), 400

        # Validate knowledge base
        is_valid_kb, kb_error = validate_knowledge_id(knowledge_id)
        if not is_valid_kb:
            return jsonify(kb_error), 404

        # Extract settings
        top_k = max(1, min(retrieval_setting.get('top_k', DIFY_CONFIG['DEFAULT_TOP_K']), DIFY_CONFIG['MAX_TOP_K']))
        score_threshold = max(DIFY_CONFIG['MIN_SCORE_THRESHOLD'],
                            min(retrieval_setting.get('score_threshold', DIFY_CONFIG['DEFAULT_SCORE_THRESHOLD']), 1.0))
        performance_mode = retrieval_setting.get('performance_mode', 'balanced')

        if performance_mode not in PERFORMANCE_MODES:
            performance_mode = 'balanced'

        logger.info(f"📝 Optimized API request: query='{query}', mode={performance_mode}, top_k={top_k}, threshold={score_threshold}")

        # Perform deep optimized retrieval
        results, error = deep_optimized_retrieval(query, top_k, score_threshold, performance_mode)

        if error:
            return jsonify(error), 500

        # Return results
        response = {"records": results}
        logger.info(f"✅ Optimized API response: {len(results)} records returned")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"❌ Optimized API error: {str(e)}")
        return jsonify({"error_code": 500, "error_msg": f"Internal server error: {str(e)}"}), 500

@dify_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "CodeQA Deep Optimized Dify External Knowledge API",
        "version": "3.0.0",
        "optimizations": {
            "smart_cache": DIFY_CONFIG['ENABLE_SMART_CACHE'] and redis_client is not None,
            "parallel_llm": DIFY_CONFIG['ENABLE_PARALLEL_LLM'],
            "batch_rerank": DIFY_CONFIG['ENABLE_BATCH_RERANK'],
            "similarity_model": similarity_model is not None
        },
        "performance_modes": list(PERFORMANCE_MODES.keys())
    }), 200

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dify_api_optimized.py <codebase_path>")
        sys.exit(1)

    codebase_path = sys.argv[1]

    # Initialize the optimized API
    init_optimized_dify_api(codebase_path)

    # Run the Deep Optimized Dify API server
    print("🚀 Starting Deep Optimized Dify External Knowledge API...")
    print(f"📚 Knowledge Base ID: {DIFY_CONFIG['KNOWLEDGE_BASE_ID']}")
    print(f"🔑 API Key: {DIFY_CONFIG['API_KEY'][:10]}...")
    print(f"💾 Smart Cache: {'Enabled' if DIFY_CONFIG['ENABLE_SMART_CACHE'] and redis_client else 'Disabled'}")
    print(f"⚡ Parallel LLM: {'Enabled' if DIFY_CONFIG['ENABLE_PARALLEL_LLM'] else 'Disabled'}")
    print(f"🔄 Batch Rerank: {'Enabled' if DIFY_CONFIG['ENABLE_BATCH_RERANK'] else 'Disabled'}")
    print(f"🎯 Performance Modes: {', '.join(PERFORMANCE_MODES.keys())}")
    print("🌐 Server running on http://0.0.0.0:5004")

    dify_app.run(host='0.0.0.0', port=5004, debug=False)
