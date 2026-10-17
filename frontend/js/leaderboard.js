/**
 * leaderboard.js —— 排行榜页面
 */

let lbCurrentBoard = 'fastest';   // fastest | most-solved | accuracy

/* ---------- 每个榜的配置：怎么取数、怎么显示值、怎么排序 ---------- */
const BOARDS = {
    'fastest': {
        title: '⚡ 最快解题',
        fetcher: () => API.leaderboardFastest(),
        valueKey: 'best_elapsed',
        formatValue: (v) => `${v.toFixed(2)}s`,
        // 给"我的排名"用的：按值升序
        betterIsSmaller: true,
    },
    'most-solved': {
        title: '🎯 解题数',
        fetcher: () => API.leaderboardMostSolved(),
        valueKey: 'solved_count',
        formatValue: (v) => `${v} 局`,
        betterIsSmaller: false,
    },
    'accuracy': {
        title: '📊 正确率',
        fetcher: () => API.leaderboardAccuracy(),
        valueKey: 'accuracy',
        formatValue: (v) => `${(v * 100).toFixed(1)}%`,
        betterIsSmaller: false,
    },
};

/* ---------- 渲染榜单 ---------- */
function renderBoard(entries) {
    const el = document.getElementById('lbContent');
    const conf = BOARDS[lbCurrentBoard];

    if (!entries || entries.length === 0) {
        el.innerHTML = `
            <div class="lb-empty">
                <span class="lb-empty-icon">🏆</span>
                暂无数据，快来成为第一个吧！
            </div>
        `;
        return;
    }

    const rows = entries.map((entry, idx) => {
        const rank = idx + 1;
        const rankClass = rank === 1 ? 'top1' : rank === 2 ? 'top2' : rank === 3 ? 'top3' : '';
        const rankIcon = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : rank;
        const meClass = (Auth.isLoggedIn() && entry.user_id === Auth.getUserId()) ? 'me' : '';
        const value = entry[conf.valueKey];

        return `
            <div class="lb-row ${rankClass} ${meClass}">
                <div class="lb-rank">${rankIcon}</div>
                <div class="lb-name">${escapeHtml(entry.username)}</div>
                <div class="lb-value">${conf.formatValue(value)}</div>
            </div>
        `;
    }).join('');

    el.innerHTML = `<div class="lb-list">${rows}</div>`;
}

/* ---------- 渲染"我的排名"卡片 ---------- */
async function renderMyRank(entries) {
    const el = document.getElementById('myRank');
    const conf = BOARDS[lbCurrentBoard];

    if (!Auth.isLoggedIn()) {
        el.style.display = 'none';
        return;
    }

    // 找自己在榜上的位置
    const myId = Auth.getUserId();
    const myIdx = entries.findIndex(e => e.user_id === myId);

    if (myIdx === -1) {
        // 没上榜（可能没数据，或次数不够）
        el.style.display = 'flex';
        el.innerHTML = `
            <span class="my-rank-label">我的排名</span>
            <span class="my-rank-empty">未上榜，继续加油 💪</span>
        `;
        return;
    }

    const rank = myIdx + 1;
    const entry = entries[myIdx];
    const value = entry[conf.valueKey];

    el.style.display = 'flex';
    el.innerHTML = `
        <span class="my-rank-label">我的排名</span>
        <span class="my-rank-content">
            <span class="my-rank-pos">#${rank}</span>
            <span class="my-rank-value">${conf.formatValue(value)}</span>
        </span>
    `;
}

/* ---------- 加载并渲染 ---------- */
async function loadBoard() {
    const el = document.getElementById('lbContent');
    el.innerHTML = '<div class="lb-loading">加载中...</div>';

    // 同时清掉"我的排名"（等数据回来再渲染）
    const myRankEl = document.getElementById('myRank');
    myRankEl.style.display = 'none';

    try {
        const { status, data } = await BOARDS[lbCurrentBoard].fetcher();
        if (status !== 200) {
            el.innerHTML = `<div class="lb-empty">加载失败：${data?.detail || `HTTP ${status}`}</div>`;
            return;
        }

        renderBoard(data);
        await renderMyRank(data);
    } catch (err) {
        console.error(err);
        el.innerHTML = `<div class="lb-empty">网络错误，请稍后再试</div>`;
    }
}

/* ---------- 简单的 HTML 转义（防 XSS） ---------- */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/* ---------- 初始化 ---------- */
function initLeaderboard() {
    // 绑定子 tab
    document.querySelectorAll('.lb-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.lb-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            lbCurrentBoard = tab.dataset.board;
            loadBoard();
        });
    });

    // 首次加载
    loadBoard();
}

/* ---------- 暴露 ---------- */
window.Leaderboard = {
    init: initLeaderboard,
    reload: loadBoard,
};
