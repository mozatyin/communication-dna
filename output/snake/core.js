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
const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const GRID_SIZE = 20;
const INITIAL_SNAKE_LENGTH = 3;

// Shared State Objects
const GameState = {
    gameStatus: 'main_menu',
    score: 0,
    highScore: 0,
    gameSpeed: 200
};

const SnakeState = {
    snakeBody: [],
    snakeDirection: 'right',
    foodPosition: {x: 0, y: 0},
    gridWidth: 20,
    gridHeight: 20
};

// Module: game_state
const game_state = (function() {
    function init() {
        // Initialize GameState with default values
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.highScore = parseInt(localStorage.getItem('snakeHighScore') || '0');
        GameState.gameSpeed = 200;
        
        // Update UI
        updateHighScoreDisplay();
        
        // Set up event listeners
        EventBus.on('GAME_OVER', handleGameOver);
        EventBus.on('FOOD_EATEN', handleFoodEaten);
    }
    
    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            // Emit GAME_START event
            EventBus.emit('GAME_START', {});
            showScreen('gameplay');
            updateScoreDisplay();
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.gameStatus = 'game_over';
            
            // Update high score if needed
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
                localStorage.setItem('snakeHighScore', GameState.highScore.toString());
            }
            
            showScreen('game_over');
            updateFinalScoreDisplay();
        }
    }
    
    function retryGame() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            // Emit RETRY event
            EventBus.emit('RETRY', {});
            showScreen('gameplay');
            updateScoreDisplay();
        }
    }
    
    function returnToMenu() {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
            
            // Emit RETURN_MENU event
            EventBus.emit('RETURN_MENU', {});
            showScreen('main_menu');
            updateHighScoreDisplay();
        }
    }
    
    function showLeaderboard() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            
            // Emit SHOW_LEADERBOARD event
            EventBus.emit('SHOW_LEADERBOARD', {});
            showScreen('leaderboard');
            updateLeaderboardDisplay();
        }
    }
    
    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
            updateScoreDisplay();
        }
    }
    
    function handleGameOver(event) {
        endGame();
    }
    
    function handleFoodEaten(event) {
        addScore(event.points);
    }
    
    function updateScoreDisplay() {
        const scoreDisplay = document.getElementById('score_display');
        const bestDisplay = document.getElementById('best_display');
        if (scoreDisplay) scoreDisplay.textContent = `分数: ${GameState.score}`;
        if (bestDisplay) bestDisplay.textContent = `最高: ${GameState.highScore}`;
    }
    
    function updateHighScoreDisplay() {
        const highScore = document.getElementById('high_score');
        if (highScore) highScore.textContent = `最高分: ${GameState.highScore}`;
    }
    
    function updateFinalScoreDisplay() {
        const finalScore = document.getElementById('final_score');
        if (finalScore) finalScore.textContent = `最终分数: ${GameState.score}`;
    }
    
    function updateLeaderboardDisplay() {
        const scoreList = document.getElementById('score_list');
        if (scoreList) {
            const scores = JSON.parse(localStorage.getItem('snakeScores') || '[]');
            if (scores.length === 0) {
                scoreList.innerHTML = '1. 暂无记录<br>2. 暂无记录<br>3. 暂无记录<br>4. 暂无记录<br>5. 暂无记录';
            } else {
                let html = '';
                for (let i = 0; i < Math.min(5, scores.length); i++) {
                    html += `${i + 1}. ${scores[i]}<br>`;
                }
                scoreList.innerHTML = html;
            }
        }
    }
    
    return {
        init,
        startGame,
        endGame,
        retryGame,
        returnToMenu,
        showLeaderboard,
        addScore
    };
})();

