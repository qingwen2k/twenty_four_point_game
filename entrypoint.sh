#!/bin/sh
set -e

echo "⏳ 正在执行数据库迁移..."
alembic upgrade head

echo "🚀 启动 FastAPI 服务..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
