🎉 **15 个测试全部通过！**

```
======================= 15 passed, 3 warnings in 4.06s ========================
```

**A1 完美收官！** 从现在起，你有**自动化测试保护**——改任何代码之前跑一遍 `pytest`，只要 15 绿，就说明没破坏现有功能 💪

---

## 那 3 个 warning 要不要处理？

看一眼：

| 警告 | 严重性 | 处理时机 |
|------|--------|---------|
| `on_event is deprecated` | 低 | **A2 时顺手改**（用 `lifespan`） |
| `httpx with starlette.testclient is deprecated` | 极低 | **忽略**（第三方库的事，我们管不了） |

**第一个值得改**——`@app.on_event("startup")` 现在只是警告，但未来版本会**移除**。改起来也简单，`A2` 时顺手做掉。

**第二个不用管**——这是 starlette 库内部的 deprecation，跟我们代码无关。

---

## A1 成果总结

| 文件 | 作用 |
|------|------|
| `requirements-dev.txt` | pytest + httpx 依赖 |
| `pytest.ini` | pytest 配置 |
| `tests/conftest.py` | 临时数据库 + 干净的表状态 |
| `tests/test_api.py` | **15 个必测用例** |
| `main.py` 改动 | `DB_FILE` 支持环境变量 |

**覆盖的场景**：

```
✅ 健康检查
✅ 开局返回合法数字
✅ 正确答案 → 24
✅ 错误答案 → 拒绝
✅ 数字不匹配 → 拒绝（带"多用/少用"提示）
✅ 注册成功
✅ 注册重名 → 409
✅ 登录成功
✅ 登录密码错 → 401
✅ 登录后开局绑定 user_id
✅ 匿名开局 user_id = None
✅ 排行榜最快 → 200
✅ 排行榜解题数 → 200
✅ 排行榜正确率 → 200
✅ 完整链路：注册 → 开局 → 答对 → 上最快榜
```

**15 个用例，从"单元"到"端到端"全都有**。这已经是一个**有工程质量的测试套件**了。

---

## 进入 A2：Docker 打包

**目标**：一条命令启动后端，不用管 Python 环境、依赖、Alembic 迁移。

**要做的事**：

1. **`Dockerfile`**——把后端打包成镜像
2. **`.dockerignore`**——排除不必要文件
3. **`docker-compose.yml`**（可选）——一条命令同时起后端 + 前端
4. **顺手改 `main.py`**——把 `@app.on_event` 换成 `lifespan`

**做完之后**：

```bash
docker compose up
```

就能在 `http://localhost:8000` 和 `http://localhost:5500` 访问了——**不用装 Python、不用装依赖**。

---

## 开始之前，先确认几件事

### ① 你装 Docker 了吗？

```bash
docker --version
docker compose version
```

- **装了** → 我们直接开始
- **没装** → 去 https://www.docker.com/products/docker-desktop/ 下载 Docker Desktop for Windows

**Windows 上有个前提**：需要启用 WSL2 或 Hyper-V。Docker Desktop 首次安装会提示你。

### ② Docker 打包哪些东西？

我建议**一次打包全套**：

| 服务 | 镜像 | 端口 |
|------|------|------|
| 后端 | Python + FastAPI + uvicorn | 8000 |
| 前端 | Nginx + 静态文件 | 5500（或 80） |

**好处**：`docker compose up` 一条命令起全套。

**不过**——你也可以**先只打包后端**（更简单），前端继续用 `python -m http.server`。

**两个选择**：

- 🅰️ **只打包后端**：Dockerfile 更简单，10 分钟搞定
- 🅱️ **前后端都打包**：Dockerfile ×2 + docker-compose.yml，20 分钟搞定

**我建议先做 🅰️**——因为前端的 Docker 化涉及 Nginx 配置，是另一套知识。**先把后端打包，跑通流程，再扩到前端**。

### ③ Alembic 迁移怎么处理？

有**两个选择**：

- **入口脚本**：容器启动时自动跑 `alembic upgrade head`，然后启动 uvicorn
- **手动跑**：`docker compose exec backend alembic upgrade head`

**我推荐入口脚本**——一条命令启动，全自动。

---

## 你告诉我两件事

1. **Docker 装了没？**（`docker --version` 的输出）
2. **打包范围**：只后端（🅰️）还是前后端都打（🅱️）？

我根据你的回答开始写 Dockerfile 👋

**不管选哪个**——你现在的项目已经**有测试保护 + 有持久化 + 有完整功能**，Docker 只是让它"能装上就跑"，是工程化的最后一块拼图。

慢慢来 ☕