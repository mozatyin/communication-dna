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

// Module Code (concatenated exactly as provided)
const game_state = (function() {
    let eventListeners = [];

    function init() {
        // Load high score from localStorage
        const savedHighScore = localStorage.getItem('snakeHighScore');
        if (savedHighScore) {
            GameState.highScore = parseInt(savedHighScore, 10);
        }

        // Set up event listeners
        setupEventListeners();
        updateHighScoreDisplay();
    }

    function setupEventListeners() {
        EventBus.on('GAME_OVER', function(data) {
            if (GameState.gameStatus === 'gameplay') {
                endGame();
            }
        });

        EventBus.on('FOOD_EATEN', function(data) {
            if (GameState.gameStatus === 'gameplay' && data && data.points) {
                addScore(data.points);
            }
        });
    }

    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            EventBus.emit('GAME_START', {});
            showScreen('gameplay');
            updateScoreDisplay();
        }
    }

    function endGame() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.gameStatus = 'game_over';
            
            // Update high score if current score is higher
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
                localStorage.setItem('snakeHighScore', GameState.highScore.toString());
                updateHighScoreDisplay();
            }
            
            // Save score to leaderboard
            saveScoreToLeaderboard(GameState.score);
            
            showScreen('game_over');
            updateFinalScoreDisplay();
        }
    }

    function retryGame() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            EventBus.emit('RETRY', {});
            showScreen('gameplay');
            updateScoreDisplay();
        }
    }

    function returnToMenu() {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
            
            EventBus.emit('RETURN_MENU', {});
            showScreen('main_menu');
        }
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            
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

    function updateScoreDisplay() {
        const scoreDisplay = document.getElementById('score_display');
        const bestDisplay = document.getElementById('best_display');
        if (scoreDisplay) scoreDisplay.textContent = `分数: ${GameState.score}`;
        if (bestDisplay) bestDisplay.textContent = `最高: ${GameState.highScore}`;
    }

    function updateHighScoreDisplay() {
        const highScoreEl = document.getElementById('high_score');
        if (highScoreEl) highScoreEl.textContent = `最高分: ${GameState.highScore}`;
    }

    function updateFinalScoreDisplay() {
        const finalScoreEl = document.getElementById('final_score');
        if (finalScoreEl) finalScoreEl.textContent = `最终分数: ${GameState.score}`;
    }

    function saveScoreToLeaderboard(score) {
        let scores = JSON.parse(localStorage.getItem('snakeScores') || '[]');
        scores.push({score: score, date: new Date().toISOString()});
        scores.sort((a, b) => b.score - a.score);
        scores = scores.slice(0, 5); // Keep top 5
        localStorage.setItem('snakeScores', JSON.stringify(scores));
    }

    function updateLeaderboardDisplay() {
        const scoreListEl = document.getElementById('score_list');
        if (!scoreListEl) return;
        
        const scores = JSON.parse(localStorage.getItem('snakeScores') || '[]');
        let html = '';
        
        for (let i = 0; i < 5; i++) {
            if (i < scores.length) {
                html += `${i + 1}. ${scores[i].score}<br>`;
            } else {
                html += `${i + 1}. 暂无记录<br>`;
            }
        }
        
        scoreListEl.innerHTML = html;
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

const snake_game = (function() {
    let lastMoveTime = 0;
    let nextDirection = null;
    
    function init() {
        // Initialize snake body with initial length
        SnakeState.snakeBody = [];
        for (let i = 0; i < INITIAL_SNAKE_LENGTH; i++) {
            SnakeState.snakeBody.push({
                x: Math.floor(SnakeState.gridWidth / 2) - i,
                y: Math.floor(SnakeState.gridHeight / 2)
            });
        }
        
        SnakeState.snakeDirection = 'right';
        nextDirection = null;
        
        // Spawn initial food
        spawnFood();
        
        // Listen for events
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('DIRECTION_CHANGE', handleDirectionChange);
    }
    
    function update() {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        const currentTime = Date.now();
        if (currentTime - lastMoveTime < GameState.gameSpeed) {
            return;
        }
        
        // Apply queued direction change if valid
        if (nextDirection && isValidDirectionChange(nextDirection)) {
            SnakeState.snakeDirection = nextDirection;
            nextDirection = null;
        }
        
        // Move snake
        moveSnake();
        
        // Check collisions
        checkCollisions();
        
        lastMoveTime = currentTime;
    }
    
    function moveSnake() {
        const head = {...SnakeState.snakeBody[0]};
        
        // Calculate new head position based on direction
        switch (SnakeState.snakeDirection) {
            case 'up':
                head.y--;
                break;
            case 'down':
                head.y++;
                break;
            case 'left':
                head.x--;
                break;
            case 'right':
                head.x++;
                break;
        }
        
        // Add new head
        SnakeState.snakeBody.unshift(head);
        
        // Check if food was eaten
        if (head.x === SnakeState.foodPosition.x && head.y === SnakeState.foodPosition.y) {
            // Snake grows (don't remove tail)
            spawnFood();
            
            // Emit food eaten event
            EventBus.emit('FOOD_EATEN', { points: 10 });
        } else {
            // Remove tail (normal movement)
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
    
    function spawnFood() {
        let validPosition = false;
        let newFoodPosition;
        
        // Keep trying until we find a position not occupied by snake
        while (!validPosition) {
            newFoodPosition = {
                x: Math.floor(Math.random() * SnakeState.gridWidth),
                y: Math.floor(Math.random() * SnakeState.gridHeight)
            };
            
            validPosition = true;
            for (let segment of SnakeState.snakeBody) {
                if (segment.x === newFoodPosition.x && segment.y === newFoodPosition.y) {
                    validPosition = false;
                    break;
                }
            }
        }
        
        SnakeState.foodPosition = newFoodPosition;
    }
    
    function gameOver() {
        EventBus.emit('GAME_OVER', { finalScore: GameState.score });
    }
    
    function changeDirection(direction) {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        if (!isValidDirection(direction)) {
            return;
        }
        
        // Queue the direction change to prevent rapid direction changes
        nextDirection = direction;
    }
    
    function isValidDirection(direction) {
        return ['up', 'down', 'left', 'right'].includes(direction);
    }
    
    function isValidDirectionChange(newDirection) {
        // Can't reverse direction immediately
        const opposites = {
            'up': 'down',
            'down': 'up',
            'left': 'right',
            'right': 'left'
        };
        
        return opposites[SnakeState.snakeDirection] !== newDirection;
    }
    
    function resetGame() {
        // Reset snake to initial state
        SnakeState.snakeBody = [];
        for (let i = 0; i < INITIAL_SNAKE_LENGTH; i++) {
            SnakeState.snakeBody.push({
                x: Math.floor(SnakeState.gridWidth / 2) - i,
                y: Math.floor(SnakeState.gridHeight / 2)
            });
        }
        
        SnakeState.snakeDirection = 'right';
        nextDirection = null;
        lastMoveTime = 0;
        
        // Spawn new food
        spawnFood();
    }
    
    function handleGameStart(event) {
        resetGame();
    }
    
    function handleRetry(event) {
        resetGame();
    }
    
    function handleDirectionChange(event) {
        changeDirection(event.direction);
    }
    
    return {
        init,
        update,
        changeDirection,
        resetGame
    };
})();

const InputControls = (function() {
    let keysPressed = {};
    let lastDirectionChange = 0;
    const DIRECTION_COOLDOWN = 100;

    function init() {
        // Register keyboard event listeners
        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('keyup', handleKeyUp);
        
        // Register touch event listeners for mobile d-pad
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
            
            // Minimum swipe distance to register
            const minSwipeDistance = 30;
            
            if (Math.abs(dx) > minSwipeDistance || Math.abs(dy) > minSwipeDistance) {
                let direction = '';
                
                if (Math.abs(dx) > Math.abs(dy)) {
                    // Horizontal swipe
                    direction = dx > 0 ? 'right' : 'left';
                } else {
                    // Vertical swipe
                    direction = dy > 0 ? 'down' : 'up';
                }
                
                if (direction && canChangeDirection()) {
                    emitDirectionChange(direction);
                }
            }
        });

        // Add click handlers for control buttons
        document.getElementById('btn_up').addEventListener('click', () => emitDirectionChange('up'));
        document.getElementById('btn_down').addEventListener('click', () => emitDirectionChange('down'));
        document.getElementById('btn_left').addEventListener('click', () => emitDirectionChange('left'));
        document.getElementById('btn_right').addEventListener('click', () => emitDirectionChange('right'));
    }

    function handleKeyDown(e) {
        keysPressed[e.key] = true;
        
        // Prevent default behavior for arrow keys and WASD
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'a', 's', 'd'].includes(e.key)) {
            e.preventDefault();
        }
    }

    function handleKeyUp(e) {
        keysPressed[e.key] = false;
    }

    function canChangeDirection() {
        const now = Date.now();
        return now - lastDirectionChange > DIRECTION_COOLDOWN;
    }

    function emitDirectionChange(direction) {
        EventBus.emit('DIRECTION_CHANGE', { direction: direction });
        lastDirectionChange = Date.now();
    }

    function update() {
        // Only process input during gameplay
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }

        if (!canChangeDirection()) {
            return;
        }

        let newDirection = '';

        // Check arrow keys
        if (keysPressed['ArrowUp'] || keysPressed['w'] || keysPressed['W']) {
            newDirection = 'up';
        } else if (keysPressed['ArrowDown'] || keysPressed['s'] || keysPressed['S']) {
            newDirection = 'down';
        } else if (keysPressed['ArrowLeft'] || keysPressed['a'] || keysPressed['A']) {
            newDirection = 'left';
        } else if (keysPressed['ArrowRight'] || keysPressed['d'] || keysPressed['D']) {
            newDirection = 'right';
        }

        if (newDirection) {
            emitDirectionChange(newDirection);
        }
    }

    return {
        init,
        update
    };
})();

