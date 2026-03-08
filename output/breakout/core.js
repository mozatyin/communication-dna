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
const PADDLE_WIDTH = 100;
const PADDLE_HEIGHT = 20;
const BALL_RADIUS = 10;
const BRICK_WIDTH = 80;
const BRICK_HEIGHT = 30;
const BRICK_ROWS = 8;
const BRICK_COLS = 12;

// Shared state
const GameState = {
    gameStatus: 'menu',
    score: 0,
    lives: 3,
    level: 1,
    ballX: 540,
    ballY: 1500,
    ballVelX: 300,
    ballVelY: -300,
    paddleX: 490,
    paddleY: 1800,
    activeBricks: 0,
    inputX: 0
};

// Make EventBus globally available
window.eventBus = EventBus;

// Module code
const game_state = (function() {
    function init() {
        GameState.gameStatus = 'menu';
        GameState.score = 0;
        GameState.lives = 3;
        GameState.level = 1;
        GameState.ballX = 540;
        GameState.ballY = 1500;
        GameState.ballVelX = 300;
        GameState.ballVelY = -300;
        GameState.paddleX = 490;
        GameState.paddleY = 1800;
        GameState.activeBricks = 0;
        GameState.inputX = 0;

        // Listen for events
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('GAME_PAUSE', handleGamePause);
        EventBus.on('GAME_RESUME', handleGameResume);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('BRICK_DESTROYED', handleBrickDestroyed);
        EventBus.on('BALL_LOST', handleBallLost);
        EventBus.on('LEVEL_COMPLETE', handleLevelComplete);
    }

    function startGame() {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.lives = 3;
            GameState.level = 1;
            GameState.ballX = 540;
            GameState.ballY = 1500;
            GameState.ballVelX = 300;
            GameState.ballVelY = -300;
            GameState.paddleX = 490;
            GameState.paddleY = 1800;
            GameState.inputX = 0;
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

    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            EventBus.emit('GAME_OVER', {});
        }
    }

    function returnToMenu() {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'menu';
        }
    }

    function addScore(points) {
        if (GameState.gameStatus === 'playing') {
            GameState.score += points;
        }
    }

    function loseLife() {
        if (GameState.gameStatus === 'playing' && GameState.lives > 0) {
            GameState.lives -= 1;
            if (GameState.lives <= 0) {
                endGame();
            } else {
                physics_engine.resetBall();
            }
        }
    }

    function nextLevel() {
        if (GameState.gameStatus === 'playing') {
            GameState.level += 1;
            game_objects.resetLevel();
            physics_engine.resetBall();
        }
    }

    function update(dt) {
        // Game state update logic runs regardless of game status
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

    function handleRetry(event) {
        startGame();
    }

    function handleReturnMenu(event) {
        returnToMenu();
    }

    function handleBrickDestroyed(event) {
        const { points } = event;
        addScore(points);
    }

    function handleBallLost(event) {
        loseLife();
    }

    function handleLevelComplete(event) {
        nextLevel();
    }

    return {
        init,
        startGame,
        pauseGame,
        resumeGame,
        endGame,
        returnToMenu,
        addScore,
        loseLife,
        nextLevel,
        update
    };
})();

