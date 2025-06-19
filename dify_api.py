#!/usr/bin/env python3
"""
Dify External Knowledge Base API
符合Dify规范的外部知识库API接口
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

# Load environment variables
load_dotenv()

# Import existing functions
from app import (
    setup_logging, setup_database, openai_hyde, openai_hyde_v2, 
    enhance_query, CONFIG
)

# Dify API Configuration
DIFY_CONFIG = {
    'API_KEY': os.environ.get('DIFY_API_KEY', 'your-api-key-here'),
    'KNOWLEDGE_BASE_ID': os.environ.get('KNOWLEDGE_BASE_ID', 'codeqa-knowledge-base'),
    'DEFAULT_TOP_K': 5,
    'DEFAULT_SCORE_THRESHOLD': 0.5,
    'MAX_TOP_K': 20,
    'MIN_SCORE_THRESHOLD': 0.0
}

# Create Flask app for Dify API
dify_app = Flask(__name__)
dify_app.config.update(CONFIG)

# Setup logging
logger = setup_logging(CONFIG)

# Global variables for database tables
method_table = None
class_table = None
reranker = None
client = None

def init_dify_api(codebase_path):
    """Initialize the Dify API with codebase"""
    global method_table, class_table, reranker, client
    
    logger.info("🚀 Initializing Dify API...")
    
    # Setup database
    method_table, class_table = setup_database(codebase_path)
    logger.info("✅ Database tables loaded")
    
    # Initialize reranker
    reranker = AnswerdotaiRerankers(column="source_code")
    logger.info("✅ Reranker initialized")
    
    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL")
    )
    logger.info("✅ OpenAI client initialized")
    
    logger.info("🎉 Dify API initialization completed")

def authenticate_request():
    """Authenticate API request using Bearer token"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return False, {
            "error_code": 1001,
            "error_msg": "Missing Authorization header"
        }
    
    if not auth_header.startswith('Bearer '):
        return False, {
            "error_code": 1001,
            "error_msg": "Invalid Authorization header format. Expected format: 'Bearer <api-key>'"
        }
    
    api_key = auth_header[7:]  # Remove 'Bearer ' prefix
    
    if api_key != DIFY_CONFIG['API_KEY']:
        return False, {
            "error_code": 1002,
            "error_msg": "Authorization failed"
        }
    
    return True, None

def validate_knowledge_id(knowledge_id):
    """Validate knowledge base ID"""
    if knowledge_id != DIFY_CONFIG['KNOWLEDGE_BASE_ID']:
        return False, {
            "error_code": 2001,
            "error_msg": "Knowledge base does not exist"
        }
    return True, None

def enhanced_retrieval(query, top_k=5, score_threshold=0.5, use_rerank=True):
    """
    Enhanced retrieval function for Dify API
    """
    start_time = time.time()
    logger.info(f"🔍 Dify API retrieval for query: '{query}' (top_k={top_k}, threshold={score_threshold})")
    
    try:
        # Step 1: Enhance query
        enhanced_query_text = enhance_query(query)
        logger.info(f"🔧 Enhanced query: '{enhanced_query_text}'")
        
        # Step 2: HYDE query generation
        hyde_query = openai_hyde(enhanced_query_text)
        logger.info(f"✅ HYDE query generated")
        
        # Step 3: Initial search
        method_search_initial = method_table.search(hyde_query).limit(top_k * 2)
        class_search_initial = class_table.search(hyde_query).limit(top_k * 2)
        
        method_docs_initial = method_search_initial.to_pandas()
        class_docs_initial = class_search_initial.to_pandas()
        
        # Step 4: Generate context for HYDE v2
        if len(method_docs_initial) > 0 and len(class_docs_initial) > 0:
            temp_context = '\n'.join(method_docs_initial['code'][:3].tolist() + 
                                   class_docs_initial['source_code'][:3].tolist())
        elif len(method_docs_initial) > 0:
            temp_context = '\n'.join(method_docs_initial['code'][:5].tolist())
        elif len(class_docs_initial) > 0:
            temp_context = '\n'.join(class_docs_initial['source_code'][:5].tolist())
        else:
            temp_context = ""
        
        # Step 5: HYDE v2 query generation
        hyde_query_v2 = openai_hyde_v2(enhanced_query_text, temp_context, hyde_query)
        logger.info(f"✅ HYDE v2 query generated")
        
        # Step 6: Final search
        method_search = method_table.search(hyde_query_v2).limit(top_k * 2)
        class_search = class_table.search(hyde_query_v2).limit(top_k * 2)
        
        # Step 7: Apply reranking if requested
        if use_rerank:
            method_search = method_search.rerank(reranker)
            class_search = class_search.rerank(reranker)
            logger.info("✅ Reranking applied")
        
        # Step 8: Get results and format for Dify
        method_docs = method_search.to_list()
        class_docs = class_search.to_list()
        
        # Combine and sort by score
        all_results = []
        
        # Process method results
        for doc in method_docs:
            score = 1.0 - doc.get('_distance', 0.5)  # Convert distance to similarity score
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
            score = 1.0 - doc.get('_distance', 0.5)  # Convert distance to similarity score
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
        
        # Sort by score (descending) and limit to top_k
        all_results.sort(key=lambda x: x['score'], reverse=True)
        final_results = all_results[:top_k]
        
        duration = time.time() - start_time
        logger.info(f"✅ Dify retrieval completed in {duration:.2f}s, returned {len(final_results)} results")
        
        return final_results, None
        
    except Exception as e:
        logger.error(f"❌ Error in Dify retrieval: {str(e)}")
        return None, {
            "error_code": 500,
            "error_msg": f"Internal server error: {str(e)}"
        }

