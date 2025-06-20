# Optimized prompts for better performance while maintaining quality

# Optimized HYDE prompt - reduced from ~200 to ~100 tokens
OPTIMIZED_HYDE_PROMPT = '''Generate code for the query. Include method names, class names, key concepts.
Output only the code snippet.'''

# Optimized HYDE-v2 prompt - reduced from ~300 to ~150 tokens
OPTIMIZED_HYDE_V2_PROMPT = '''Enhance query using context.
Query: {query}
Context: {temp_context}
Output: enhanced query only.'''

# Performance-optimized system prompts
FAST_HYDE_PROMPT = '''Code for: {query}
Include: methods, classes, keywords.
Output: code only.'''

FAST_HYDE_V2_PROMPT = '''Improve: {query}
Using: {context}
Output: better query.'''

# Semantic similarity cache configuration
CACHE_SIMILARITY_THRESHOLD = 0.85
HYDE_CACHE_TTL = 7200  # 2 hours for HYDE results
RERANK_CACHE_TTL = 3600  # 1 hour for rerank results
