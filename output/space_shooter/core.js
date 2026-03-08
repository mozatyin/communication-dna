core.js
// EventBus
const EventBus = {
    _handlers: {},
    on(event, fn) {
        (this._handlers[event] = this._handlers[event] || []).push(fn);
    },
    emit(event, data) {
        (this._handlers[event] || []).forEach(fn => fn(data));
    }
};

// Global constants
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const PLAYER_SPEED = 5;
const BULLET_SPEED = 8;
const ENEMY_SPEED = 2;

// Shared state objects
const GameState = {
    gameStatus: 'menu',
    score: 0,
    lives: 3,
    level: 1,
    highScore: 0
};

const PlayerShip = {
    x: 540,
    y: 1700,
    health: 100,
    width: 60,
    height: 80
};

const PlayerBullets = {
    bullets: []
};

const Enemies = {
    enemies: []
};

const EnemyBullets = {
    bullets: []
};

// Module code
const GameStateModule = (function() {
    function init() {
        GameState.gameStatus = 'menu';
        GameState.score = 0;
        GameState.lives = 3;
        GameState.level = 1;
        GameState.highScore = parseInt(localStorage.getItem('spaceShooterHighScore')) || 0;
        
        // Set up event listeners
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('GAME_PAUSE', handleGamePause);
        EventBus.on('GAME_RESUME', handleGameResume);
        EventBus.on('PLAYER_DIED', handlePlayerDied);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('SHOW_LEADERBOARD', handleShowLeaderboard);
        EventBus.on('CLOSE_LEADERBOARD', handleCloseLeaderboard);
        EventBus.on('ENEMY_DESTROYED', handleEnemyDestroyed);
    }
    
    function startGame() {
        if (GameState.gameStatus === 'menu') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.lives = 3;
            GameState.level = 1;
        }
    }
    
    function pauseGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'paused';
        }
    }
    
    function resumeGame() {
        if (GameState.gameStatus === 'paused') {
            GameState.gameStatus = 'playing';
        }
    }
    
    function gameOver() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
                localStorage.setItem('spaceShooterHighScore', GameState.highScore.toString());
            }
        }
    }
    
    function returnToMenu() {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'menu';
        }
    }
    
    function showLeaderboard() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
        }
    }
    
    function addScore(points) {
        if (GameState.gameStatus === 'playing') {
            GameState.score += points;
        }
    }
    
    function update(dt) {
        if (GameState.gameStatus === 'playing') {
            const newLevel = Math.floor(GameState.score / 1000) + 1;
            if (newLevel > GameState.level) {
                GameState.level = newLevel;
            }
        }
    }
    
    // Event handlers
    function handleGameStart() {
        startGame();
    }
    
    function handleGamePause() {
        pauseGame();
    }
    
    function handleGameResume() {
        resumeGame();
    }
    
    function handlePlayerDied() {
        GameState.lives--;
        if (GameState.lives <= 0) {
            gameOver();
        }
    }
    
    function handleRetry() {
        startGame();
    }
    
    function handleReturnMenu() {
        returnToMenu();
    }
    
    function handleShowLeaderboard() {
        showLeaderboard();
    }
    
    function handleCloseLeaderboard() {
        returnToMenu();
    }
    
    function handleEnemyDestroyed(event) {
        addScore(event.points);
    }
    
    return {
        init,
        startGame,
        pauseGame,
        resumeGame,
        gameOver,
        returnToMenu,
        showLeaderboard,
        addScore,
        update
    };
})();

