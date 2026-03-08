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

// Global Constants
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const BALL_RADIUS = 10;
const PADDLE_WIDTH = 100;
const PADDLE_HEIGHT = 20;
const BRICK_WIDTH = 80;
const BRICK_HEIGHT = 30;
const BRICK_ROWS = 5;
const BRICK_COLS = 10;

// Shared State Objects
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
    bricksDestroyed: 0,
    totalBricks: 50,
    inputX: 0
};

// Make GameState globally available
window.GameState = GameState;

// Module: game_state
const game_state = (function() {
    let eventListeners = [];

    function init() {
        // GameState is already initialized globally
        setupEventListeners();
    }

    function setupEventListeners() {
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('GAME_PAUSE', handleGamePause);
        EventBus.on('GAME_RESUME', handleGameResume);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('BRICK_DESTROYED', handleBrickDestroyed);
        EventBus.on('BALL_LOST', handleBallLost);
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

    function handleRetry() {
        if (GameState.gameStatus === 'game_over') {
            GameState.score = 0;
            GameState.lives = 3;
            GameState.level = 1;
            GameState.bricksDestroyed = 0;
            GameState.totalBricks = 50;
            startGame();
        }
    }

    function handleReturnMenu() {
        if (GameState.gameStatus === 'game_over') {
            returnToMenu();
        }
    }

    function handleBrickDestroyed(event) {
        if (GameState.gameStatus === 'playing') {
            addScore(event.points);
            GameState.bricksDestroyed++;
            
            if (GameState.bricksDestroyed >= GameState.totalBricks) {
                nextLevel();
            }
        }
    }

    function handleBallLost() {
        if (GameState.gameStatus === 'playing') {
            loseLife();
            
            if (GameState.lives <= 0) {
                endGame();
            }
        }
    }

    function startGame() {
        if (GameState.gameStatus === 'menu') {
            GameState.gameStatus = 'playing';
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
            GameState.lives--;
        }
    }

    function nextLevel() {
        if (GameState.gameStatus === 'playing') {
            GameState.level++;
            GameState.bricksDestroyed = 0;
            EventBus.emit('LEVEL_COMPLETE', {});
        }
    }

    function update(dt) {
        // Game state module doesn't need frame-by-frame updates
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

// Module: game_objects
const game_objects = (function() {
    let bricks = [];

    function init() {
        initializeBricks();
        EventBus.on('LEVEL_COMPLETE', resetLevel);
        EventBus.on('BRICK_DESTROYED', handleBrickDestroyed);
    }

    function initializeBricks() {
        bricks = [];
        const startX = (CANVAS_WIDTH - (BRICK_COLS * BRICK_WIDTH + (BRICK_COLS - 1) * 5)) / 2;
        const startY = 200;
        
        for (let row = 0; row < BRICK_ROWS; row++) {
            for (let col = 0; col < BRICK_COLS; col++) {
                const brickId = `brick_${row}_${col}`;
                bricks.push({
                    id: brickId,
                    x: startX + col * (BRICK_WIDTH + 5),
                    y: startY + row * (BRICK_HEIGHT + 5),
                    width: BRICK_WIDTH,
                    height: BRICK_HEIGHT,
                    destroyed: false,
                    points: (BRICK_ROWS - row) * 10
                });
            }
        }
        
        GameState.totalBricks = bricks.length;
        GameState.bricksDestroyed = 0;
    }

    function updatePaddle(inputX) {
        if (GameState.gameStatus !== 'playing') return;
        
        const paddleSpeed = 800;
        const newX = GameState.paddleX + inputX * paddleSpeed * (1/60);
        
        GameState.paddleX = Math.max(0, Math.min(CANVAS_WIDTH - PADDLE_WIDTH, newX));
    }

    function getBallBounds() {
        return {
            x: GameState.ballX - BALL_RADIUS,
            y: GameState.ballY - BALL_RADIUS,
            width: BALL_RADIUS * 2,
            height: BALL_RADIUS * 2
        };
    }

    function getPaddleBounds() {
        return {
            x: GameState.paddleX,
            y: GameState.paddleY,
            width: PADDLE_WIDTH,
            height: PADDLE_HEIGHT
        };
    }

    function getBrickBounds(brickId) {
        const brick = bricks.find(b => b.id === brickId && !b.destroyed);
        if (!brick) return null;
        
        return {
            x: brick.x,
            y: brick.y,
            width: brick.width,
            height: brick.height
        };
    }

    function destroyBrick(brickId) {
        const brick = bricks.find(b => b.id === brickId && !b.destroyed);
        if (!brick) return 0;
        
        brick.destroyed = true;
        GameState.bricksDestroyed++;
        
        return brick.points;
    }

    function resetLevel() {
        initializeBricks();
        GameState.ballX = 540;
        GameState.ballY = 1500;
        GameState.paddleX = 490;
        GameState.paddleY = 1800;
    }

    function handleBrickDestroyed(event) {
        // Handled by physics engine
    }

    function update(dt) {
        updatePaddle(GameState.inputX);
    }

    function render(ctx) {
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Draw ball
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(GameState.ballX, GameState.ballY, BALL_RADIUS, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw paddle
        ctx.fillStyle = '#00BCD4';
        ctx.fillRect(GameState.paddleX, GameState.paddleY, PADDLE_WIDTH, PADDLE_HEIGHT);
        
        // Draw bricks
        for (let brick of bricks) {
            if (!brick.destroyed) {
                const row = Math.floor((brick.y - 200) / (BRICK_HEIGHT + 5));
                const colors = ['#ff0000', '#ff8800', '#ffff00', '#00ff00', '#0088ff'];
                ctx.fillStyle = colors[row % colors.length];
                ctx.fillRect(brick.x, brick.y, brick.width, brick.height);
                
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1;
                ctx.strokeRect(brick.x, brick.y, brick.width, brick.height);
            }
        }
    }

    return {
        init,
        updatePaddle,
        getBallBounds,
        getPaddleBounds,
        getBrickBounds,
        destroyBrick,
        resetLevel,
        update,
        render
    };
})();

// Module: physics_engine
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
        checkPaddleCollision();
        checkBrickCollisions();
        checkBottomBoundary();
    }
    
    function checkWallCollisions() {
        const ballRadius = BALL_RADIUS;
        const canvasWidth = CANVAS_WIDTH;
        
        if (GameState.ballX - ballRadius <= 0) {
            GameState.ballX = ballRadius;
            GameState.ballVelX = Math.abs(GameState.ballVelX);
        }
        
        if (GameState.ballX + ballRadius >= canvasWidth) {
            GameState.ballX = canvasWidth - ballRadius;
            GameState.ballVelX = -Math.abs(GameState.ballVelX);
        }
        
        if (GameState.ballY - ballRadius <= 0) {
            GameState.ballY = ballRadius;
            GameState.ballVelY = Math.abs(GameState.ballVelY);
        }
    }
    
    function checkPaddleCollision() {
        const ballBounds = game_objects.getBallBounds();
        const paddleBounds = game_objects.getPaddleBounds();
        
        if (ballBounds.x < paddleBounds.x + paddleBounds.width + 2 &&
            ballBounds.x + ballBounds.width > paddleBounds.x - 2 &&
            ballBounds.y < paddleBounds.y + paddleBounds.height + 2 &&
            ballBounds.y + ballBounds.height > paddleBounds.y - 2) {
            
            if (GameState.ballVelY > 0) {
                const paddleCenterX = paddleBounds.x + paddleBounds.width / 2;
                const ballCenterX = ballBounds.x + ballBounds.width / 2;
                const hitOffset = (ballCenterX - paddleCenterX) / (paddleBounds.width / 2);
                
                const maxAngle = Math.PI / 3;
                const angle = hitOffset * maxAngle;
                const speed = Math.sqrt(GameState.ballVelX * GameState.ballVelX + GameState.ballVelY * GameState.ballVelY);
                
                GameState.ballVelX = speed * Math.sin(angle);
                GameState.ballVelY = -Math.abs(speed * Math.cos(angle));
                
                GameState.ballY = paddleBounds.y - ballBounds.height - 1;
            }
        }
    }
    
    function checkBrickCollisions() {
        for (let row = 0; row < BRICK_ROWS; row++) {
            for (let col = 0; col < BRICK_COLS; col++) {
                const brickId = `brick_${row}_${col}`;
                
                try {
                    const brickBounds = game_objects.getBrickBounds(brickId);
                    if (!brickBounds) continue;
                    
                    const ballBounds = game_objects.getBallBounds();
                    
                    if (ballBounds.x < brickBounds.x + brickBounds.width + 1 &&
                        ballBounds.x + ballBounds.width > brickBounds.x - 1 &&
                        ballBounds.y < brickBounds.y + brickBounds.height + 1 &&
                        ballBounds.y + ballBounds.height > brickBounds.y - 1) {
                        
                        const points = game_objects.destroyBrick(brickId);
                        
                        const ballCenterX = ballBounds.x + ballBounds.width / 2;
                        const ballCenterY = ballBounds.y + ballBounds.height / 2;
                        const brickCenterX = brickBounds.x + brickBounds.width / 2;
                        const brickCenterY = brickBounds.y + brickBounds.height / 2;
                        
                        const deltaX = Math.abs(ballCenterX - brickCenterX);
                        const deltaY = Math.abs(ballCenterY - brickCenterY);
                        
                        if (deltaX / brickBounds.width > deltaY / brickBounds.height) {
                            GameState.ballVelX = -GameState.ballVelX;
                        } else {
                            GameState.ballVelY = -GameState.ballVelY;
                        }
                        
                        EventBus.emit('BRICK_DESTROYED', {
                            brickId: brickId,
                            points: points
                        });
                        
                        return;
                    }
                } catch (e) {
                    continue;
                }
            }
        }
    }
    
    function checkBottomBoundary() {
        const ballRadius = BALL_RADIUS;
        const canvasHeight = CANVAS_HEIGHT;
        
        if (GameState.ballY + ballRadius >= canvasHeight) {
            EventBus.emit('BALL_LOST', {});
            resetBall();
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

// Module: ui_manager
const ui_manager = (function() {
    let leaderboard = [];

    function init() {
        const savedLeaderboard = localStorage.getItem('breakout_leaderboard');
        if (savedLeaderboard) {
            leaderboard = JSON.parse(savedLeaderboard);
        }

        setupEventListeners();
        updateUI();
    }

    function setupEventListeners() {
        EventBus.on('GAME_OVER', handleGameOver);
        EventBus.on('LEVEL_COMPLETE', handleLevelComplete);
        
        document.addEventListener('keydown', handleKeyInput);
        document.addEventListener('keyup', handleKeyUp);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('touchmove', handleTouchMove);
    }

    function handleKeyInput(event) {
        const key = event.key;
        
        if (GameState.gameStatus === 'playing') {
            handleGameInput(key);
        }
    }

    function handleKeyUp(event) {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === 'a' || event.key === 'd') {
            GameState.inputX = 0;
        }
    }

    function handleGameInput(key) {
        switch(key) {
            case 'ArrowLeft':
            case 'a':
                GameState.inputX = -1;
                break;
            case 'ArrowRight':
            case 'd':
                GameState.inputX = 1;
                break;
        }
    }

    function handleMouseMove(event) {
        if (GameState.gameStatus === 'playing') {
            const canvas = document.querySelector('#gameCanvas');
            if (canvas) {
                const rect = canvas.getBoundingClientRect();
                const mouseX = event.clientX - rect.left;
                const normalizedX = (mouseX / rect.width) * CANVAS_WIDTH;
                
                const centerX = CANVAS_WIDTH / 2;
                GameState.inputX = Math.max(-1, Math.min(1, (normalizedX - centerX) / centerX));
            }
        }
    }

    function handleTouchMove(event) {
        event.preventDefault();
        if (GameState.gameStatus === 'playing' && event.touches.length > 0) {
            const canvas = document.querySelector('#gameCanvas');
            if (canvas) {
                const rect = canvas.getBoundingClientRect();
                const touchX = event.touches[0].clientX - rect.left;
                const normalizedX = (touchX / rect.width) * CANVAS_WIDTH;
                
                const centerX = CANVAS_WIDTH / 2;
                GameState.inputX = Math.max(-1, Math.min(1, (normalizedX - centerX) / centerX));
            }
        }
    }

    function handleInput(inputType, inputValue) {
        if (inputType === 'paddle') {
            GameState.inputX = Math.max(-1, Math.min(1, inputValue));
        }
    }

    function handleGameOver() {
        updateUI();
    }

    function handleLevelComplete() {
        // Level complete handling
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            EventBus.emit('SHOW_LEADERBOARD', {});
            updateUI();
        }
    }

    function hideLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'menu';
            EventBus.emit('CLOSE_LEADERBOARD', {});
            updateUI();
        }
    }

    function saveScore(playerName, score) {
        if (GameState.gameStatus === 'game_over') {
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

    function updateUI() {
        // Update score display
        const scoreDisplay = document.getElementById('score_display');
        if (scoreDisplay) {
            scoreDisplay.textContent = `得分: ${GameState.score}`;
        }

        // Update lives display
        const livesDisplay = document.getElementById('lives_display');
        if (livesDisplay) {
            livesDisplay.textContent = `生命: ${GameState.lives}`;
        }

        // Update level display
        const levelDisplay = document.getElementById('level_display');
        if (levelDisplay) {
            levelDisplay.textContent = `关卡: ${GameState.level}`;
        }

        // Update final score
        const finalScore = document.getElementById('final_score');
        if (finalScore) {
            finalScore.textContent = `最终得分: ${GameState.score}`;
        }

        updateLeaderboardDisplay();
    }

    function updateLeaderboardDisplay() {
        const scoreList = document.getElementById('score_list');
        if (scoreList) {
            if (leaderboard.length === 0) {
                scoreList.textContent = '暂无记录';
            } else {
                let html = '';
                for (let i = 0; i < Math.min(10, leaderboard.length); i++) {
                    const entry = leaderboard[i];
                    html += `<div>${i + 1}. ${entry.name} - ${entry.score}</div>`;
                }
                scoreList.innerHTML = html;
            }
        }
    }

    function update(dt) {
        updateUI();
    }

    function render(ctx) {
        // UI rendering handled by HTML/CSS
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

// Screen Management
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

// State Transitions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
    if (!gameLoopRunning) {
        gameLoopRunning = true;
        requestAnimationFrame(gameLoop);
    }
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', {});
    showScreen('game_over');
    gameLoopRunning = false;
}

function retry() {
    EventBus.emit('RETRY', {});
    showScreen('gameplay');
    if (!gameLoopRunning) {
        gameLoopRunning = true;
        requestAnimationFrame(gameLoop);
    }
}

function returnToMenu() {
    GameState.gameStatus = 'menu';
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
    gameLoopRunning = false;
}

function showLeaderboardScreen() {
    ui_manager.showLeaderboard();
    showScreen('leaderboard');
}

function hideLeaderboardScreen() {
    ui_manager.hideLeaderboard();
    showScreen('main_menu');
}

// Game Loop
let lastTime = 0;
let gameLoopRunning = false;

function gameLoop(timestamp) {
    const dt = Math.min((timestamp - lastTime) / 1000, 1/30); // Cap at 30fps minimum
    lastTime = timestamp;
    
    // Update modules in order
    ui_manager.update(dt);
    game_objects.update(dt);
    physics_engine.update(dt);
    game_state.update(dt);
    
    // Render modules in order
    const canvas = document.getElementById('gameCanvas');
    if (canvas && GameState.gameStatus === 'playing') {
        const ctx = canvas.getContext('2d');
        game_objects.render(ctx);
        ui_manager.render(ctx);
    }
    
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    } else {
        gameLoopRunning = false;
    }
}

// Event Listeners for State Transitions
EventBus.on('GAME_OVER', () => {
    gameOver();
});

// Input Handlers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in order
    game_state.init();
    game_objects.init();
    physics_engine.init();
    ui_manager.init();
    
    // Set up button event listeners
    const btnPlay = document.getElementById('btn_play');
    if (btnPlay) {
        btnPlay.addEventListener('click', startGame);
    }
    
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    if (btnLeaderboard) {
        btnLeaderboard.addEventListener('click', showLeaderboardScreen);
    }
    
    const btnRetry = document.getElementById('btn_retry');
    if (btnRetry) {
        btnRetry.addEventListener('click', retry);
    }
    
    const btnMenu = document.getElementById('btn_menu');
    if (btnMenu) {
        btnMenu.addEventListener('click', returnToMenu);
    }
    
    const btnLeaderboardGo = document.getElementById('btn_leaderboard_go');
    if (btnLeaderboardGo) {
        btnLeaderboardGo.addEventListener('click', showLeaderboardScreen);
    }
    
    const btnClose = document.getElementById('btn_close');
    if (btnClose) {
        btnClose.addEventListener('click', hideLeaderboardScreen);
    }
    
    // Show initial screen
    showScreen('main_menu');
});