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
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.highScore = 0;
        GameState.gameSpeed = 200;
        
        // Listen for events from other modules
        document.addEventListener('GAME_OVER', handleGameOver);
        document.addEventListener('FOOD_EATEN', handleFoodEaten);
    }
    
    function handleGameOver(event) {
        if (GameState.gameStatus === 'gameplay') {
            endGame();
        }
    }
    
    function handleFoodEaten(event) {
        if (GameState.gameStatus === 'gameplay') {
            addScore(event.detail.points);
        }
    }
    
    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            // Emit GAME_START event
            const event = new CustomEvent('GAME_START', { detail: {} });
            document.dispatchEvent(event);
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.gameStatus = 'game_over';
            
            // Update high score if needed
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
            }
        }
    }
    
    function retryGame() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            
            // Emit RETRY event
            const event = new CustomEvent('RETRY', { detail: {} });
            document.dispatchEvent(event);
        }
    }
    
    function returnToMenu() {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
            
            // Emit RETURN_MENU event
            const event = new CustomEvent('RETURN_MENU', { detail: {} });
            document.dispatchEvent(event);
        }
    }
    
    function showLeaderboard() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            
            // Emit SHOW_LEADERBOARD event
            const event = new CustomEvent('SHOW_LEADERBOARD', { detail: {} });
            document.dispatchEvent(event);
        }
    }
    
    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
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
        document.addEventListener('GAME_START', handleGameStart);
        document.addEventListener('RETRY', handleRetry);
        document.addEventListener('DIRECTION_CHANGE', handleDirectionChange);
    }
    
    function handleGameStart() {
        resetGame();
    }
    
    function handleRetry() {
        resetGame();
    }
    
    function handleDirectionChange(event) {
        changeDirection(event.detail.direction);
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
        
        // Check if food was eaten
        if (head.x === SnakeState.foodPosition.x && head.y === SnakeState.foodPosition.y) {
            // Food eaten - don't remove tail, spawn new food, emit event
            spawnFood();
            document.dispatchEvent(new CustomEvent('FOOD_EATEN', {
                detail: { points: 10 }
            }));
        } else {
            // No food eaten - remove tail
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
        document.dispatchEvent(new CustomEvent('GAME_OVER', {
            detail: { finalScore: GameState.score }
        }));
    }
    
    function spawnFood() {
        let newPosition;
        let validPosition = false;
        
        while (!validPosition) {
            newPosition = {
                x: Math.floor(Math.random() * SnakeState.gridWidth),
                y: Math.floor(Math.random() * SnakeState.gridHeight)
            };
            
            // Check if position is not occupied by snake
            validPosition = true;
            for (let segment of SnakeState.snakeBody) {
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
        // Initialize snake in center of grid
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

// Module: input_controls
const InputControls = (function() {
    let keysPressed = {};
    let lastDirectionSent = null;
    let directionBuffer = null;

    function init() {
        // Register keyboard event listeners
        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('keyup', handleKeyUp);
        
        // Register touch/mouse events for mobile d-pad
        const dpadButtons = document.querySelectorAll('.dpad-btn');
        dpadButtons.forEach(btn => {
            btn.addEventListener('click', handleDpadClick);
            btn.addEventListener('touchstart', handleDpadTouch);
        });
    }

    function handleKeyDown(event) {
        keysPressed[event.code] = true;
        
        // Prevent default behavior for arrow keys
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.code)) {
            event.preventDefault();
        }
    }

    function handleKeyUp(event) {
        keysPressed[event.code] = false;
    }

    function handleDpadClick(event) {
        event.preventDefault();
        const direction = getDpadDirection(event.target.id);
        if (direction) {
            directionBuffer = direction;
        }
    }

    function handleDpadTouch(event) {
        event.preventDefault();
        const direction = getDpadDirection(event.target.id);
        if (direction) {
            directionBuffer = direction;
        }
    }

    function getDpadDirection(buttonId) {
        switch (buttonId) {
            case 'btn_up': return 'up';
            case 'btn_down': return 'down';
            case 'btn_left': return 'left';
            case 'btn_right': return 'right';
            default: return null;
        }
    }

    function update() {
        if (GameState.gameStatus !== 'gameplay') return;

        let newDirection = null;

        // Check keyboard input
        if (keysPressed['ArrowUp'] || keysPressed['KeyW']) {
            newDirection = 'up';
        } else if (keysPressed['ArrowDown'] || keysPressed['KeyS']) {
            newDirection = 'down';
        } else if (keysPressed['ArrowLeft'] || keysPressed['KeyA']) {
            newDirection = 'left';
        } else if (keysPressed['ArrowRight'] || keysPressed['KeyD']) {
            newDirection = 'right';
        }

        // Check buffered direction from touch/click
        if (directionBuffer) {
            newDirection = directionBuffer;
            directionBuffer = null;
        }

        // Send direction change if we have a new direction and it's different from last sent
        if (newDirection && newDirection !== lastDirectionSent) {
            // Emit DIRECTION_CHANGE event
            const event = new CustomEvent('DIRECTION_CHANGE', {
                detail: { direction: newDirection }
            });
            document.dispatchEvent(event);
            
            // Also call snake_game.changeDirection directly
            if (typeof SnakeGame !== 'undefined' && SnakeGame.changeDirection) {
                SnakeGame.changeDirection(newDirection);
            }
            
            lastDirectionSent = newDirection;
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
        updateUI();
        
        if (!canvas || !ctx) return;

        // Clear canvas
        ctx.fillStyle = '#111';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        if (GameState.gameStatus === 'gameplay') {
            renderGameplay();
        }
    }

    function updateUI() {
        // Update score displays
        const scoreDisplay = document.getElementById('score_display');
        const bestDisplay = document.getElementById('best_display');
        const highScore = document.getElementById('high_score');
        const finalScore = document.getElementById('final_score');
        const finalBest = document.getElementById('final_best');

        if (scoreDisplay) scoreDisplay.textContent = `分数: ${GameState.score}`;
        if (bestDisplay) bestDisplay.textContent = `最高: ${GameState.highScore}`;
        if (highScore) highScore.textContent = `最高分: ${GameState.highScore}`;
        if (finalScore) finalScore.textContent = `最终分数: ${GameState.score}`;
        if (finalBest) finalBest.textContent = `最高分: ${GameState.highScore}`;
    }

    function renderGameplay() {
        if (!ctx) return;

        // Grid lines
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 1;
        for (let i = 0; i <= SnakeState.gridWidth; i++) {
            ctx.beginPath();
            ctx.moveTo(i * GRID_SIZE, 0);
            ctx.lineTo(i * GRID_SIZE, SnakeState.gridHeight * GRID_SIZE);
            ctx.stroke();
        }
        for (let i = 0; i <= SnakeState.gridHeight; i++) {
            ctx.beginPath();
            ctx.moveTo(0, i * GRID_SIZE);
            ctx.lineTo(SnakeState.gridWidth * GRID_SIZE, i * GRID_SIZE);
            ctx.stroke();
        }

        // Snake
        ctx.fillStyle = '#4CAF50';
        for (let i = 0; i < SnakeState.snakeBody.length; i++) {
            const segment = SnakeState.snakeBody[i];
            ctx.fillRect(
                segment.x * GRID_SIZE + 1,
                segment.y * GRID_SIZE + 1,
                GRID_SIZE - 2,
                GRID_SIZE - 2
            );
        }

        // Snake head (different color)
        if (SnakeState.snakeBody.length > 0) {
            const head = SnakeState.snakeBody[0];
            ctx.fillStyle = '#8BC34A';
            ctx.fillRect(
                head.x * GRID_SIZE + 1,
                head.y * GRID_SIZE + 1,
                GRID_SIZE - 2,
                GRID_SIZE - 2
            );
        }

        // Food
        ctx.fillStyle = '#F44336';
        ctx.fillRect(
            SnakeState.foodPosition.x * GRID_SIZE + 1,
            SnakeState.foodPosition.y * GRID_SIZE + 1,
            GRID_SIZE - 2,
            GRID_SIZE - 2
        );
    }

    function handleClick(x, y) {
        // Handled by individual button event listeners
    }

    return {
        init,
        render,
        handleClick
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

// Game Loop
let lastTime = 0;
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions in order
    InputControls.update();
    SnakeGame.update();
    
    // Render functions in order
    ui_screens.render();
    
    if (GameState.gameStatus === 'playing' || GameState.gameStatus === 'gameplay') {
        requestAnimationFrame(gameLoop);
    } else {
        // Continue loop for other states too
        requestAnimationFrame(gameLoop);
    }
}

// State Transition Functions
function startGame() {
    game_state.startGame();
    showScreen('gameplay');
}

function gameOver() {
    showScreen('game_over');
}

function retryGame() {
    game_state.retryGame();
    showScreen('gameplay');
}

function returnToMenu() {
    game_state.returnToMenu();
    showScreen('main_menu');
}

// Input Handlers and Screen Navigation
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in order
    game_state.init();
    SnakeGame.init();
    InputControls.init();
    ui_screens.init();
    
    // Set up button event listeners
    const btnStart = document.getElementById('btn_start');
    const btnRetry = document.getElementById('btn_retry');
    const btnMenu = document.getElementById('btn_menu');
    
    if (btnStart) {
        btnStart.addEventListener('click', startGame);
    }
    
    if (btnRetry) {
        btnRetry.addEventListener('click', retryGame);
    }
    
    if (btnMenu) {
        btnMenu.addEventListener('click', returnToMenu);
    }
    
    // Listen for state changes to update screens
    document.addEventListener('GAME_START', () => showScreen('gameplay'));
    document.addEventListener('GAME_OVER', () => showScreen('game_over'));
    document.addEventListener('RETRY', () => showScreen('gameplay'));
    document.addEventListener('RETURN_MENU', () => showScreen('main_menu'));
    
    // Start with main menu
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
});