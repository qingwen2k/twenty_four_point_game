"""
conftest.py —— pytest 的共享 fixture

核心思路：
    1. 先设置 DB_FILE 环境变量到临时文件
    2. 再 import main（只 import 一次）
    3. 每个测试用例跑之前清空所有表
    4. 测试会话结束时删掉临时数据库
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# 让测试能 import 到 v5.4 下的 main.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------- 会话级别：一次性设置临时数据库 ----------
@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    """整个测试会话共用一个临时数据库文件"""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db", prefix="test_24game_")
    os.close(tmp_fd)

    # 关键：在 import main 之前设好环境变量
    os.environ["DB_FILE"] = tmp_path

    # import main（只一次！不 reload）
    import main
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(main.engine)

    yield

    # 测试会话结束：删掉临时库
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


# ---------- 每个测试函数：清空表 ----------
@pytest.fixture
def client():
    """
    给每个测试函数一个 TestClient，且保证数据库是干净的。
    """
    import main
    from fastapi.testclient import TestClient
    from sqlmodel import Session, delete
    from main import Game, Submission, User

    # 清空所有表（保持表结构，只清数据）
    with Session(main.engine) as session:
        session.exec(delete(Submission))
        session.exec(delete(Game))
        session.exec(delete(User))
        session.commit()

    with TestClient(main.app) as c:
        yield c
