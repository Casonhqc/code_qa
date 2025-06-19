from flask import Flask, render_template, request, session, jsonify
import os
import sys
import time
import lancedb
from lancedb.rerankers import AnswerdotaiRerankers
import re
import redis
import uuid
import logging
import markdown
from openai import OpenAI
import json
from dotenv import load_dotenv
from redis import ConnectionPool

load_dotenv()

from prompts import (
    HYDE_SYSTEM_PROMPT,
    HYDE_V2_SYSTEM_PROMPT
)

# Configuration
CONFIG = {
    'SECRET_KEY': os.urandom(24),
    'REDIS_HOST': os.environ.get('REDIS_HOST', 'localhost'),
    'REDIS_PORT': int(os.environ.get('REDIS_PORT', 6379)),
    'REDIS_PASSWORD': os.environ.get('REDIS_PASSWORD'),
    'REDIS_DB': int(os.environ.get('REDIS_DB', 0)),
    'REDIS_POOL_SIZE': 10,  # Add pool size configuration
    'LOG_FILE': 'app.log',
    'LOG_FORMAT': '%(asctime)s - %(message)s',
    'LOG_DATE_FORMAT': '%d-%b-%y %H:%M:%S'
}

# Logging setup
def setup_logging(config):
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    formatter = logging.Formatter(
        fmt=config['LOG_FORMAT'],
        datefmt=config['LOG_DATE_FORMAT']
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(config['LOG_FILE'])
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Database setup
def setup_database(codebase_path):
    normalized_path = os.path.normpath(os.path.abspath(codebase_path))
    codebase_folder_name = os.path.basename(normalized_path)

    # lancedb connection
    uri = "database"
    db = lancedb.connect(uri)

    method_table = db.open_table(codebase_folder_name + "_method")
    class_table = db.open_table(codebase_folder_name + "_class")

    return method_table, class_table

# Application setup
def setup_app():
    app = Flask(__name__)
    app.config.update(CONFIG)
    
    # Setup logging
    app.logger = setup_logging(app.config)
    
    # Redis connection pooling setup
    redis_config = {
        'host': app.config['REDIS_HOST'],
        'port': app.config['REDIS_PORT'],
        'db': app.config['REDIS_DB'],
        'max_connections': app.config['REDIS_POOL_SIZE']
    }

    # Add password if provided
    if app.config['REDIS_PASSWORD']:
        redis_config['password'] = app.config['REDIS_PASSWORD']

    app.redis_pool = ConnectionPool(**redis_config)
    
    # Create Redis client using the connection pool
    app.redis_client = redis.Redis(connection_pool=app.redis_pool)
    
    # Markdown filter
    @app.template_filter('markdown')
    def markdown_filter(text):
        return markdown.markdown(text, extensions=['fenced_code', 'tables'])
    
    return app

# Create the Flask app
app = setup_app()

# OpenAI client setup
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)


# Initialize the reranker
reranker = AnswerdotaiRerankers(column="source_code")

# Replace groq_hyde function
def openai_hyde(query):
    chat_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": HYDE_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"Help predict the answer to the query: {query}",
            }
        ]
    )
    return chat_completion.choices[0].message.content

def openai_hyde_v2(query, temp_context, hyde_query):
    chat_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": HYDE_V2_SYSTEM_PROMPT.format(query=query, temp_context=temp_context)
            },
            {
                "role": "user",
                "content": f"Predict the answer to the query: {hyde_query}",
            }
        ]
    )
    return chat_completion.choices[0].message.content




def process_input(input_text):
    processed_text = input_text.replace('\n', ' ').replace('\t', ' ')
    processed_text = re.sub(r'\s+', ' ', processed_text)
    processed_text = processed_text.strip()

    return processed_text

