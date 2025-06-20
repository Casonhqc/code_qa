#!/usr/bin/env python3
"""
Unified Web Interface - 使用统一后端的Web界面
保留原始Web界面功能，但使用优化的统一后端
"""

from flask import Flask, render_template, request, jsonify, session
import os
import sys
import json
import uuid
import redis
from redis import ConnectionPool
import markdown
from dotenv import load_dotenv

# Import unified backend
from unified_retrieval_engine import initialize_engine, get_engine

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'your-secret-key-here'),
    'REDIS_HOST': os.environ.get('REDIS_HOST', 'localhost'),
    'REDIS_PORT': int(os.environ.get('REDIS_PORT', 6379)),
    'REDIS_PASSWORD': os.environ.get('REDIS_PASSWORD'),
    'REDIS_DB': int(os.environ.get('REDIS_DB', 0)),
    'DEBUG': os.environ.get('DEBUG', 'False').lower() == 'true'
}

def setup_app():
    """Setup Flask application with unified backend"""
    app = Flask(__name__)
    app.config.update(CONFIG)
    
    # Setup Redis connection pool
    redis_config = {
        'host': CONFIG['REDIS_HOST'],
        'port': CONFIG['REDIS_PORT'],
        'db': CONFIG['REDIS_DB'],
        'decode_responses': False,
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
        'retry_on_timeout': True,
        'health_check_interval': 30
    }
    
    if CONFIG['REDIS_PASSWORD']:
        redis_config['password'] = CONFIG['REDIS_PASSWORD']
    
    app.redis_pool = ConnectionPool(**redis_config)
    app.redis_client = redis.Redis(connection_pool=app.redis_pool)
    
    # Markdown filter
    @app.template_filter('markdown')
    def markdown_filter(text):
        return markdown.markdown(text, extensions=['fenced_code', 'tables'])
    
    return app

# Create Flask app
app = setup_app()

def format_context_for_web(results, metadata):
    """Format unified backend results for web display"""
    if not results:
        return "No relevant code found for your query."
    
    # Group results by type
    methods = [r for r in results if r['metadata']['type'] == 'method']
    classes = [r for r in results if r['metadata']['type'] == 'class']
    
    # Format methods
    methods_formatted = []
    for i, result in enumerate(methods, 1):
        score_info = f" (Score: {result['score']:.3f})"
        methods_formatted.append(
            f"=== METHOD {i}{score_info} ===\n"
            f"File: {result['metadata']['file_path']}\n"
            f"Method: {result['metadata']['method_name']}\n"
            f"Class: {result['metadata']['class_name']}\n"
            f"Code:\n{result['content']}\n"
        )
    
    # Format classes
    classes_formatted = []
    for i, result in enumerate(classes, 1):
        score_info = f" (Score: {result['score']:.3f})"
        references = result['metadata'].get('references', 'N/A')
        classes_formatted.append(
            f"=== CLASS {i}{score_info} ===\n"
            f"File: {result['metadata']['file_path']}\n"
            f"Class: {result['metadata']['class_name']}\n"
            f"References: {references}\n"
            f"Code:\n{result['content']}\n"
        )
    
    # Combine results
    methods_combined = "\n".join(methods_formatted) if methods_formatted else "No methods found."
    classes_combined = "\n".join(classes_formatted) if classes_formatted else "No classes found."
    
    # Performance info
    perf_info = f"""
⏱️ Performance Details:
- Total Time: {metadata.get('total_time', 0):.2f}s
- HYDE Time: {metadata.get('hyde_time', 0):.2f}s  
- HYDE-v2 Time: {metadata.get('hyde_v2_time', 0):.2f}s
- Rerank Time: {metadata.get('rerank_time', 0):.2f}s
- Mode: {metadata.get('performance_mode', 'unknown')}
- Reranking: {'Enabled' if metadata.get('rerank_enabled') else 'Disabled'}
"""
    
    final_context = f"""
🔍 UNIFIED RETRIEVAL RESULTS
{'='*60}

📋 METHODS FOUND ({len(methods)}):
{methods_combined}

📋 CLASSES FOUND ({len(classes)}):
{classes_combined}

{'='*60}
{perf_info}
"""
    
    return final_context

