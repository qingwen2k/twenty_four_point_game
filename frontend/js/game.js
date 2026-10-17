/**
 * game.js —— 二十四点游戏视图
 */

let currentGameId = null;
let currentNumbers = [];
let solved = false;
let timerInterval = null;
let secondsElapsed = 0;
let gameActive = false;

/* ---------- DOM ---------- */
let cardEls, expressionInput, messageEl, submitBtn, newGameBtn, clearBtn;
let timerDisplay, statusDot, statusText;

/* ---------- UI 工具 ---------- */
function updateCardsDisplay() {
    for (let i = 0; i < 4; i++) {
        const val = currentNumbers[i];
        cardEls[i].textContent = val !== undefined ? val : '?';
        cardEls[i].classList.remove('small-value', 'ten');
        if (val >= 10) cardEls[i].classList.add('ten');
        else if (val >= 7) cardEls[i].classList.add('small-value');
        cardEls[i].classList.toggle('solved', solved);
    }
}

function resetTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;
    secondsElapsed = 0;
    timerDisplay.textContent = `⏱ 0 s`;
}

function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    secondsElapsed = 0;
    timerDisplay.textContent = `⏱ 0 s`;
    timerInterval = setInterval(() => {
        secondsElapsed++;
        timerDisplay.textContent = `⏱ ${secondsElapsed} s`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;
}

function setMessage(text, type = 'info') {
    messageEl.textContent = text;
    messageEl.classList.remove('success', 'error');
    if (type === 'success') messageEl.classList.add('success');
    if (type === 'error') messageEl.classList.add('error');
}

function clearInput() {
    expressionInput.value = '';
    expressionInput.focus();
}

function setBackendStatus(online) {
    statusDot.classList.toggle('online', online);
    statusDot.classList.toggle('offline', !online);
    statusText.textContent = online ? '后端已连接' : '后端未连接';
}

/* ---------- 游戏逻辑 ---------- */
async function newGame() {
    newGameBtn.disabled = true;
    setMessage('正在请求新题目...', 'info');
    try {
        const { status, data } = await API.newGame();
        if (status !== 200) throw new Error(data?.detail || `HTTP ${status}`);

        currentGameId = data.game_id;
        currentNumbers = data.numbers;
        solved = false;
        gameActive = true;
        resetTimer();
        updateCardsDisplay();
        clearInput();
        startTimer();

        const roleHint = data.is_anonymous ? '' : `（已登录：${Auth.getUsername()}）`;
        setMessage(`用这四个数算出 24 吧！${roleHint}`, 'info');
        setBackendStatus(true);
        expressionInput.disabled = false;
        submitBtn.disabled = false;
    } catch (err) {
        console.error(err);
        setBackendStatus(false);
        gameActive = false;
        currentGameId = null;
        setMessage('❌ 无法连接后端，请确认 uvicorn 已启动', 'error');
        currentNumbers = ['?', '?', '?', '?'];
        updateCardsDisplay();
    } finally {
        newGameBtn.disabled = false;
    }
}

async function validateExpression() {
    if (!gameActive) {
        setMessage('请先点击「新一局」开始游戏', 'error');
        return;
    }
    if (solved) {
        setMessage('🎉 你已经解出来了！点「新一局」继续挑战吧', 'success');
        return;
    }
    if (!currentGameId) {
        setMessage('会话丢失，请点「新一局」重新开始', 'error');
        return;
    }

    const expr = expressionInput.value.trim();
    if (expr === '') {
        setMessage('请输入一个表达式', 'error');
        return;
    }

    submitBtn.disabled = true;
    setMessage('正在验证...', 'info');

    try {
        const { status, data } = await API.checkAnswer(currentGameId, expr);

        if (status !== 200) {
            setMessage(`❌ ${data?.detail || '请求无效'}`, 'error');
            if (status === 404 || status === 410) {
                gameActive = false;
                stopTimer();
                submitBtn.disabled = true;
            }
            return;
        }

        if (data.correct) {
            solved = true;
            gameActive = false;
            stopTimer();
            updateCardsDisplay();
            const timeText = data.elapsed !== undefined ? ` 用时 ${data.elapsed}s` : '';
            const prefix = data.already_solved ? '✅ 这一局你已经答对了' : '🎉 正确！';
            setMessage(`${prefix}${timeText}`, 'success');
            submitBtn.disabled = true;
        } else {
            setMessage(`❌ ${data.reason || `结果是 ${data.result}，不是 24`}`, 'error');
        }
        setBackendStatus(true);
    } catch (err) {
        console.error(err);
        setBackendStatus(false);
        setMessage('❌ 网络错误，无法连接后端', 'error');
    } finally {
        if (!solved) submitBtn.disabled = false;
    }
}

/* ---------- 初始化 ---------- */
function initGame() {
    cardEls = [0, 1, 2, 3].map(i => document.getElementById('card' + i));
    expressionInput = document.getElementById('expression');
    messageEl = document.getElementById('message');
    submitBtn = document.getElementById('submitBtn');
    newGameBtn = document.getElementById('newGameBtn');
    clearBtn = document.getElementById('clearBtn');
    timerDisplay = document.getElementById('timerDisplay');
    statusDot = document.getElementById('statusDot');
    statusText = document.getElementById('statusText');

    currentNumbers = [0, 0, 0, 0];
    for (const el of cardEls) el.textContent = '?';
    setMessage('点击「新一局」开始挑战', 'info');
    resetTimer();

    newGameBtn.addEventListener('click', newGame);
    submitBtn.addEventListener('click', validateExpression);
    clearBtn.addEventListener('click', () => {
        expressionInput.value = '';
        expressionInput.focus();
    });
    expressionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            validateExpression();
        }
    });

    API.ping().then(setBackendStatus);
}

window.Game = { initGame };