const game_objects = (function() {
    let paddle;
    let ball;
    let bricks = [];
    let brickIdCounter = 0;

    function init() {
        // Initialize paddle
        paddle = {
            x: GameState.paddleX,
            y: GameState.paddleY,
            width: PADDLE_WIDTH,
            height: PADDLE_HEIGHT
        };

        // Initialize ball
        ball = {
            x: GameState.ballX,
            y: GameState.ballY,
            radius: BALL_RADIUS
        };

        // Initialize bricks
        resetLevel();
    }

    function updatePaddle(inputX) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Update paddle position based on input, keeping it within screen bounds
        let newX = inputX;
        newX = Math.max(0, Math.min(CANVAS_WIDTH - PADDLE_WIDTH, newX));
        
        GameState.paddleX = newX;
        paddle.x = newX;
    }

    function destroyBrick(brickId) {
        const brickIndex = bricks.findIndex(brick => brick.id === brickId);
        if (brickIndex === -1) return 0;
        
        const brick = bricks[brickIndex];
        const points = brick.points;
        
        // Remove brick from array
        bricks.splice(brickIndex, 1);
        
        // Update active brick count
        GameState.activeBricks = bricks.length;
        
        // Check if level is complete
        if (bricks.length === 0) {
            EventBus.emit('LEVEL_COMPLETE', {});
        }
        
        return points;
    }

    function resetLevel() {
        bricks = [];
        brickIdCounter = 0;
        
        // Create brick grid based on current level
        const startY = 300;
        const startX = (CANVAS_WIDTH - (BRICK_COLS * BRICK_WIDTH)) / 2;
        
        for (let row = 0; row < BRICK_ROWS; row++) {
            for (let col = 0; col < BRICK_COLS; col++) {
                const brick = {
                    id: `brick_${brickIdCounter++}`,
                    x: startX + col * BRICK_WIDTH,
                    y: startY + row * BRICK_HEIGHT,
                    width: BRICK_WIDTH,
                    height: BRICK_HEIGHT,
                    points: (BRICK_ROWS - row) * 10,
                    color: getBrickColor(row),
                    active: true
                };
                bricks.push(brick);
            }
        }
        
        GameState.activeBricks = bricks.length;
    }

    function getBrickColor(row) {
        const colors = ['#ff0000', '#ff8800', '#ffff00', '#88ff00', '#00ff00', '#00ff88', '#0088ff', '#0000ff'];
        return colors[row % colors.length];
    }

    function getAllBricks() {
        return bricks.slice();
    }

    function getPaddle() {
        return {
            x: GameState.paddleX,
            y: GameState.paddleY,
            width: PADDLE_WIDTH,
            height: PADDLE_HEIGHT
        };
    }

    function getBall() {
        return {
            x: GameState.ballX,
            y: GameState.ballY,
            radius: BALL_RADIUS
        };
    }

    function update(dt) {
        // Update paddle position from input
        if (GameState.gameStatus === 'playing') {
            updatePaddle(GameState.inputX);
        }
        
        // Update paddle position from GameState
        paddle.x = GameState.paddleX;
        paddle.y = GameState.paddleY;
        
        // Update ball position from GameState
        ball.x = GameState.ballX;
        ball.y = GameState.ballY;
    }

    return {
        init,
        updatePaddle,
        destroyBrick,
        resetLevel,
        getAllBricks,
        getPaddle,
        getBall,
        update
    };
})();

