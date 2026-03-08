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

// Make EventBus globally available
window.eventBus = EventBus;

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

// Module code
const GameStateModule = (function() {
    function init() {
        GameState.gameStatus = 'menu';
        GameState.score = 0;
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
        // Game state update logic if needed
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
        gameOver();
    }
    
    function handleRetry(event) {
        startGame();
    }
    
    function handleReturnMenu(event) {
        returnToMenu();
    }
    
    function handleShowLeaderboard(event) {
        showLeaderboard();
    }
    
    function handleCloseLeaderboard(event) {
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

const player_ship = (function() {
    let lastShotTime = 0;
    const SHOT_COOLDOWN = 200; // milliseconds between shots

    function init() {
        PlayerShip.x = 540;
        PlayerShip.y = 1700;
        PlayerShip.health = 3;
        PlayerShip.width = 60;
        PlayerShip.height = 80;
        PlayerBullets.bullets = [];
        lastShotTime = 0;
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
            x: PlayerShip.x + PlayerShip.width / 2 - 2,
            y: PlayerShip.y,
            speed: BULLET_SPEED,
            width: 4,
            height: 10
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

        // Update player bullets
        for (let i = PlayerBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = PlayerBullets.bullets[i];
            bullet.y -= bullet.speed;
            
            // Remove bullets that are off screen
            if (bullet.y < -bullet.height) {
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
                        const points = enemy.type === 'basic' ? 100 : 200;
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
                break; // Only take damage once per frame
            }
        }
    }

    function render(ctx) {
        if (GameState.gameStatus !== 'playing') return;

        // Render player ship
        ctx.fillStyle = '#00ff00';
        ctx.fillRect(PlayerShip.x, PlayerShip.y, PlayerShip.width, PlayerShip.height);
        
        // Draw a simple ship shape
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.moveTo(PlayerShip.x + PlayerShip.width / 2, PlayerShip.y);
        ctx.lineTo(PlayerShip.x + 10, PlayerShip.y + PlayerShip.height);
        ctx.lineTo(PlayerShip.x + PlayerShip.width - 10, PlayerShip.y + PlayerShip.height);
        ctx.closePath();
        ctx.fill();

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

const EnemySystem = (function() {
    let spawnTimer = 0;
    let spawnInterval = 2000; // milliseconds
    let enemyIdCounter = 0;
    
    function init() {
        Enemies.enemies = [];
        EnemyBullets.bullets = [];
        spawnTimer = 0;
        enemyIdCounter = 0;
    }
    
    function spawnEnemy(x, y, type) {
        if (GameState.gameStatus !== 'playing') return;
        
        const enemy = {
            id: 'enemy_' + (enemyIdCounter++),
            x: x,
            y: y,
            type: type,
            health: type === 'basic' ? 1 : type === 'heavy' ? 3 : 1,
            width: type === 'heavy' ? 80 : 60,
            height: type === 'heavy' ? 100 : 80,
            speed: type === 'fast' ? ENEMY_SPEED * 1.5 : ENEMY_SPEED,
            shootTimer: 0,
            shootInterval: type === 'shooter' ? 1500 : 3000
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
        
        // Spawn enemies periodically
        spawnTimer += dt * 1000;
        if (spawnTimer >= spawnInterval) {
            spawnTimer = 0;
            
            // Spawn random enemy type at random x position
            const x = Math.random() * (CANVAS_WIDTH - 80);
            const types = ['basic', 'fast', 'heavy', 'shooter'];
            const type = types[Math.floor(Math.random() * types.length)];
            spawnEnemy(x, -100, type);
            
            // Decrease spawn interval slightly each level
            spawnInterval = Math.max(800, 2000 - (GameState.level * 100));
        }
        
        // Update enemies
        for (let i = Enemies.enemies.length - 1; i >= 0; i--) {
            const enemy = Enemies.enemies[i];
            
            // Move enemy down
            enemy.y += enemy.speed;
            
            // Remove enemies that are off screen
            if (enemy.y > CANVAS_HEIGHT + 100) {
                Enemies.enemies.splice(i, 1);
                continue;
            }
            
            // Enemy shooting logic
            if (enemy.type === 'shooter' || enemy.type === 'heavy') {
                enemy.shootTimer += dt * 1000;
                if (enemy.shootTimer >= enemy.shootInterval) {
                    enemy.shootTimer = 0;
                    
                    // Create enemy bullet
                    const bullet = {
                        x: enemy.x + enemy.width / 2,
                        y: enemy.y + enemy.height,
                        speed: BULLET_SPEED * 0.7,
                        width: 8,
                        height: 16
                    };
                    EnemyBullets.bullets.push(bullet);
                }
            }
        }
        
        // Update enemy bullets
        for (let i = EnemyBullets.bullets.length - 1; i >= 0; i--) {
            const bullet = EnemyBullets.bullets[i];
            bullet.y += bullet.speed;
            
            // Remove bullets that are off screen
            if (bullet.y > CANVAS_HEIGHT + 50) {
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
            
            // Draw health indicator for heavy enemies
            if (enemy.type === 'heavy' && enemy.health > 1) {
                ctx.fillStyle = '#ff0000';
                const healthBarWidth = (enemy.width * enemy.health) / 3;
                ctx.fillRect(enemy.x, enemy.y - 10, healthBarWidth, 4);
            }
        });
        
        // Render enemy bullets
        ctx.fillStyle = '#ff4444';
        EnemyBullets.bullets.forEach(bullet => {
            ctx.fillRect(bullet.x, bullet.y, bullet.width, bullet.height);
        });
    }
    
    function getEnemyColor(type) {
        switch (type) {
            case 'basic': return '#ff6666';
            case 'fast': return '#ffaa66';
            case 'heavy': return '#aa6666';
            case 'shooter': return '#ff66aa';
            default: return '#ff6666';
        }
    }
    
    // Listen for ENEMY_DESTROYED events
    EventBus.on('ENEMY_DESTROYED', function(data) {
        destroyEnemy(data.enemyId);
    });
    
    return {
        init,
        spawnEnemy,
        destroyEnemy,
        update,
        render
    };
})();

const UIManager = (function() {
    function init() {
        // UI manager initialized
    }
    
    function handleClick(x, y) {
        if (GameState.gameStatus === 'menu') {
            // Start button area (center of screen)
            if (x >= 390 && x <= 690 && y >= 900 && y <= 1000) {
                EventBus.emit('GAME_START', {});
            }
        } else if (GameState.gameStatus === 'paused') {
            // Resume button
            if (x >= 390 && x <= 690 && y >= 800 && y <= 900) {
                EventBus.emit('GAME_RESUME', {});
            }
            // Return to menu button
            if (x >= 390 && x <= 690 && y >= 1000 && y <= 1100) {
                EventBus.emit('RETURN_MENU', {});
            }
        } else if (GameState.gameStatus === 'game_over') {
            // Retry button
            if (x >= 290 && x <= 490 && y >= 1200 && y <= 1300) {
                EventBus.emit('RETRY', {});
            }
            // Menu button
            if (x >= 590 && x <= 790 && y >= 1200 && y <= 1300) {
                EventBus.emit('RETURN_MENU', {});
            }
            // Leaderboard button
            if (x >= 390 && x <= 690 && y >= 1350 && y <= 1450) {
                EventBus.emit('SHOW_LEADERBOARD', {});
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            // Back button
            if (x >= 390 && x <= 690 && y >= 1600 && y <= 1700) {
                EventBus.emit('CLOSE_LEADERBOARD', {});
            }
        } else if (GameState.gameStatus === 'playing') {
            EventBus.emit('PLAYER_SHOOT', { x: PlayerShip.x, y: PlayerShip.y });
        }
    }
    
    function handleKeyPress(key) {
        if (GameState.gameStatus === 'playing') {
            if (key === 'ArrowLeft' || key === 'a' || key === 'A') {
                EventBus.emit('PLAYER_MOVE', { direction: 'left' });
            } else if (key === 'ArrowRight' || key === 'd' || key === 'D') {
                EventBus.emit('PLAYER_MOVE', { direction: 'right' });
            } else if (key === ' ' || key === 'Enter') {
                EventBus.emit('PLAYER_SHOOT', { x: PlayerShip.x, y: PlayerShip.y });
            } else if (key === 'Escape' || key === 'p' || key === 'P') {
                EventBus.emit('GAME_PAUSE', {});
            }
        } else if (GameState.gameStatus === 'paused') {
            if (key === 'Escape' || key === 'p' || key === 'P') {
                EventBus.emit('GAME_RESUME', {});
            }
        } else if (GameState.gameStatus === 'menu') {
            if (key === 'Enter' || key === ' ') {
                EventBus.emit('GAME_START', {});
            }
        } else if (GameState.gameStatus === 'game_over') {
            if (key === 'r' || key === 'R') {
                EventBus.emit('RETRY', {});
            } else if (key === 'm' || key === 'M') {
                EventBus.emit('RETURN_MENU', {});
            }
        }
    }
    
    function update(dt) {
        // Update UI elements
        const scoreDisplay = document.getElementById('score_display');
        if (scoreDisplay) {
            scoreDisplay.textContent = '得分: ' + GameState.score;
        }
        
        const finalScore = document.getElementById('final_score');
        if (finalScore) {
            finalScore.textContent = '最终得分: ' + GameState.score;
        }
        
        const lives = document.getElementById('lives');
        if (lives) {
            lives.textContent = '❤'.repeat(Math.max(0, PlayerShip.health));
        }
        
        const scoreList = document.getElementById('score_list');
        if (scoreList) {
            scoreList.innerHTML = `1. ${GameState.highScore}<br>2. 0<br>3. 0<br>4. 0<br>5. 0`;
        }
    }
    
    function render(ctx) {
        // UI rendering handled by HTML/CSS
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
    
    // Update modules in update_order
    UIManager.update(dt);
    player_ship.update(dt);
    EnemySystem.update(dt);
    GameStateModule.update(dt);
    
    // Render modules in render_order
    if (GameState.gameStatus === 'playing' && ctx) {
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        player_ship.render(ctx);
        EnemySystem.render(ctx);
        UIManager.render(ctx);
    }
    
    // Handle screen transitions
    if (GameState.gameStatus === 'menu') {
        showScreen('main_menu');
    } else if (GameState.gameStatus === 'playing') {
        showScreen('gameplay');
    } else if (GameState.gameStatus === 'game_over') {
        showScreen('game_over');
    } else if (GameState.gameStatus === 'leaderboard') {
        showScreen('leaderboard');
    }
    
    requestAnimationFrame(gameLoop);
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('PLAYER_DIED', {});
    showScreen('game_over');
}

function retry() {
    GameState.gameStatus = 'playing';
    EventBus.emit('RETRY', {});
    showScreen('gameplay');
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
}

// Input handlers
document.addEventListener('keydown', (e) => {
    UIManager.handleKeyPress(e.key);
});

document.addEventListener('click', (e) => {
    const rect = document.body.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    UIManager.handleClick(x, y);
});

// Touch support
document.addEventListener('touchstart', (e) => {
    e.preventDefault();
    const rect = document.body.getBoundingClientRect();
    const touch = e.touches[0];
    const x = touch.clientX - rect.left;
    const y = touch.clientY - rect.top;
    UIManager.handleClick(x, y);
});

// Button event handlers
document.addEventListener('DOMContentLoaded', () => {
    canvas = document.getElementById('gameCanvas');
    ctx = canvas.getContext('2d');
    
    // Initialize modules in init_order
    GameStateModule.init();
    player_ship.init();
    EnemySystem.init();
    UIManager.init();
    
    // Button event listeners
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
    
    document.getElementById('tap_area').addEventListener('click', () => {
        if (GameState.gameStatus === 'playing') {
            EventBus.emit('PLAYER_SHOOT', { x: PlayerShip.x, y: PlayerShip.y });
        }
    });
    
    // Start game loop
    requestAnimationFrame(gameLoop);
});