


**Current Branch: feature/retrieval-only** - This branch focuses exclusively on code retrieval functionality without LLM-generated responses. It uses the specified OpenAI-compatible API configuration and returns only the retrieved code context.

**Key Features of this branch:**
1. **Retrieval-Only Mode** - No LLM-generated answers, only code context retrieval
2. **Custom OpenAI API Configuration** - Uses specified base URL and API key
3. **HYDE Query Enhancement** - Still uses HYDE and HYDE-v2 for better retrieval
4. **Reranking Support** - Optional reranking with ColBERT for improved relevance

**Previous Updates**: Check the branch [`feature/optimization`](https://github.com/sankalp1999/code_qa/tree/feature/optimization) which runs 2.5x faster than the main branch with full LLM response generation.

## What is CodeQA - Retrieval Only?

A focused code retrieval system that lets you explore codebases using natural language queries. This version specializes in retrieving relevant code context without generating LLM responses. Powered by LanceDB, OpenAI-compatible APIs for query enhancement, and Answerdotai's colbert-small-v1 reranker. Supports Python, Rust, JavaScript and Java with a clean, minimal UI.

Blog Links:

[An attempt to build cursor's @codebase feature - RAG on codebases - part 1](https://blog.lancedb.com/rag-codebase-1/)

[An attempt to build cursor's @codebase feature - RAG on codebases - part 2](https://blog.lancedb.com/building-rag-on-codebases-part-2/)


CodeQA - Retrieval Only helps you explore codebases by:
- Extracting code structure and metadata using tree-sitter AST parsing
- Indexing the code chunks using OpenAI/Jina embeddings and storing them in LanceDB
- Enabling natural language searches across the codebase by using @codebase in queries
- Retrieving relevant code context with file paths and references
- Supporting interactive retrieval-based code exploration


## Prerequisites

- Python 3.6 or higher
- Redis server running on `localhost:6379`

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/sankalp1999/code_qa.git
   ```

2. Navigate to the project directory:

   ```bash
   cd code_qa
   ```

3. Set up a Python virtual environment:

 Treesitter is supported >=3.8 to 3.11

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

4. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

5. Run the redis server
```
redis-server
```

## Configuration
This branch uses a custom OpenAI-compatible API configuration. The .env file is already configured with the specified settings:

```
OPENAI_BASE_URL=https://api.oaipro.com/v1
OPENAI_API_KEY=sk-GCYpSq4rQMnm8xiScoxtRecBSYgZqaQANF2DTLeRZtac2CNUdHaY
```

Optional: Add Jina API key if you want to use Jina embeddings instead of OpenAI:
```
JINA_API_KEY="your-jina-api-key"
```
## Building the Codebase Index

To build the index for the codebase, run the following script:


```
chmod +x index_codebase.sh
```

```bash
./index_codebase.sh <absolute_path_to_codebase>
```

This will parse the codebase to get the code chunks, generate embeddings, references and store them in LanceDB.

## Usage

To start the server

```bash
python app.py <folder_path>
```

For example, to analyze a JavaScript project located in `/Users/sankalp/Documents/code2prompt/twitter-circle`, run:

```bash
python app.py /Users/sankalp/Documents/code2prompt/twitter-circle
```

Once the server is running, open a web browser and navigate to `http://localhost:5001` to access the code retrieval interface.

**Usage Instructions:**
- Use @codebase keyword in queries to fetch relevant code context via embeddings
- Enable re-ranking option to get more relevant results
- This version returns only the retrieved code context, not generated responses


## Technologies Used

- Flask: server and UI
- Treesitter: parsing methods, classes, constructor declarations in a language agnostic way using the abstract syntax tree
- LanceDB: vector db for storing and searching code embeddings
- Redis: in-memory data store for caching and session management
- OpenAI, Jina for chat functionalities and colbert-small-v1 for reranker


## License

This project is licensed under the [MIT License](LICENSE).
