#!/bin/bash

# CodeQA 云服务器部署脚本
# 使用方法: ./deploy.sh <target_codebase_path>

set -e  # 遇到错误立即退出

# 检查参数
if [ $# -eq 0 ]; then
    echo "❌ 错误: 请提供目标代码库路径"
    echo "使用方法: ./deploy.sh <target_codebase_path>"
    exit 1
fi

TARGET_CODEBASE="$1"

# 检查目标代码库是否存在
if [ ! -d "$TARGET_CODEBASE" ]; then
    echo "❌ 错误: 目录 '$TARGET_CODEBASE' 不存在"
    exit 1
fi

echo "🚀 开始部署 CodeQA 到云服务器..."
echo "📚 目标代码库: $TARGET_CODEBASE"

# 1. 检查Python环境
echo "🔍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 2. 安装依赖
echo "📦 安装Python依赖..."
pip3 install -r requirements.txt

# 3. 检查环境配置
echo "⚙️ 检查环境配置..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 复制环境配置模板..."
        cp .env.example .env
        echo "⚠️ 请编辑 .env 文件配置API密钥和Redis连接"
        echo "⚠️ 配置完成后重新运行此脚本"
        exit 1
    else
        echo "❌ 缺少环境配置文件"
        exit 1
    fi
fi

# 4. 检查数据库文件
echo "🗄️ 检查数据库文件..."
if [ ! -d "database" ]; then
    echo "⚠️ 数据库文件夹不存在，需要重新索引代码库..."
    echo "🔄 开始索引代码库..."
    chmod +x index_codebase.sh
    ./index_codebase.sh "$TARGET_CODEBASE"
else
    echo "✅ 数据库文件已存在"
fi

# 5. 检查Redis连接
echo "🔗 检查Redis连接..."
python3 -c "
import redis
import os
from dotenv import load_dotenv

load_dotenv()

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
    
    client = redis.Redis(**redis_config)
    client.ping()
    print('✅ Redis连接成功')
except Exception as e:
    print(f'⚠️ Redis连接失败: {e}')
    print('💡 服务仍可运行，但缓存功能将被禁用')
"

echo ""
echo "🎉 部署完成！"
echo ""
echo "🌐 启动服务命令:"
echo "   Web界面:    python3 app_unified.py '$TARGET_CODEBASE'"
echo "   Dify API:   python3 dify_api_unified.py '$TARGET_CODEBASE'"
echo ""
echo "📡 服务端口:"
echo "   Web界面:    http://0.0.0.0:5001"
echo "   Dify API:   http://0.0.0.0:5002"
echo ""
echo "🔧 健康检查:"
echo "   curl http://localhost:5001/health"
echo "   curl http://localhost:5002/health"
