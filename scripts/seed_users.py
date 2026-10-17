"""
seed_users.py —— 批量创建测试用户（直接写数据库）

用法：
    cd v5.3b_1
    python scripts/seed_users.py

效果：
    创建 100 个用户 user001 ~ user100
    密码统一为 password001 ~ password100（或者统一 test123）
"""
import sys
import os
import time
from pathlib import Path

# 把 v5.3b_1 加到 sys.path，这样能 import main 里的东西
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.context import CryptContext
from sqlmodel import Session, create_engine, select
from main import User, DB_FILE

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

NUM_USERS = 100
PASSWORD = "test123"          # 所有测试用户统一密码，方便登录
USERNAME_PREFIX = "user"


def main():
    engine = create_engine(f"sqlite:///{DB_FILE}")

    created = 0
    skipped = 0

    with Session(engine) as session:
        for i in range(1, NUM_USERS + 1):
            username = f"{USERNAME_PREFIX}{i:03d}"   # user001, user002, ...

            # 已存在就跳过
            existing = session.exec(
                select(User).where(User.username == username)
            ).first()
            if existing:
                skipped += 1
                continue

            user = User(
                username=username,
                hashed_password=pwd_context.hash(PASSWORD),
                created_at=time.time(),
            )
            session.add(user)
            created += 1

        session.commit()

    print(f"✅ 完成")
    print(f"   新建用户: {created}")
    print(f"   跳过(已存在): {skipped}")
    print(f"   统一密码: {PASSWORD}")


if __name__ == "__main__":
    main()
