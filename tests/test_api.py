"""
test_api.py —— 24点游戏后端的必测用例

覆盖：
    1. 健康检查
    2. 开局返回合法数字 + 有解
    3. 正确答案 → 24
    4. 错误答案 → 拒绝
    5. 数字不匹配 → 拒绝
    6. 注册成功
    7. 注册重名 → 409
    8. 登录成功
    9. 登录密码错 → 401
    10. 带 token 玩一局 → user_id 绑定
    11. 匿名玩一局 → user_id = None
    12. 排行榜三个接口 → 200 + 结构正确
"""
import time


# ============================================================
# 1. 健康检查
# ============================================================

def test_root_health(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "active_games" in data
    assert "total_submissions" in data
    assert "total_users" in data


# ============================================================
# 2. 开局
# ============================================================

def test_new_game_returns_valid_numbers(client):
    r = client.get("/new-game")
    assert r.status_code == 200
    data = r.json()

    assert "game_id" in data
    assert "numbers" in data
    assert "expires_in" in data

    nums = data["numbers"]
    assert isinstance(nums, list)
    assert len(nums) == 4
    for n in nums:
        assert isinstance(n, int)
        assert 1 <= n <= 13


# ============================================================
# 3~5. 验证答案
# ============================================================

def _start_game(client, token=None):
    """工具：开一局，返回 (game_id, numbers)"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = client.get("/new-game", headers=headers)
    assert r.status_code == 200
    data = r.json()
    return data["game_id"], data["numbers"]


def _solve(nums):
    """工具：找出一组解（简单版，复用 solve.py 的逻辑）"""
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ROOT))
    from solve import solve
    return solve(nums)


def test_correct_answer(client):
    gid, nums = _start_game(client)
    expr = _solve(nums)
    assert expr is not None, f"生成题目无解: {nums}"

    r = client.post("/check", json={"game_id": gid, "expression": expr})
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is True
    assert data["result"] == 24.0
    assert "elapsed" in data


def test_wrong_answer(client):
    gid, nums = _start_game(client)
    # 故意提交一个数字不匹配的表达式
    r = client.post("/check", json={"game_id": gid, "expression": "1+2+3+4"})
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is False
    assert "reason" in data


def test_number_mismatch(client):
    """用错数字个数"""
    gid, nums = _start_game(client)
    # 用五个数字
    expr = "+".join(str(n) for n in nums + [1])
    r = client.post("/check", json={"game_id": gid, "expression": expr})
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is False
    # 明确提示"多用"或"少用"
    assert "多用" in data["reason"] or "少用" in data["reason"]


# ============================================================
# 6~9. 注册 / 登录
# ============================================================

def test_register_success(client):
    r = client.post("/register", json={
        "username": "testuser1",
        "password": "secret123",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "testuser1"
    assert "token" in data
    assert data["user_id"] > 0


def test_register_duplicate(client):
    client.post("/register", json={"username": "dupuser", "password": "secret123"})
    r = client.post("/register", json={"username": "dupuser", "password": "another"})
    assert r.status_code == 409
    assert "占用" in r.json()["detail"]


def test_login_success(client):
    client.post("/register", json={"username": "loginuser", "password": "secret123"})
    r = client.post("/login", json={"username": "loginuser", "password": "secret123"})
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "loginuser"
    assert "token" in data


def test_login_wrong_password(client):
    client.post("/register", json={"username": "pwuser", "password": "secret123"})
    r = client.post("/login", json={"username": "pwuser", "password": "wrongpass"})
    assert r.status_code == 401
    assert "用户名或密码错误" in r.json()["detail"]


# ============================================================
# 10~11. 用户绑定
# ============================================================

def test_logged_in_game_binds_user(client):
    """登录后开局，user_id 应该被绑定"""
    # 注册 + 拿 token
    r = client.post("/register", json={"username": "binder", "password": "secret123"})
    token = r.json()["token"]
    user_id = r.json()["user_id"]

    # 带 token 开局
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/new-game", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == user_id
    assert data["is_anonymous"] is False


def test_anonymous_game_no_user(client):
    """匿名开局，user_id 应该为 None"""
    r = client.get("/new-game")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] is None
    assert data["is_anonymous"] is True


# ============================================================
# 12. 排行榜
# ============================================================

def test_leaderboard_fastest(client):
    r = client.get("/leaderboard/fastest")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_leaderboard_most_solved(client):
    r = client.get("/leaderboard/most-solved")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_leaderboard_accuracy(client):
    r = client.get("/leaderboard/accuracy")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_leaderboard_has_data_after_play(client):
    """完整链路：注册 → 开局 → 答对 → 上最快榜"""
    # 1. 注册
    r = client.post("/register", json={"username": "champ", "password": "secret123"})
    token = r.json()["token"]
    user_id = r.json()["user_id"]

    # 2. 带 token 开局
    headers = {"Authorization": f"Bearer {token}"}
    gid, nums = _start_game(client, token=token)

    # 3. 求解并提交
    expr = _solve(nums)
    r = client.post(
        "/check",
        json={"game_id": gid, "expression": expr},
        headers=headers,
    )
    assert r.json()["correct"] is True

    # 4. 最快榜上应该有 champ
    r = client.get("/leaderboard/fastest")
    data = r.json()
    assert any(e["user_id"] == user_id for e in data)