@app.route('/', methods=['GET', 'POST'])
def home():
    """Main route with unified backend integration"""
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request
            data = request.get_json()
            query = data['query']
            rerank = data.get('rerank', True)
            performance_mode = data.get('performance_mode', 'balanced')  # New parameter
            
            user_id = session.get('user_id')
            if user_id is None:
                user_id = str(uuid.uuid4())
                session['user_id'] = user_id
            
            # Ensure rerank is boolean
            rerank = True if rerank in [True, 'true', 'True', '1'] else False
            
            if '@codebase' in query:
                original_query = query
                query = query.replace('@codebase', '').strip()
                
                app.logger.info(f"🚀 Processing unified query: '{original_query}' -> '{query}'")
                app.logger.info(f"👤 User ID: {user_id}")
                app.logger.info(f"🔄 Reranking: {rerank}")
                app.logger.info(f"⚡ Performance Mode: {performance_mode}")
                
                # Use unified retrieval engine
                engine = get_engine()
                if engine is None:
                    return jsonify({'response': 'Error: Retrieval engine not initialized'}), 500
                
                try:
                    # Call unified backend
                    result = engine.retrieve(
                        query=query,
                        performance_mode=performance_mode,
                        top_k=5,
                        score_threshold=0.3,
                        enable_rerank=rerank,
                        return_format="detailed"
                    )
                    
                    if result.get('status') == 'error':
                        context = f"Error: {result.get('error', 'Unknown error')}"
                    else:
                        # Format results for web display
                        context = format_context_for_web(result['results'], result['metadata'])
                    
                    # Cache the context
                    app.redis_client.set(f"user:{user_id}:chat_context", context)
                    app.logger.info(f"💾 Context cached for user {user_id}")
                    
                    # Store conversation history
                    redis_key = f"user:{user_id}:responses"
                    combined_response = {
                        'query': original_query, 
                        'response': context,
                        'performance_mode': performance_mode,
                        'rerank_enabled': rerank
                    }
                    app.redis_client.rpush(redis_key, json.dumps(combined_response))
                    
                    app.logger.info(f"✅ Unified query processing completed successfully")
                    
                    return jsonify({'response': context})
                    
                except Exception as e:
                    app.logger.error(f"❌ Unified retrieval error: {str(e)}")
                    error_response = f"Error in unified retrieval: {str(e)}"
                    return jsonify({'response': error_response}), 500
            else:
                # For queries without @codebase
                response = "Please use '@codebase' in your query to retrieve relevant code context."
                
                # Store conversation history
                redis_key = f"user:{user_id}:responses"
                combined_response = {'query': query, 'response': response}
                app.redis_client.rpush(redis_key, json.dumps(combined_response))
                
                return jsonify({'response': response})
    
    # GET request - display conversation history
    user_id = session.get('user_id')
    if user_id:
        redis_key = f"user:{user_id}:responses"
        responses = app.redis_client.lrange(redis_key, -5, -1)
        responses = [json.loads(resp.decode()) for resp in responses]
        results = {'responses': responses}
    else:
        results = None
    
    return render_template('query_form_unified.html', results=results)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    engine = get_engine()
    return jsonify({
        "status": "healthy",
        "service": "CodeQA Unified Web Interface",
        "version": "4.0.0",
        "backend": "unified_retrieval_engine",
        "engine_initialized": engine is not None,
        "features": {
            "performance_modes": ["fast", "balanced", "quality"],
            "reranking": True,
            "caching": True,
            "unified_backend": True
        }
    }), 200

@app.route('/api/modes', methods=['GET'])
def get_performance_modes():
    """Get available performance modes"""
    engine = get_engine()
    if engine:
        return jsonify({
            "modes": list(engine.performance_modes.keys()),
            "default": "balanced",
            "descriptions": {
                "fast": "6-8s response time, good quality",
                "balanced": "8-12s response time, optimal balance", 
                "quality": "10-15s response time, highest quality"
            }
        })
    else:
        return jsonify({"error": "Engine not initialized"}), 500

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app_unified.py <codebase_path>")
        sys.exit(1)
    
    codebase_path = sys.argv[1]
    
    # Initialize unified retrieval engine
    try:
        engine = initialize_engine(codebase_path, app.logger)
        app.logger.info("✅ Unified retrieval engine initialized")
    except Exception as e:
        app.logger.error(f"❌ Failed to initialize unified engine: {e}")
        sys.exit(1)
    
    print("🚀 Starting Unified Web Interface...")
    print(f"📚 Codebase: {codebase_path}")
    print(f"🔧 Backend: Unified Retrieval Engine")
    print(f"⚡ Performance Modes: fast, balanced, quality")
    print(f"🌐 Server: http://0.0.0.0:5001")
    
    app.run(host='0.0.0.0', port=5001, debug=CONFIG['DEBUG'])