const PlayerShipModule = (function() {
    let lastShotTime = 0;
    const SHOT_COOLDOWN = 200;

    function init() {
        PlayerShip.x = 540;
        PlayerShip.y = 1700;
        PlayerShip.health = 100;
        PlayerShip.width = 60;
        PlayerShip.height = 80;
        
        PlayerBullets.bullets = [];
        
        EventBus.on('PLAYER_MOVE_LEFT', moveLeft);
        EventBus.on('PLAYER_MOVE_RIGHT', moveRight);
        EventBus.on('PLAYER_SHOOT', shoot);
    }

    function moveLeft() {
        if (GameState.gameStatus !== 'playing') return;
        
        PlayerShip.x -= PLAYER_SPEED;
        if (PlayerShip.x < 0) {
            PlayerShip.x = 0;
        }
    }

    function moveRight() {
        if (GameState.gameStatus !== 'playing') return;
        
        PlayerShip.x += PLAYER_SPEED;
        if (PlayerShip.x > CANVAS_WIDTH - PlayerShip.width) {
            PlayerShip.x = CANVAS_WIDTH - PlayerShip.width;
        }
    }

    function shoot() {
        if (GameState.gameStatus !== 'playing') return;
        
        const currentTime = Date.now();
        if (currentTime - lastShotTime < SHOT_COOLDOWN) return;
        
        const bullet = {
            id: 'bullet_' + currentTime + '_' + Math.random(),
            x: PlayerShip.x + PlayerShip.width / 2 - 2,
            y: PlayerShip.y,
            width: 4,
            height: 10,
            speed: BULLET_SPEED
        };
        
        PlayerBullets.bullets.push(bullet);
        lastShotTime = currentTime;
    }

    function takeDamage(damage) {
        if (GameState.gameStatus !== 'playing') return;
        
        PlayerShip.health -= damage;
        if (PlayerShip.health <= 0) {
            PlayerShip.health = 0;
            EventBus.emit('PLAYER_DIED', {});
        }
    }

    function checkBoundingBoxOverlap(rect1, rect2) {
        return rect1.x < rect2.x + rect2.width &&
               rect1.x + rect1.width > rect2.x &&
               rect1.y < rect2.y + rect2.height &&
               rect1.y + rect1.height > rect2.y;
    }

    function update(dt) {
        if (GameState.gameStatus !== 'playing') return;
        
        for (let i = PlayerBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = PlayerBullets.bullets[i];
            bullet.y -= bullet.speed;
            
            if (bullet.y + bullet.height < 0) {
                PlayerBullets.bullets.splice(i, 1);
                continue;
            }
            
            for (let j = Enemies.enemies.length - 1; j >= 0; j--) {
                const enemy = Enemies.enemies[j];
                if (checkBoundingBoxOverlap(bullet, enemy)) {
                    PlayerBullets.bullets.splice(i, 1);
                    
                    enemy.health -= 25;
                    if (enemy.health <= 0) {
                        EventBus.emit('ENEMY_DESTROYED', {
                            enemyId: enemy.id,
                            points: enemy.points || 100
                        });
                    }
                    break;
                }
            }
        }
        
        for (let i = EnemyBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = EnemyBullets.bullets[i];
            if (checkBoundingBoxOverlap(bullet, PlayerShip)) {
                EnemyBullets.bullets.splice(i, 1);
                takeDamage(10);
                break;
            }
        }
        
        for (let i = 0; i < Enemies.enemies.length; i++) {
            const enemy = Enemies.enemies[i];
            if (checkBoundingBoxOverlap(enemy, PlayerShip)) {
                takeDamage(20);
                break;
            }
        }
    }

    function render(ctx) {
        if (!ctx) return;
        
        ctx.fillStyle = '#00ff00';
        ctx.fillRect(PlayerShip.x, PlayerShip.y, PlayerShip.width, PlayerShip.height);
        
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(PlayerShip.x + 25, PlayerShip.y + 10, 10, 30);
        ctx.fillRect(PlayerShip.x + 10, PlayerShip.y + 50, 40, 20);
        
        ctx.fillStyle = '#ffff00';
        for (const bullet of PlayerBullets.bullets) {
            ctx.fillRect(bullet.x, bullet.y, bullet.width, bullet.height);
        }
    }

    return {
        init,
        moveLeft,
        moveRight,
        shoot,
        takeDamage,
        update,
        render
    };
})();

