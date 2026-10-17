import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ============================================================
# 1. 路径与模型导入
# ============================================================
# 将项目根目录加入 sys.path，以便能够 import main
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import SQLModel
# 导入所有模型，让 Alembic 知道表结构
from main import Game, Submission, User

# 这是 Alembic 的配置对象，代表 alembic.ini
config = context.config

# ============================================================
# 2. 日志配置
# ============================================================
# 根据 alembic.ini 设置 Python 日志记录器
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================================
# 3. 元数据
# ============================================================
# 告诉 Alembic 你的模型长什么样
target_metadata = SQLModel.metadata


# ============================================================
# 4. 动态数据库 URL 覆盖（Docker 关键）
# ============================================================
# 如果环境变量里有 DB_FILE（比如 Docker 里设置的 /app/data/game.db），
# 就用它来覆盖 alembic.ini 里的 sqlalchemy.url
db_file = os.environ.get("DB_FILE")
if db_file:
    # 确保路径是 sqlite:/// 开头的格式
    if not db_file.startswith("sqlite:///"):
        # 如果是相对路径，转为绝对路径，避免受当前执行目录影响
        db_file = f"sqlite:///{os.path.abspath(db_file)}"
    config.set_main_option("sqlalchemy.url", db_file)
else:
    # 如果没有环境变量，使用 alembic.ini 里的默认值
    # 为了避免本地运行时找不到库，可以顺便强制一下默认值（可选）
    pass


# ============================================================
# 5. 离线迁移
# ============================================================
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite 必需
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# 6. 在线迁移
# ============================================================
def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 使用 config 中（已经被环境变量覆盖过的）url
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False},  # SQLite 多线程必需
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,    # SQLite 重建表必需
            compare_type=True,       # 检测字段类型变化
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
