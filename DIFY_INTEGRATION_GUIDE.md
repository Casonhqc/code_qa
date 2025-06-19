# Dify 集成指南 - CodeQA 外部知识库

## 🎯 概述

本指南将帮助您将CodeQA代码召回系统集成到Dify中，作为外部知识库使用。通过这个集成，您可以在Dify应用中直接查询和召回代码片段。

## ✅ 集成验证

我们已经成功实现并测试了符合Dify规范的外部知识库API：

### 🧪 测试结果

```
🧪 Dify External Knowledge API Test Suite
============================================================
✅ Health check passed: healthy
✅ Authentication tests: All passed
✅ Retrieval API tests: 3/3 successful
✅ Edge cases: All handled correctly
```

### 📊 性能指标

- **响应时间**: 17-24秒
- **召回精度**: 高质量代码片段
- **支持查询**: 中文 + 英文
- **并发处理**: 支持多用户同时访问

## 🚀 部署步骤

### 1. 启动CodeQA Dify API服务

```bash
# 确保在feature/retrieval-only分支
git checkout feature/retrieval-only

# 启动Dify API服务（端口5002）
python3 dify_api.py /path/to/your/codebase
```

### 2. 验证服务状态

```bash
# 健康检查
curl http://localhost:5002/health

# 预期响应
{
  "status": "healthy",
  "service": "CodeQA Dify External Knowledge API",
  "version": "1.0.0"
}
```

### 3. 在Dify中配置外部知识库

#### 步骤1: 进入知识库管理
1. 登录Dify控制台
2. 导航到 **知识库** 页面
3. 点击 **连接外部知识库**

#### 步骤2: 选择API类型
1. 选择 **API** 作为外部知识库类型
2. 填写以下配置信息：

```
API端点: http://your-server:5002/retrieval
API密钥: codeqa-api-key-2025
知识库ID: codeqa-java-mall
```

#### 步骤3: 测试连接
使用以下测试查询验证连接：
- **测试查询**: "用户登录功能"
- **预期结果**: 返回相关的登录方法和用户类

## 📋 API 规范详情

### 请求格式

```http
POST http://your-server:5002/retrieval
Content-Type: application/json
Authorization: Bearer codeqa-api-key-2025

{
    "knowledge_id": "codeqa-java-mall",
    "query": "用户登录功能",
    "retrieval_setting": {
        "top_k": 5,
        "score_threshold": 0.5
    }
}
```

### 响应格式

```json
{
    "records": [
        {
            "content": "@PostMapping(\"/login\")\npublic String login(...)",
            "score": 0.8542,
            "title": "Method in AdminIndexController.java",
            "metadata": {
                "file_path": "/path/to/AdminIndexController.java",
                "type": "method",
                "method_name": "login",
                "class_name": "AdminIndexController"
            }
        }
    ]
}
```

## 🔧 配置参数

### 环境变量配置

在`.env`文件中设置：

```env
# Dify API配置
DIFY_API_KEY=codeqa-api-key-2025
KNOWLEDGE_BASE_ID=codeqa-java-mall

# OpenAI配置
OPENAI_BASE_URL=https://api.oaipro.com/v1
OPENAI_API_KEY=your-openai-api-key

# Redis配置
REDIS_HOST=your-redis-host
REDIS_PORT=6380
REDIS_PASSWORD=your-redis-password
```

### 检索参数

| 参数 | 默认值 | 范围 | 描述 |
|------|--------|------|------|
| top_k | 5 | 1-20 | 返回结果数量 |
| score_threshold | 0.5 | 0.0-1.0 | 相似度阈值 |

## 🎯 使用场景

### 1. 代码助手应用

在Dify中创建代码助手应用：

```
系统提示词：
你是一个专业的Java代码助手。基于提供的代码库上下文，帮助用户理解和使用代码。

知识库：CodeQA Java Mall
检索设置：top_k=5, score_threshold=0.5
```

### 2. 代码审查助手

```
系统提示词：
你是一个代码审查专家。分析提供的代码片段，给出改进建议和最佳实践。

知识库：CodeQA Java Mall
检索设置：top_k=3, score_threshold=0.6
```

### 3. 技术文档生成

```
系统提示词：
基于代码库中的实现，生成技术文档和API说明。

知识库：CodeQA Java Mall
检索设置：top_k=10, score_threshold=0.4
```

## 📊 查询示例

### 功能查询

```
用户: "如何实现用户登录功能？"
召回: AdminIndexController.login方法 + MallUser类
回答: 基于召回的代码提供登录实现说明
```

### 架构查询

```
用户: "这个项目的支付系统是如何设计的？"
召回: MallPayController + AlipayConfig + 支付相关方法
回答: 支付系统架构和实现细节
```

### 问题诊断

```
用户: "订单状态更新有什么问题？"
召回: OrderService + OrderStatusEnum + 相关方法
回答: 订单状态管理的实现和潜在问题
```

## 🔍 检索原理

### 1. 查询增强
- **中文关键词映射**: 用户→user, 登录→login
- **领域术语扩展**: 商品→goods product

### 2. HYDE双重增强
- **HYDE-1**: 生成预测代码片段
- **HYDE-2**: 基于初步结果优化查询

### 3. 智能召回
- **方法级检索**: 精确到函数级别
- **类级检索**: 完整的类定义和关系
- **语义重排序**: ColBERT提升相关性

## 🚨 注意事项

### 1. 性能考虑
- **响应时间**: 15-25秒（包含HYDE处理）
- **并发限制**: 建议不超过10个并发请求
- **缓存策略**: 启用Redis缓存提升性能

### 2. 安全配置
- **API密钥**: 妥善保管`codeqa-api-key-2025`
- **网络访问**: 确保Dify能访问API服务器
- **防火墙**: 开放端口5002

### 3. 监控和日志
- **服务监控**: 定期检查API服务状态
- **日志分析**: 查看检索质量和性能
- **错误处理**: 监控API错误率

## 🔧 故障排除

### 常见问题

1. **连接失败**
   ```
   检查: API服务是否运行在端口5002
   解决: python3 dify_api.py /path/to/codebase
   ```

2. **认证失败**
   ```
   检查: API密钥是否正确
   解决: 确认使用 codeqa-api-key-2025
   ```

3. **无结果返回**
   ```
   检查: score_threshold是否过高
   解决: 降低阈值到0.3-0.4
   ```

4. **响应超时**
   ```
   检查: OpenAI API是否可用
   解决: 验证OPENAI_API_KEY和网络连接
   ```

## 📞 技术支持

### 日志查看
```bash
# 查看API服务日志
tail -f app.log

# 查看实时控制台输出
# API服务会输出详细的检索过程日志
```

### 测试工具
```bash
# 运行完整测试套件
python3 test_dify_api.py

# 单独测试健康检查
curl http://localhost:5002/health
```

---

**🎉 集成完成！**

现在您可以在Dify中使用CodeQA作为外部知识库，为您的AI应用提供强大的代码检索和理解能力。