const EnemySystemModule = (function() {
    let spawnTimer = 0;
    let nextEnemyId = 1;
    
    function init() {
        Enemies.enemies = [];
        EnemyBullets.bullets = [];
        spawnTimer = 0;
        nextEnemyId = 1;
        
        EventBus.on('ENEMY_DESTROYED', function(event) {
            destroyEnemy(event.enemyId);
        });
    }
    
    function spawnEnemy(x, y, type) {
        if (GameState.gameStatus !== 'playing') return;
        
        const enemy = {
            id: 'enemy_' + nextEnemyId++,
            x: x,
            y: y,
            type: type,
            width: type === 'small' ? 40 : type === 'medium' ? 60 : 80,
            height: type === 'small' ? 40 : type === 'medium' ? 60 : 80,
            health: type === 'small' ? 1 : type === 'medium' ? 3 : 5,
            speed: type === 'small' ? ENEMY_SPEED * 1.5 : type === 'medium' ? ENEMY_SPEED : ENEMY_SPEED * 0.7,
            shootTimer: 0,
            shootInterval: type === 'small' ? 120 : type === 'medium' ? 90 : 60,
            points: type === 'small' ? 10 : type === 'medium' ? 25 : 50
        };
        
        Enemies.enemies.push(enemy);
    }
    
    function destroyEnemy(enemyId) {
        if (GameState.gameStatus !== 'playing') return;
        
        const index = Enemies.enemies.findIndex(enemy => enemy.id === enemyId);
        if (index !== -1) {
            Enemies.enemies.splice(index, 1);
        }
    }
    
    function update(dt) {
        if (GameState.gameStatus !== 'playing') return;
        
        spawnTimer++;
        const spawnRate = Math.max(60 - (GameState.level * 5), 20);
        if (spawnTimer >= spawnRate) {
            spawnTimer = 0;
            const x = Math.random() * (CANVAS_WIDTH - 80);
            const types = ['small', 'medium', 'large'];
            const weights = [0.6, 0.3, 0.1];
            let rand = Math.random();
            let type = 'small';
            if (rand > weights[0]) {
                type = rand > weights[0] + weights[1] ? 'large' : 'medium';
            }
            spawnEnemy(x, -80, type);
        }
        
        for (let i = Enemies.enemies.length - 1; i >= 0; i--) {
            const enemy = Enemies.enemies[i];
            
            enemy.y += enemy.speed;
            
            if (enemy.y > CANVAS_HEIGHT + 50) {
                Enemies.enemies.splice(i, 1);
                continue;
            }
            
            enemy.shootTimer++;
            if (enemy.shootTimer >= enemy.shootInterval) {
                enemy.shootTimer = 0;
                shootEnemyBullet(enemy.x + enemy.width / 2, enemy.y + enemy.height);
            }
        }
        
        for (let i = EnemyBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = EnemyBullets.bullets[i];
            bullet.y += BULLET_SPEED;
            
            if (bullet.y > CANVAS_HEIGHT + 10) {
                EnemyBullets.bullets.splice(i, 1);
            }
        }
        
        checkPlayerBulletCollisions();
    }
    
    function shootEnemyBullet(x, y) {
        EnemyBullets.bullets.push({
            x: x - 2,
            y: y,
            width: 4,
            height: 10
        });
    }
    
    function checkPlayerBulletCollisions() {
        for (let i = PlayerBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = PlayerBullets.bullets[i];
            
            for (let j = Enemies.enemies.length - 1; j >= 0; j--) {
                const enemy = Enemies.enemies[j];
                
                if (bullet.x < enemy.x + enemy.width &&
                    bullet.x + bullet.width > enemy.x &&
                    bullet.y < enemy.y + enemy.height &&
                    bullet.y + bullet.height > enemy.y) {
                    
                    PlayerBullets.bullets.splice(i, 1);
                    
                    enemy.health--;
                    
                    if (enemy.health <= 0) {
                        EventBus.emit('ENEMY_DESTROYED', {
                            enemyId: enemy.id,
                            points: enemy.points
                        });
                    }
                    
                    break;
                }
            }
        }
    }
    
    function render(ctx) {
        if (GameState.gameStatus !== 'playing') return;
        
        ctx.fillStyle = '#ff4444';
        for (const enemy of Enemies.enemies) {
            ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
            
            if (enemy.type === 'small') {
                ctx.fillStyle = '#ff6666';
            } else if (enemy.type === 'medium') {
                ctx.fillStyle = '#ff4444';
            } else {
                ctx.fillStyle = '#ff2222';
            }
            ctx.fillRect(enemy.x + 2, enemy.y + 2, enemy.width - 4, enemy.height - 4);
            ctx.fillStyle = '#ff4444';
        }
        
        ctx.fillStyle = '#ffaa00';
        for (const bullet of EnemyBullets.bullets) {
            ctx.fillRect(bullet.x, bullet.y, bullet.width, bullet.height);
        }
    }
    
    return {
        init,
        spawnEnemy,
        destroyEnemy,
        update,
        render
    };
})();