const physics_engine = (function() {
    function init() {
        // Physics engine initialized
    }

    function updateBallPosition(deltaTime) {
        if (GameState.gameStatus !== 'playing') return;
        
        GameState.ballX += GameState.ballVelX * deltaTime;
        GameState.ballY += GameState.ballVelY * deltaTime;
    }

    function checkCollisions() {
        if (GameState.gameStatus !== 'playing') return;
        
        checkWallCollisions();
        checkBottomBoundary();
        checkPaddleCollision();
        checkBrickCollisions();
    }

    function checkWallCollisions() {
        // Left wall
        if (GameState.ballX - BALL_RADIUS <= 0) {
            GameState.ballX = BALL_RADIUS;
            GameState.ballVelX = Math.abs(GameState.ballVelX);
        }
        
        // Right wall
        if (GameState.ballX + BALL_RADIUS >= CANVAS_WIDTH) {
            GameState.ballX = CANVAS_WIDTH - BALL_RADIUS;
            GameState.ballVelX = -Math.abs(GameState.ballVelX);
        }
        
        // Top wall
        if (GameState.ballY - BALL_RADIUS <= 0) {
            GameState.ballY = BALL_RADIUS;
            GameState.ballVelY = Math.abs(GameState.ballVelY);
        }
    }

    function checkBottomBoundary() {
        if (GameState.ballY > CANVAS_HEIGHT) {
            EventBus.emit('BALL_LOST', {});
        }
    }

    function checkPaddleCollision() {
        const paddle = game_objects.getPaddle();
        
        // Check if ball is in paddle area
        if (GameState.ballY + BALL_RADIUS >= paddle.y &&
            GameState.ballY - BALL_RADIUS <= paddle.y + PADDLE_HEIGHT &&
            GameState.ballX + BALL_RADIUS >= paddle.x &&
            GameState.ballX - BALL_RADIUS <= paddle.x + PADDLE_WIDTH) {
            
            // Reverse Y direction
            GameState.ballVelY = -Math.abs(GameState.ballVelY);
            
            // Adjust X direction based on hit position
            const hitPosition = (GameState.ballX - paddle.x) / PADDLE_WIDTH;
            const angle = (hitPosition - 0.5) * Math.PI / 3;
            const speed = Math.sqrt(GameState.ballVelX * GameState.ballVelX + GameState.ballVelY * GameState.ballVelY);
            
            GameState.ballVelX = speed * Math.sin(angle);
            GameState.ballVelY = -Math.abs(speed * Math.cos(angle));
            
            // Ensure ball is above paddle
            GameState.ballY = paddle.y - BALL_RADIUS;
        }
    }

    function checkBrickCollisions() {
        const bricks = game_objects.getAllBricks();
        
        for (let brick of bricks) {
            if (!brick.active) continue;
            
            // Check bounding box overlap
            if (GameState.ballX + BALL_RADIUS >= brick.x &&
                GameState.ballX - BALL_RADIUS <= brick.x + BRICK_WIDTH &&
                GameState.ballY + BALL_RADIUS >= brick.y &&
                GameState.ballY - BALL_RADIUS <= brick.y + BRICK_HEIGHT) {
                
                // Determine collision side
                const ballCenterX = GameState.ballX;
                const ballCenterY = GameState.ballY;
                const brickCenterX = brick.x + BRICK_WIDTH / 2;
                const brickCenterY = brick.y + BRICK_HEIGHT / 2;
                
                const deltaX = ballCenterX - brickCenterX;
                const deltaY = ballCenterY - brickCenterY;
                
                const overlapX = (BRICK_WIDTH / 2 + BALL_RADIUS) - Math.abs(deltaX);
                const overlapY = (BRICK_HEIGHT / 2 + BALL_RADIUS) - Math.abs(deltaY);
                
                // Reverse ball direction based on collision side
                if (overlapX < overlapY) {
                    GameState.ballVelX = -GameState.ballVelX;
                } else {
                    GameState.ballVelY = -GameState.ballVelY;
                }
                
                // Destroy brick and emit event
                const points = game_objects.destroyBrick(brick.id);
                EventBus.emit('BRICK_DESTROYED', { brickId: brick.id, points: points });
                
                break;
            }
        }
    }

    function resetBall() {
        GameState.ballX = 540;
        GameState.ballY = 1500;
        GameState.ballVelX = 300;
        GameState.ballVelY = -300;
    }

    function update(deltaTime) {
        if (GameState.gameStatus === 'playing') {
            updateBallPosition(deltaTime);
            checkCollisions();
        }
    }

    return {
        init,
        updateBallPosition,
        checkCollisions,
        resetBall,
        update
    };
})();

