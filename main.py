import os

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sqlmodel import SQLModel, Field, Session, create_engine, select
from sqlalchemy import func, case

from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import random
import ast
import operator
import re
import time
import uuid
import jwt

from pathlib import Path
VERSION = Path(__file__).parent.joinpath("VERSION").read_text().strip()

app = FastAPI(title="24点游戏后端", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 数据库
# ============================================================
DB_FILE = os.environ.get("DB_FILE", "game.db")
engine = create_engine(
    f"sqlite:///{DB_FILE}",
    echo=False,
    connect_args={"check_same_thread": False},
)

class Game(SQLModel, table=True):
    __tablename__ = "games"

    game_id: str = Field(primary_key=True)
    numbers: str
    created_at: float
    expires_at: float
    status: str = "playing"
    result: float | None = None
    elapsed: float | None = None
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)

class Submission(SQLModel, table=True):
    __tablename__ = "submissions"

    id: int | None = Field(default=None, primary_key=True)
    game_id: str = Field(index=True)
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    expression: str
    is_correct: bool
    result: float | None = None
    error: str | None = None
    created_at: float
    elapsed: float | None = None

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=32)
    hashed_password: str
    created_at: float

def get_session():
    with Session(engine) as session:
        yield session

# ============================================================
# 密码哈希 & JWT
# ============================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = "dev-secret-change-me-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# ============================================================
# 依赖：可选登录
# ============================================================

def get_current_user_optional(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    """
    从 Authorization: Bearer <token> 解析当前用户。
    没带 / 格式错 / token 无效或过期 → 都返回 None（不报错）。
    """
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    payload = decode_token(parts[1])
    if payload is None:
        return None
    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return None
    return session.get(User, user_id)

# ============================================================
# 表达式预处理
# ============================================================
_FULLWIDTH_MAP = str.maketrans({
    "−": "-", "–": "-", "—": "-",
    "×": "*", "÷": "/",
    "（": "(", "）": ")",
    "＋": "+", "－": "-", "＊": "*", "／": "/",
    "１": "1", "２": "2", "３": "3", "４": "4", "５": "5",
    "６": "6", "７": "7", "８": "8", "９": "9", "０": "0",
})

def normalize_expression(expr: str) -> str:
    return expr.translate(_FULLWIDTH_MAP)

# ============================================================
# 游戏逻辑
# ============================================================
def is_solvable(nums):
    EPS = 1e-6
    def dfs(arr):
        if len(arr) == 1:
            return abs(arr[0] - 24) < EPS
        for i in range(len(arr)):
            for j in range(len(arr)):
                if i == j:
                    continue
                rest = [arr[k] for k in range(len(arr)) if k != i and k != j]
                a, b = arr[i], arr[j]
                candidates = [a + b, a - b, b - a, a * b]
                if abs(b) > EPS:
                    candidates.append(a / b)
                if abs(a) > EPS:
                    candidates.append(b / a)
                for val in candidates:
                    if dfs(rest + [val]):
                        return True
        return False
    return dfs(nums)

def generate_solvable_numbers():
    while True:
        nums = [random.randint(1, 13) for _ in range(4)]
        if is_solvable(nums):
            return nums

# ============================================================
# 安全表达式求值
# ============================================================
_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_ALLOWED_UNARYOPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
MAX_ABS_VALUE = 10 ** 12

def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise ValueError("不允许布尔值")
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"不支持的常量类型: {type(node.value).__name__}")
        return float(node.value)

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ValueError(f"不支持的运算符: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if op_type is ast.Div and abs(right) < 1e-12:
            raise ZeroDivisionError("除以0")
        result = _ALLOWED_BINOPS[op_type](left, right)
        if abs(result) > MAX_ABS_VALUE:
            raise ValueError("结果数值过大")
        return result

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise ValueError(f"不支持的一元运算符: {op_type.__name__}")
        return _ALLOWED_UNARYOPS[op_type](_eval_node(node.operand))

    raise ValueError(f"不允许的语法结构: {type(node).__name__}")

def safe_eval(expr: str) -> float:
    if len(expr) > 200:
        raise ValueError("表达式过长")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"语法错误: {e.msg}")
    return _eval_node(tree.body)

