#!/bin/bash

# CodeQA 服务启动脚本
# 使用方法: ./start_services.sh <target_codebase_path> [service_type]
# service_type: web (默认) | dify | both

set -e

# 检查参数
if [ $# -eq 0 ]; then
    echo "❌ 错误: 请提供目标代码库路径"
    echo "使用方法: ./start_services.sh <target_codebase_path> [service_type]"
    echo "service_type: web (默认) | dify | both"
    exit 1
fi

TARGET_CODEBASE="$1"
SERVICE_TYPE="${2:-web}"

# 检查目标代码库是否存在
if [ ! -d "$TARGET_CODEBASE" ]; then
    echo "❌ 错误: 目录 '$TARGET_CODEBASE' 不存在"
    exit 1
fi

echo "🚀 启动 CodeQA 服务..."
echo "📚 目标代码库: $TARGET_CODEBASE"
echo "🔧 服务类型: $SERVICE_TYPE"

# 启动函数
start_web() {
    echo "🌐 启动Web界面服务 (端口5001)..."
    python3 app_unified.py "$TARGET_CODEBASE"
}

start_dify() {
    echo "📡 启动Dify API服务 (端口5002)..."
    python3 dify_api_unified.py "$TARGET_CODEBASE"
}

start_both() {
    echo "🔄 启动所有服务..."
    echo "📡 启动Dify API服务 (后台运行)..."
    nohup python3 dify_api_unified.py "$TARGET_CODEBASE" > dify_api.log 2>&1 &
    DIFY_PID=$!
    echo "Dify API PID: $DIFY_PID"
    
    sleep 3
    
    echo "🌐 启动Web界面服务..."
    python3 app_unified.py "$TARGET_CODEBASE"
}

# 根据服务类型启动
case $SERVICE_TYPE in
    "web")
        start_web
        ;;
    "dify")
        start_dify
        ;;
    "both")
        start_both
        ;;
    *)
        echo "❌ 错误: 无效的服务类型 '$SERVICE_TYPE'"
        echo "有效选项: web | dify | both"
        exit 1
        ;;
esac