const ui_screens = (function() {
    let canvas;
    let ctx;
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        ctx = canvas.getContext('2d');
    }
    
    function render() {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        // Clear canvas
        ctx.fillStyle = '#1A1A1A';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        renderGameplay();
    }
    
    function renderGameplay() {
        // Draw grid background
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 1;
        
        const cellSize = GRID_SIZE;
        const gridOffsetX = (CANVAS_WIDTH - SnakeState.gridWidth * cellSize) / 2;
        const gridOffsetY = (CANVAS_HEIGHT - SnakeState.gridHeight * cellSize) / 2;
        
        // Grid lines
        for (let x = 0; x <= SnakeState.gridWidth; x++) {
            ctx.beginPath();
            ctx.moveTo(gridOffsetX + x * cellSize, gridOffsetY);
            ctx.lineTo(gridOffsetX + x * cellSize, gridOffsetY + SnakeState.gridHeight * cellSize);
            ctx.stroke();
        }
        
        for (let y = 0; y <= SnakeState.gridHeight; y++) {
            ctx.beginPath();
            ctx.moveTo(gridOffsetX, gridOffsetY + y * cellSize);
            ctx.lineTo(gridOffsetX + SnakeState.gridWidth * cellSize, gridOffsetY + y * cellSize);
            ctx.stroke();
        }
        
        // Draw food
        ctx.fillStyle = '#ff0000';
        ctx.fillRect(
            gridOffsetX + SnakeState.foodPosition.x * cellSize + 1,
            gridOffsetY + SnakeState.foodPosition.y * cellSize + 1,
            cellSize - 2,
            cellSize - 2
        );
        
        // Draw snake
        for (let i = 0; i < SnakeState.snakeBody.length; i++) {
            const segment = SnakeState.snakeBody[i];
            if (i === 0) {
                // Head - slightly different color
                ctx.fillStyle = '#00aa00';
            } else {
                ctx.fillStyle = '#00ff00';
            }
            ctx.fillRect(
                gridOffsetX + segment.x * cellSize + 1,
                gridOffsetY + segment.y * cellSize + 1,
                cellSize - 2,
                cellSize - 2
            );
        }
    }
    
    return {
        init,
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
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Call update functions in update_order
    InputControls.update();
    snake_game.update();
    
    // Call render functions in render_order
    ui_screens.render();
    
    if (GameState.gameStatus === 'playing' || GameState.gameStatus === 'gameplay') {
        requestAnimationFrame(gameLoop);
    } else {
        // Continue loop for input handling even when not playing
        requestAnimationFrame(gameLoop);
    }
}

// Initialize modules in init_order
function initGame() {
    game_state.init();
    snake_game.init();
    InputControls.init();
    ui_screens.init();
    
    // Set up screen navigation
    document.getElementById('btn_start').addEventListener('click', () => {
        game_state.startGame();
    });
    
    document.getElementById('btn_retry').addEventListener('click', () => {
        game_state.retryGame();
    });
    
    document.getElementById('btn_menu').addEventListener('click', () => {
        game_state.returnToMenu();
    });
    
    document.getElementById('btn_leaderboard').addEventListener('click', () => {
        game_state.showLeaderboard();
    });
    
    document.getElementById('btn_close').addEventListener('click', () => {
        game_state.returnToMenu();
    });
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

// Start the game when page loads
document.addEventListener('DOMContentLoaded', initGame);