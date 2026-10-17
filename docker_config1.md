太棒了！Docker 29.8.2 已就绪 🐳

我们正式进入 **v5.5：Docker 打包与工程化**。

考虑到你最终想“接近工程实践”并考虑上云（如 Cloudflare Pages 或 Render），我们的打包方案会采用**业界标准的前后端分离结构**：

1. **后端 (`backend`)**：Python 环境，容器启动时自动执行 Alembic 迁移，然后启动 Uvicorn。
2. **前端 (`frontend`)**：Nginx 容器，托管静态文件，并**通过 Nginx 反向代理解决跨域问题**（这样前端代码里的 `API_BASE` 可以直接写成相对路径，上线时无需修改，最符合生产环境做法）。

---

## 第一步：建立 v5.5 目录

```bash
cd /c/zhangqw/project/web_design/twenty_four
# 复制目录
cp -r v5.4 v5.5
cd v5.5

# 更新版本号
echo "5.5" > VERSION

# 清理不需要进 Docker 的本地文件
rm -f game.db
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
rm -rf .pytest_cache
```

---

## 第二步：准备后端 Docker 文件

在 `v5.5/` 根目录下创建三个文件：

### ① `requirements.txt`（生产依赖）

```text
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
sqlmodel>=0.0.16
passlib[bcrypt]>=1.7.4
bcrypt==4.0.1
pyjwt>=2.8.0
alembic>=1.13.0
```

### ② `entrypoint.sh`（启动脚本）

这个脚本负责在容器启动时先做数据库迁移，再启动服务。

```bash
#!/bin/sh
set -e

echo "⏳ 正在执行数据库迁移..."
alembic upgrade head

echo "🚀 启动 FastAPI 服务..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
```

### ③ `Dockerfile`（后端镜像）

```dockerfile
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
```

---

## 第三步：准备前端 Docker 文件

在 `v5.5/frontend/` 目录下创建两个文件：

### ① `nginx.conf`（核心：反向代理配置）

```nginx
server {
    listen 80;
    server_name localhost;

    # 1. 托管静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # 2. 反向代理到后端 API（解决跨域）
    location /api/ {
        # 注意：这里的 backend 是 docker-compose 里的服务名
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### ② `Dockerfile`（前端镜像）

```dockerfile
FROM nginx:alpine

# 删除 Nginx 默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 拷贝自定义配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝静态文件
COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## 第四步：编排文件 `docker-compose.yml`

在 `v5.5/` 根目录创建：

```yaml
services:
  backend:
    build: .
    container_name: game24_backend
    restart: unless-stopped
    volumes:
      # 将数据库文件挂载到宿主机，防止容器销毁数据丢失
      - ./data:/app/data
    environment:
      # 指定数据库存放到挂载的目录中
      - DB_FILE=/app/data/game.db

  frontend:
    build: ./frontend
    container_name: game24_frontend
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - backend
```

### ⑤ 创建数据目录

```bash
mkdir data
```

---

## 第五步：修改前端代码（适配反向代理）

因为我们在 Nginx 配置了 `/api/` 反向代理，所以前端代码请求后端时，**不再需要写死 `127.0.0.1:8000`**，直接写相对路径即可。这符合生产环境标准（上线后不用改代码）。

打开 `frontend/js/api.js`，找到第一行：

```javascript
const API_BASE = 'http://127.0.0.1:8000';
```

**修改为：**

```javascript
// 如果当前访问的是 localhost:5500 (本地开发)，走 8000 端口
// 如果访问的是 8080 (Docker Nginx)，走 /api 相对路径
const API_BASE = (window.location.port === '5500' || window.location.port === '') 
    ? 'http://127.0.0.1:8000' 
    : '/api';
```

---

## 第六步：一键启动

回到 `v5.5` 根目录，执行：

```bash
docker compose up --build -d
```

*(提示：第一次运行会下载基础镜像并安装依赖，可能需要 2-5 分钟，请耐心等待。)*

看到类似如下输出即为成功：
```text
[+] Running 3/3
 ✔ Network v55_default       Created
 ✔ Container game24_backend  Started
 ✔ Container game24_frontend Started
```

---

## 验证测试

1. **检查容器状态**：
   ```bash
   docker compose ps
   ```
   应该看到 `backend` 和 `frontend` 都在 `Up` 状态。

2. **检查后端迁移**：
   ```bash
   docker compose logs backend
   ```
   应该能看到我们脚本里写的 `⏳ 正在执行数据库迁移...` 和 `🚀 启动 FastAPI 服务...`。

3. **访问前端**：
   打开浏览器，访问 `http://127.0.0.1:8080`
   - 页面应该能正常打开。
   - 尝试注册一个新用户、开局、验证答案。由于有反向代理，前端通过 `/api` 请求后端，**全程无任何跨域报错**。
   - 去排行榜，数据正常展示。

4. **验证数据持久化**：
   ```bash
   ls -l data/
   ```
   你会在本地看到 `data/game.db` 文件。当你重启电脑或执行 `docker compose down` 之后再次 `up`，你的用户和战绩依然保留！

---

## 下一步准备

当你把 `docker compose up --build -d` 跑通，并且能在 `8080` 端口完整游玩后，就可以告诉我。

到那时，你的工程化就彻底闭环了。我们会讨论如何：
1. 把前端推到 GitHub，连接 Cloudflare Pages。
2. 把后端镜像推到 Docker Hub 或直接用 Render 拉取部署。

先跑这一步，有任何构建报错（比如网络拉取慢、bcrypt 编译错误等），直接把报错贴给我！