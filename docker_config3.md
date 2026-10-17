完美！这绝对是历史性的一刻 🎉

从截图看，前后端完全打通了，而且这 100 个用户和 570 局游戏数据**全都成功写入了 Docker 挂载的 SQLite 数据库中**。排行榜再次满血复活，三种榜单的数据非常丰满。

---

## 开始准备上线：Git 初始化

上线第一步是**把代码托管到 GitHub**。我们要确保推到 GitHub 上的代码是“干净”的（不包含本地数据库、缓存文件等）。

### ① 创建 `.gitignore`

在 `v5.5` 根目录下，创建一个名为 `.gitignore` 的文件，内容如下：

```gitignore
# Python 缓存
__pycache__/
*.py[cod]
*$py.class

# Pytest 缓存
.pytest_cache/

# 数据库文件（本地开发用，绝不能推到 GitHub）
*.db
data/

# 环境变量
.env
.venv/
venv/

# 操作系统文件
.DS_Store
Thumbs.db

# IDE 配置
.vscode/
.idea/
```

> **特别注意**：`data/` 被忽略了。这意味着你推送到 GitHub 的代码不包含那 100 个用户和 570 局的游戏数据。这**完全符合工程实践**——业务数据（数据库）永远不应该进 Git 仓库。云端部署时，Render 会给你分配一个干净的持久化磁盘，你需要重新注册或重新造数据。

### ② 初始化 Git 并提交

在 `v5.5` 根目录执行：

```bash
git init
git add .
git commit -m "feat: v5.5 完整前后端 + Docker 化"
```

### ③ 在 GitHub 创建仓库

1. 登录你的 GitHub 账号。
2. 点击右上角 `+` -> `New repository`。
3. 仓库名随便起（比如 `twenty-four-game`），**不要勾选** "Add a README file" 和 "Add .gitignore"（因为你本地已经有了）。
4. 创建后，GitHub 会显示一段命令，类似：
   ```bash
   git remote add origin https://github.com/你的用户名/twenty-four-game.git
   git branch -M main
   git push -u origin main
   ```
5. 在你的终端里运行这三条命令，把代码推上去。

> 如果提示需要验证，推荐使用 **GitHub Personal Access Token (PAT)** 代替密码进行验证。

---

## 下一步：配置 Render 部署后端

代码推上去之后，我们要部署后端。**Render** 是一个支持 Docker 部署、带持久化磁盘且免费对个人开放的平台。

### ① 在 Render 创建 Web Service

1. 登录 [Render](https://render.com/)，用 GitHub 账号登录。
2. 点击 **New** -> **Web Service**。
3. 选择你刚刚推上去的仓库。
4. 填写基本信息：
   - **Name**: `twenty-four-api`（随意）
   - **Region**: 选一个离你近的（比如 Singapore 或 Oregon）
   - **Branch**: `main`
   - **Runtime**: 选择 **Docker**（Render 会自动找到你根目录下的 `Dockerfile`）
   - **Instance Type**: **Free**（免费层有冷启动延迟，但够学习用）

### ② 配置持久化磁盘（非常关键！）

在 Render 的服务设置里，往下滑动找到 **Disks** 选项卡：

1. 点击 **Add Disk**。
2. **Name**: `game-data`
3. **Mount Path**: `/app/data` （这必须和我们在 Docker 里设置的路径一致）
4. **Size**: 1 GB (免费额度)

### ③ 配置环境变量

在 **Environment** 选项卡中，添加一个环境变量：

- **Key**: `DB_FILE`
- **Value**: `/app/data/game.db`

### ④ 部署

点击底部的 **Create Web Service**。Render 会自动开始拉取你的代码、构建 Docker 镜像、启动容器。

第一次部署大概需要 **3-5 分钟**（因为要安装 Python 依赖）。如果你在 Render 的 Logs 里看到熟悉的：

```text
⏳ 正在执行数据库迁移...
INFO  [alembic.runtime.migration] Running upgrade ...
🚀 启动 FastAPI 服务...
INFO: Uvicorn running on http://0.0.0.0:8000
```

那就说明**后端成功上云了**！

---

## 下一步：配置 Cloudflare Pages 部署前端

后端起好之后，Render 会给你一个公网地址（例如 `https://twenty-four-api.onrender.com`）。

我们要把前端托管到 **Cloudflare Pages**。

### ① 修改前端的 API 地址

在把前端推上去之前，我们需要告诉前端：“后端在哪里”。
打开你本地电脑上的 `frontend/js/api.js`，找到最上面：

```javascript
const API_BASE = (window.location.port === '5500' || window.location.port === '') 
    ? 'http://127.0.0.1:8000' 
    : '/api';
```

改成：

```javascript
const API_BASE = (window.location.port === '5500' || window.location.port === '') 
    ? 'http://127.0.0.1:8000' 
    : (window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1'))
        ? '/api'
        : 'https://twenty-four-api.onrender.com'; // ★ 替换成你的 Render 真实地址
```

*(这样一来，本地开发走代理或 8000，上线后直接请求 Render 的地址)*

改完后，**重新 commit 并 push 到 GitHub**：

```bash
git add frontend/js/api.js
git commit -m "chore: 配置生产环境 API 地址"
git push
```

### ② 在 Cloudflare Pages 部署

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)。
2. 左侧菜单点击 **Workers & Pages** -> **Create** -> **Pages** -> **Connect to Git**。
3. 选择你刚刚的 GitHub 仓库。
4. 填写构建配置：
   - **Project name**: `twenty-four-game`（随意）
   - **Production branch**: `main`
   - **Framework preset**: `None`
   - **Build command**: 留空（因为是纯静态）
   - **Build output directory**: `frontend`
5. 点击 **Save and Deploy**。

Cloudflare 会立刻把你的前端静态文件分发到全球 CDN。几秒钟后，你会得到一个类似 `https://twenty-four-game.pages.dev` 的网址。

---

## 预期结果

当你打开 `https://twenty-four-game.pages.dev` 时：
- 前端界面瞬间加载（走 Cloudflare CDN）。
- 点「新一局」时，请求会发往你在 Render 上的后端。
- 因为后端开启了 CORS（允许任何来源），所以请求成功。
- 注册、游玩、排行榜全部正常工作。

**准备好了吗？** 你可以先执行第一步：**创建 `.gitignore` 并推送到 GitHub**。推上去后告诉我，我们就去 Render 操作。