// Module: snake_game
const SnakeGame = (function() {
    let lastMoveTime = 0;
    let nextDirection = null;
    
    function init() {
        resetGame();
        
        // Listen for events
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('DIRECTION_CHANGE', handleDirectionChange);
    }
    
    function handleGameStart() {
        resetGame();
    }
    
    function handleRetry() {
        resetGame();
    }
    
    function handleDirectionChange(event) {
        const direction = event.direction;
        changeDirection(direction);
    }
    
    function update() {
        if (GameState.gameStatus !== 'gameplay') return;
        
        const currentTime = Date.now();
        if (currentTime - lastMoveTime < GameState.gameSpeed) return;
        
        // Apply pending direction change
        if (nextDirection) {
            SnakeState.snakeDirection = nextDirection;
            nextDirection = null;
        }
        
        moveSnake();
        checkCollisions();
        
        lastMoveTime = currentTime;
    }
    
    function moveSnake() {
        const head = {...SnakeState.snakeBody[0]};
        
        // Move head based on direction
        switch (SnakeState.snakeDirection) {
            case 'up':
                head.y -= 1;
                break;
            case 'down':
                head.y += 1;
                break;
            case 'left':
                head.x -= 1;
                break;
            case 'right':
                head.x += 1;
                break;
        }
        
        // Add new head
        SnakeState.snakeBody.unshift(head);
        
        // Check if food eaten
        if (head.x === SnakeState.foodPosition.x && head.y === SnakeState.foodPosition.y) {
            // Don't remove tail (snake grows)
            spawnFood();
            
            // Emit food eaten event
            EventBus.emit('FOOD_EATEN', { points: 10 });
        } else {
            // Remove tail
            SnakeState.snakeBody.pop();
        }
    }
    
    function checkCollisions() {
        const head = SnakeState.snakeBody[0];
        
        // Check wall collision
        if (head.x < 0 || head.x >= SnakeState.gridWidth || 
            head.y < 0 || head.y >= SnakeState.gridHeight) {
            gameOver();
            return;
        }
        
        // Check self collision
        for (let i = 1; i < SnakeState.snakeBody.length; i++) {
            if (head.x === SnakeState.snakeBody[i].x && 
                head.y === SnakeState.snakeBody[i].y) {
                gameOver();
                return;
            }
        }
    }
    
    function gameOver() {
        EventBus.emit('GAME_OVER', { finalScore: GameState.score });
    }
    
    function changeDirection(direction) {
        if (GameState.gameStatus !== 'gameplay') return;
        
        const validDirections = ['up', 'down', 'left', 'right'];
        if (!validDirections.includes(direction)) return;
        
        // Prevent reversing into self
        const opposites = {
            'up': 'down',
            'down': 'up',
            'left': 'right',
            'right': 'left'
        };
        
        if (direction === opposites[SnakeState.snakeDirection]) return;
        
        nextDirection = direction;
    }
    
    function resetGame() {
        // Initialize snake in center
        const centerX = Math.floor(SnakeState.gridWidth / 2);
        const centerY = Math.floor(SnakeState.gridHeight / 2);
        
        SnakeState.snakeBody = [];
        for (let i = 0; i < INITIAL_SNAKE_LENGTH; i++) {
            SnakeState.snakeBody.push({
                x: centerX - i,
                y: centerY
            });
        }
        
        SnakeState.snakeDirection = 'right';
        nextDirection = null;
        lastMoveTime = 0;
        
        spawnFood();
    }
    
    function spawnFood() {
        let foodX, foodY;
        let validPosition = false;
        
        while (!validPosition) {
            foodX = Math.floor(Math.random() * SnakeState.gridWidth);
            foodY = Math.floor(Math.random() * SnakeState.gridHeight);
            
            validPosition = true;
            // Check if food spawns on snake
            for (const segment of SnakeState.snakeBody) {
                if (segment.x === foodX && segment.y === foodY) {
                    validPosition = false;
                    break;
                }
            }
        }
        
        SnakeState.foodPosition = { x: foodX, y: foodY };
    }
    
    return {
        init,
        update,
        changeDirection,
        resetGame
    };
})();

// Module: input_controls
const InputControls = (function() {
    let keysPressed = {};
    let lastDirectionTime = 0;
    const DIRECTION_COOLDOWN = 100; // Prevent rapid direction changes

    function init() {
        // Keyboard event listeners
        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('keyup', handleKeyUp);
        
        // Touch event listeners for mobile d-pad
        let touchStartX = 0;
        let touchStartY = 0;
        
        document.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        });
        
        document.addEventListener('touchend', function(e) {
            if (GameState.gameStatus !== 'gameplay') return;
            
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const dx = touchEndX - touchStartX;
            const dy = touchEndY - touchStartY;
            
            const minSwipeDistance = 30;
            
            if (Math.abs(dx) > minSwipeDistance || Math.abs(dy) > minSwipeDistance) {
                let direction;
                if (Math.abs(dx) > Math.abs(dy)) {
                    direction = dx > 0 ? 'right' : 'left';
                } else {
                    direction = dy > 0 ? 'down' : 'up';
                }
                
                emitDirectionChange(direction);
            }
        });
    }

    function handleKeyDown(e) {
        keysPressed[e.key] = true;
        e.preventDefault();
    }

    function handleKeyUp(e) {
        keysPressed[e.key] = false;
    }

    function update() {
        if (GameState.gameStatus !== 'gameplay') return;
        
        const currentTime = Date.now();
        if (currentTime - lastDirectionTime < DIRECTION_COOLDOWN) return;
        
        let direction = null;
        
        // Check arrow keys and WASD
        if (keysPressed['ArrowUp'] || keysPressed['w'] || keysPressed['W']) {
            direction = 'up';
        } else if (keysPressed['ArrowDown'] || keysPressed['s'] || keysPressed['S']) {
            direction = 'down';
        } else if (keysPressed['ArrowLeft'] || keysPressed['a'] || keysPressed['A']) {
            direction = 'left';
        } else if (keysPressed['ArrowRight'] || keysPressed['d'] || keysPressed['D']) {
            direction = 'right';
        }
        
        if (direction) {
            emitDirectionChange(direction);
            lastDirectionTime = currentTime;
        }
    }

    function emitDirectionChange(direction) {
        // Emit DIRECTION_CHANGE event
        EventBus.emit('DIRECTION_CHANGE', { direction: direction });
        
        // Also call snake_game.changeDirection directly
        if (typeof SnakeGame !== 'undefined' && SnakeGame.changeDirection) {
            SnakeGame.changeDirection(direction);
        }
    }

    return {
        init,
        update
    };
})();

