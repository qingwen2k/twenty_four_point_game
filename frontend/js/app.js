/**
 * app.js —— 入口，串联各个模块
 */

(function () {
    function bindTabs() {
        const tabs = document.querySelectorAll('.tab');
        const views = {
            game: document.getElementById('view-game'),
            leaderboard: document.getElementById('view-leaderboard'),
        };

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.view;
                tabs.forEach(t => t.classList.toggle('active', t === tab));
                Object.entries(views).forEach(([name, el]) => {
                    el.classList.toggle('active', name === target);
                });
        
                // 如果切到排行榜，刷新数据（保证数据最新）
                if (target === 'leaderboard') {
                    Leaderboard.reload();
                }
            });
        });
    }

    function handleAuthChange() {
        Auth.renderUserArea();
        Leaderboard.reload();     // ← 新增
    }

    function boot() {
        Auth.bindAuthUI();
        Auth.onChange(handleAuthChange);
        Auth.renderUserArea();
    
        Game.initGame();
        Leaderboard.init();      // ← 新增
        bindTabs();
    }

    document.addEventListener('DOMContentLoaded', boot);
})();