def enhance_query(query):
    """
    Enhance user query for better retrieval results
    """
    # Common Chinese to English mappings for better search
    translations = {
        '用户': 'user',
        '登录': 'login',
        '注册': 'register',
        '商品': 'goods product',
        '订单': 'order',
        '支付': 'payment pay',
        '购物车': 'shopping cart',
        '秒杀': 'seckill',
        '优惠券': 'coupon',
        '管理': 'management manager',
        '服务': 'service',
        '控制器': 'controller',
        '数据库': 'database dao',
        '缓存': 'cache redis',
        '配置': 'config configuration',
        '异常': 'exception error',
        '工具': 'util utility',
        '验证': 'validate validation',
        '搜索': 'search',
        '分页': 'page pagination',
        '文件': 'file upload',
        '图片': 'image picture',
        '邮件': 'email mail',
        '短信': 'sms message',
        '权限': 'permission auth',
        '角色': 'role',
        '菜单': 'menu',
        '日志': 'log',
        '监控': 'monitor',
        '统计': 'statistics',
        '报表': 'report'
    }

    enhanced_query = query
    for chinese, english in translations.items():
        if chinese in query:
            enhanced_query += f" {english}"

    return enhanced_query

def generate_context(query, rerank=False):
    """
    Enhanced context generation with detailed logging and improved retrieval
    """
    start_time = time.time()
    app.logger.info(f"🔍 Starting context generation for query: '{query}' (rerank={rerank})")

    try:
        # Step 0: Enhance query
        enhanced_query = enhance_query(query)
        app.logger.info(f"🔧 Enhanced query: '{enhanced_query}'")

        # Step 1: HYDE query generation
        app.logger.info("📝 Step 1: Generating HYDE query...")
        hyde_query = openai_hyde(enhanced_query)
        app.logger.info(f"✅ HYDE query generated: '{hyde_query}'")

        # Step 2: Initial search with HYDE query
        app.logger.info("🔍 Step 2: Performing initial search...")
        method_search_initial = method_table.search(hyde_query).limit(10)
        class_search_initial = class_table.search(hyde_query).limit(10)

        method_docs_initial = method_search_initial.to_pandas()
        class_docs_initial = class_search_initial.to_pandas()

        app.logger.info(f"📊 Initial search results: {len(method_docs_initial)} methods, {len(class_docs_initial)} classes")

        # Step 3: Generate temporary context for HYDE v2
        if len(method_docs_initial) > 0 and len(class_docs_initial) > 0:
            temp_context = '\n'.join(method_docs_initial['code'][:3].tolist() + class_docs_initial['source_code'][:3].tolist())
        elif len(method_docs_initial) > 0:
            temp_context = '\n'.join(method_docs_initial['code'][:5].tolist())
        elif len(class_docs_initial) > 0:
            temp_context = '\n'.join(class_docs_initial['source_code'][:5].tolist())
        else:
            temp_context = ""
            app.logger.warning("⚠️ No initial results found for HYDE v2 context")

        # Step 4: HYDE v2 query generation
        app.logger.info("📝 Step 3: Generating enhanced HYDE v2 query...")
        hyde_query_v2 = openai_hyde_v2(query, temp_context, hyde_query)
        app.logger.info(f"✅ HYDE v2 query generated: '{hyde_query_v2}'")

        # Step 5: Final search with enhanced query
        app.logger.info("🔍 Step 4: Performing final search with enhanced query...")
        method_search = method_table.search(hyde_query_v2).limit(10)
        class_search = class_table.search(hyde_query_v2).limit(10)

        # Step 6: Apply reranking if requested
        if rerank:
            app.logger.info("🔄 Step 5: Applying ColBERT reranking...")
            method_search = method_search.rerank(reranker)
            class_search = class_search.rerank(reranker)
            app.logger.info("✅ Reranking completed")

        # Step 7: Get final results
        method_docs = method_search.to_list()
        class_docs = class_search.to_list()

        app.logger.info(f"📊 Final search results: {len(method_docs)} methods, {len(class_docs)} classes")

        # Step 8: Format results with scores if available
        top_methods = method_docs[:5]  # Increased from 3 to 5
        top_classes = class_docs[:5]   # Increased from 3 to 5

        # Format methods with similarity scores
        methods_formatted = []
        for i, doc in enumerate(top_methods):
            score_info = f" (Score: {doc.get('_distance', 'N/A')})" if '_distance' in doc else ""
            methods_formatted.append(
                f"=== METHOD {i+1}{score_info} ===\n"
                f"File: {doc['file_path']}\n"
                f"Code:\n{doc['code']}\n"
            )

        # Format classes with similarity scores
        classes_formatted = []
        for i, doc in enumerate(top_classes):
            score_info = f" (Score: {doc.get('_distance', 'N/A')})" if '_distance' in doc else ""
            references = doc.get('references', 'N/A')
            classes_formatted.append(
                f"=== CLASS {i+1}{score_info} ===\n"
                f"File: {doc['file_path']}\n"
                f"Class Info:\n{doc['source_code']}\n"
                f"References: {references}\n"
            )

        # Combine results
        methods_combined = "\n".join(methods_formatted)
        classes_combined = "\n".join(classes_formatted)

        final_context = f"""
🔍 RETRIEVAL RESULTS FOR: "{query}"
{'='*60}

📋 METHODS FOUND ({len(top_methods)}):
{methods_combined}

📋 CLASSES FOUND ({len(top_classes)}):
{classes_combined}

{'='*60}
⏱️ Retrieval completed in {time.time() - start_time:.2f} seconds
🔄 Reranking: {'Enabled' if rerank else 'Disabled'}
"""

        app.logger.info(f"✅ Context generation completed in {time.time() - start_time:.2f} seconds")
        app.logger.info(f"📊 Final context length: {len(final_context)} characters")

        return final_context

    except Exception as e:
        app.logger.error(f"❌ Error in context generation: {str(e)}")
        return f"Error generating context: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # This is an AJAX request
            data = request.get_json()
            query = data['query']
            rerank = data.get('rerank', False)  # Extract rerank value
            user_id = session.get('user_id')
            if user_id is None:
                user_id = str(uuid.uuid4())
                session['user_id'] = user_id

            # Ensure rerank is a boolean
            rerank = True if rerank in [True, 'true', 'True', '1'] else False

            if '@codebase' in query:
                original_query = query
                query = query.replace('@codebase', '').strip()

                app.logger.info(f"🚀 Processing codebase query: '{original_query}' -> '{query}'")
                app.logger.info(f"👤 User ID: {user_id}")
                app.logger.info(f"🔄 Reranking: {rerank}")

                # Generate context with enhanced logging
                context = generate_context(query, rerank)

                # Cache the context
                app.redis_client.set(f"user:{user_id}:chat_context", context)
                app.logger.info(f"💾 Context cached for user {user_id}")

                # Store the conversation history with retrieved context
                redis_key = f"user:{user_id}:responses"
                combined_response = {'query': original_query, 'response': context}
                app.redis_client.rpush(redis_key, json.dumps(combined_response))

                app.logger.info(f"✅ Query processing completed successfully")

                # Return the retrieved context as JSON
                return jsonify({'response': context})
            else:
                # For queries without @codebase, return a message asking for context
                response = "Please use '@codebase' in your query to retrieve relevant code context."

                # Store the conversation history
                redis_key = f"user:{user_id}:responses"
                combined_response = {'query': query, 'response': response}
                app.redis_client.rpush(redis_key, json.dumps(combined_response))

                # Return the message as JSON
                return jsonify({'response': response})

    # For GET requests and non-AJAX POST requests, render the template as before
    # Retrieve the conversation history to display
    user_id = session.get('user_id')
    if user_id:
        redis_key = f"user:{user_id}:responses"
        responses = app.redis_client.lrange(redis_key, -5, -1)
        responses = [json.loads(resp.decode()) for resp in responses]
        results = {'responses': responses}
    else:
        results = None

    return render_template('query_form.html', results=results)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app.py <codebase_path>")
        sys.exit(1)

    codebase_path = sys.argv[1]
    
    # Setup database
    method_table, class_table = setup_database(codebase_path)
    
    app.run(host='0.0.0.0', port=5001)
