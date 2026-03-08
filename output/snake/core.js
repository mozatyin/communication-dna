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

// Shared state objects
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

// Global constants
const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const GRID_SIZE = 20;
const INITIAL_SNAKE_LENGTH = 3;

// Game State Module
const game_state = (function() {
    function init() {
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.highScore = parseInt(localStorage.getItem('snakeHighScore')) || 0;
        GameState.gameSpeed = 200;
        
        // Listen for events from other modules
        EventBus.on('GAME_OVER', handleGameOver);
        EventBus.on('FOOD_EATEN', handleFoodEaten);
        
        updateHighScoreDisplay();
    }
    
    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            EventBus.emit('GAME_START', {});
            showScreen('gameplay');
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.gameStatus = 'game_over';
            
            // Update high score if needed
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
                localStorage.setItem('snakeHighScore', GameState.highScore);
            }
            
            updateFinalScore();
            showScreen('game_over');
        }
    }
    
    function retryGame() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            EventBus.emit('RETRY', {});
            showScreen('gameplay');
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
            updateLeaderboard();
            showScreen('leaderboard');
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
    
    function updateFinalScore() {
        const finalScore = document.getElementById('final_score');
        if (finalScore) finalScore.textContent = `最终得分: ${GameState.score}`;
    }
    
    function updateLeaderboard() {
        const scoreList = document.getElementById('score_list');
        if (scoreList) {
            scoreList.innerHTML = `
                1. 最高分: ${GameState.highScore}<br>
                2. ---<br>
                3. ---<br>
                4. ---<br>
                5. ---
            `;
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

// Snake Game Module
const snake_game = (function() {
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
        changeDirection(event.direction);
    }
    
    function update() {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        const currentTime = Date.now();
        if (currentTime - lastMoveTime < GameState.gameSpeed) {
            return;
        }
        
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
        const head = { ...SnakeState.snakeBody[0] };
        
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
            const points = 10;
            EventBus.emit('FOOD_EATEN', { points });
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
            if (head.x === SnakeState.snakeBody[i].x && head.y === SnakeState.snakeBody[i].y) {
                gameOver();
                return;
            }
        }
    }
    
    function gameOver() {
        EventBus.emit('GAME_OVER', { finalScore: GameState.score });
    }
    
    function spawnFood() {
        let newPosition;
        let validPosition = false;
        
        while (!validPosition) {
            newPosition = {
                x: Math.floor(Math.random() * SnakeState.gridWidth),
                y: Math.floor(Math.random() * SnakeState.gridHeight)
            };
            
            // Check if position overlaps with snake
            validPosition = true;
            for (const segment of SnakeState.snakeBody) {
                if (segment.x === newPosition.x && segment.y === newPosition.y) {
                    validPosition = false;
                    break;
                }
            }
        }
        
        SnakeState.foodPosition = newPosition;
    }
    
    function changeDirection(direction) {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        // Validate direction
        const validDirections = ['up', 'down', 'left', 'right'];
        if (!validDirections.includes(direction)) {
            return;
        }
        
        // Prevent reversing into self
        const opposites = {
            'up': 'down',
            'down': 'up',
            'left': 'right',
            'right': 'left'
        };
        
        if (direction === opposites[SnakeState.snakeDirection]) {
            return;
        }
        
        // Store direction to apply on next update
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
    
    return {
        init,
        update,
        changeDirection,
        resetGame
    };
})();

// Input Controls Module
const input_controls = (function() {
    let keysPressed = {};
    let lastDirectionSent = '';
    
    function init() {
        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('keyup', handleKeyUp);
    }
    
    function handleKeyDown(event) {
        keysPressed[event.key] = true;
        event.preventDefault();
    }
    
    function handleKeyUp(event) {
        keysPressed[event.key] = false;
        event.preventDefault();
    }
    
    function update() {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        let newDirection = '';
        
        // Check arrow keys and WASD
        if (keysPressed['ArrowUp'] || keysPressed['w'] || keysPressed['W']) {
            newDirection = 'up';
        } else if (keysPressed['ArrowDown'] || keysPressed['s'] || keysPressed['S']) {
            newDirection = 'down';
        } else if (keysPressed['ArrowLeft'] || keysPressed['a'] || keysPressed['A']) {
            newDirection = 'left';
        } else if (keysPressed['ArrowRight'] || keysPressed['d'] || keysPressed['D']) {
            newDirection = 'right';
        }
        
        // Only send direction change if it's different from last sent direction
        if (newDirection && newDirection !== lastDirectionSent) {
            EventBus.emit('DIRECTION_CHANGE', { direction: newDirection });
            lastDirectionSent = newDirection;
        }
    }
    
    return {
        init,
        update
    };
})();

// UI Screens Module
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
        if (GameState.gameStatus === 'gameplay' && canvas && ctx) {
            renderGameplay();
        }
    }

    function renderGameplay() {
        // Clear canvas
        ctx.fillStyle = '#1A1A1A';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const cellWidth = canvas.width / SnakeState.gridWidth;
        const cellHeight = canvas.height / SnakeState.gridHeight;

        // Draw grid
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

        // Draw snake
        ctx.fillStyle = '#4CAF50';
        for (let i = 0; i < SnakeState.snakeBody.length; i++) {
            const segment = SnakeState.snakeBody[i];
            ctx.fillRect(
                segment.x * cellWidth + 1,
                segment.y * cellHeight + 1,
                cellWidth - 2,
                cellHeight - 2
            );
        }

        // Draw food
        ctx.fillStyle = '#F44336';
        ctx.fillRect(
            SnakeState.foodPosition.x * cellWidth + 1,
            SnakeState.foodPosition.y * cellHeight + 1,
            cellWidth - 2,
            cellHeight - 2
        );
    }

    return {
        init,
        render
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
    
    // Update functions in order
    input_controls.update();
    snake_game.update();
    
    // Render functions in order
    ui_screens.render();
    
    if (GameState.gameStatus === 'playing' || GameState.gameStatus === 'gameplay') {
        requestAnimationFrame(gameLoop);
    }
}

