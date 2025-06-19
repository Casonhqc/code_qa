# CodeQA - Retrieval Only Branch

## 概述

这个分支 (`feature/retrieval-only`) 是从原始分支创建的专注于代码召回功能的版本。它移除了最后一步的大模型回答生成功能，专注于高质量的代码检索。

## 主要变更

### 🔧 技术变更

1. **移除了大模型回答生成**
   - 删除了 `openai_chat` 函数
   - 移除了 `CHAT_SYSTEM_PROMPT` 的导入和使用
   - 路由处理只返回检索到的代码上下文，不生成回答

2. **配置了指定的LLM设置**
   - 使用自定义的 OpenAI 兼容 API
   - Base URL: `https://api.oaipro.com/v1`
   - API Key: `sk-GCYpSq4rQMnm8xiScoxtRecBSYgZqaQANF2DTLeRZtac2CNUdHaY`

3. **保留了核心召回功能**
   - HYDE 查询增强 (使用 gpt-4o-mini)
   - HYDE-v2 二次查询优化
   - ColBERT 重排序功能
   - LanceDB 向量搜索

### 🎨 界面变更

1. **更新了页面标题**
   - 从 "CodeQA" 改为 "CodeQA - Retrieval Only"

2. **修改了欢迎消息**
   - 明确说明这是检索专用版本
   - 提示用户使用 `@codebase` 关键词

3. **更新了输入提示**
   - 占位符文本提示使用 `@codebase` 进行检索

### 📚 文档更新

1. **README.md**
   - 更新了分支说明
   - 修改了功能描述
   - 更新了配置说明

2. **新增测试脚本**
   - `test_retrieval.py` 用于验证配置和依赖

## 功能特点

### ✅ 保留的功能

- **智能查询增强**: 使用 HYDE 和 HYDE-v2 提升检索质量
- **向量搜索**: 基于 LanceDB 的高效代码搜索
- **重排序**: 可选的 ColBERT 重排序提升相关性
- **多语言支持**: Python, Rust, JavaScript, Java
- **AST 解析**: 使用 tree-sitter 进行代码结构分析
- **会话管理**: Redis 缓存检索上下文

### ❌ 移除的功能

- **LLM 回答生成**: 不再生成自然语言回答
- **对话式交互**: 不支持连续对话
- **代码解释**: 不提供代码解释和分析

## 使用方法

### 1. 环境准备

```bash
# 确保 Python 3.8-3.11 (tree-sitter 要求)
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动 Redis
redis-server
```

### 2. 验证配置

```bash
# 运行测试脚本
python3 test_retrieval.py
```

### 3. 索引代码库

```bash
# 给脚本执行权限
chmod +x index_codebase.sh

# 索引你的代码库
./index_codebase.sh /path/to/your/codebase
```

### 4. 启动应用

```bash
python3 app.py /path/to/your/codebase
```

### 5. 使用界面

1. 打开浏览器访问 `http://localhost:5001`
2. 在查询中使用 `@codebase` 关键词
3. 可选择启用重排序功能
4. 系统将返回相关的代码片段和文件路径

## 查询示例

```
@codebase 如何处理用户认证
@codebase 数据库连接的实现
@codebase 错误处理机制
@codebase API 路由定义
```

## 技术架构

```
用户查询 → HYDE增强 → 向量搜索 → HYDE-v2优化 → 重排序(可选) → 返回代码上下文
```

## 优势

1. **专注性**: 专注于代码检索，避免了LLM幻觉问题
2. **速度**: 无需等待LLM生成回答，响应更快
3. **准确性**: 直接返回相关代码，信息更准确
4. **成本效益**: 减少了LLM API调用成本

## 适用场景

- 代码库探索和理解
- 快速定位相关代码片段
- 代码审查和重构准备
- 学习和研究现有代码库
- 构建更复杂的代码分析工具的基础

## 后续扩展

这个分支可以作为基础，进一步扩展为：
- 代码相似性分析工具
- 代码重复检测系统
- 自动化代码文档生成
- 代码质量分析工具
