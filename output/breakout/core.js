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
        if (GameState.gameStatus === 'menu') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.lives = 3;
            GameState.level = 1;
            resetGameObjects();
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
        if (GameState.gameStatus === 'game_over') {
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
                resetBallPosition();
            }
        }
    }

    function nextLevel() {
        if (GameState.gameStatus === 'playing') {
            GameState.level += 1;
            resetBallPosition();
        }
    }

    function resetGameObjects() {
        GameState.ballX = 540;
        GameState.ballY = 1500;
        GameState.ballVelX = 300;
        GameState.ballVelY = -300;
        GameState.paddleX = 490;
        GameState.paddleY = 1800;
        GameState.inputX = 0;
    }

    function resetBallPosition() {
        GameState.ballX = 540;
        GameState.ballY = 1500;
        GameState.ballVelX = 300;
        GameState.ballVelY = -300;
    }

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
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.lives = 3;
            GameState.level = 1;
            resetGameObjects();
        }
    }

    function handleReturnMenu(event) {
        returnToMenu();
    }

    function handleBrickDestroyed(event) {
        if (GameState.gameStatus === 'playing') {
            addScore(event.points);
        }
    }

    function handleBallLost(event) {
        if (GameState.gameStatus === 'playing') {
            loseLife();
        }
    }

    function handleLevelComplete(event) {
        if (GameState.gameStatus === 'playing') {
            nextLevel();
        }
    }

    function update(dt) {
        // Game state logic runs regardless of game status
        // Most state changes are event-driven
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
    let bricks = new Map();
    let eventBus;

    function init() {
        // Initialize event bus
        if (typeof window !== 'undefined' && window.eventBus) {
            eventBus = window.eventBus;
        } else {
            eventBus = {
                emit: function() {},
                on: function() {}
            };
        }

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

        // Initialize bricks for level 1
        resetLevel();

        // Listen for BRICK_DESTROYED events to update our brick collection
        eventBus.on('BRICK_DESTROYED', function(data) {
            if (bricks.has(data.brickId)) {
                bricks.delete(data.brickId);
                GameState.activeBricks = bricks.size;
                
                // Check if level is complete
                if (bricks.size === 0) {
                    eventBus.emit('LEVEL_COMPLETE', {});
                }
            }
        });
    }

    function updatePaddle(inputX) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Update paddle position based on input, keeping it within screen bounds
        paddle.x = Math.max(0, Math.min(CANVAS_WIDTH - PADDLE_WIDTH, inputX));
        
        // Update shared state
        GameState.paddleX = paddle.x;
    }

    function destroyBrick(brickId) {
        if (!bricks.has(brickId)) return 0;
        
        const brick = bricks.get(brickId);
        const points = brick.points;
        
        bricks.delete(brickId);
        GameState.activeBricks = bricks.size;
        
        // Check if level is complete
        if (bricks.size === 0) {
            eventBus.emit('LEVEL_COMPLETE', {});
        }
        
        return points;
    }

    function resetLevel() {
        bricks.clear();
        
        // Create brick layout based on current level
        const level = GameState.level;
        const startY = 100;
        const brickSpacing = 5;
        const totalBrickWidth = BRICK_COLS * BRICK_WIDTH + (BRICK_COLS - 1) * brickSpacing;
        const startX = (CANVAS_WIDTH - totalBrickWidth) / 2;
        
        for (let row = 0; row < BRICK_ROWS; row++) {
            for (let col = 0; col < BRICK_COLS; col++) {
                const brickId = `brick_${row}_${col}`;
                const brick = {
                    id: brickId,
                    x: startX + col * (BRICK_WIDTH + brickSpacing),
                    y: startY + row * (BRICK_HEIGHT + brickSpacing),
                    width: BRICK_WIDTH,
                    height: BRICK_HEIGHT,
                    points: (BRICK_ROWS - row) * 10 * level, // Higher rows worth more points, scaled by level
                    color: getColorForRow(row)
                };
                bricks.set(brickId, brick);
            }
        }
        
        GameState.activeBricks = bricks.size;
    }

    function getColorForRow(row) {
        const colors = ['#ff0000', '#ff8800', '#ffff00', '#88ff00', '#00ff00', '#00ff88', '#0088ff', '#0000ff'];
        return colors[row % colors.length];
    }

    function getAllBricks() {
        return Array.from(bricks.values());
    }

    function getPaddle() {
        return {
            x: paddle.x,
            y: paddle.y,
            width: paddle.width,
            height: paddle.height
        };
    }

    function getBall() {
        return {
            x: GameState.ballX,
            y: GameState.ballY,
            radius: ball.radius
        };
    }

    function update(dt) {
        // Update paddle position from shared state
        paddle.x = GameState.paddleX;
        paddle.y = GameState.paddleY;
        
        // Update ball position from shared state
        ball.x = GameState.ballX;
        ball.y = GameState.ballY;
        
        // Update paddle based on input
        updatePaddle(GameState.inputX);
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
    let eventBus;
    
    function init() {
        eventBus = window.eventBus || {
            emit: function(eventName, payload) {
                console.log('Event emitted:', eventName, payload);
            }
        };
    }
    
    function update(deltaTime) {
        if (GameState.gameStatus === 'playing') {
            updateBallPosition(deltaTime);
            checkCollisions();
        }
    }
    
    function updateBallPosition(deltaTime) {
        if (GameState.gameStatus !== 'playing') return;
        
        GameState.ballX += GameState.ballVelX * deltaTime;
        GameState.ballY += GameState.ballVelY * deltaTime;
    }
    
    function checkCollisions() {
        if (GameState.gameStatus !== 'playing') return;
        
        // Check wall collisions
        checkWallCollisions();
        
        // Check bottom boundary
        checkBottomBoundary();
        
        // Check paddle collision
        checkPaddleCollision();
        
        // Check brick collisions
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
            eventBus.emit('BALL_LOST', {});
        }
    }
    
    function checkPaddleCollision() {
        const paddle = game_objects.getPaddle();
        
        // Check if ball overlaps with paddle
        if (GameState.ballX + BALL_RADIUS >= paddle.x &&
            GameState.ballX - BALL_RADIUS <= paddle.x + PADDLE_WIDTH &&
            GameState.ballY + BALL_RADIUS >= paddle.y &&
            GameState.ballY - BALL_RADIUS <= paddle.y + PADDLE_HEIGHT &&
            GameState.ballVelY > 0) {
            
            // Reverse Y direction
            GameState.ballVelY = -Math.abs(GameState.ballVelY);
            
            // Adjust X direction based on hit position
            const hitPosition = (GameState.ballX - paddle.x) / PADDLE_WIDTH;
            const angle = (hitPosition - 0.5) * Math.PI / 3; // Max 60 degrees
            const speed = Math.sqrt(GameState.ballVelX * GameState.ballVelX + GameState.ballVelY * GameState.ballVelY);
            
            GameState.ballVelX = Math.sin(angle) * speed;
            GameState.ballVelY = -Math.abs(Math.cos(angle) * speed);
            
            // Ensure ball is above paddle
            GameState.ballY = paddle.y - BALL_RADIUS;
        }
    }
    
    function checkBrickCollisions() {
        const bricks = game_objects.getAllBricks();
        
        for (let brick of bricks) {
            if (brick.destroyed) continue;
            
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
                    // Hit from left or right
                    GameState.ballVelX = -GameState.ballVelX;
                } else {
                    // Hit from top or bottom
                    GameState.ballVelY = -GameState.ballVelY;
                }
                
                // Destroy brick and emit event
                const points = game_objects.destroyBrick(brick.id);
                eventBus.emit('BRICK_DESTROYED', {
                    brickId: brick.id,
                    points: points
                });
                
                break; // Only handle one collision per frame
            }
        }
    }
    
    function resetBall() {
        GameState.ballX = 540;
        GameState.ballY = 1500;
        GameState.ballVelX = 300;
        GameState.ballVelY = -300;
    }
    
    return {
        init,
        update,
        updateBallPosition,
        checkCollisions,
        resetBall
    };
})();

