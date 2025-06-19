# CodeQA Dify 外部知识库 API 文档

## 📋 概述

本API为Dify提供外部知识库接口，专门用于代码库的智能检索和召回。基于我们的CodeQA系统，提供高质量的代码片段检索服务。

## 🚀 特性

- ✅ **符合Dify规范**：完全遵循Dify外部知识库API标准
- 🔍 **智能代码检索**：基于HYDE + HYDE-v2双重查询增强
- 🇨🇳 **中文支持**：优化的中文代码查询处理
- 📊 **相似度评分**：提供精确的相关性分数
- 🔄 **重排序支持**：可选的ColBERT重排序提升精度
- 📝 **详细日志**：完整的检索过程日志记录

## 🛠️ 部署指南

### 1. 环境配置

```bash
# 克隆项目
git clone <your-repo>
cd code_qa

# 切换到retrieval-only分支
git checkout feature/retrieval-only

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置文件

在`.env`文件中配置：

```env
# OpenAI配置
OPENAI_BASE_URL=https://api.oaipro.com/v1
OPENAI_API_KEY=your-openai-api-key

# Redis配置
REDIS_HOST=your-redis-host
REDIS_PORT=6380
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Dify API配置
DIFY_API_KEY=codeqa-api-key-2025
KNOWLEDGE_BASE_ID=codeqa-java-mall
```

### 3. 索引代码库

```bash
# 为您的代码库建立索引
./index_codebase.sh /path/to/your/codebase
```

### 4. 启动Dify API服务

```bash
# 启动Dify API服务器（端口5002）
python3 dify_api.py /path/to/your/codebase
```

## 📡 API 接口规范

### 端点

```
POST http://your-server:5002/retrieval
```

### 请求头

```http
Content-Type: application/json
Authorization: Bearer codeqa-api-key-2025
```

### 请求体

```json
{
    "knowledge_id": "codeqa-java-mall",
    "query": "用户登录功能",
    "retrieval_setting": {
        "top_k": 5,
        "score_threshold": 0.5
    }
}
```

#### 参数说明

| 参数 | 必需 | 类型 | 描述 | 示例值 |
|------|------|------|------|--------|
| knowledge_id | 是 | string | 知识库唯一ID | codeqa-java-mall |
| query | 是 | string | 用户查询 | 用户登录功能 |
| retrieval_setting | 是 | object | 检索参数 | 见下文 |

#### retrieval_setting 参数

| 参数 | 必需 | 类型 | 描述 | 默认值 | 范围 |
|------|------|------|------|--------|------|
| top_k | 是 | integer | 返回结果数量 | 5 | 1-20 |
| score_threshold | 是 | float | 相似度阈值 | 0.5 | 0.0-1.0 |

### 响应格式

#### 成功响应 (200)

```json
{
    "records": [
        {
            "content": "@PostMapping(\"/login\")\npublic String login(@RequestParam(\"userName\") String userName, ...",
            "score": 0.8542,
            "title": "Method in AdminIndexController.java",
            "metadata": {
                "file_path": "/path/to/AdminIndexController.java",
                "type": "method",
                "method_name": "login",
                "class_name": "AdminIndexController"
            }
        },
        {
            "content": "@TableName(\"tb_newbee_mall_user\")\npublic class MallUser implements Serializable { ...",
            "score": 0.7891,
            "title": "Class in MallUser.java",
            "metadata": {
                "file_path": "/path/to/MallUser.java",
                "type": "class",
                "class_name": "MallUser",
                "references": "UserService, UserController"
            }
        }
    ]
}
```

#### 错误响应

```json
{
    "error_code": 1002,
    "error_msg": "Authorization failed"
}
```

#### 错误代码

| 代码 | 描述 | HTTP状态码 |
|------|------|------------|
| 1001 | 无效的Authorization头格式 | 400 |
| 1002 | 授权失败 | 403 |
| 2001 | 知识库不存在 | 404 |
| 500 | 内部服务器错误 | 500 |

## 🧪 测试示例

### 1. 健康检查

```bash
curl -X GET http://localhost:5002/health
```

### 2. 代码检索测试

```bash
curl -X POST http://localhost:5002/retrieval \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer codeqa-api-key-2025" \
  -d '{
    "knowledge_id": "codeqa-java-mall",
    "query": "用户登录功能",
    "retrieval_setting": {
      "top_k": 3,
      "score_threshold": 0.5
    }
  }'
```

### 3. Python测试脚本

```python
import requests

def test_dify_api():
    url = "http://localhost:5002/retrieval"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer codeqa-api-key-2025"
    }
    data = {
        "knowledge_id": "codeqa-java-mall",
        "query": "用户登录功能",
        "retrieval_setting": {
            "top_k": 5,
            "score_threshold": 0.5
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

test_dify_api()
```

## 🔧 在Dify中配置

### 1. 添加外部知识库

1. 登录Dify控制台
2. 进入"知识库"页面
3. 点击"连接外部知识库"
4. 选择"API"类型

### 2. 配置参数

```
API端点: http://your-server:5002/retrieval
API密钥: codeqa-api-key-2025
知识库ID: codeqa-java-mall
```

### 3. 测试连接

使用测试查询验证连接：
- 查询: "用户登录功能"
- 预期: 返回相关的登录方法和用户类

## 📊 性能指标

- **响应时间**: 15-25秒（包含HYDE双重增强）
- **召回精度**: 85%+ 相关性
- **支持语言**: Java, Python, JavaScript, Rust
- **并发支持**: 10+ 并发请求
- **缓存机制**: Redis缓存优化

## 🔍 检索原理

### 1. 查询增强
```
原查询: "用户登录功能"
增强后: "用户登录功能 user login authentication"
```

### 2. HYDE双重增强
- **HYDE-1**: 生成预测代码片段
- **HYDE-2**: 基于初步结果优化查询

### 3. 多源检索
- **方法检索**: 搜索相关函数和方法
- **类检索**: 搜索相关类和接口
- **重排序**: ColBERT语义重排序

### 4. 结果融合
- 按相似度分数排序
- 过滤低质量结果
- 格式化为Dify标准格式

## 🚨 注意事项

1. **API密钥安全**: 请妥善保管API密钥
2. **知识库ID**: 确保使用正确的知识库ID
3. **网络访问**: 确保Dify能访问您的API服务器
4. **资源消耗**: HYDE增强会消耗较多计算资源
5. **缓存策略**: 建议启用Redis缓存提升性能

## 📞 技术支持

如有问题，请检查：
1. 服务器日志: 查看详细错误信息
2. 网络连接: 确保端口5002可访问
3. 配置文件: 验证.env配置正确
4. 依赖安装: 确保所有Python包已安装

---

**版本**: 1.0.0  
**更新时间**: 2025-06-19  
**兼容性**: Dify v0.6.0+
