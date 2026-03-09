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

// Global Constants
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const PLAYER_SPEED = 5;
const BULLET_SPEED = 8;
const ENEMY_SPEED = 2;

// Shared State Objects
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

// Module Code
const GameStateModule = (function() {
    let leaderboard = [];
    
    function init() {
        GameState.gameStatus = 'menu';
        GameState.score = 0;
        GameState.lives = 3;
        GameState.level = 1;
        GameState.highScore = loadHighScore();
        
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
            updateHighScore();
            saveScore();
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
            
            // Check for level progression every 1000 points
            const newLevel = Math.floor(GameState.score / 1000) + 1;
            if (newLevel > GameState.level) {
                GameState.level = newLevel;
            }
        }
    }
    
    function update(dt) {
        // Game state module doesn't need frame-based updates
        // All state changes are event-driven
    }
    
    // Event handlers
    function handleGameStart(event) {
        startGame();
    }
    
    function handleGamePause(event) {
        pauseGame();
    }
    
    function handleGameResume(event) {
        resumeGame();
    }
    
    function handlePlayerDied(event) {
        if (GameState.gameStatus === 'playing') {
            GameState.lives--;
            if (GameState.lives <= 0) {
                gameOver();
            }
        }
    }
    
    function handleRetry(event) {
        if (GameState.gameStatus === 'game_over') {
            startGame();
        }
    }
    
    function handleReturnMenu(event) {
        returnToMenu();
    }
    
    function handleShowLeaderboard(event) {
        showLeaderboard();
    }
    
    function handleCloseLeaderboard(event) {
        if (GameState.gameStatus === 'leaderboard') {
            returnToMenu();
        }
    }
    
    function handleEnemyDestroyed(event) {
        if (GameState.gameStatus === 'playing' && event && event.points) {
            addScore(event.points);
        }
    }
    
    // High score management
    function updateHighScore() {
        if (GameState.score > GameState.highScore) {
            GameState.highScore = GameState.score;
            saveHighScore();
        }
    }
    
    function loadHighScore() {
        try {
            const saved = localStorage.getItem('spaceShooterHighScore');
            return saved ? parseInt(saved, 10) : 0;
        } catch (e) {
            return 0;
        }
    }
    
    function saveHighScore() {
        try {
            localStorage.setItem('spaceShooterHighScore', GameState.highScore.toString());
        } catch (e) {
            // Ignore localStorage errors
        }
    }
    
    function saveScore() {
        try {
            const scores = loadLeaderboard();
            scores.push({
                score: GameState.score,
                level: GameState.level,
                date: new Date().toISOString()
            });
            
            // Keep only top 10 scores
            scores.sort((a, b) => b.score - a.score);
            scores.splice(10);
            
            localStorage.setItem('spaceShooterLeaderboard', JSON.stringify(scores));
            leaderboard = scores;
        } catch (e) {
            // Ignore localStorage errors
        }
    }
    
    function loadLeaderboard() {
        try {
            const saved = localStorage.getItem('spaceShooterLeaderboard');
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            return [];
        }
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
    let lastFireTime = 0;
    const fireRate = 200; // milliseconds between shots
    
    function init() {
        PlayerShip.x = 540;
        PlayerShip.y = 1700;
        PlayerShip.health = 100;
        PlayerShip.width = 60;
        PlayerShip.height = 80;
        
        // Initialize PlayerBullets array
        PlayerBullets.bullets = [];
        
        // Listen for events
        EventBus.on('PLAYER_MOVE_LEFT', moveLeft);
        EventBus.on('PLAYER_MOVE_RIGHT', moveRight);
        EventBus.on('PLAYER_SHOOT', shoot);
        EventBus.on('ENEMY_DESTROYED', handleEnemyDestroyed);
    }
    
    function moveLeft() {
        if (GameState.gameStatus !== 'playing') return;
        
        PlayerShip.x -= PLAYER_SPEED;
        PlayerShip.x = Math.max(0, PlayerShip.x);
    }
    
    function moveRight() {
        if (GameState.gameStatus !== 'playing') return;
        
        PlayerShip.x += PLAYER_SPEED;
        PlayerShip.x = Math.min(CANVAS_WIDTH - PlayerShip.width, PlayerShip.x);
    }
    
    function shoot() {
        if (GameState.gameStatus !== 'playing') return;
        
        const now = Date.now();
        if (now - lastFireTime < fireRate) return;
        
        const bullet = {
            x: PlayerShip.x + PlayerShip.width / 2 - 2,
            y: PlayerShip.y,
            width: 4,
            height: 10,
            active: true
        };
        
        PlayerBullets.bullets.push(bullet);
        lastFireTime = now;
    }
    
    function takeDamage(damage) {
        if (GameState.gameStatus !== 'playing') return;
        
        PlayerShip.health -= damage;
        PlayerShip.health = Math.max(0, PlayerShip.health);
        
        if (PlayerShip.health <= 0) {
            EventBus.emit('PLAYER_DIED', {});
        }
    }
    
    function handleEnemyDestroyed(event) {
        const { enemyId } = event;
        // Remove the enemy from our collision detection
        // This is handled by enemy_system, we just need to clean up any references
    }
    
    function update(dt) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Update player bullets
        for (let i = PlayerBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = PlayerBullets.bullets[i];
            bullet.y -= BULLET_SPEED;
            
            // Remove bullets that are off-screen
            if (bullet.y < -bullet.height) {
                PlayerBullets.bullets.splice(i, 1);
                continue;
            }
            
            // Check collision with enemies
            for (let j = 0; j < Enemies.enemies.length; j++) {
                const enemy = Enemies.enemies[j];
                if (checkCollision(bullet, enemy)) {
                    // Remove bullet
                    PlayerBullets.bullets.splice(i, 1);
                    
                    // Damage enemy and emit event
                    enemy.health -= 25;
                    if (enemy.health <= 0) {
                        const points = enemy.type === 'basic' ? 100 : 200;
                        EventBus.emit('ENEMY_DESTROYED', { enemyId: enemy.id, points: points });
                    }
                    break;
                }
            }
        }
        
        // Check collision with enemy bullets
        for (let i = EnemyBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = EnemyBullets.bullets[i];
            if (checkCollision(bullet, PlayerShip)) {
                // Remove bullet
                EnemyBullets.bullets.splice(i, 1);
                takeDamage(20);
                break;
            }
        }
        
        // Check collision with enemies
        for (let i = 0; i < Enemies.enemies.length; i++) {
            const enemy = Enemies.enemies[i];
            if (checkCollision(enemy, PlayerShip)) {
                takeDamage(30);
                // Remove enemy on collision
                Enemies.enemies.splice(i, 1);
                break;
            }
        }
    }
    
    function checkCollision(rect1, rect2) {
        return rect1.x < rect2.x + rect2.width &&
               rect1.x + rect1.width > rect2.x &&
               rect1.y < rect2.y + rect2.height &&
               rect1.y + rect1.height > rect2.y;
    }
    
    function render(ctx) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Draw player ship
        ctx.fillStyle = '#00FF00';
        ctx.fillRect(PlayerShip.x, PlayerShip.y, PlayerShip.width, PlayerShip.height);
        
        // Draw player ship details (simple triangle shape)
        ctx.fillStyle = '#00AA00';
        ctx.beginPath();
        ctx.moveTo(PlayerShip.x + PlayerShip.width / 2, PlayerShip.y);
        ctx.lineTo(PlayerShip.x + 10, PlayerShip.y + 30);
        ctx.lineTo(PlayerShip.x + PlayerShip.width - 10, PlayerShip.y + 30);
        ctx.closePath();
        ctx.fill();
        
        // Draw player bullets
        ctx.fillStyle = '#FFFF00';
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
    let lastSpawnTime = 0;
    let spawnInterval = 2000; // 2 seconds
    let enemyIdCounter = 0;
    let lastEnemyShootTime = {};
    
    function init() {
        Enemies.enemies = [];
        EnemyBullets.bullets = [];
        lastSpawnTime = 0;
        enemyIdCounter = 0;
        lastEnemyShootTime = {};
        
        // Listen for enemy destruction events
        EventBus.on('ENEMY_DESTROYED', function(event) {
            destroyEnemy(event.enemyId);
        });
    }
    
    function spawnEnemy(x, y, type) {
        if (GameState.gameStatus !== 'playing') return;
        
        const enemy = {
            id: 'enemy_' + (++enemyIdCounter),
            x: x,
            y: y,
            type: type,
            width: type === 'small' ? 40 : type === 'medium' ? 60 : 80,
            height: type === 'small' ? 40 : type === 'medium' ? 60 : 80,
            health: type === 'small' ? 20 : type === 'medium' ? 50 : 100,
            maxHealth: type === 'small' ? 20 : type === 'medium' ? 50 : 100,
            speed: type === 'small' ? ENEMY_SPEED * 1.5 : type === 'medium' ? ENEMY_SPEED : ENEMY_SPEED * 0.7,
            points: type === 'small' ? 10 : type === 'medium' ? 25 : 50,
            movePattern: type === 'small' ? 'straight' : type === 'medium' ? 'sine' : 'toward_player',
            sineOffset: Math.random() * Math.PI * 2,
            shootCooldown: type === 'small' ? 3000 : type === 'medium' ? 2000 : 1500,
            active: true
        };
        
        Enemies.enemies.push(enemy);
        lastEnemyShootTime[enemy.id] = Date.now();
    }
    
    function destroyEnemy(enemyId) {
        if (GameState.gameStatus !== 'playing') return;
        
        const index = Enemies.enemies.findIndex(enemy => enemy.id === enemyId);
        if (index !== -1) {
            delete lastEnemyShootTime[enemyId];
            Enemies.enemies.splice(index, 1);
        }
    }
    
    function update(dt) {
        if (GameState.gameStatus !== 'playing') return;
        
        const now = Date.now();
        
        // Spawn enemies based on level
        const adjustedSpawnInterval = Math.max(500, spawnInterval - (GameState.level - 1) * 200);
        if (now - lastSpawnTime > adjustedSpawnInterval) {
            spawnRandomEnemy();
            lastSpawnTime = now;
        }
        
        // Update enemies
        for (let i = Enemies.enemies.length - 1; i >= 0; i--) {
            const enemy = Enemies.enemies[i];
            
            // Move enemy based on pattern
            moveEnemy(enemy, dt);
            
            // Enemy shooting
            if (now - lastEnemyShootTime[enemy.id] > enemy.shootCooldown) {
                shootEnemyBullet(enemy);
                lastEnemyShootTime[enemy.id] = now;
            }
            
            // Remove enemies that are off screen
            if (enemy.y > CANVAS_HEIGHT + enemy.height) {
                destroyEnemy(enemy.id);
            }
        }
        
        // Update enemy bullets
        for (let i = EnemyBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = EnemyBullets.bullets[i];
            bullet.y += bullet.speed * dt / 16.67; // normalize to 60fps
            
            // Remove bullets that are off screen
            if (bullet.y > CANVAS_HEIGHT + 10) {
                EnemyBullets.bullets.splice(i, 1);
            }
        }
        
        // Check collision between player bullets and enemies
        checkPlayerBulletCollisions();
    }
    
    function spawnRandomEnemy() {
        const x = Math.random() * (CANVAS_WIDTH - 80);
        const y = -80;
        
        // Choose enemy type based on level
        let type;
        const rand = Math.random();
        if (GameState.level <= 2) {
            type = rand < 0.7 ? 'small' : 'medium';
        } else if (GameState.level <= 5) {
            type = rand < 0.5 ? 'small' : rand < 0.8 ? 'medium' : 'large';
        } else {
            type = rand < 0.3 ? 'small' : rand < 0.6 ? 'medium' : 'large';
        }
        
        spawnEnemy(x, y, type);
    }
    
    function moveEnemy(enemy, dt) {
        const speedMultiplier = dt / 16.67; // normalize to 60fps
        
        switch (enemy.movePattern) {
            case 'straight':
                enemy.y += enemy.speed * speedMultiplier;
                break;
                
            case 'sine':
                enemy.y += enemy.speed * speedMultiplier;
                enemy.x += Math.sin(enemy.y * 0.01 + enemy.sineOffset) * 2 * speedMultiplier;
                // Keep enemy within bounds
                enemy.x = Math.max(0, Math.min(CANVAS_WIDTH - enemy.width, enemy.x));
                break;
                
            case 'toward_player':
                enemy.y += enemy.speed * speedMultiplier;
                const playerCenterX = PlayerShip.x + PlayerShip.width / 2;
                const enemyCenterX = enemy.x + enemy.width / 2;
                const diff = playerCenterX - enemyCenterX;
                if (Math.abs(diff) > 5) {
                    enemy.x += Math.sign(diff) * enemy.speed * 0.3 * speedMultiplier;
                }
                // Keep enemy within bounds
                enemy.x = Math.max(0, Math.min(CANVAS_WIDTH - enemy.width, enemy.x));
                break;
        }
    }
    
    function shootEnemyBullet(enemy) {
        const bullet = {
            x: enemy.x + enemy.width / 2 - 3,
            y: enemy.y + enemy.height,
            width: 6,
            height: 12,
            speed: BULLET_SPEED * 0.8,
            active: true
        };
        
        EnemyBullets.bullets.push(bullet);
    }
    
    function checkPlayerBulletCollisions() {
        for (let i = PlayerBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = PlayerBullets.bullets[i];
            
            for (let j = Enemies.enemies.length - 1; j >= 0; j--) {
                const enemy = Enemies.enemies[j];
                
                // Bounding box collision detection
                if (bullet.x < enemy.x + enemy.width &&
                    bullet.x + bullet.width > enemy.x &&
                    bullet.y < enemy.y + enemy.height &&
                    bullet.y + bullet.height > enemy.y) {
                    
                    // Remove bullet
                    PlayerBullets.bullets.splice(i, 1);
                    
                    // Damage enemy
                    enemy.health -= 25;
                    
                    if (enemy.health <= 0) {
                        // Enemy destroyed
                        EventBus.emit('ENEMY_DESTROYED', {
                            enemyId: enemy.id,
                            points: enemy.points
                        });
                    }
                    
                    break; // Bullet can only hit one enemy
                }
            }
        }
    }
    
    function render(ctx) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Render enemies
        ctx.fillStyle = '#ff4444';
        for (const enemy of Enemies.enemies) {
            ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
            
            // Draw health bar for larger enemies
            if (enemy.type !== 'small' && enemy.health < enemy.maxHealth) {
                const healthBarWidth = enemy.width;
                const healthBarHeight = 4;
                const healthPercentage = enemy.health / enemy.maxHealth;
                
                // Background
                ctx.fillStyle = '#333333';
                ctx.fillRect(enemy.x, enemy.y - 8, healthBarWidth, healthBarHeight);
                
                // Health
                ctx.fillStyle = '#44ff44';
                ctx.fillRect(enemy.x, enemy.y - 8, healthBarWidth * healthPercentage, healthBarHeight);
                
                ctx.fillStyle = '#ff4444';
            }
        }
        
        // Render enemy bullets
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
    let keyStates = {};
    
    function init() {
        // Initialize key states
        keyStates = {
            ArrowLeft: false,
            ArrowRight: false,
            ' ': false,
            Escape: false
        };
        
        // Set up continuous key handling for movement
        setInterval(handleContinuousKeys, 16); // ~60fps
    }
    
    function handleClick(x, y) {
        // Handle clicks based on current screen
    }
    
    function handleKeyPress(key) {
        // Handle immediate key press actions
        if (key === "Escape") {
            if (GameState.gameStatus === "playing") {
                EventBus.emit("GAME_PAUSE", {});
            } else if (GameState.gameStatus === "paused") {
                EventBus.emit("GAME_RESUME", {});
            }
        }
        
        // Track key states for continuous actions
        if (key in keyStates) {
            keyStates[key] = true;
        }
        
        // Handle space for shooting (single press)
        if (key === " " && GameState.gameStatus === "playing") {
            EventBus.emit("PLAYER_SHOOT", {});
        }
    }
    
    function handleKeyRelease(key) {
        if (key in keyStates) {
            keyStates[key] = false;
        }
    }
    
    function handleContinuousKeys() {
        if (GameState.gameStatus === "playing") {
            if (keyStates.ArrowLeft) {
                EventBus.emit("PLAYER_MOVE_LEFT", {});
            }
            if (keyStates.ArrowRight) {
                EventBus.emit("PLAYER_MOVE_RIGHT", {});
            }
        }
    }
    
    function update(dt) {
        // Update UI elements based on game state
        updateScoreDisplay();
        updateLivesDisplay();
    }
    
    function updateScoreDisplay() {
        const scoreElement = document.getElementById('score_display');
        if (scoreElement) {
            scoreElement.textContent = `得分: ${GameState.score}`;
        }
    }
    
    function updateLivesDisplay() {
        const livesElement = document.getElementById('lives');
        if (livesElement) {
            livesElement.textContent = '❤'.repeat(Math.max(0, GameState.lives));
        }
        
        const finalScoreElement = document.getElementById('final_score');
        if (finalScoreElement) {
            finalScoreElement.textContent = `最终得分: ${GameState.score}`;
        }
        
        const bestScoreElement = document.getElementById('best_score');
        if (bestScoreElement) {
            bestScoreElement.textContent = `最高得分: ${GameState.highScore}`;
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

// Game loop variables
let lastTime = 0;
let canvas, ctx;

function gameLoop(timestamp) {
    const dt = timestamp - lastTime;
    lastTime = timestamp;
    
    // Update modules in order
    UIManagerModule.update(dt);
    PlayerShipModule.update(dt);
    EnemySystemModule.update(dt);
    GameStateModule.update(dt);
    
    // Render if playing
    if (GameState.gameStatus === 'playing' && ctx) {
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Render in order
        EnemySystemModule.render(ctx);
        PlayerShipModule.render(ctx);
        UIManagerModule.render(ctx);
    }
    
    requestAnimationFrame(gameLoop);
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
    
    // Reset player ship
    PlayerShip.x = 540;
    PlayerShip.y = 1700;
    PlayerShip.health = 100;
    PlayerBullets.bullets = [];
    
    // Reset enemies
    Enemies.enemies = [];
    EnemyBullets.bullets = [];
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('PLAYER_DIED', {});
    showScreen('game_over');
}

function retry() {
    startGame();
}

function returnToMenu() {
    GameState.gameStatus = 'menu';
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

function showLeaderboard() {
    GameState.gameStatus = 'leaderboard';
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
    updateLeaderboardDisplay();
}

function updateLeaderboardDisplay() {
    try {
        const scores = JSON.parse(localStorage.getItem('spaceShooterLeaderboard') || '[]');
        const scoreItems = document.querySelectorAll('.score-item');
        
        for (let i = 0; i < scoreItems.length; i++) {
            if (i < scores.length) {
                scoreItems[i].textContent = `${i + 1}. ${scores[i].score}`;
            } else {
                scoreItems[i].textContent = `${i + 1}. 0`;
            }
        }
    } catch (e) {
        // Ignore errors
    }
}

// Input handlers
function setupInputHandlers() {
    // Keyboard
    document.addEventListener('keydown', function(e) {
        UIManagerModule.handleKeyPress(e.key);
        e.preventDefault();
    });
    
    document.addEventListener('keyup', function(e) {
        UIManagerModule.handleKeyRelease(e.key);
        e.preventDefault();
    });
    
    // Mouse/Touch for gameplay
    const tapArea = document.getElementById('tap_area');
    if (tapArea) {
        tapArea.addEventListener('click', function(e) {
            if (GameState.gameStatus === 'playing') {
                EventBus.emit('PLAYER_SHOOT', {});
            }
        });
        
        tapArea.addEventListener('touchstart', function(e) {
            if (GameState.gameStatus === 'playing') {
                EventBus.emit('PLAYER_SHOOT', {});
            }
            e.preventDefault();
        });
    }
    
    // Button handlers
    const btnPlay = document.getElementById('btn_play');
    if (btnPlay) {
        btnPlay.addEventListener('click', startGame);
    }
    
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    if (btnLeaderboard) {
        btnLeaderboard.addEventListener('click', showLeaderboard);
    }
    
    const btnRetry = document.getElementById('btn_retry');
    if (btnRetry) {
        btnRetry.addEventListener('click', retry);
    }
    
    const btnMenu = document.getElementById('btn_menu');
    if (btnMenu) {
        btnMenu.addEventListener('click', returnToMenu);
    }
    
    const btnLeaderboardGameover = document.getElementById('btn_leaderboard_gameover');
    if (btnLeaderboardGameover) {
        btnLeaderboardGameover.addEventListener('click', showLeaderboard);
    }
    
    const btnClose = document.getElementById('btn_close');
    if (btnClose) {
        btnClose.addEventListener('click', returnToMenu);
    }
}

// Initialize game
function initGame() {
    // Get canvas
    canvas = document.getElementById('gameCanvas');
    if (canvas) {
        ctx = canvas.getContext('2d');
        
        // Set canvas size to match viewport
        function resizeCanvas() {
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;
        }
        
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
    }
    
    // Initialize modules in order
    GameStateModule.init();
    PlayerShipModule.init();
    EnemySystemModule.init();
    UIManagerModule.init();
    
    // Setup input
    setupInputHandlers();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', initGame);