const ui_manager = (function() {
    let leaderboard = [];
    let currentScreen = 'menu';
    let menuSelection = 0;
    let gameOverSelection = 0;
    let leaderboardSelection = 0;
    let nameInput = '';
    let enteringName = false;
    let canvas, ctx;
    
    const eventBus = window.eventBus || {
        emit: function(event, payload) {
            console.log('Event emitted:', event, payload);
        },
        on: function(event, callback) {
            console.log('Event listener added:', event);
        }
    };

    function init() {
        canvas = document.getElementById('gameCanvas');
        ctx = canvas.getContext('2d');
        
        // Load leaderboard from localStorage
        const savedLeaderboard = localStorage.getItem('breakout_leaderboard');
        if (savedLeaderboard) {
            leaderboard = JSON.parse(savedLeaderboard);
        }
        
        // Listen for game events
        eventBus.on('GAME_OVER', handleGameOver);
        eventBus.on('SHOW_LEADERBOARD', showLeaderboard);
        eventBus.on('CLOSE_LEADERBOARD', hideLeaderboard);
    }

    function handleGameOver() {
        enteringName = true;
        nameInput = '';
        gameOverSelection = 0;
    }

    function handleInput(inputType, inputValue) {
        if (inputType === 'mouse_x') {
            GameState.inputX = inputValue;
            return;
        }

        if (GameState.gameStatus === 'menu') {
            handleMenuInput(inputType, inputValue);
        } else if (GameState.gameStatus === 'playing') {
            handleGameInput(inputType, inputValue);
        } else if (GameState.gameStatus === 'paused') {
            handlePausedInput(inputType, inputValue);
        } else if (GameState.gameStatus === 'game_over') {
            handleGameOverInput(inputType, inputValue);
        } else if (GameState.gameStatus === 'leaderboard') {
            handleLeaderboardInput(inputType, inputValue);
        }
    }

    function handleMenuInput(inputType, inputValue) {
        if (inputType === 'key_down') {
            if (inputValue === 38) { // Up arrow
                menuSelection = Math.max(0, menuSelection - 1);
            } else if (inputValue === 40) { // Down arrow
                menuSelection = Math.min(2, menuSelection + 1);
            } else if (inputValue === 13 || inputValue === 32) { // Enter or Space
                if (menuSelection === 0) {
                    eventBus.emit('GAME_START', {});
                } else if (menuSelection === 1) {
                    showLeaderboard();
                } else if (menuSelection === 2) {
                    // Quit - could close window or show quit confirmation
                }
            }
        }
    }

    function handleGameInput(inputType, inputValue) {
        if (inputType === 'key_down') {
            if (inputValue === 27) { // Escape
                eventBus.emit('GAME_PAUSE', {});
            }
        }
    }

    function handlePausedInput(inputType, inputValue) {
        if (inputType === 'key_down') {
            if (inputValue === 27 || inputValue === 13 || inputValue === 32) { // Escape, Enter, or Space
                eventBus.emit('GAME_RESUME', {});
            }
        }
    }

    function handleGameOverInput(inputType, inputValue) {
        if (enteringName) {
            if (inputType === 'key_down') {
                if (inputValue === 13) { // Enter
                    if (nameInput.trim().length > 0) {
                        saveScore(nameInput.trim(), GameState.score);
                        enteringName = false;
                    }
                } else if (inputValue === 8) { // Backspace
                    nameInput = nameInput.slice(0, -1);
                } else if (inputValue >= 32 && inputValue <= 126 && nameInput.length < 10) {
                    nameInput += String.fromCharCode(inputValue);
                }
            }
        } else {
            if (inputType === 'key_down') {
                if (inputValue === 38) { // Up arrow
                    gameOverSelection = Math.max(0, gameOverSelection - 1);
                } else if (inputValue === 40) { // Down arrow
                    gameOverSelection = Math.min(2, gameOverSelection + 1);
                } else if (inputValue === 13 || inputValue === 32) { // Enter or Space
                    if (gameOverSelection === 0) {
                        eventBus.emit('RETRY', {});
                    } else if (gameOverSelection === 1) {
                        showLeaderboard();
                    } else if (gameOverSelection === 2) {
                        eventBus.emit('RETURN_MENU', {});
                    }
                }
            }
        }
    }

    function handleLeaderboardInput(inputType, inputValue) {
        if (inputType === 'key_down') {
            if (inputValue === 27 || inputValue === 13 || inputValue === 32) { // Escape, Enter, or Space
                hideLeaderboard();
            }
        }
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            currentScreen = 'leaderboard';
        }
    }

    function hideLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'menu';
            currentScreen = 'menu';
        }
    }

    function saveScore(playerName, score) {
        if (GameState.gameStatus === 'game_over') {
            const newEntry = { name: playerName, score: score, date: new Date().toLocaleDateString() };
            leaderboard.push(newEntry);
            leaderboard.sort((a, b) => b.score - a.score);
            leaderboard = leaderboard.slice(0, 10); // Keep top 10
            
            localStorage.setItem('breakout_leaderboard', JSON.stringify(leaderboard));
        }
    }

    function update(deltaTime) {
        // Update UI elements
        updateScoreDisplay();
        updateLivesDisplay();
        updateBallPosition();
        updatePaddlePosition();
    }

    function updateScoreDisplay() {
        const scoreDisplay = document.getElementById('score_display');
        if (scoreDisplay) {
            scoreDisplay.textContent = `得分: ${GameState.score}`;
        }
    }

    function updateLivesDisplay() {
        const livesDisplay = document.getElementById('lives_display');
        if (livesDisplay) {
            livesDisplay.textContent = `生命: ${GameState.lives}`;
        }
    }

    function updateBallPosition() {
        const ball = document.getElementById('ball');
        if (ball) {
            ball.style.left = `${(GameState.ballX / CANVAS_WIDTH) * 100}vw`;
            ball.style.top = `${(GameState.ballY / CANVAS_HEIGHT) * 100}vh`;
        }
    }

    function updatePaddlePosition() {
        const paddle = document.getElementById('paddle');
        if (paddle) {
            paddle.style.left = `${(GameState.paddleX / CANVAS_WIDTH) * 100}vw`;
        }
    }

    function render(ctx) {
        if (!ctx) return;
        
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        if (GameState.gameStatus === 'playing') {
            renderGame(ctx);
        } else if (GameState.gameStatus === 'paused') {
            renderGame(ctx);
            renderPauseOverlay(ctx);
        }
    }

    function renderGame(ctx) {
        // Render game objects
        renderBall(ctx);
        renderPaddle(ctx);
        renderBricks(ctx);
    }

    function renderBall(ctx) {
        ctx.fillStyle = '#fff';
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
        for (let brick of bricks) {
            ctx.fillStyle = brick.color || '#f80';
            ctx.fillRect(brick.x, brick.y, BRICK_WIDTH, BRICK_HEIGHT);
            ctx.strokeStyle = '#000';
            ctx.strokeRect(brick.x, brick.y, BRICK_WIDTH, BRICK_HEIGHT);
        }
    }

    function renderPauseOverlay(ctx) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#fff';
        ctx.font = '48px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('PAUSED', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2);
        
        ctx.font = '24px Arial';
        ctx.fillText('Press ESC or ENTER to resume', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 80);
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

