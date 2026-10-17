/**
 * api.js —— 所有后端请求封装
 * 其他模块不直接调用 fetch，只用这里的函数。
 */

// 如果当前访问的是 localhost:5500 (本地开发)，走 8000 端口
// 如果访问的是 8080 (Docker Nginx)，走 /api 相对路径
const API_BASE = (window.location.port === '5500' || window.location.port === '')
    ? 'http://127.0.0.1:8000' 
    : (window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1'))
        ? '/api'
        : 'https://twenty-four-point-game.onrender.com';

/* ---------- 内部工具：给请求自动加 Authorization 头 ---------- */
function withAuth(headers = {}) {
    const token = localStorage.getItem('token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

async function handleResponse(res) {
    let data;
    try {
        data = await res.json();
    } catch {
        data = null;
    }
    return { status: res.status, data };
}

/* ---------- 健康检查 ---------- */
/* export_async_function_check_placeholder = null; */  // 占位，防混淆

async function ping() {
    try {
        const res = await fetch(`${API_BASE}/`);
        return res.ok;
    } catch {
        return false;
    }
}

/* ---------- 游戏 ---------- */
async function newGame() {
    const res = await fetch(`${API_BASE}/new-game`, {
        headers: withAuth(),
    });
    return handleResponse(res);
}

async function checkAnswer(gameId, expression) {
    const res = await fetch(`${API_BASE}/check`, {
        method: 'POST',
        headers: withAuth({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ game_id: gameId, expression }),
    });
    return handleResponse(res);
}

/* ---------- 认证 ---------- */
async function register(username, password) {
    const res = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });
    return handleResponse(res);
}

async function login(username, password) {
    const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });
    return handleResponse(res);
}

/* ---------- 统计 ---------- */
async function myStats() {
    const res = await fetch(`${API_BASE}/my-stats`, {
        headers: withAuth(),
    });
    return handleResponse(res);
}

/* ---------- 排行榜 ---------- */
async function leaderboardFastest() {
    const res = await fetch(`${API_BASE}/leaderboard/fastest`);
    return handleResponse(res);
}

async function leaderboardMostSolved() {
    const res = await fetch(`${API_BASE}/leaderboard/most-solved`);
    return handleResponse(res);
}

async function leaderboardAccuracy() {
    const res = await fetch(`${API_BASE}/leaderboard/accuracy`);
    return handleResponse(res);
}

/* ---------- 暴露到全局（不用模块系统，简单粗暴） ---------- */
window.API = {
    API_BASE,
    ping,
    newGame,
    checkAnswer,
    register,
    login,
    myStats,
    leaderboardFastest,        // ← 新增
    leaderboardMostSolved,     // ← 新增
    leaderboardAccuracy,       // ← 新增
};