@dify_app.route('/retrieval', methods=['POST'])
def dify_retrieval():
    """
    Dify External Knowledge Base API endpoint
    """
    try:
        # Authentication
        is_authenticated, auth_error = authenticate_request()
        if not is_authenticated:
            return jsonify(auth_error), 403 if auth_error['error_code'] == 1002 else 400
        
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({
                "error_code": 1001,
                "error_msg": "Invalid JSON data"
            }), 400
        
        # Validate required fields
        knowledge_id = data.get('knowledge_id')
        query = data.get('query')
        retrieval_setting = data.get('retrieval_setting', {})
        
        if not knowledge_id:
            return jsonify({
                "error_code": 1001,
                "error_msg": "Missing required field: knowledge_id"
            }), 400
        
        if not query:
            return jsonify({
                "error_code": 1001,
                "error_msg": "Missing required field: query"
            }), 400
        
        # Validate knowledge base ID
        is_valid_kb, kb_error = validate_knowledge_id(knowledge_id)
        if not is_valid_kb:
            return jsonify(kb_error), 404
        
        # Extract retrieval settings
        top_k = retrieval_setting.get('top_k', DIFY_CONFIG['DEFAULT_TOP_K'])
        score_threshold = retrieval_setting.get('score_threshold', DIFY_CONFIG['DEFAULT_SCORE_THRESHOLD'])
        
        # Validate parameters
        top_k = max(1, min(top_k, DIFY_CONFIG['MAX_TOP_K']))
        score_threshold = max(DIFY_CONFIG['MIN_SCORE_THRESHOLD'], min(score_threshold, 1.0))
        
        logger.info(f"📝 Dify API request: knowledge_id={knowledge_id}, query='{query}', top_k={top_k}, threshold={score_threshold}")
        
        # Perform retrieval
        results, error = enhanced_retrieval(query, top_k, score_threshold)
        
        if error:
            return jsonify(error), 500
        
        # Return results in Dify format
        response = {
            "records": results
        }
        
        logger.info(f"✅ Dify API response: {len(results)} records returned")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Dify API error: {str(e)}")
        return jsonify({
            "error_code": 500,
            "error_msg": f"Internal server error: {str(e)}"
        }), 500

@dify_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "CodeQA Dify External Knowledge API",
        "version": "1.0.0"
    }), 200

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dify_api.py <codebase_path>")
        sys.exit(1)
    
    codebase_path = sys.argv[1]
    
    # Initialize the API
    init_dify_api(codebase_path)
    
    # Run the Dify API server
    print("🚀 Starting Dify External Knowledge API...")
    print(f"📚 Knowledge Base ID: {DIFY_CONFIG['KNOWLEDGE_BASE_ID']}")
    print(f"🔑 API Key: {DIFY_CONFIG['API_KEY'][:10]}...")
    print("🌐 Server running on http://0.0.0.0:5002")
    
    dify_app.run(host='0.0.0.0', port=5002, debug=False)