const UIManagerModule = (function() {
    let keysPressed = {};
    
    function init() {
        setupEventListeners();
    }
    
    function setupEventListeners() {
        document.addEventListener('keydown', (e) => {
            keysPressed[e.key] = true;
            handleKeyPress(e.key);
        });
        
        document.addEventListener('keyup', (e) => {
            keysPressed[e.key] = false;
        });
        
        document.addEventListener('click', (e) => {
            const rect = e.target.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            handleClick(x, y);
        });
        
        document.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const rect = e.target.getBoundingClientRect();
            const touch = e.touches[0];
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            handleClick(x, y);
        });
    }
    
    function handleClick(x, y) {
        if (GameState.gameStatus === 'playing') {
            EventBus.emit('PLAYER_SHOOT', {});
        }
    }
    
    function handleKeyPress(key) {
        if (GameState.gameStatus === 'playing') {
            switch(key) {
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    EventBus.emit('PLAYER_MOVE_LEFT', {});
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    EventBus.emit('PLAYER_MOVE_RIGHT', {});
                    break;
                case ' ':
                case 'Enter':
                    EventBus.emit('PLAYER_SHOOT', {});
                    break;
                case 'Escape':
                case 'p':
                case 'P':
                    EventBus.emit('GAME_PAUSE', {});
                    break;
            }
        } else if (GameState.gameStatus === 'paused') {
            if (key === 'Escape' || key === 'p' || key === 'P') {
                EventBus.emit('GAME_RESUME', {});
            }
        } else if (GameState.gameStatus === 'menu') {
            if (key === 'Enter' || key === ' ') {
                EventBus.emit('GAME_START', {});
            }
        }
    }
    
    function update(dt) {
        if (GameState.gameStatus === 'playing') {
            if (keysPressed['ArrowLeft'] || keysPressed['a'] || keysPressed['A']) {
                EventBus.emit('PLAYER_MOVE_LEFT', {});
            }
            if (keysPressed['ArrowRight'] || keysPressed['d'] || keysPressed['D']) {
                EventBus.emit('PLAYER_MOVE_RIGHT', {});
            }
        }
        
        // Update UI elements
        updateUIElements();
    }
    
    function updateUIElements() {
        const scoreDisplay = document.getElementById('score_display');
        if (scoreDisplay) {
            scoreDisplay.textContent = `得分: ${GameState.score}`;
        }
        
        const livesDisplay = document.getElementById('lives');
        if (livesDisplay) {
            livesDisplay.textContent = '❤'.repeat(Math.max(0, GameState.lives));
        }
        
        const finalScore = document.getElementById('final_score');
        if (finalScore) {
            finalScore.textContent = `最终得分: ${GameState.score}`;
        }
        
        const highScoreDisplay = document.getElementById('high_score_display');
        if (highScoreDisplay) {
            highScoreDisplay.textContent = `最高分: ${GameState.highScore}`;
        }
        
        const leaderboardHighScore = document.getElementById('leaderboard_high_score');
        if (leaderboardHighScore) {
            leaderboardHighScore.textContent = GameState.highScore;
        }
    }
    
    function render(ctx) {
        // UI rendering is handled by HTML/CSS
    }
    
    return {
        init,
        handleClick,
        handleKeyPress,
        update,
        render
    };
})();