// Module: ui_screens
const ui_screens = (function() {
    let canvas;
    let ctx;

    function init() {
        canvas = document.getElementById('gameCanvas');
        if (canvas) {
            ctx = canvas.getContext('2d');
        }
    }

    function render() {
        if (!canvas || !ctx) return;
        
        if (GameState.gameStatus === 'gameplay') {
            renderGameplay();
        }
    }

    function renderGameplay() {
        // Clear canvas
        ctx.fillStyle = '#1A1A1A';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const cellWidth = canvas.width / SnakeState.gridWidth;
        const cellHeight = canvas.height / SnakeState.gridHeight;

        // Draw grid lines
        ctx.strokeStyle = '#333333';
        ctx.lineWidth = 1;
        
        for (let x = 0; x <= SnakeState.gridWidth; x++) {
            ctx.beginPath();
            ctx.moveTo(x * cellWidth, 0);
            ctx.lineTo(x * cellWidth, canvas.height);
            ctx.stroke();
        }
        
        for (let y = 0; y <= SnakeState.gridHeight; y++) {
            ctx.beginPath();
            ctx.moveTo(0, y * cellHeight);
            ctx.lineTo(canvas.width, y * cellHeight);
            ctx.stroke();
        }

        // Draw food
        ctx.fillStyle = '#FF0000';
        ctx.fillRect(
            SnakeState.foodPosition.x * cellWidth,
            SnakeState.foodPosition.y * cellHeight,
            cellWidth,
            cellHeight
        );

        // Draw snake
        for (let i = 0; i < SnakeState.snakeBody.length; i++) {
            const segment = SnakeState.snakeBody[i];
            if (i === 0) {
                // Head - slightly different color
                ctx.fillStyle = '#45a049';
            } else {
                ctx.fillStyle = '#4CAF50';
            }
            ctx.fillRect(
                segment.x * cellWidth,
                segment.y * cellHeight,
                cellWidth,
                cellHeight
            );
        }
    }

    function handleClick(x, y) {
        // This function is kept for compatibility but not used in this implementation
    }

    return {
        init,
        render,
        handleClick
    };
})();

// Screen management
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

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Call update functions in update_order
    InputControls.update();
    SnakeGame.update();
    
    // Call render functions in render_order
    ui_screens.render();
    
    if (GameState.gameStatus === 'playing' || GameState.gameStatus === 'gameplay') {
        requestAnimationFrame(gameLoop);
    } else {
        // Continue loop for other states too
        requestAnimationFrame(gameLoop);
    }
}

// State transition functions
function startGame() {
    game_state.startGame();
}

function gameOver() {
    game_state.endGame();
}

function retry() {
    game_state.retryGame();
}

function returnToMenu() {
    game_state.returnToMenu();
}

function showLeaderboard() {
    game_state.showLeaderboard();
}

// Input handlers
function setupInputHandlers() {
    // Main menu start button
    const btnStart = document.getElementById('btn_start');
    if (btnStart) {
        btnStart.addEventListener('click', startGame);
    }
    
    // Gameplay d-pad buttons
    const btnUp = document.getElementById('btn_up');
    const btnDown = document.getElementById('btn_down');
    const btnLeft = document.getElementById('btn_left');
    const btnRight = document.getElementById('btn_right');
    
    if (btnUp) btnUp.addEventListener('click', () => EventBus.emit('DIRECTION_CHANGE', {direction: 'up'}));
    if (btnDown) btnDown.addEventListener('click', () => EventBus.emit('DIRECTION_CHANGE', {direction: 'down'}));
    if (btnLeft) btnLeft.addEventListener('click', () => EventBus.emit('DIRECTION_CHANGE', {direction: 'left'}));
    if (btnRight) btnRight.addEventListener('click', () => EventBus.emit('DIRECTION_CHANGE', {direction: 'right'}));
    
    // Game over buttons
    const btnRetry = document.getElementById('btn_retry');
    const btnMenu = document.getElementById('btn_menu');
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    
    if (btnRetry) btnRetry.addEventListener('click', retry);
    if (btnMenu) btnMenu.addEventListener('click', returnToMenu);
    if (btnLeaderboard) btnLeaderboard.addEventListener('click', showLeaderboard);
    
    // Leaderboard close button
    const btnClose = document.getElementById('btn_close');
    if (btnClose) btnClose.addEventListener('click', returnToMenu);
}

// Initialize game
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in init_order
    game_state.init();
    SnakeGame.init();
    InputControls.init();
    ui_screens.init();
    
    // Set up input handlers
    setupInputHandlers();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
});