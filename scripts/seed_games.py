"""
seed_games.py —— 为每个测试用户生成游戏数据

用法：
    cd v5.3b_1
    python scripts/seed_games.py

前提：
    uvicorn 已在 127.0.0.1:8000 运行
    已跑过 seed_users.py（用户已存在）

效果：
    每个 user 玩 3~8 局
    每局以 60% 概率答对，40% 概率先错 1~3 次再对
    数据写入数据库（games + submissions）
"""
import requests
import time
import sys
from pathlib import Path

# 复用 solve.py 的求解函数
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from solve import solve

API = "http://127.0.0.1:8080/api"

PASSWORD = "test123"
NUM_USERS = 100
MIN_GAMES = 3
MAX_GAMES = 8

# 随机错误答案（数字肯定不对，所以会被数字比对拦下）
WRONG_EXPRS = ["1+2+3+4", "5*5+1-1", "10+10+5-1", "9*3-2-1"]


def login(username):
    r = requests.post(f"{API}/login", json={
        "username": username,
        "password": PASSWORD,
    })
    if r.status_code != 200:
        return None
    return r.json()["token"]


def play_one_game(token, allow_wrong_first=True):
    """玩一局，返回是否最终答对"""
    # 1. 开局
    r = requests.get(f"{API}/new-game", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        return False
    data = r.json()
    gid = data["game_id"]
    nums = data["numbers"]

    # 2. 决定这一局是否要先提交错误答案（模拟真实玩家）
    if allow_wrong_first and __import__("random").random() < 0.4:
        wrong_count = __import__("random").randint(1, 3)
        for _ in range(wrong_count):
            wrong = __import__("random").choice(WRONG_EXPRS)
            requests.post(
                f"{API}/check",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={"game_id": gid, "expression": wrong},
            )

    # 3. 求解并提交正确答案
    expr = solve(nums)
    if expr is None:
        return False

    r = requests.post(
        f"{API}/check",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json={"game_id": gid, "expression": expr},
    )
    if r.status_code != 200:
        return False
    return r.json().get("correct", False)


def main():
    import random
    random.seed(42)   # 可复现

    total_users = 0
    total_games = 0
    total_solved = 0
    failed_users = []

    for i in range(1, NUM_USERS + 1):
        username = f"user{i:03d}"
        token = login(username)
        if not token:
            failed_users.append(username)
            continue

        n_games = random.randint(MIN_GAMES, MAX_GAMES)
        solved = 0
        for _ in range(n_games):
            if play_one_game(token):
                solved += 1

        total_users += 1
        total_games += n_games
        total_solved += solved

        print(f"  {username}: {solved}/{n_games} solved")

    print()
    print(f"✅ 完成")
    print(f"   参与用户: {total_users}")
    print(f"   总游戏数: {total_games}")
    print(f"   答对局数: {total_solved}")
    if failed_users:
        print(f"⚠️  登录失败: {failed_users}")


if __name__ == "__main__":
    main()
