#!/bin/bash

echo "=================================="
echo "  LLM Anything Web 启动器"
echo "=================================="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 未安装"
    exit 1
fi

# 检查并安装依赖
echo "📦 检查依赖..."

if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "安装 FastAPI..."
    pip3 install fastapi
fi

if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "安装 Uvicorn..."
    pip3 install uvicorn
fi

if ! python3 -c "import openai" 2>/dev/null; then
    echo "安装 OpenAI..."
    pip3 install openai
fi

if ! python3 -c "import websockets" 2>/dev/null; then
    echo "安装 WebSockets..."
    pip3 install websockets
fi

# 检查 API KEY
if [ -z "$DB_API_KEY" ]; then
    echo ""
    echo "⚠️  未设置 API KEY"
    echo "请输入你的 API KEY (OpenRouter/OpenAI):"
    read -r api_key
    export DB_API_KEY="$api_key"
fi

# 启动服务器
echo ""
echo "🚀 启动服务器..."
echo "=================================="
echo ""

python3 app.py