const ui_manager = (function() {
    let leaderboard = [];
    let canvas, ctx;

    function init() {
        canvas = document.getElementById('gameCanvas');
        ctx = canvas.getContext('2d');
        
        // Load leaderboard from localStorage
        const savedLeaderboard = localStorage.getItem('breakout_leaderboard');
        if (savedLeaderboard) {
            leaderboard = JSON.parse(savedLeaderboard);
        }
        
        setupEventListeners();
        
        // Listen for game events
        EventBus.on('GAME_OVER', handleGameOver);
    }

    function setupEventListeners() {
        // Mouse/touch input for paddle control
        const tapArea = document.getElementById('tap_area');
        
        tapArea.addEventListener('mousemove', (e) => {
            if (GameState.gameStatus === 'playing') {
                const rect = tapArea.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const normalizedX = (mouseX / rect.width) * CANVAS_WIDTH;
                GameState.inputX = normalizedX - PADDLE_WIDTH / 2;
            }
        });

        tapArea.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (GameState.gameStatus === 'playing') {
                const rect = tapArea.getBoundingClientRect();
                const touch = e.touches[0];
                const touchX = touch.clientX - rect.left;
                const normalizedX = (touchX / rect.width) * CANVAS_WIDTH;
                GameState.inputX = normalizedX - PADDLE_WIDTH / 2;
            }
        });

        // Keyboard input
        document.addEventListener('keydown', (e) => {
            if (GameState.gameStatus === 'playing') {
                switch(e.key) {
                    case 'ArrowLeft':
                        GameState.inputX = Math.max(0, GameState.paddleX - 50);
                        break;
                    case 'ArrowRight':
                        GameState.inputX = Math.min(CANVAS_WIDTH - PADDLE_WIDTH, GameState.paddleX + 50);
                        break;
                }
            }
        });
    }

    function handleInput(inputType, inputValue) {
        if (inputType === 'mouse_x' && GameState.gameStatus === 'playing') {
            GameState.inputX = Math.max(0, Math.min(CANVAS_WIDTH - PADDLE_WIDTH, inputValue - PADDLE_WIDTH / 2));
        }
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            updateLeaderboardDisplay();
            EventBus.emit('SHOW_LEADERBOARD', {});
        }
    }

    function hideLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'menu';
            EventBus.emit('CLOSE_LEADERBOARD', {});
        }
    }

    function saveScore(playerName, score) {
        if (playerName && score > 0) {
            const newEntry = { 
                name: playerName, 
                score: score, 
                date: new Date().toLocaleDateString() 
            };
            leaderboard.push(newEntry);
            leaderboard.sort((a, b) => b.score - a.score);
            leaderboard = leaderboard.slice(0, 10);
            
            localStorage.setItem('breakout_leaderboard', JSON.stringify(leaderboard));
            updateLeaderboardDisplay();
        }
    }

    function updateLeaderboardDisplay() {
        const listElement = document.getElementById('leaderboard_list');
        if (leaderboard.length === 0) {
            listElement.innerHTML = '<div class="no-scores">暂无记录</div>';
        } else {
            listElement.innerHTML = leaderboard.map((entry, index) => 
                `<div class="leaderboard-entry">
                    <span class="leaderboard-rank">${index + 1}.</span>
                    <span class="leaderboard-name">${entry.name}</span>
                    <span class="leaderboard-score">${entry.score}</span>
                </div>`
            ).join('');
        }
    }

    function handleGameOver() {
        document.getElementById('final_score').textContent = GameState.score;
    }

    function update(dt) {
        // Update HUD
        document.getElementById('score_display').textContent = `得分: ${GameState.score}`;
        document.getElementById('lives_display').textContent = `生命: ${GameState.lives}`;
        document.getElementById('level_display').textContent = `关卡: ${GameState.level}`;
    }

    function render(ctx) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Clear canvas
        ctx.fillStyle = 'rgba(0,0,0,0.1)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // Render game objects
        renderBall(ctx);
        renderPaddle(ctx);
        renderBricks(ctx);
    }

    function renderBall(ctx) {
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(GameState.ballX, GameState.ballY, BALL_RADIUS, 0, Math.PI * 2);
        ctx.fill();
    }

    function renderPaddle(ctx) {
        ctx.fillStyle = '#00BCD4';
        ctx.fillRect(GameState.paddleX, GameState.paddleY, PADDLE_WIDTH, PADDLE_HEIGHT);
    }

    function renderBricks(ctx) {
        const bricks = game_objects.getAllBricks();
        for (const brick of bricks) {
            if (brick.active) {
                ctx.fillStyle = brick.color || '#FF0000';
                ctx.fillRect(brick.x, brick.y, BRICK_WIDTH, BRICK_HEIGHT);
                
                ctx.strokeStyle = '#FFFFFF';
                ctx.lineWidth = 1;
                ctx.strokeRect(brick.x, brick.y, BRICK_WIDTH, BRICK_HEIGHT);
            }
        }
    }

    return {
        init,
        handleInput,
        showLeaderboard,
        hideLeaderboard,
        saveScore,
        update,
        render
    };
})();