// State transition functions
function startGame() {
    game_state.startGame();
    requestAnimationFrame(gameLoop);
}

function gameOver() {
    game_state.endGame();
}

function retry() {
    game_state.retryGame();
    requestAnimationFrame(gameLoop);
}

function returnToMenu() {
    game_state.returnToMenu();
}

function showLeaderboard() {
    game_state.showLeaderboard();
}

// Input handlers
function setupInputHandlers() {
    // Main menu
    const btnStart = document.getElementById('btn_start');
    if (btnStart) {
        btnStart.addEventListener('click', startGame);
    }
    
    // Game over screen
    const btnRetry = document.getElementById('btn_retry');
    if (btnRetry) {
        btnRetry.addEventListener('click', retry);
    }
    
    const btnMenu = document.getElementById('btn_menu');
    if (btnMenu) {
        btnMenu.addEventListener('click', returnToMenu);
    }
    
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    if (btnLeaderboard) {
        btnLeaderboard.addEventListener('click', showLeaderboard);
    }
    
    // Leaderboard screen
    const btnClose = document.getElementById('btn_close');
    if (btnClose) {
        btnClose.addEventListener('click', returnToMenu);
    }
    
    // D-pad controls
    const btnUp = document.getElementById('btn_up');
    if (btnUp) {
        btnUp.addEventListener('click', () => {
            EventBus.emit('DIRECTION_CHANGE', { direction: 'up' });
        });
    }
    
    const btnDown = document.getElementById('btn_down');
    if (btnDown) {
        btnDown.addEventListener('click', () => {
            EventBus.emit('DIRECTION_CHANGE', { direction: 'down' });
        });
    }
    
    const btnLeft = document.getElementById('btn_left');
    if (btnLeft) {
        btnLeft.addEventListener('click', () => {
            EventBus.emit('DIRECTION_CHANGE', { direction: 'left' });
        });
    }
    
    const btnRight = document.getElementById('btn_right');
    if (btnRight) {
        btnRight.addEventListener('click', () => {
            EventBus.emit('DIRECTION_CHANGE', { direction: 'right' });
        });
    }
}

// Initialize game
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in order
    game_state.init();
    snake_game.init();
    input_controls.init();
    ui_screens.init();
    
    // Setup input handlers
    setupInputHandlers();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
});