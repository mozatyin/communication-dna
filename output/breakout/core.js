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

// Game State Module
const game_state = (function() {
    let eventBus;
    let highScores = [];
    
    function init() {
        eventBus = EventBus;
        
        // Load high scores from localStorage
        loadHighScores();
        
        // Set up event listeners
        eventBus.on('GAME_START', handleGameStart);
        eventBus.on('GAME_PAUSE', handleGamePause);
        eventBus.on('GAME_RESUME', handleGameResume);
        eventBus.on('RETRY', handleRetry);
        eventBus.on('RETURN_MENU', handleReturnMenu);
        eventBus.on('BRICK_DESTROYED', handleBrickDestroyed);
        eventBus.on('BALL_LOST', handleBallLost);
    }
    
    function startGame() {
        if (GameState.gameStatus === 'menu') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.lives = 3;
            GameState.level = 1;
            GameState.bricksDestroyed = 0;
            GameState.totalBricks = 50;
            
            // Reset ball and paddle positions
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
            saveHighScore();
            eventBus.emit('GAME_OVER', {});
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
            }
        }
    }
    
    function nextLevel() {
        if (GameState.gameStatus === 'playing') {
            GameState.level += 1;
            GameState.bricksDestroyed = 0;
            GameState.totalBricks = 50;
            
            // Reset ball position and increase speed slightly
            GameState.ballX = 540;
            GameState.ballY = 1500;
            const speedMultiplier = 1 + (GameState.level - 1) * 0.1;
            GameState.ballVelX = 300 * speedMultiplier * (GameState.ballVelX > 0 ? 1 : -1);
            GameState.ballVelY = -300 * speedMultiplier;
            
            eventBus.emit('LEVEL_COMPLETE', {});
        }
    }
    
    function update(dt) {
        if (GameState.gameStatus === 'playing') {
            // Check for level completion
            if (GameState.bricksDestroyed >= GameState.totalBricks) {
                nextLevel();
            }
        }
    }
    
    function handleGameStart() {
        startGame();
    }
    
    function handleGamePause() {
        pauseGame();
    }
    
    function handleGameResume() {
        resumeGame();
    }
    
    function handleRetry() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'menu';
            startGame();
        }
    }
    
    function handleReturnMenu() {
        returnToMenu();
    }
    
    function handleBrickDestroyed(payload) {
        if (GameState.gameStatus === 'playing') {
            addScore(payload.points);
            GameState.bricksDestroyed += 1;
        }
    }
    
    function handleBallLost() {
        if (GameState.gameStatus === 'playing') {
            loseLife();
        }
    }
    
    function loadHighScores() {
        try {
            const saved = localStorage.getItem('breakout_highscores');
            if (saved) {
                highScores = JSON.parse(saved);
            } else {
                highScores = [];
            }
        } catch (e) {
            highScores = [];
        }
    }
    
    function saveHighScore() {
        try {
            // Add current score to high scores
            highScores.push({
                score: GameState.score,
                level: GameState.level,
                date: new Date().toISOString()
            });
            
            // Sort by score descending and keep top 10
            highScores.sort((a, b) => b.score - a.score);
            highScores = highScores.slice(0, 10);
            
            // Save to localStorage
            localStorage.setItem('breakout_highscores', JSON.stringify(highScores));
        } catch (e) {
            // localStorage not available or full
        }
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

// Game Objects Module
const game_objects = (function() {
    let bricks = [];
    let eventBus = null;
    
    function init() {
        eventBus = EventBus;
        
        // Initialize bricks grid
        initializeBricks();
        
        // Listen for level complete events
        eventBus.on('LEVEL_COMPLETE', function() {
            resetLevel();
        });
        
        eventBus.on('BRICK_DESTROYED', function(data) {
            if (data && data.brickId) {
                destroyBrick(data.brickId);
            }
        });
    }
    
    function initializeBricks() {
        bricks = [];
        const startX = 100;
        const startY = 200;
        const spacing = 5;
        
        for (let row = 0; row < BRICK_ROWS; row++) {
            for (let col = 0; col < BRICK_COLS; col++) {
                const brickId = `brick_${row}_${col}`;
                const x = startX + col * (BRICK_WIDTH + spacing);
                const y = startY + row * (BRICK_HEIGHT + spacing);
                
                bricks.push({
                    id: brickId,
                    x: x,
                    y: y,
                    width: BRICK_WIDTH,
                    height: BRICK_HEIGHT,
                    destroyed: false,
                    points: (BRICK_ROWS - row) * 10 // Higher rows worth more points
                });
            }
        }
        
        // Update total bricks count
        GameState.totalBricks = bricks.length;
        GameState.bricksDestroyed = 0;
    }
    
    function updatePaddle(inputX) {
        if (GameState.gameStatus !== 'playing') return;
        
        const paddleSpeed = 800;
        const deltaX = inputX * paddleSpeed * (1/60); // Assume 60fps
        
        GameState.paddleX += deltaX;
        
        // Clamp paddle to canvas bounds
        const minX = 0;
        const maxX = CANVAS_WIDTH - PADDLE_WIDTH;
        GameState.paddleX = Math.max(minX, Math.min(maxX, GameState.paddleX));
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
        if (!brick) {
            return { x: 0, y: 0, width: 0, height: 0 };
        }
        
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
        // Reset all bricks
        bricks.forEach(brick => {
            brick.destroyed = false;
        });
        
        GameState.bricksDestroyed = 0;
        GameState.totalBricks = bricks.length;
        
        // Reset paddle position
        GameState.paddleX = 490;
        GameState.paddleY = 1800;
    }
    
    function update(dt) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Update paddle based on input
        updatePaddle(GameState.inputX);
    }
    
    function render(ctx) {
        if (!ctx) return;
        
        // Render ball
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(GameState.ballX, GameState.ballY, BALL_RADIUS, 0, Math.PI * 2);
        ctx.fill();
        
        // Render paddle
        ctx.fillStyle = '#00BCD4';
        ctx.fillRect(GameState.paddleX, GameState.paddleY, PADDLE_WIDTH, PADDLE_HEIGHT);
        
        // Render bricks
        bricks.forEach(brick => {
            if (!brick.destroyed) {
                // Color bricks based on row for visual variety
                const row = parseInt(brick.id.split('_')[1]);
                const colors = ['#FF0000', '#FF8800', '#FFFF00', '#00FF00', '#0088FF'];
                ctx.fillStyle = colors[row % colors.length];
                ctx.fillRect(brick.x, brick.y, brick.width, brick.height);
                
                // Add border
                ctx.strokeStyle = '#FFFFFF';
                ctx.lineWidth = 1;
                ctx.strokeRect(brick.x, brick.y, brick.width, brick.height);
            }
        });
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

// Physics Engine Module
const physics_engine = (function() {
    let eventBus;
    
    function init() {
        eventBus = EventBus;
    }
    
    function updateBallPosition(deltaTime) {
        if (GameState.gameStatus !== 'playing') return;
        
        // Update ball position based on velocity and time
        GameState.ballX += GameState.ballVelX * deltaTime;
        GameState.ballY += GameState.ballVelY * deltaTime;
    }
    
    function checkCollisions() {
        if (GameState.gameStatus !== 'playing') return;
        
        // Check wall collisions first
        checkWallCollisions();
        
        // Check bottom boundary (ball lost)
        if (GameState.ballY + BALL_RADIUS > CANVAS_HEIGHT) {
            eventBus.emit('BALL_LOST', {});
            resetBall();
            return;
        }
        
        // Check paddle collision
        checkPaddleCollision();
        
        // Check brick collisions
        checkBrickCollisions();
    }
    
    function checkWallCollisions() {
        // Left wall
        if (GameState.ballX - BALL_RADIUS <= 0) {
            GameState.ballX = BALL_RADIUS;
            GameState.ballVelX = -GameState.ballVelX;
        }
        
        // Right wall
        if (GameState.ballX + BALL_RADIUS >= CANVAS_WIDTH) {
            GameState.ballX = CANVAS_WIDTH - BALL_RADIUS;
            GameState.ballVelX = -GameState.ballVelX;
        }
        
        // Top wall
        if (GameState.ballY - BALL_RADIUS <= 0) {
            GameState.ballY = BALL_RADIUS;
            GameState.ballVelY = -GameState.ballVelY;
        }
    }
    
    function checkPaddleCollision() {
        const ballBounds = game_objects.getBallBounds();
        const paddleBounds = game_objects.getPaddleBounds();
        
        // Check bounding box overlap with tolerance
        if (ballBounds.x < paddleBounds.x + paddleBounds.width + 2 &&
            ballBounds.x + ballBounds.width > paddleBounds.x - 2 &&
            ballBounds.y < paddleBounds.y + paddleBounds.height + 2 &&
            ballBounds.y + ballBounds.height > paddleBounds.y - 2) {
            
            // Only bounce if ball is moving downward
            if (GameState.ballVelY > 0) {
                // Calculate hit position relative to paddle center
                const paddleCenterX = paddleBounds.x + paddleBounds.width / 2;
                const ballCenterX = ballBounds.x + ballBounds.width / 2;
                const hitOffset = (ballCenterX - paddleCenterX) / (paddleBounds.width / 2);
                
                // Adjust ball velocity based on hit position
                const maxAngle = Math.PI / 3; // 60 degrees max
                const angle = hitOffset * maxAngle;
                const speed = Math.sqrt(GameState.ballVelX * GameState.ballVelX + GameState.ballVelY * GameState.ballVelY);
                
                GameState.ballVelX = speed * Math.sin(angle);
                GameState.ballVelY = -Math.abs(speed * Math.cos(angle)); // Always upward
                
                // Move ball above paddle to prevent sticking
                GameState.ballY = paddleBounds.y - BALL_RADIUS - 1;
            }
        }
    }
    
    function checkBrickCollisions() {
        // Check collision with each brick
        for (let row = 0; row < BRICK_ROWS; row++) {
            for (let col = 0; col < BRICK_COLS; col++) {
                const brickId = `brick_${row}_${col}`;
                
                try {
                    const brickBounds = game_objects.getBrickBounds(brickId);
                    if (!brickBounds || brickBounds.width === 0) continue; // Brick already destroyed
                    
                    const ballBounds = game_objects.getBallBounds();
                    
                    // Check bounding box overlap
                    if (ballBounds.x < brickBounds.x + brickBounds.width &&
                        ballBounds.x + ballBounds.width > brickBounds.x &&
                        ballBounds.y < brickBounds.y + brickBounds.height &&
                        ballBounds.y + ballBounds.height > brickBounds.y) {
                        
                        // Destroy brick and get points
                        const points = game_objects.destroyBrick(brickId);
                        
                        // Emit brick destroyed event
                        eventBus.emit('BRICK_DESTROYED', {
                            brickId: brickId,
                            points: points
                        });
                        
                        // Determine collision side and reverse appropriate velocity
                        const ballCenterX = ballBounds.x + ballBounds.width / 2;
                        const ballCenterY = ballBounds.y + ballBounds.height / 2;
                        const brickCenterX = brickBounds.x + brickBounds.width / 2;
                        const brickCenterY = brickBounds.y + brickBounds.height / 2;
                        
                        const deltaX = ballCenterX - brickCenterX;
                        const deltaY = ballCenterY - brickCenterY;
                        
                        // Determine which side was hit based on the overlap
                        const overlapX = (ballBounds.width + brickBounds.width) / 2 - Math.abs(deltaX);
                        const overlapY = (ballBounds.height + brickBounds.height) / 2 - Math.abs(deltaY);
                        
                        if (overlapX < overlapY) {
                            // Hit from left or right
                            GameState.ballVelX = -GameState.ballVelX;
                        } else {
                            // Hit from top or bottom
                            GameState.ballVelY = -GameState.ballVelY;
                        }
                        
                        // Only handle one collision per frame
                        return;
                    }
                } catch (e) {
                    // Brick doesn't exist, continue
                    continue;
                }
            }
        }
    }
    
    function resetBall() {
        GameState.ballX = 540; // Center X
        GameState.ballY = 1500; // Above paddle
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

// UI Manager Module
const ui_manager = (function() {
    let leaderboard = [];
    let currentMenuSelection = 0;
    let menuOptions = [];
    let showingNameInput = false;
    let playerNameInput = '';
    let inputCursor = 0;
    
    function init() {
        // Load leaderboard from localStorage
        const savedLeaderboard = localStorage.getItem('breakout_leaderboard');
        if (savedLeaderboard) {
            leaderboard = JSON.parse(savedLeaderboard);
        } else {
            leaderboard = [
                { name: 'AAA', score: 1000 },
                { name: 'BBB', score: 800 },
                { name: 'CCC', score: 600 },
                { name: 'DDD', score: 400 },
                { name: 'EEE', score: 200 }
            ];
        }
        
        updateMenuOptions();
    }
    
    function updateMenuOptions() {
        switch (GameState.gameStatus) {
            case 'menu':
                menuOptions = ['Start Game', 'Leaderboard'];
                break;
            case 'paused':
                menuOptions = ['Resume', 'Return to Menu'];
                break;
            case 'game_over':
                menuOptions = ['Retry', 'Return to Menu', 'Leaderboard'];
                break;
            case 'leaderboard':
                menuOptions = ['Back to Menu'];
                break;
            default:
                menuOptions = [];
        }
        currentMenuSelection = Math.min(currentMenuSelection, menuOptions.length - 1);
    }
    
    function handleInput(inputType, inputValue) {
        if (inputType === 'mouse_x' && GameState.gameStatus === 'playing') {
            GameState.inputX = inputValue - PADDLE_WIDTH / 2;
        } else if (inputType === 'key_left' && GameState.gameStatus === 'playing') {
            GameState.inputX = Math.max(0, GameState.inputX - 10);
        } else if (inputType === 'key_right' && GameState.gameStatus === 'playing') {
            GameState.inputX = Math.min(CANVAS_WIDTH - PADDLE_WIDTH, GameState.inputX + 10);
        }
    }
    
    function showLeaderboard() {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over') {
            EventBus.emit('SHOW_LEADERBOARD', {});
            updateMenuOptions();
        }
    }
    
    function hideLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            EventBus.emit('CLOSE_LEADERBOARD', {});
            updateMenuOptions();
        }
    }
    
    function saveScore(playerName, score) {
        if (GameState.gameStatus === 'game_over') {
            const newEntry = { name: playerName, score: score };
            leaderboard.push(newEntry);
            leaderboard.sort((a, b) => b.score - a.score);
            leaderboard = leaderboard.slice(0, 10);
            
            localStorage.setItem('breakout_leaderboard', JSON.stringify(leaderboard));
        }
    }
    
    function update(dt) {
        updateMenuOptions();
        
        // Handle continuous input for paddle movement
        if (GameState.gameStatus === 'playing') {
            // Clamp paddle input to canvas bounds
            GameState.inputX = Math.max(0, Math.min(CANVAS_WIDTH - PADDLE_WIDTH, GameState.inputX));
        }
        
        // Update UI elements
        updateUIElements();
    }
    
    function updateUIElements() {
        const scoreDisplay = document.getElementById('score_display');
        const livesDisplay = document.getElementById('lives_display');
        const finalScore = document.getElementById('final_score');
        const bestScore = document.getElementById('best_score');
        
        if (scoreDisplay) {
            scoreDisplay.textContent = `得分: ${GameState.score}`;
        }
        
        if (livesDisplay) {
            livesDisplay.textContent = `生命: ${GameState.lives}`;
        }
        
        if (finalScore) {
            finalScore.textContent = `最终得分: ${GameState.score}`;
        }
        
        if (bestScore && leaderboard.length > 0) {
            bestScore.textContent = `最高得分: ${leaderboard[0].score}`;
        }
        
        // Update leaderboard display
        updateLeaderboardDisplay();
    }
    
    function updateLeaderboardDisplay() {
        const scoreList = document.getElementById('score_list');
        if (scoreList) {
            scoreList.innerHTML = '';
            for (let i = 0; i < Math.min(5, leaderboard.length); i++) {
                const entry = leaderboard[i];
                const div = document.createElement('div');
                div.className = 'score_entry';
                div.textContent = `${i + 1}. ${entry.name} - ${entry.score}`;
                scoreList.appendChild(div);
            }
        }
    }
    
    function render(ctx) {
        // UI rendering is handled by HTML/CSS
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

// Show Screen Function
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

// Game Loop
let lastTime = 0;
let canvas, ctx;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Call update functions in update_order
    ui_manager.update(dt);
    game_objects.update(dt);
    physics_engine.update(dt);
    game_state.update(dt);
    
    // Call render functions in render_order
    if (canvas && ctx && GameState.gameStatus === 'playing') {
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        game_objects.render(ctx);
        ui_manager.render(ctx);
    }
    
    requestAnimationFrame(gameLoop);
}

// State Transition Functions
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
    GameState.gameStatus = 'menu';
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
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
}

function hideLeaderboardScreen() {
    GameState.gameStatus = 'menu';
    EventBus.emit('CLOSE_LEADERBOARD', {});
    showScreen('main_menu');
}

// Input Handlers
function setupInputHandlers() {
    // Keyboard input
    document.addEventListener('keydown', (e) => {
        if (GameState.gameStatus === 'playing') {
            switch (e.key) {
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    GameState.inputX = Math.max(0, GameState.inputX - 20);
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    GameState.inputX = Math.min(CANVAS_WIDTH - PADDLE_WIDTH, GameState.inputX + 20);
                    break;
            }
        }
    });
    
    // Mouse input
    document.addEventListener('mousemove', (e) => {
        if (GameState.gameStatus === 'playing') {
            const rect = canvas.getBoundingClientRect();
            const scaleX = CANVAS_WIDTH / rect.width;
            const mouseX = (e.clientX - rect.left) * scaleX;
            GameState.inputX = mouseX - PADDLE_WIDTH / 2;
        }
    });
    
    // Touch input
    document.addEventListener('touchmove', (e) => {
        e.preventDefault();
        if (GameState.gameStatus === 'playing' && e.touches.length > 0) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = CANVAS_WIDTH / rect.width;
            const touchX = (e.touches[0].clientX - rect.left) * scaleX;
            GameState.inputX = touchX - PADDLE_WIDTH / 2;
        }
    });
    
    // Button click handlers
    document.getElementById('btn_play').addEventListener('click', startGame);
    document.getElementById('btn_leaderboard').addEventListener('click', showLeaderboardScreen);
    document.getElementById('btn_retry').addEventListener('click', retry);
    document.getElementById('btn_menu').addEventListener('click', returnToMenu);
    document.getElementById('btn_leaderboard_go').addEventListener('click', showLeaderboardScreen);
    document.getElementById('btn_close').addEventListener('click', hideLeaderboardScreen);
}

// Event Bus Listeners
EventBus.on('GAME_OVER', () => {
    showScreen('game_over');
});

// Initialize Game
function initGame() {
    // Get canvas and context
    canvas = document.getElementById('gameCanvas');
    ctx = canvas.getContext('2d');
    
    // Scale canvas to fit screen while maintaining aspect ratio
    function resizeCanvas() {
        const container = canvas.parentElement;
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        
        const scaleX = containerWidth / CANVAS_WIDTH;
        const scaleY = containerHeight / CANVAS_HEIGHT;
        const scale = Math.min(scaleX, scaleY);
        
        canvas.style.width = (CANVAS_WIDTH * scale) + 'px';
        canvas.style.height = (CANVAS_HEIGHT * scale) + 'px';
    }
    
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
    
    // Initialize modules in init_order
    game_state.init();
    game_objects.init();
    physics_engine.init();
    ui_manager.init();
    
    // Setup input handlers
    setupInputHandlers();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

// Start the game when DOM is loaded
document.addEventListener('DOMContentLoaded', initGame);