// Screen management
function showScreen(screenId) {
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.style.display = 'none';
    });
    
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.style.display = 'block';
    }
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', {});
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

function showLeaderboardScreen() {
    GameState.gameStatus = 'leaderboard';
    ui_manager.showLeaderboard();
    showScreen('leaderboard');
}

function hideLeaderboardScreen() {
    GameState.gameStatus = 'menu';
    ui_manager.hideLeaderboard();
    showScreen('main_menu');
}

// Game loop
let lastTime = 0;
let gameLoopId;

function gameLoop(timestamp) {
    const dt = Math.min((timestamp - lastTime) / 1000, 0.016);
    lastTime = timestamp;
    
    // Update modules in order
    ui_manager.update(dt);
    game_objects.update(dt);
    physics_engine.update(dt);
    game_state.update(dt);
    
    // Render
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    ui_manager.render(ctx);
    
    // Continue loop if playing
    if (GameState.gameStatus === 'playing') {
        gameLoopId = requestAnimationFrame(gameLoop);
    }
}

// Initialize game
document.addEventListener('DOMContentLoaded', () => {
    // Initialize modules in order
    game_state.init();
    game_objects.init();
    physics_engine.init();
    ui_manager.init();
    
    // Set up button event listeners
    document.getElementById('btn_play').addEventListener('click', startGame);
    document.getElementById('btn_leaderboard').addEventListener('click', showLeaderboardScreen);
    document.getElementById('btn_retry').addEventListener('click', retry);
    document.getElementById('btn_return_menu').addEventListener('click', returnToMenu);
    document.getElementById('btn_show_leaderboard').addEventListener('click', showLeaderboardScreen);
    document.getElementById('btn_back_to_menu').addEventListener('click', hideLeaderboardScreen);
    
    // Save score functionality
    document.getElementById('btn_save_score').addEventListener('click', () => {
        document.getElementById('name_input_area').style.display = 'block';
    });
    
    document.getElementById('btn_confirm_name').addEventListener('click', () => {
        const playerName = document.getElementById('player_name').value.trim();
        if (playerName) {
            ui_manager.saveScore(playerName, GameState.score);
            document.getElementById('name_input_area').style.display = 'none';
            document.getElementById('player_name').value = '';
        }
    });
    
    // Listen for game state changes to manage game loop
    EventBus.on('GAME_START', () => {
        if (gameLoopId) cancelAnimationFrame(gameLoopId);
        lastTime = performance.now();
        gameLoopId = requestAnimationFrame(gameLoop);
    });
    
    EventBus.on('RETRY', () => {
        if (gameLoopId) cancelAnimationFrame(gameLoopId);
        lastTime = performance.now();
        gameLoopId = requestAnimationFrame(gameLoop);
    });
    
    EventBus.on('GAME_OVER', () => {
        if (gameLoopId) {
            cancelAnimationFrame(gameLoopId);
            gameLoopId = null;
        }
        setTimeout(() => showScreen('game_over'), 1000);
    });
    
    // Show initial screen
    showScreen('main_menu');
});