# 🚀 CodeQA 云服务器部署指南

## 📋 概述

本指南将帮助您在云服务器上部署CodeQA项目。项目已经过清理，只包含生产环境必需的文件。

## 🎯 部署分支

**推荐使用分支**: `feature/retrieval-only`

这个分支包含：
- ✅ 清理后的生产代码
- ✅ 统一的API架构
- ✅ 部署脚本
- ✅ 环境配置模板

## 📦 云服务器部署步骤

### 1. 克隆项目到云服务器

```bash
# 登录云服务器
ssh user@your-server

# 克隆项目
git clone https://github.com/Casonhqc/code_qa.git
cd code_qa

# 切换到生产分支
git checkout feature/retrieval-only
```

### 2. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv redis-server

# CentOS/RHEL
sudo yum install python3 python3-pip redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 3. 创建Python虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑环境配置
nano .env
```

配置内容：
```env
# OpenAI Configuration
OPENAI_BASE_URL=https://api.oaipro.com/v1
OPENAI_API_KEY=your-openai-api-key

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Dify External Knowledge API Configuration
DIFY_API_KEY=your-dify-api-key
KNOWLEDGE_BASE_ID=your-knowledge-base-id
```

### 5. 运行部署脚本

```bash
# 给脚本执行权限
chmod +x deploy.sh
chmod +x start_services.sh

# 运行部署脚本
./deploy.sh /path/to/your/target/codebase
```

### 6. 启动服务

```bash
# 启动Web界面 (端口5001)
./start_services.sh /path/to/your/target/codebase web

# 或启动Dify API (端口5002)
./start_services.sh /path/to/your/target/codebase dify

# 或同时启动两个服务
./start_services.sh /path/to/your/target/codebase both
```

## 🌐 服务访问

- **Web界面**: `http://your-server:5001`
- **Dify API**: `http://your-server:5002`
- **健康检查**: 
  - `http://your-server:5001/health`
  - `http://your-server:5002/health`

## 🔧 生产环境配置

### 使用Nginx反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:5002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 使用systemd管理服务

创建服务文件：
```bash
sudo nano /etc/systemd/system/codeqa-web.service
```

```ini
[Unit]
Description=CodeQA Web Interface
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/code_qa
Environment=PATH=/path/to/code_qa/venv/bin
ExecStart=/path/to/code_qa/venv/bin/python app_unified.py /path/to/target/codebase
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable codeqa-web
sudo systemctl start codeqa-web
```

## 🔍 故障排除

### 检查服务状态
```bash
# 检查进程
ps aux | grep python

# 检查端口
netstat -tlnp | grep :5001
netstat -tlnp | grep :5002

# 检查日志
tail -f nohup.out
```

### 常见问题

1. **Redis连接失败**
   - 检查Redis服务状态：`sudo systemctl status redis`
   - 检查防火墙设置
   - 验证Redis配置

2. **端口被占用**
   - 查找占用进程：`lsof -i :5001`
   - 杀死进程：`kill -9 <PID>`

3. **权限问题**
   - 确保用户有读写权限
   - 检查文件所有者：`ls -la`

## 📊 性能监控

### 监控脚本
```bash
#!/bin/bash
# monitor.sh
while true; do
    echo "$(date): Checking services..."
    curl -s http://localhost:5001/health || echo "Web service down"
    curl -s http://localhost:5002/health || echo "API service down"
    sleep 60
done
```

## 🔄 更新部署

```bash
# 拉取最新代码
git pull origin feature/retrieval-only

# 重启服务
sudo systemctl restart codeqa-web
sudo systemctl restart codeqa-api
```

## 📞 支持

如果遇到问题，请检查：
1. 环境配置是否正确
2. 依赖是否完整安装
3. 服务日志中的错误信息
4. 网络连接和防火墙设置