# ============================================================
# 数字提取与对比
# ============================================================
def extract_numbers(expr: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", expr)]

def numbers_match(used: list[int], required: list[int]) -> tuple[bool, str | None]:
    if sorted(used) == sorted(required):
        return True, None

    from collections import Counter
    used_c = Counter(used)
    req_c = Counter(required)

    missing, extra = [], []
    for n in sorted(set(used_c) | set(req_c)):
        u, r = used_c.get(n, 0), req_c.get(n, 0)
        if u < r:
            missing.append(f"{n}×{r - u}")
        elif u > r:
            extra.append(f"{n}×{u - r}")

    parts = [f"题目数字: {required}", f"你用了: {used}"]
    if missing:
        parts.append(f"少用: {', '.join(missing)}")
    if extra:
        parts.append(f"多用: {', '.join(extra)}")
    return False, "；".join(parts)

# ============================================================
# 会话操作
# ============================================================
GAME_TTL_SECONDS = 300

def _cleanup_games(session: Session):
    now = time.time()
    stmt = select(Game).where(Game.expires_at < now)
    expired = session.exec(stmt).all()
    for g in expired:
        session.delete(g)
    if expired:
        session.commit()

def create_game(session: Session, user_id: int | None = None) -> Game:
    _cleanup_games(session)
    now = time.time()
    nums = generate_solvable_numbers()
    game = Game(
        game_id=uuid.uuid4().hex,
        numbers=str(nums),
        created_at=now,
        expires_at=now + GAME_TTL_SECONDS,
        status="playing",
        user_id=user_id,
    )
    session.add(game)
    session.commit()
    session.refresh(game)
    return game

def get_game(session: Session, game_id: str) -> Game | None:
    return session.get(Game, game_id)

def record_submission(
    session: Session,
    game: Game,
    expression: str,
    is_correct: bool,
    result: float | None = None,
    error: str | None = None,
) -> Submission:
    sub = Submission(
        game_id=game.game_id,
        user_id=game.user_id,
        expression=expression,
        is_correct=is_correct,
        result=result,
        error=error,
        created_at=time.time(),
        elapsed=round(time.time() - game.created_at, 2),
    )
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub

# ============================================================
# 请求/响应模型
# ============================================================
class AnswerRequest(BaseModel):
    game_id: str
    expression: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    user_id: int
    username: str
    token: str
    message: str

# ============================================================
# 启动事件
# ============================================================
@app.on_event("startup")
def on_startup():
    # ★ 不再调用 init_db()，数据库结构由 Alembic 管理
    print(f"✅ 数据库已就绪: {DB_FILE}（由 Alembic 管理）")

# ============================================================
# 接口：基础 & 游戏
# ============================================================
@app.api_route("/", methods=["GET", "HEAD"])
def root(session: Session = Depends(get_session)):
    game_count = len(session.exec(select(Game)).all())
    sub_count = len(session.exec(select(Submission)).all())
    user_count = len(session.exec(select(User)).all())
    return {
        "message": "24点游戏后端已启动 🎮 (v5.2: 会话绑定用户)",
        "active_games": game_count,
        "total_submissions": sub_count,
        "total_users": user_count,
    }

@app.get("/new-game")
def new_game(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    user_id = current_user.id if current_user else None
    game = create_game(session, user_id=user_id)
    nums = ast.literal_eval(game.numbers)
    return {
        "game_id": game.game_id,
        "numbers": nums,
        "expires_in": GAME_TTL_SECONDS,
        "user_id": game.user_id,           # ★ 方便前端确认当前局绑定了谁
        "is_anonymous": game.user_id is None,
        "message": "用这四个数字和 + - * / ( ) 算出24",
    }

@app.post("/check")
def check_answer(
    req: AnswerRequest,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    expr = normalize_expression(req.expression.strip())

    game = get_game(session, req.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="会话不存在，请重新开始")

    if game.expires_at < time.time():
        game.status = "expired"
        session.add(game)
        session.commit()
        raise HTTPException(status_code=410, detail="本局已过期，请重新开始")

    if game.status == "solved":
        return {
            "correct": True,
            "already_solved": True,
            "result": game.result,
            "elapsed": game.elapsed,
            "message": "这一局你已经答对了 ✅",
        }

    if not expr:
        raise HTTPException(status_code=400, detail="表达式不能为空")

    nums = ast.literal_eval(game.numbers)
    used = extract_numbers(expr)
    ok, err = numbers_match(used, nums)
    if not ok:
        record_submission(session, game, expr, is_correct=False, error=err)
        return {"correct": False, "reason": err}

    try:
        result = safe_eval(expr)
    except ZeroDivisionError:
        err = "不能除以0"
        record_submission(session, game, expr, is_correct=False, error=err)
        return {"correct": False, "reason": err}
    except ValueError as e:
        err = f"表达式无效: {e}"
        record_submission(session, game, expr, is_correct=False, error=err)
        return {"correct": False, "reason": err}

    elapsed = round(time.time() - game.created_at, 2)
    if abs(result - 24) < 1e-8:
        game.status = "solved"
        game.result = 24.0
        game.elapsed = elapsed
        session.add(game)
        session.commit()
        record_submission(session, game, expr, is_correct=True, result=24.0)
        return {
            "correct": True,
            "result": 24.0,
            "elapsed": elapsed,
            "message": "🎉 恭喜答对！",
        }
    else:
        err = f"结果是 {result}，不是24"
        record_submission(session, game, expr, is_correct=False, result=result, error=err)
        return {
            "correct": False,
            "result": result,
            "reason": err,
        }

# ============================================================
# 接口：用户
# ============================================================
@app.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, session: Session = Depends(get_session)):
    username = req.username.strip()
    password = req.password

    if not username or not (2 <= len(username) <= 32):
        raise HTTPException(status_code=400, detail="用户名长度必须为 2~32 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if not username.isalnum():
        raise HTTPException(status_code=400, detail="用户名只能包含字母和数字")

    existing = session.exec(select(User).where(User.username == username)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="用户名已被占用")

    user = User(
        username=username,
        hashed_password=hash_password(password),
        created_at=time.time(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_token(user.id, user.username)
    return AuthResponse(
        user_id=user.id,
        username=user.username,
        token=token,
        message="🎉 注册成功",
    )

@app.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, session: Session = Depends(get_session)):
    username = req.username.strip()
    password = req.password

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(user.id, user.username)
    return AuthResponse(
        user_id=user.id,
        username=user.username,
        token=token,
        message="🎉 登录成功",
    )

# ============================================================
# 接口：排行榜 & 个人统计
# ============================================================
class FastestEntry(BaseModel):
    user_id: int
    username: str
    best_elapsed: float

class MostSolvedEntry(BaseModel):
    user_id: int
    username: str
    solved_count: int

class AccuracyEntry(BaseModel):
    user_id: int
    username: str
    total_submissions: int
    correct_submissions: int
    accuracy: float

class MyStats(BaseModel):
    user_id: int
    username: str
    total_games: int
    solved_games: int
    total_submissions: int
    correct_submissions: int
    accuracy: float
    fastest_seconds: float | None
    average_seconds: float | None

@app.get("/leaderboard/fastest", response_model=list[FastestEntry])
def leaderboard_fastest(session: Session = Depends(get_session)):
    """最快解题 Top 10（只统计登录用户）"""
    stmt = (
        select(
            User.id.label("user_id"),
            User.username,
            func.min(Game.elapsed).label("best_elapsed"),
        )
        .join(Game, Game.user_id == User.id)
        .where(Game.status == "solved")
        .group_by(User.id)
        .order_by(func.min(Game.elapsed).asc())
        .limit(10)
    )
    rows = session.exec(stmt).all()
    return [
        FastestEntry(
            user_id=r.user_id,
            username=r.username,
            best_elapsed=round(r.best_elapsed, 2),
        )
        for r in rows
    ]

@app.get("/leaderboard/most-solved", response_model=list[MostSolvedEntry])
def leaderboard_most_solved(session: Session = Depends(get_session)):
    """解题数 Top 10"""
    stmt = (
        select(
            User.id.label("user_id"),
            User.username,
            func.count(Game.game_id).label("solved_count"),
        )
        .join(Game, Game.user_id == User.id)
        .where(Game.status == "solved")
        .group_by(User.id)
        .order_by(func.count(Game.game_id).desc(), User.id.asc())
        .limit(10)
    )
    rows = session.exec(stmt).all()
    return [
        MostSolvedEntry(
            user_id=r.user_id,
            username=r.username,
            solved_count=r.solved_count,
        )
        for r in rows
    ]

@app.get("/leaderboard/accuracy", response_model=list[AccuracyEntry])
def leaderboard_accuracy(session: Session = Depends(get_session)):
    """正确率 Top 10（至少提交 5 次）"""
    correct_case = func.sum(case((Submission.is_correct == True, 1), else_=0))
    total_count = func.count(Submission.id)

    stmt = (
        select(
            User.id.label("user_id"),
            User.username,
            total_count.label("total_submissions"),
            correct_case.label("correct_submissions"),
        )
        .join(Submission, Submission.user_id == User.id)
        .group_by(User.id)
        .having(total_count >= 5)
        .order_by((correct_case * 1.0 / total_count).desc(), total_count.desc())
        .limit(10)
    )
    rows = session.exec(stmt).all()
    return [
        AccuracyEntry(
            user_id=r.user_id,
            username=r.username,
            total_submissions=r.total_submissions,
            correct_submissions=r.correct_submissions,
            accuracy=round(r.correct_submissions / r.total_submissions, 4),
        )
        for r in rows
    ]

@app.get("/my-stats", response_model=MyStats)
def my_stats(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    """当前登录用户的个人统计（需登录）"""
    if current_user is None:
        raise HTTPException(status_code=401, detail="请先登录")

    # 1. 我的 games
    games = session.exec(
        select(Game).where(Game.user_id == current_user.id)
    ).all()
    total_games = len(games)
    solved_games = [g for g in games if g.status == "solved"]
    elapsed_list = [g.elapsed for g in solved_games if g.elapsed is not None]

    # 2. 我的 submissions
    subs = session.exec(
        select(Submission).where(Submission.user_id == current_user.id)
    ).all()
    total_submissions = len(subs)
    correct_submissions = sum(1 for s in subs if s.is_correct)

    return MyStats(
        user_id=current_user.id,
        username=current_user.username,
        total_games=total_games,
        solved_games=len(solved_games),
        total_submissions=total_submissions,
        correct_submissions=correct_submissions,
        accuracy=round(correct_submissions / total_submissions, 4) if total_submissions else 0,
        fastest_seconds=round(min(elapsed_list), 2) if elapsed_list else None,
        average_seconds=round(sum(elapsed_list) / len(elapsed_list), 2) if elapsed_list else None,
    )

from pydantic import BaseModel
from fastapi import Header

class AdminResetRequest(BaseModel):
    password: str

@app.post("/admin/reset-db")
def admin_reset_db(req: AdminResetRequest, session: Session = Depends(get_session)):
    """危险操作：清空数据库所有数据（用于测试环境重置）"""
    # 设置一个只有你知道的清理密码
    ADMIN_PASSWORD = "reset-me-please" 
    
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="密码错误，无权操作")
    
    # 清空所有表的数据（保留表结构）
    from sqlmodel import delete
    session.exec(delete(Submission))
    session.exec(delete(Game))
    session.exec(delete(User))
    session.commit()
    
    return {"message": "🎉 数据库已清空，所有测试数据已删除！"}

@app.get("/my-games")
def my_games(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    
    # 查出所有属于该用户的局，按时间倒序排列
    games = session.exec(
        select(Game).where(Game.user_id == current_user.id).order_by(Game.created_at.desc())
    ).all()
    
    return [
        {
            "game_id": g.game_id,
            "numbers": g.numbers,
            "status": g.status,
            "created_at": g.created_at,
            "elapsed": g.elapsed,
        }
        for g in games
    ]

# 启动方式：uvicorn main:app --reload