// Game loop
let lastTime = 0;
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
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
    
    requestAnimationFrame(gameLoop);
}

// State transitions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
    game_objects.resetLevel();
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', {});
    showScreen('game_over');
    document.getElementById('final_score').textContent = `最终得分: ${GameState.score}`;
}

function retry() {
    GameState.gameStatus = 'playing';
    EventBus.emit('RETRY', {});
    showScreen('gameplay');
    game_objects.resetLevel();
}

function returnToMenu() {
    GameState.gameStatus = 'menu';
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

function showLeaderboardScreen() {
    GameState.gameStatus = 'leaderboard';
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
    updateLeaderboardDisplay();
}

function hideLeaderboardScreen() {
    GameState.gameStatus = 'menu';
    EventBus.emit('CLOSE_LEADERBOARD', {});
    showScreen('main_menu');
}

function updateLeaderboardDisplay() {
    const scoreList = document.getElementById('score_list');
    const savedLeaderboard = localStorage.getItem('breakout_leaderboard');
    let leaderboard = [];
    
    if (savedLeaderboard) {
        leaderboard = JSON.parse(savedLeaderboard);
    }
    
    if (leaderboard.length === 0) {
        scoreList.innerHTML = '暂无记录';
    } else {
        let html = '';
        for (let i = 0; i < Math.min(10, leaderboard.length); i++) {
            const entry = leaderboard[i];
            html += `<div>${i + 1}. ${entry.name} - ${entry.score}</div>`;
        }
        scoreList.innerHTML = html;
    }
}

// Input handlers
let mouseX = 0;
document.addEventListener('mousemove', (e) => {
    const rect = document.body.getBoundingClientRect();
    mouseX = (e.clientX / rect.width) * CANVAS_WIDTH;
    GameState.inputX = mouseX - PADDLE_WIDTH / 2;
});

document.addEventListener('touchmove', (e) => {
    e.preventDefault();
    const rect = document.body.getBoundingClientRect();
    const touch = e.touches[0];
    mouseX = (touch.clientX / rect.width) * CANVAS_WIDTH;
    GameState.inputX = mouseX - PADDLE_WIDTH / 2;
});

document.addEventListener('keydown', (e) => {
    if (GameState.gameStatus === 'playing') {
        if (e.key === 'ArrowLeft') {
            GameState.inputX = Math.max(0, GameState.inputX - 20);
        } else if (e.key === 'ArrowRight') {
            GameState.inputX = Math.min(CANVAS_WIDTH - PADDLE_WIDTH, GameState.inputX + 20);
        }
    }
});

// Event listeners
EventBus.on('GAME_OVER', gameOver);

// Button event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Main menu buttons
    document.getElementById('btn_play').addEventListener('click', startGame);
    document.getElementById('btn_leaderboard').addEventListener('click', showLeaderboardScreen);
    
    // Game over buttons
    document.getElementById('btn_retry').addEventListener('click', retry);
    document.getElementById('btn_menu').addEventListener('click', returnToMenu);
    document.getElementById('btn_leaderboard_gameover').addEventListener('click', showLeaderboardScreen);
    
    // Leaderboard button
    document.getElementById('btn_close').addEventListener('click', hideLeaderboardScreen);
    
    // Tap area for mobile
    document.getElementById('tap_area').addEventListener('click', (e) => {
        const rect = e.target.getBoundingClientRect();
        mouseX = (e.clientX / rect.width) * CANVAS_WIDTH;
        GameState.inputX = mouseX - PADDLE_WIDTH / 2;
    });
});

// Initialize modules
document.addEventListener('DOMContentLoaded', () => {
    game_state.init();
    game_objects.init();
    physics_engine.init();
    ui_manager.init();
    
    // Start game loop
    requestAnimationFrame(gameLoop);
    
    // Show initial screen
    showScreen('main_menu');
});