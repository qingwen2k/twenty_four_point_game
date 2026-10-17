FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（SQLite 需要）
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 赋予启动脚本执行权限
RUN chmod +x entrypoint.sh

# 声明端口
EXPOSE 8000

# 使用启动脚本
CMD ["./entrypoint.sh"]