// showScreen function
function showScreen(id) {
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.style.display = 'none';
    });
    
    const targetScreen = document.getElementById(id);
    if (targetScreen) {
        targetScreen.style.display = 'block';
    }
}

// Game loop
let lastTime = 0;
let canvas, ctx;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update modules in order
    UIManagerModule.update(dt);
    PlayerShipModule.update(dt);
    EnemySystemModule.update(dt);
    GameStateModule.update(dt);
    
    // Render only if playing
    if (GameState.gameStatus === 'playing' && ctx) {
        // Clear canvas
        ctx.fillStyle = 'linear-gradient(180deg, #000033 0%, #000066 100%)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Render modules in order
        EnemySystemModule.render(ctx);
        PlayerShipModule.render(ctx);
        UIManagerModule.render(ctx);
    }
    
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    }
}

// State transition functions
function startGameTransition() {
    GameStateModule.startGame();
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
    
    // Reset player and enemies
    PlayerShipModule.init();
    EnemySystemModule.init();
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

function gameOverTransition() {
    GameStateModule.gameOver();
    EventBus.emit('PLAYER_DIED', {});
    showScreen('game_over');
}

function retryTransition() {
    GameStateModule.startGame();
    EventBus.emit('RETRY', {});
    showScreen('gameplay');
    
    // Reset player and enemies
    PlayerShipModule.init();
    EnemySystemModule.init();
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

function returnToMenuTransition() {
    GameStateModule.returnToMenu();
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

function showLeaderboardTransition() {
    GameStateModule.showLeaderboard();
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
}

function closeLeaderboardTransition() {
    GameStateModule.returnToMenu();
    EventBus.emit('CLOSE_LEADERBOARD', {});
    showScreen('main_menu');
}

// Initialize game
window.addEventListener('DOMContentLoaded', function() {
    // Get canvas and context
    canvas = document.getElementById('gameCanvas');
    if (canvas) {
        ctx = canvas.getContext('2d');
    }
    
    // Initialize modules in order
    GameStateModule.init();
    PlayerShipModule.init();
    EnemySystemModule.init();
    UIManagerModule.init();
    
    // Set up button event listeners
    const btnPlay = document.getElementById('btn_play');
    if (btnPlay) {
        btnPlay.addEventListener('click', startGameTransition);
    }
    
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    if (btnLeaderboard) {
        btnLeaderboard.addEventListener('click', showLeaderboardTransition);
    }
    
    const btnRetry = document.getElementById('btn_retry');
    if (btnRetry) {
        btnRetry.addEventListener('click', retryTransition);
    }
    
    const btnLeaderboardGo = document.getElementById('btn_leaderboard_go');
    if (btnLeaderboardGo) {
        btnLeaderboardGo.addEventListener('click', showLeaderboardTransition);
    }
    
    const btnMenu = document.getElementById('btn_menu');
    if (btnMenu) {
        btnMenu.addEventListener('click', returnToMenuTransition);
    }
    
    const btnBack = document.getElementById('btn_back');
    if (btnBack) {
        btnBack.addEventListener('click', closeLeaderboardTransition);
    }
    
    const tapArea = document.getElementById('tap_area');
    if (tapArea) {
        tapArea.addEventListener('click', function() {
            if (GameState.gameStatus === 'playing') {
                EventBus.emit('PLAYER_SHOOT', {});
            }
        });
    }
    
    // Listen for game over condition
    EventBus.on('PLAYER_DIED', function() {
        if (GameState.lives <= 0) {
            setTimeout(gameOverTransition, 1000);
        }
    });
    
    // Show initial screen
    showScreen('main_menu');
});