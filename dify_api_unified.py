#!/usr/bin/env python3
"""
Unified Dify API - 使用统一后端的Dify外部知识库API
所有优化策略通过统一后端实现
"""

from flask import Flask, request, jsonify
import os
import sys
import logging
from dotenv import load_dotenv

# Import unified backend
from unified_retrieval_engine import initialize_engine, get_engine

# Load environment variables
load_dotenv()

# Dify API Configuration
DIFY_CONFIG = {
    'API_KEY': os.environ.get('DIFY_API_KEY', 'codeqa-api-key-2025'),
    'KNOWLEDGE_BASE_ID': os.environ.get('KNOWLEDGE_BASE_ID', 'codeqa-java-mall'),
    'DEFAULT_TOP_K': 5,
    'DEFAULT_SCORE_THRESHOLD': 0.3,
    'DEFAULT_PERFORMANCE_MODE': 'balanced',
    'MAX_TOP_K': 20,
    'MIN_SCORE_THRESHOLD': 0.0,
}

# Create Flask app
dify_app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
def unified_dify_retrieval():
    """Unified Dify External Knowledge Base API endpoint"""
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
        
        # Extract retrieval settings with defaults
        top_k = retrieval_setting.get('top_k', DIFY_CONFIG['DEFAULT_TOP_K'])
        score_threshold = retrieval_setting.get('score_threshold', DIFY_CONFIG['DEFAULT_SCORE_THRESHOLD'])
        performance_mode = retrieval_setting.get('performance_mode', DIFY_CONFIG['DEFAULT_PERFORMANCE_MODE'])
        
        # Advanced settings (backward compatibility)
        use_hyde_v2 = retrieval_setting.get('use_hyde_v2', True)  # Always enabled in unified backend
        use_rerank = retrieval_setting.get('use_rerank', True)    # Default enabled
        enable_cache = retrieval_setting.get('enable_cache', True) # Default enabled
        
        # Validate and constrain parameters
        top_k = max(1, min(top_k, DIFY_CONFIG['MAX_TOP_K']))
        score_threshold = max(DIFY_CONFIG['MIN_SCORE_THRESHOLD'], min(score_threshold, 1.0))
        
        # Validate performance mode
        engine = get_engine()
        if not engine:
            return jsonify({"error_code": 500, "error_msg": "Retrieval engine not initialized"}), 500
        
        if performance_mode not in engine.performance_modes:
            performance_mode = DIFY_CONFIG['DEFAULT_PERFORMANCE_MODE']
        
        logger.info(f"📝 Unified Dify API request:")
        logger.info(f"   Query: '{query}'")
        logger.info(f"   Performance Mode: {performance_mode}")
        logger.info(f"   Top K: {top_k}")
        logger.info(f"   Score Threshold: {score_threshold}")
        logger.info(f"   Reranking: {use_rerank}")
        logger.info(f"   Cache: {enable_cache}")
        
        # Call unified retrieval engine
        try:
            result = engine.retrieve(
                query=query,
                performance_mode=performance_mode,
                top_k=top_k,
                score_threshold=score_threshold,
                enable_rerank=use_rerank,
                enable_cache=enable_cache,
                return_format="dify"
            )
            
            # Check for errors
            if isinstance(result, dict) and 'error_code' in result:
                return jsonify(result), 500
            
            # Log success
            records_count = len(result.get('records', []))
            logger.info(f"✅ Unified Dify API response: {records_count} records returned")
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"❌ Unified retrieval error: {str(e)}")
            return jsonify({
                "error_code": 500,
                "error_msg": f"Retrieval engine error: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Unified Dify API error: {str(e)}")
        return jsonify({
            "error_code": 500,
            "error_msg": f"Internal server error: {str(e)}"
        }), 500

@dify_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    engine = get_engine()
    
    health_info = {
        "status": "healthy",
        "service": "CodeQA Unified Dify External Knowledge API",
        "version": "5.0.0",
        "backend": "unified_retrieval_engine",
        "engine_status": "initialized" if engine else "not_initialized"
    }
    
    if engine:
        health_info["features"] = {
            "performance_modes": list(engine.performance_modes.keys()),
            "default_mode": DIFY_CONFIG['DEFAULT_PERFORMANCE_MODE'],
            "caching": engine.cache_config['enable_cache'],
            "reranking": True,
            "unified_backend": True
        }
        
        health_info["performance_modes_info"] = {
            "fast": "6-8s response time, optimized for speed",
            "balanced": "8-12s response time, optimal balance",
            "quality": "10-15s response time, maximum quality"
        }
    
    return jsonify(health_info), 200

@dify_app.route('/modes', methods=['GET'])
def get_performance_modes():
    """Get available performance modes and their configurations"""
    engine = get_engine()
    
    if not engine:
        return jsonify({"error": "Engine not initialized"}), 500
    
    modes_info = {}
    for mode_name, config in engine.performance_modes.items():
        modes_info[mode_name] = {
            "target_time": config["target_time"],
            "hyde_model": config["hyde_model"],
            "hyde_v2_model": config["hyde_v2_model"],
            "search_limit": config["search_limit"],
            "context_size": config["context_size"]
        }
    
    return jsonify({
        "available_modes": modes_info,
        "default_mode": DIFY_CONFIG['DEFAULT_PERFORMANCE_MODE'],
        "usage": {
            "fast": "Real-time applications, quick responses",
            "balanced": "General use, optimal speed/quality balance",
            "quality": "High-accuracy requirements, comprehensive search"
        }
    }), 200

@dify_app.route('/stats', methods=['GET'])
def get_stats():
    """Get engine statistics and performance info"""
    engine = get_engine()
    
    if not engine:
        return jsonify({"error": "Engine not initialized"}), 500
    
    stats = {
        "engine_type": "UnifiedRetrievalEngine",
        "cache_enabled": engine.cache_config['enable_cache'],
        "cache_ttl": engine.cache_config['cache_ttl'],
        "performance_modes": len(engine.performance_modes),
        "redis_available": engine.redis_client is not None,
        "reranker_loaded": engine.reranker is not None
    }
    
    return jsonify(stats), 200

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dify_api_unified.py <codebase_path>")
        sys.exit(1)
    
    codebase_path = sys.argv[1]
    
    # Initialize unified retrieval engine
    try:
        engine = initialize_engine(codebase_path, logger)
        logger.info("✅ Unified retrieval engine initialized for Dify API")
    except Exception as e:
        logger.error(f"❌ Failed to initialize unified engine: {e}")
        sys.exit(1)
    
    # Display startup information
    print("🚀 Starting Unified Dify External Knowledge API...")
    print(f"📚 Knowledge Base ID: {DIFY_CONFIG['KNOWLEDGE_BASE_ID']}")
    print(f"🔑 API Key: {DIFY_CONFIG['API_KEY'][:10]}...")
    print(f"🔧 Backend: Unified Retrieval Engine")
    print(f"⚡ Performance Modes: {', '.join(engine.performance_modes.keys())}")
    print(f"🎯 Default Mode: {DIFY_CONFIG['DEFAULT_PERFORMANCE_MODE']}")
    print(f"💾 Cache: {'Enabled' if engine.cache_config['enable_cache'] else 'Disabled'}")
    print(f"🔄 Reranking: Enabled")
    print("🌐 Server running on http://0.0.0.0:5002")
    print()
    print("📖 API Endpoints:")
    print("   POST /retrieval - Main retrieval endpoint")
    print("   GET  /health    - Health check")
    print("   GET  /modes     - Performance modes info")
    print("   GET  /stats     - Engine statistics")
    
    dify_app.run(host='0.0.0.0', port=5002, debug=False)
