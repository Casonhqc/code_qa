#!/usr/bin/env python3
"""
Unified Retrieval Engine - 统一的优化检索后端
所有API接口的统一后端逻辑，提供一致的优化性能
"""

import os
import time
import logging
import hashlib
import json
import redis
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv
import lancedb
from lancedb.rerankers import AnswerdotaiRerankers

# Load environment variables
load_dotenv()

class UnifiedRetrievalEngine:
    """统一检索引擎 - 为所有API提供优化的检索服务"""
    
    def __init__(self, codebase_path, logger=None):
        self.logger = logger or self._setup_logger()
        self.method_table = None
        self.class_table = None
        self.reranker = None
        self.client = None
        self.redis_client = None
        self.executor = None
        
        # Performance modes configuration
        self.performance_modes = {
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
        self.prompts = {
            "hyde_fast": "Generate code for: {query}\nInclude method names, class names, key concepts.\nOutput code only.",
            "hyde_balanced": "Generate relevant code for the query. Focus on method names, class names, and key programming concepts. Output only the code snippet.",
            "hyde_v2_fast": "Enhance query: {query}\nUsing context: {context}\nOutput enhanced query only.",
            "hyde_v2_balanced": "Enhance the query using the provided context. Query: {query}\nContext: {context}\nOutput the enhanced query only."
        }
        
        # Cache configuration
        self.cache_config = {
            'enable_cache': True,
            'cache_ttl': 1800,  # 30 minutes
            'hyde_cache_ttl': 3600,  # 1 hour for HYDE results
        }
        
        # Initialize the engine
        self._initialize(codebase_path)
    
    def _setup_logger(self):
        """Setup logger if not provided"""
        logger = logging.getLogger('UnifiedRetrievalEngine')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _initialize(self, codebase_path):
        """Initialize the unified retrieval engine"""
        self.logger.info("🚀 Initializing Unified Retrieval Engine...")
        
        # Setup database
        self._setup_database(codebase_path)
        
        # Initialize thread pool
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.logger.info("✅ Thread pool initialized")
        
        # Initialize reranker (lazy loading)
        self.reranker = None
        self.logger.info("✅ Reranker set to lazy loading")
        
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
            max_retries=2,
            timeout=15.0
        )
        self.logger.info("✅ Optimized OpenAI client initialized")
        
        # Initialize Redis cache
        self._setup_redis()
        
        self.logger.info("🎉 Unified Retrieval Engine initialization completed")
    
    def _setup_database(self, codebase_path):
        """Setup LanceDB tables"""
        try:
            db = lancedb.connect("./database")
            self.method_table = db.open_table("main_method")
            self.class_table = db.open_table("main_class")
            self.logger.info("✅ Database tables loaded")
        except Exception as e:
            self.logger.error(f"❌ Database setup error: {e}")
            raise
    
    def _setup_redis(self):
        """Setup Redis cache"""
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
            
            self.redis_client = redis.Redis(**redis_config)
            self.redis_client.ping()
            self.logger.info("✅ Redis cache initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Redis cache not available: {e}")
            self.redis_client = None
    
    def enhance_query(self, query):
        """Enhanced query preprocessing"""
        translations = {
            '用户': 'user', '登录': 'login', '注册': 'register',
            '商品': 'goods product', '订单': 'order', '支付': 'payment pay',
            '购物车': 'shopping cart', '秒杀': 'seckill', '优惠券': 'coupon',
            '管理': 'management manager', '服务': 'service', '控制器': 'controller',
            '数据库': 'database dao', '缓存': 'cache redis', '配置': 'config configuration',
            '异常': 'exception error', '工具': 'util utility', '验证': 'validate validation',
            '搜索': 'search', '分页': 'page pagination', '文件': 'file upload',
            '图片': 'image picture', '邮件': 'email mail', '短信': 'sms message',
            '权限': 'permission auth', '角色': 'role', '菜单': 'menu',
            '日志': 'log', '监控': 'monitor', '统计': 'statistics', '报表': 'report'
        }
        
        enhanced_query = query
        for chinese, english in translations.items():
            if chinese in query:
                enhanced_query += f" {english}"
        
        return enhanced_query
    
    def _get_cache_key(self, query, mode, **kwargs):
        """Generate cache key"""
        key_data = f"{query}:{mode}:{json.dumps(kwargs, sort_keys=True)}"
        return f"unified_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _optimized_hyde(self, query, mode_config):
        """Optimized HYDE with reduced tokens"""
        try:
            model = mode_config['hyde_model']
            max_tokens = mode_config['max_tokens_hyde']
            
            if mode_config.get('target_time') == "6-8s":
                prompt = self.prompts['hyde_fast'].format(query=query)
            else:
                prompt = self.prompts['hyde_balanced'].format(query=query)
            
            chat_completion = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            self.logger.error(f"❌ Optimized HYDE error: {e}")
            return query
    
    def _optimized_hyde_v2(self, query, context, hyde_result, mode_config):
        """Optimized HYDE-v2 with context truncation"""
        try:
            model = mode_config['hyde_v2_model']
            max_tokens = mode_config['max_tokens_hyde_v2']
            
            # Truncate context based on mode
            max_context = 800 if mode_config.get('target_time') == "6-8s" else 1200
            truncated_context = context[:max_context] if len(context) > max_context else context
            
            if mode_config.get('target_time') == "6-8s":
                prompt = self.prompts['hyde_v2_fast'].format(query=query, context=truncated_context)
            else:
                prompt = self.prompts['hyde_v2_balanced'].format(query=query, context=truncated_context)
            
            chat_completion = self.client.chat.completions.create(
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
            self.logger.error(f"❌ Optimized HYDE-v2 error: {e}")
            return hyde_result
    
    def retrieve(self, query, performance_mode="balanced", top_k=5, score_threshold=0.3, 
                enable_rerank=True, enable_cache=None, return_format="detailed"):
        """
        统一检索接口 - 为所有API提供一致的优化检索服务
        
        Args:
            query: 查询字符串
            performance_mode: 性能模式 ("fast", "balanced", "quality")
            top_k: 返回结果数量
            score_threshold: 分数阈值
            enable_rerank: 是否启用重排序
            enable_cache: 是否启用缓存 (None=使用默认配置)
            return_format: 返回格式 ("detailed", "simple", "dify")
        
        Returns:
            根据return_format返回不同格式的结果
        """
        start_time = time.time()
        mode_config = self.performance_modes.get(performance_mode, self.performance_modes["balanced"])
        
        # Use cache setting
        use_cache = enable_cache if enable_cache is not None else self.cache_config['enable_cache']
        
        self.logger.info(f"🚀 Unified retrieval: '{query}' (mode={performance_mode}, format={return_format})")
        
        try:
            # Step 1: Check cache
            cache_key = self._get_cache_key(query, performance_mode, top_k=top_k, 
                                          score_threshold=score_threshold, rerank=enable_rerank)
            
            if use_cache and self.redis_client:
                try:
                    cached_result = self.redis_client.get(cache_key)
                    if cached_result:
                        data = json.loads(cached_result.decode())
                        self.logger.info(f"🎯 Cache hit! Returned in {time.time() - start_time:.2f}s")
                        return self._format_results(data['results'], return_format, data.get('metadata', {}))
                except Exception:
                    pass
            
            # Step 2: Enhanced query
            enhanced_query = self.enhance_query(query)
            self.logger.info(f"🔧 Enhanced query: '{enhanced_query}'")
            
            # Step 3: Optimized HYDE
            hyde_start = time.time()
            hyde_result = self._optimized_hyde(enhanced_query, mode_config)
            hyde_time = time.time() - hyde_start
            self.logger.info(f"✅ Optimized HYDE completed in {hyde_time:.2f}s")
            
            # Step 4: Initial search
            search_limit = mode_config['search_limit']
            method_search_initial = self.method_table.search(hyde_result).limit(search_limit)
            class_search_initial = self.class_table.search(hyde_result).limit(search_limit)
            
            method_docs_initial = method_search_initial.to_pandas()
            class_docs_initial = class_search_initial.to_pandas()
            
            self.logger.info(f"📊 Initial search: {len(method_docs_initial)} methods, {len(class_docs_initial)} classes")
            
            # Step 5: Context building
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
            hyde_v2_result = self._optimized_hyde_v2(enhanced_query, temp_context, hyde_result, mode_config)
            hyde_v2_time = time.time() - hyde_v2_start
            self.logger.info(f"✅ Optimized HYDE-v2 completed in {hyde_v2_time:.2f}s")
            
            # Step 7: Final search
            method_search = self.method_table.search(hyde_v2_result).limit(search_limit)
            class_search = self.class_table.search(hyde_v2_result).limit(search_limit)
            
            # Step 8: Reranking
            rerank_start = time.time()
            if enable_rerank:
                if self.reranker is None:
                    self.logger.info("🔄 Loading reranker...")
                    self.reranker = AnswerdotaiRerankers(column="source_code")
                
                method_search = method_search.rerank(self.reranker)
                class_search = class_search.rerank(self.reranker)
            
            rerank_time = time.time() - rerank_start
            self.logger.info(f"✅ Reranking completed in {rerank_time:.2f}s")
            
            # Step 9: Process results
            method_docs = method_search.to_list()
            class_docs = class_search.to_list()
            
            # Combine and filter results
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
            
            # Metadata for analysis
            metadata = {
                'total_time': total_time,
                'hyde_time': hyde_time,
                'hyde_v2_time': hyde_v2_time,
                'rerank_time': rerank_time,
                'performance_mode': performance_mode,
                'results_count': len(final_results),
                'rerank_enabled': enable_rerank
            }
            
            self.logger.info(f"✅ Unified retrieval completed in {total_time:.2f}s")
            self.logger.info(f"   HYDE: {hyde_time:.2f}s, HYDE-v2: {hyde_v2_time:.2f}s, Rerank: {rerank_time:.2f}s")
            self.logger.info(f"   Returned {len(final_results)} results")
            
            # Cache results
            if use_cache and self.redis_client:
                try:
                    cache_data = {'results': final_results, 'metadata': metadata}
                    self.redis_client.setex(cache_key, self.cache_config['cache_ttl'], json.dumps(cache_data))
                    self.logger.info("💾 Results cached")
                except Exception as e:
                    self.logger.warning(f"⚠️ Cache error: {e}")
            
            return self._format_results(final_results, return_format, metadata)
            
        except Exception as e:
            self.logger.error(f"❌ Unified retrieval error: {str(e)}")
            return self._format_error(str(e), return_format)
    
    def _format_results(self, results, return_format, metadata):
        """Format results based on requested format"""
        if return_format == "dify":
            return {"records": results}
        elif return_format == "simple":
            return results
        elif return_format == "detailed":
            return {
                "results": results,
                "metadata": metadata,
                "status": "success"
            }
        else:
            return results
    
    def _format_error(self, error_msg, return_format):
        """Format error based on requested format"""
        if return_format == "dify":
            return {"error_code": 500, "error_msg": error_msg}
        elif return_format == "simple":
            return None
        elif return_format == "detailed":
            return {"status": "error", "error": error_msg}
        else:
            return None

# Global instance for easy import
_engine_instance = None

def get_engine(codebase_path=None, logger=None):
    """Get or create global engine instance"""
    global _engine_instance
    if _engine_instance is None and codebase_path:
        _engine_instance = UnifiedRetrievalEngine(codebase_path, logger)
    return _engine_instance

def initialize_engine(codebase_path, logger=None):
    """Initialize the global engine instance"""
    global _engine_instance
    _engine_instance = UnifiedRetrievalEngine(codebase_path, logger)
    return _engine_instance
