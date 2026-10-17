/**
 * auth.js —— token 存取 + 登录/注册弹窗
 */

/* ---------- token 管理 ---------- */
function getToken() {
    return localStorage.getItem('token');
}

function getUsername() {
    return localStorage.getItem('username');
}

function getUserId() {
    const id = localStorage.getItem('user_id');
    return id ? parseInt(id, 10) : null;
}

function saveAuth({ user_id, username, token }) {
    localStorage.setItem('user_id', String(user_id));
    localStorage.setItem('username', username);
    localStorage.setItem('token', token);
}

function clearAuth() {
    localStorage.removeItem('user_id');
    localStorage.removeItem('username');
    localStorage.removeItem('token');
}

function isLoggedIn() {
    return !!getToken();
}

/* ---------- DOM 引用 ---------- */
let authModal, authUsername, authPassword, authError, authSubmit, authClose;
let modalMode = 'login';  // 'login' | 'register'
let onAuthChangeCallback = null;

/* ---------- 事件绑定 ---------- */
function bindAuthUI() {
    authModal = document.getElementById('authModal');
    authUsername = document.getElementById('authUsername');
    authPassword = document.getElementById('authPassword');
    authError = document.getElementById('authError');
    authSubmit = document.getElementById('authSubmit');
    authClose = document.getElementById('authClose');

    // modal tab 切换
    document.querySelectorAll('.modal-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            modalMode = tab.dataset.mode;
            authSubmit.textContent = modalMode === 'login' ? '登录' : '注册';
            authError.textContent = '';
        });
    });

    authSubmit.addEventListener('click', submitAuth);
    authClose.addEventListener('click', closeAuthModal);
    authModal.addEventListener('click', (e) => {
        if (e.target === authModal) closeAuthModal();
    });

    // 回车提交
    [authUsername, authPassword].forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitAuth();
            }
        });
    });
}

function openAuthModal(mode = 'login') {
    modalMode = mode;
    document.querySelectorAll('.modal-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.mode === mode);
    });
    authSubmit.textContent = mode === 'login' ? '登录' : '注册';
    authError.textContent = '';
    authUsername.value = '';
    authPassword.value = '';
    authModal.classList.add('show');
    setTimeout(() => authUsername.focus(), 50);
}

function closeAuthModal() {
    authModal.classList.remove('show');
}

async function submitAuth() {
    const username = authUsername.value.trim();
    const password = authPassword.value;

    if (!username || !password) {
        authError.textContent = '请填写用户名和密码';
        return;
    }

    authSubmit.disabled = true;
    authError.textContent = '';

    try {
        const { status, data } = modalMode === 'login'
            ? await API.login(username, password)
            : await API.register(username, password);

        if (status === 200) {
            saveAuth(data);
            closeAuthModal();
            if (onAuthChangeCallback) onAuthChangeCallback();
        } else {
            authError.textContent = data?.detail || '操作失败';
        }
    } catch (e) {
        authError.textContent = '网络错误，请稍后再试';
    } finally {
        authSubmit.disabled = false;
    }
}

function logout() {
    clearAuth();
    if (onAuthChangeCallback) onAuthChangeCallback();
}

/* ---------- 渲染顶部用户区 ---------- */
function renderUserArea() {
    const userArea = document.getElementById('userArea');
    if (isLoggedIn()) {
        userArea.innerHTML = `
            <span class="user-name">👤 ${getUsername()}</span>
            <button class="link-btn" id="logoutBtn">退出</button>
        `;
        document.getElementById('logoutBtn').addEventListener('click', logout);
    } else {
        userArea.innerHTML = `
            <button class="link-btn" id="loginBtn">登录 / 注册</button>
        `;
        document.getElementById('loginBtn').addEventListener('click', () => openAuthModal('login'));
    }
}

/* ---------- 暴露 ---------- */
window.Auth = {
    bindAuthUI,
    openAuthModal,
    renderUserArea,
    isLoggedIn,
    getUsername,
    getUserId,
    logout,
    onChange(cb) { onAuthChangeCallback = cb; },
};
