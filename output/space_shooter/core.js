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
const PLAYER_SPEED = 8;
const BULLET_SPEED = 12;
const ENEMY_SPEED = 3;

// Shared state objects
const GameState = {
    gameStatus: 'menu',
    score: 0,
    level: 1,
    highScore: 0
};

const PlayerShip = {
    x: 540,
    y: 1700,
    health: 3,
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

// Set up global eventBus
window.eventBus = EventBus;

// Module: game_state
const GameStateModule = (function() {
    let eventListeners = [];

    function init() {
        GameState.gameStatus = 'menu';
        GameState.score = 0;
        GameState.level = 1;
        GameState.highScore = parseInt(localStorage.getItem('spaceShooterHighScore') || '0');
        
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

    function handleGameStart() {
        if (GameState.gameStatus === 'menu') {
            startGame();
        }
    }

    function handleGamePause() {
        if (GameState.gameStatus === 'playing') {
            pauseGame();
        }
    }

    function handleGameResume() {
        if (GameState.gameStatus === 'paused') {
            resumeGame();
        }
    }

    function handlePlayerDied() {
        if (GameState.gameStatus === 'playing') {
            gameOver();
        }
    }

    function handleRetry() {
        if (GameState.gameStatus === 'game_over') {
            startGame();
        }
    }

    function handleReturnMenu() {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            returnToMenu();
        }
    }

    function handleShowLeaderboard() {
        if (GameState.gameStatus === 'game_over') {
            showLeaderboard();
        }
    }

    function handleCloseLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            returnToMenu();
        }
    }

    function handleEnemyDestroyed(event) {
        if (GameState.gameStatus === 'playing') {
            addScore(event.points);
        }
    }

    function startGame() {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
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
            
            // Update high score if needed
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
            
            // Level progression based on score
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

// Module: player_ship
const player_ship = (function() {
    let lastShotTime = 0;
    const SHOT_COOLDOWN = 150; // milliseconds between shots

    function init() {
        PlayerShip.x = 540;
        PlayerShip.y = 1700;
        PlayerShip.health = 3;
        PlayerShip.width = 60;
        PlayerShip.height = 80;
        PlayerBullets.bullets = [];
    }

    function moveLeft() {
        if (GameState.gameStatus !== 'playing') return;
        PlayerShip.x = Math.max(0, PlayerShip.x - PLAYER_SPEED);
    }

    function moveRight() {
        if (GameState.gameStatus !== 'playing') return;
        PlayerShip.x = Math.min(CANVAS_WIDTH - PlayerShip.width, PlayerShip.x + PLAYER_SPEED);
    }

    function shoot() {
        if (GameState.gameStatus !== 'playing') return;
        
        const now = Date.now();
        if (now - lastShotTime < SHOT_COOLDOWN) return;
        
        PlayerBullets.bullets.push({
            x: PlayerShip.x + PlayerShip.width / 2 - 2,
            y: PlayerShip.y,
            width: 4,
            height: 10,
            speed: BULLET_SPEED,
            active: true
        });
        
        lastShotTime = now;
    }

    function takeDamage(damage) {
        if (GameState.gameStatus !== 'playing') return;
        
        PlayerShip.health -= damage;
        if (PlayerShip.health <= 0) {
            PlayerShip.health = 0;
            // Emit PLAYER_DIED event
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

        // Update player bullets
        for (let i = PlayerBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = PlayerBullets.bullets[i];
            bullet.y -= bullet.speed;
            
            // Remove bullets that are off-screen
            if (bullet.y + bullet.height < 0) {
                PlayerBullets.bullets.splice(i, 1);
                continue;
            }

            // Check collision with enemies
            for (let j = Enemies.enemies.length - 1; j >= 0; j--) {
                const enemy = Enemies.enemies[j];
                if (checkBoundingBoxOverlap(bullet, enemy)) {
                    // Remove bullet
                    PlayerBullets.bullets.splice(i, 1);
                    
                    // Damage enemy
                    enemy.health -= 1;
                    
                    // Check if enemy is destroyed
                    if (enemy.health <= 0) {
                        const points = enemy.type === 'basic' ? 100 : enemy.type === 'fast' ? 150 : 200;
                        
                        // Emit ENEMY_DESTROYED event
                        EventBus.emit('ENEMY_DESTROYED', {
                            enemyId: enemy.id,
                            points: points
                        });
                    }
                    break;
                }
            }
        }

        // Check collision with enemy bullets
        for (let i = EnemyBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = EnemyBullets.bullets[i];
            const playerRect = {
                x: PlayerShip.x,
                y: PlayerShip.y,
                width: PlayerShip.width,
                height: PlayerShip.height
            };
            
            if (checkBoundingBoxOverlap(bullet, playerRect)) {
                // Remove bullet
                EnemyBullets.bullets.splice(i, 1);
                
                // Damage player
                takeDamage(1);
                break;
            }
        }

        // Check collision with enemies
        for (let i = 0; i < Enemies.enemies.length; i++) {
            const enemy = Enemies.enemies[i];
            const playerRect = {
                x: PlayerShip.x,
                y: PlayerShip.y,
                width: PlayerShip.width,
                height: PlayerShip.height
            };
            
            if (checkBoundingBoxOverlap(enemy, playerRect)) {
                takeDamage(1);
                break;
            }
        }
    }

    function render(ctx) {
        if (GameState.gameStatus !== 'playing') return;

        // Render player ship
        ctx.fillStyle = '#00ff00';
        ctx.fillRect(PlayerShip.x, PlayerShip.y, PlayerShip.width, PlayerShip.height);
        
        // Add simple ship details
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(PlayerShip.x + 25, PlayerShip.y + 10, 10, 20);
        ctx.fillRect(PlayerShip.x + 10, PlayerShip.y + 40, 15, 30);
        ctx.fillRect(PlayerShip.x + 35, PlayerShip.y + 40, 15, 30);

        // Render player bullets
        ctx.fillStyle = '#ffff00';
        for (const bullet of PlayerBullets.bullets) {
            ctx.fillRect(bullet.x, bullet.y, bullet.width, bullet.height);
        }
    }

    // Listen for events
    EventBus.on('PLAYER_MOVE', (data) => {
        if (data.direction === 'left') {
            moveLeft();
        } else if (data.direction === 'right') {
            moveRight();
        }
    });

    EventBus.on('PLAYER_SHOOT', (data) => {
        shoot();
    });

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

// Module: enemy_system
const EnemySystem = (function() {
    let lastSpawnTime = 0;
    let spawnInterval = 2000; // milliseconds
    let nextEnemyId = 1;
    let lastEnemyShootTime = {};

    function init() {
        Enemies.enemies = [];
        EnemyBullets.bullets = [];
        lastSpawnTime = 0;
        nextEnemyId = 1;
        lastEnemyShootTime = {};
    }

    function spawnEnemy(x, y, type) {
        if (GameState.gameStatus !== 'playing') return;
        
        const enemy = {
            id: 'enemy_' + nextEnemyId++,
            x: x,
            y: y,
            type: type,
            health: getEnemyHealth(type),
            width: getEnemyWidth(type),
            height: getEnemyHeight(type),
            speed: ENEMY_SPEED,
            direction: 1,
            lastShot: 0
        };
        
        Enemies.enemies.push(enemy);
        lastEnemyShootTime[enemy.id] = 0;
    }

    function destroyEnemy(enemyId) {
        if (GameState.gameStatus !== 'playing') return;
        
        const index = Enemies.enemies.findIndex(enemy => enemy.id === enemyId);
        if (index !== -1) {
            delete lastEnemyShootTime[enemyId];
            Enemies.enemies.splice(index, 1);
        }
    }

    function getEnemyHealth(type) {
        switch (type) {
            case 'basic': return 1;
            case 'heavy': return 3;
            case 'fast': return 1;
            default: return 1;
        }
    }

    function getEnemyWidth(type) {
        switch (type) {
            case 'basic': return 40;
            case 'heavy': return 60;
            case 'fast': return 30;
            default: return 40;
        }
    }

    function getEnemyHeight(type) {
        switch (type) {
            case 'basic': return 40;
            case 'heavy': return 60;
            case 'fast': return 30;
            default: return 40;
        }
    }

    function getEnemySpeed(type) {
        switch (type) {
            case 'basic': return ENEMY_SPEED;
            case 'heavy': return ENEMY_SPEED * 0.5;
            case 'fast': return ENEMY_SPEED * 1.5;
            default: return ENEMY_SPEED;
        }
    }

    function update(dt) {
        if (GameState.gameStatus !== 'playing') return;

        const now = Date.now();
        
        // Spawn enemies periodically
        if (now - lastSpawnTime > spawnInterval) {
            const spawnX = Math.random() * (CANVAS_WIDTH - 60);
            const enemyTypes = ['basic', 'heavy', 'fast'];
            const randomType = enemyTypes[Math.floor(Math.random() * enemyTypes.length)];
            spawnEnemy(spawnX, -50, randomType);
            lastSpawnTime = now;
            
            // Increase difficulty over time
            spawnInterval = Math.max(800, spawnInterval - 10);
        }

        // Update enemies
        for (let i = Enemies.enemies.length - 1; i >= 0; i--) {
            const enemy = Enemies.enemies[i];
            
            // Move enemy down
            enemy.y += getEnemySpeed(enemy.type);
            
            // Add some horizontal movement for variety
            if (enemy.type === 'fast') {
                enemy.x += Math.sin(enemy.y * 0.01) * 2;
            }
            
            // Keep enemies within bounds
            enemy.x = Math.max(0, Math.min(CANVAS_WIDTH - enemy.width, enemy.x));
            
            // Enemy shooting
            if (now - lastEnemyShootTime[enemy.id] > 1500 + Math.random() * 1000) {
                const bullet = {
                    x: enemy.x + enemy.width / 2,
                    y: enemy.y + enemy.height,
                    width: 4,
                    height: 8,
                    speed: 6,
                    active: true
                };
                EnemyBullets.bullets.push(bullet);
                lastEnemyShootTime[enemy.id] = now;
            }
            
            // Remove enemies that are off screen
            if (enemy.y > CANVAS_HEIGHT) {
                delete lastEnemyShootTime[enemy.id];
                Enemies.enemies.splice(i, 1);
            }
        }

        // Update enemy bullets
        for (let i = EnemyBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = EnemyBullets.bullets[i];
            bullet.y += bullet.speed;
            
            // Remove bullets that are off screen
            if (bullet.y > CANVAS_HEIGHT) {
                EnemyBullets.bullets.splice(i, 1);
            }
        }
    }

    function render(ctx) {
        if (GameState.gameStatus !== 'playing') return;

        // Render enemies
        Enemies.enemies.forEach(enemy => {
            ctx.fillStyle = getEnemyColor(enemy.type);
            ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
            
            // Draw enemy outline
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.strokeRect(enemy.x, enemy.y, enemy.width, enemy.height);
        });

        // Render enemy bullets
        ctx.fillStyle = '#ff4444';
        EnemyBullets.bullets.forEach(bullet => {
            ctx.fillRect(bullet.x - 2, bullet.y - 8, bullet.width, bullet.height);
        });
    }

    function getEnemyColor(type) {
        switch (type) {
            case 'basic': return '#ff6666';
            case 'heavy': return '#cc3333';
            case 'fast': return '#ff9999';
            default: return '#ff6666';
        }
    }

    // Listen for ENEMY_DESTROYED events
    EventBus.on('ENEMY_DESTROYED', function(event) {
        destroyEnemy(event.enemyId);
    });

    return {
        init,
        spawnEnemy,
        destroyEnemy,
        update,
        render
    };
})();

// Module: ui_manager
const UIManager = (function() {
    let eventBus;
    let buttons = {};
    let lastKeyTime = {};
    let keyRepeatDelay = 150;

    function init() {
        eventBus = window.eventBus;
        setupButtons();
        setupEventListeners();
    }

    function setupButtons() {
        buttons = {
            menu: {
                start: { x: 390, y: 800, width: 300, height: 80, text: "START GAME" },
                leaderboard: { x: 390, y: 920, width: 300, height: 80, text: "LEADERBOARD" }
            },
            gameOver: {
                retry: { x: 290, y: 800, width: 200, height: 80, text: "RETRY" },
                menu: { x: 590, y: 800, width: 200, height: 80, text: "MENU" },
                leaderboard: { x: 390, y: 920, width: 300, height: 80, text: "VIEW SCORES" }
            },
            leaderboard: {
                back: { x: 390, y: 1400, width: 300, height: 80, text: "BACK TO MENU" }
            },
            paused: {
                resume: { x: 390, y: 800, width: 300, height: 80, text: "RESUME" },
                menu: { x: 390, y: 920, width: 300, height: 80, text: "MAIN MENU" }
            }
        };
    }

    function setupEventListeners() {
        if (eventBus) {
            eventBus.on('GAME_START', () => {});
            eventBus.on('GAME_PAUSE', () => {});
            eventBus.on('GAME_RESUME', () => {});
            eventBus.on('PLAYER_DIED', () => {});
            eventBus.on('RETRY', () => {});
            eventBus.on('RETURN_MENU', () => {});
            eventBus.on('SHOW_LEADERBOARD', () => {});
            eventBus.on('CLOSE_LEADERBOARD', () => {});
        }
    }

    function handleClick(x, y) {
        const currentButtons = buttons[GameState.gameStatus];
        if (!currentButtons) return;

        for (let buttonName in currentButtons) {
            const button = currentButtons[buttonName];
            if (isPointInButton(x, y, button)) {
                handleButtonClick(buttonName);
                break;
            }
        }
    }

    function isPointInButton(x, y, button) {
        return x >= button.x && x <= button.x + button.width &&
               y >= button.y && y <= button.y + button.height;
    }

    function handleButtonClick(buttonName) {
        if (!eventBus) return;

        switch (GameState.gameStatus) {
            case 'menu':
                if (buttonName === 'start') {
                    eventBus.emit('GAME_START', {});
                } else if (buttonName === 'leaderboard') {
                    eventBus.emit('SHOW_LEADERBOARD', {});
                }
                break;
            case 'game_over':
                if (buttonName === 'retry') {
                    eventBus.emit('RETRY', {});
                } else if (buttonName === 'menu') {
                    eventBus.emit('RETURN_MENU', {});
                } else if (buttonName === 'leaderboard') {
                    eventBus.emit('SHOW_LEADERBOARD', {});
                }
                break;
            case 'leaderboard':
                if (buttonName === 'back') {
                    eventBus.emit('CLOSE_LEADERBOARD', {});
                }
                break;
            case 'paused':
                if (buttonName === 'resume') {
                    eventBus.emit('GAME_RESUME', {});
                } else if (buttonName === 'menu') {
                    eventBus.emit('RETURN_MENU', {});
                }
                break;
        }
    }

    function handleKeyPress(key) {
        const now = Date.now();
        
        if (lastKeyTime[key] && now - lastKeyTime[key] < keyRepeatDelay) {
            return;
        }
        lastKeyTime[key] = now;

        if (!eventBus) return;

        switch (GameState.gameStatus) {
            case 'playing':
                handleGameplayKeys(key);
                break;
            case 'menu':
                if (key === 'Enter' || key === ' ') {
                    eventBus.emit('GAME_START', {});
                }
                break;
            case 'paused':
                if (key === 'Escape' || key === 'p' || key === 'P') {
                    eventBus.emit('GAME_RESUME', {});
                }
                break;
            case 'game_over':
                if (key === 'Enter' || key === ' ') {
                    eventBus.emit('RETRY', {});
                } else if (key === 'Escape') {
                    eventBus.emit('RETURN_MENU', {});
                }
                break;
            case 'leaderboard':
                if (key === 'Escape' || key === 'Enter') {
                    eventBus.emit('CLOSE_LEADERBOARD', {});
                }
                break;
        }
    }

    function handleGameplayKeys(key) {
        switch (key) {
            case 'ArrowLeft':
            case 'a':
            case 'A':
                eventBus.emit('PLAYER_MOVE', { direction: 'left' });
                break;
            case 'ArrowRight':
            case 'd':
            case 'D':
                eventBus.emit('PLAYER_MOVE', { direction: 'right' });
                break;
            case ' ':
            case 'Enter':
                eventBus.emit('PLAYER_SHOOT', { x: PlayerShip.x, y: PlayerShip.y });
                break;
            case 'Escape':
            case 'p':
            case 'P':
                eventBus.emit('GAME_PAUSE', {});
                break;
        }
    }

    function update(dt) {
        // UI doesn't need continuous updates
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
    UIManager.update(dt);
    player_ship.update(dt);
    EnemySystem.update(dt);
    GameStateModule.update(dt);
    
    // Clear canvas
    if (ctx) {
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Render modules in order
        player_ship.render(ctx);
        EnemySystem.render(ctx);
        UIManager.render(ctx);
    }
    
    // Update UI elements
    updateUI();
    
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    }
}

// Update UI elements
function updateUI() {
    const scoreDisplay = document.getElementById('score_display');
    if (scoreDisplay) {
        scoreDisplay.textContent = `得分: ${GameState.score}`;
    }
    
    const lives = document.getElementById('lives');
    if (lives) {
        lives.textContent = '❤'.repeat(Math.max(0, PlayerShip.health));
    }
    
    const finalScore = document.getElementById('final_score');
    if (finalScore) {
        finalScore.textContent = `最终得分: ${GameState.score}`;
    }
    
    const highScore = document.getElementById('high_score');
    if (highScore) {
        highScore.textContent = GameState.highScore;
    }
}

// State transition functions
function startGame() {
    GameStateModule.startGame();
    player_ship.init();
    EnemySystem.init();
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
    if (!canvas) {
        canvas = document.getElementById('gameCanvas');
        ctx = canvas.getContext('2d');
    }
    requestAnimationFrame(gameLoop);
}

function gameOver() {
    GameStateModule.gameOver();
    EventBus.emit('PLAYER_DIED', {});
    showScreen('game_over');
}

function retry() {
    startGame();
}

function returnToMenu() {
    GameStateModule.returnToMenu();
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

function showLeaderboard() {
    GameStateModule.showLeaderboard();
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
}

// Initialize modules
function initGame() {
    GameStateModule.init();
    player_ship.init();
    EnemySystem.init();
    UIManager.init();
    
    canvas = document.getElementById('gameCanvas');
    ctx = canvas.getContext('2d');
    
    // Set up state transition listeners
    EventBus.on('GAME_START', () => {
        if (GameState.gameStatus === 'menu') {
            startGame();
        }
    });
    
    EventBus.on('PLAYER_DIED', () => {
        if (GameState.gameStatus === 'playing') {
            gameOver();
        }
    });
    
    EventBus.on('RETRY', () => {
        if (GameState.gameStatus === 'game_over') {
            retry();
        }
    });
    
    EventBus.on('RETURN_MENU', () => {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            returnToMenu();
        }
    });
    
    EventBus.on('SHOW_LEADERBOARD', () => {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'menu') {
            showLeaderboard();
        }
    });
    
    EventBus.on('CLOSE_LEADERBOARD', () => {
        if (GameState.gameStatus === 'leaderboard') {
            returnToMenu();
        }
    });
}

// Input handlers
document.addEventListener('keydown', (e) => {
    UIManager.handleKeyPress(e.key);
});

document.addEventListener('click', (e) => {
    const rect = document.body.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (CANVAS_WIDTH / rect.width);
    const y = (e.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
    
    // Handle gameplay shooting
    if (GameState.gameStatus === 'playing') {
        EventBus.emit('PLAYER_SHOOT', { x: PlayerShip.x, y: PlayerShip.y });
    }
    
    UIManager.handleClick(x, y);
});

// Touch support
document.addEventListener('touchstart', (e) => {
    e.preventDefault();
    const touch = e.touches[0];
    const rect = document.body.getBoundingClientRect();
    const x = (touch.clientX - rect.left) * (CANVAS_WIDTH / rect.width);
    const y = (touch.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
    
    if (GameState.gameStatus === 'playing') {
        EventBus.emit('PLAYER_SHOOT', { x: PlayerShip.x, y: PlayerShip.y });
    }
    
    UIManager.handleClick(x, y);
});

// Screen navigation
document.getElementById('btn_play').addEventListener('click', () => {
    EventBus.emit('GAME_START', {});
});

document.getElementById('btn_leaderboard').addEventListener('click', () => {
    EventBus.emit('SHOW_LEADERBOARD', {});
});

document.getElementById('btn_retry').addEventListener('click', () => {
    EventBus.emit('RETRY', {});
});

document.getElementById('btn_menu').addEventListener('click', () => {
    EventBus.emit('RETURN_MENU', {});
});

document.getElementById('btn_leaderboard_go').addEventListener('click', () => {
    EventBus.emit('SHOW_LEADERBOARD', {});
});

document.getElementById('btn_close').addEventListener('click', () => {
    EventBus.emit('CLOSE_LEADERBOARD', {});
});

// Movement controls for mobile
let leftPressed = false;
let rightPressed = false;

document.addEventListener('keydown', (e) => {
    if (GameState.gameStatus === 'playing') {
        switch (e.key) {
            case 'ArrowLeft':
            case 'a':
            case 'A':
                if (!leftPressed) {
                    leftPressed = true;
                    movePlayer();
                }
                break;
            case 'ArrowRight':
            case 'd':
            case 'D':
                if (!rightPressed) {
                    rightPressed = true;
                    movePlayer();
                }
                break;
        }
    }
});

document.addEventListener('keyup', (e) => {
    switch (e.key) {
        case 'ArrowLeft':
        case 'a':
        case 'A':
            leftPressed = false;
            break;
        case 'ArrowRight':
        case 'd':
        case 'D':
            rightPressed = false;
            break;
    }
});

function movePlayer() {
    if (GameState.gameStatus !== 'playing') return;
    
    if (leftPressed) {
        EventBus.emit('PLAYER_MOVE', { direction: 'left' });
    }
    if (rightPressed) {
        EventBus.emit('PLAYER_MOVE', { direction: 'right' });
    }
    
    if (leftPressed || rightPressed) {
        setTimeout(movePlayer, 50);
    }
}

// Initialize game when page loads
document.addEventListener('DOMContentLoaded', () => {
    initGame();
    showScreen('main_menu');
});