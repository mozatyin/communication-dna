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
const GRID_WIDTH = 10;
const GRID_HEIGHT = 20;
const BLOCK_SIZE = 40;
const DROP_SPEED_BASE = 1000;
const POINTS_SINGLE = 100;
const POINTS_DOUBLE = 300;
const POINTS_TRIPLE = 500;
const POINTS_TETRIS = 800;

// Shared state objects
const GameState = {
    gameStatus: 'main_menu',
    score: 0,
    level: 1,
    linesCleared: 0,
    isPaused: false
};

const TetrisGrid = {
    grid: [],
    currentPiece: null,
    nextPiece: null,
    dropTimer: 0
};

const HighScores = {
    scores: []
};

// Module code
const GameStateModule = (function() {
    let eventBus;

    function init() {
        // Initialize GameState with default values
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.level = 1;
        GameState.linesCleared = 0;
        GameState.isPaused = false;

        // Initialize HighScores with default values
        HighScores.scores = loadHighScores();

        // Set up event bus reference
        eventBus = EventBus;
    }

    function loadHighScores() {
        try {
            const saved = localStorage.getItem('tetris_high_scores');
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            return [];
        }
    }

    function saveHighScores() {
        try {
            localStorage.setItem('tetris_high_scores', JSON.stringify(HighScores.scores));
        } catch (e) {
            // Ignore storage errors
        }
    }

    function updateHighScore(score) {
        const scores = HighScores.scores;
        scores.push(score);
        scores.sort((a, b) => b - a);
        if (scores.length > 5) {
            scores.splice(5);
        }
        saveHighScores();
    }

    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            GameState.level = 1;
            GameState.linesCleared = 0;
            GameState.isPaused = false;
            
            eventBus.emit('GAME_START', {});
        }
    }

    function endGame() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.gameStatus = 'game_over';
            updateHighScore(GameState.score);
        }
    }

    function retryGame() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            GameState.level = 1;
            GameState.linesCleared = 0;
            GameState.isPaused = false;
            
            eventBus.emit('RETRY', {});
        }
    }

    function returnToMenu() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'main_menu';
            eventBus.emit('RETURN_MENU', {});
        }
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'main_menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            eventBus.emit('SHOW_LEADERBOARD', {});
        }
    }

    function closeLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
            eventBus.emit('CLOSE_LEADERBOARD', {});
        }
    }

    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
        }
    }

    function addLines(lines) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.linesCleared += lines;
            
            // Update level based on lines cleared (every 10 lines)
            const newLevel = Math.floor(GameState.linesCleared / 10) + 1;
            if (newLevel > GameState.level) {
                GameState.level = newLevel;
                eventBus.emit('LEVEL_UP', { newLevel: GameState.level });
            }
        }
    }

    // Listen for GAME_OVER event from tetris_engine
    EventBus.on('GAME_OVER', function(payload) {
        endGame();
    });

    // Listen for LINES_CLEARED event from tetris_engine
    EventBus.on('LINES_CLEARED', function(payload) {
        addLines(payload.lines);
        addScore(payload.points);
    });

    return {
        init,
        startGame,
        endGame,
        retryGame,
        returnToMenu,
        showLeaderboard,
        closeLeaderboard,
        addScore,
        addLines
    };
})();

const TetrisEngine = (function() {
    // Tetromino definitions
    const TETROMINOES = {
        I: {
            shape: [
                [0, 0, 0, 0],
                [1, 1, 1, 1],
                [0, 0, 0, 0],
                [0, 0, 0, 0]
            ],
            color: '#00FFFF'
        },
        O: {
            shape: [
                [1, 1],
                [1, 1]
            ],
            color: '#FFFF00'
        },
        T: {
            shape: [
                [0, 1, 0],
                [1, 1, 1],
                [0, 0, 0]
            ],
            color: '#800080'
        },
        S: {
            shape: [
                [0, 1, 1],
                [1, 1, 0],
                [0, 0, 0]
            ],
            color: '#00FF00'
        },
        Z: {
            shape: [
                [1, 1, 0],
                [0, 1, 1],
                [0, 0, 0]
            ],
            color: '#FF0000'
        },
        J: {
            shape: [
                [1, 0, 0],
                [1, 1, 1],
                [0, 0, 0]
            ],
            color: '#0000FF'
        },
        L: {
            shape: [
                [0, 0, 1],
                [1, 1, 1],
                [0, 0, 0]
            ],
            color: '#FFA500'
        }
    };

    const TETROMINO_TYPES = Object.keys(TETROMINOES);
    let lastDropTime = 0;

    function init() {
        // Initialize grid
        TetrisGrid.grid = [];
        for (let y = 0; y < GRID_HEIGHT; y++) {
            TetrisGrid.grid[y] = [];
            for (let x = 0; x < GRID_WIDTH; x++) {
                TetrisGrid.grid[y][x] = 0;
            }
        }

        TetrisGrid.currentPiece = null;
        TetrisGrid.nextPiece = null;
        TetrisGrid.dropTimer = 0;
        lastDropTime = 0;

        // Listen for game events
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('LEVEL_UP', handleLevelUp);
    }

    function handleGameStart() {
        resetGame();
    }

    function handleRetry() {
        resetGame();
    }

    function handleLevelUp(payload) {
        // Level up handled by game_state module
    }

    function resetGame() {
        // Clear grid
        for (let y = 0; y < GRID_HEIGHT; y++) {
            for (let x = 0; x < GRID_WIDTH; x++) {
                TetrisGrid.grid[y][x] = 0;
            }
        }

        // Generate first pieces
        TetrisGrid.nextPiece = generateRandomPiece();
        spawnNextPiece();
        TetrisGrid.dropTimer = 0;
        lastDropTime = Date.now();
    }

    function generateRandomPiece() {
        const type = TETROMINO_TYPES[Math.floor(Math.random() * TETROMINO_TYPES.length)];
        const tetromino = TETROMINOES[type];
        
        return {
            type: type,
            shape: tetromino.shape.map(row => [...row]),
            color: tetromino.color,
            x: Math.floor(GRID_WIDTH / 2) - Math.floor(tetromino.shape[0].length / 2),
            y: 0
        };
    }

    function spawnNextPiece() {
        TetrisGrid.currentPiece = TetrisGrid.nextPiece;
        TetrisGrid.nextPiece = generateRandomPiece();

        // Check if spawn position is blocked (game over condition)
        if (TetrisGrid.currentPiece && isCollision(TetrisGrid.currentPiece, 0, 0)) {
            // Trigger game over
            EventBus.emit('GAME_OVER', {
                finalScore: GameState.score,
                finalLevel: GameState.level,
                finalLines: GameState.linesCleared
            });
        }
    }

    function update() {
        if (GameState.gameStatus !== 'gameplay' || GameState.isPaused) {
            return;
        }

        const currentTime = Date.now();
        const dropSpeed = Math.max(50, DROP_SPEED_BASE - (GameState.level - 1) * 50);

        if (currentTime - lastDropTime > dropSpeed) {
            if (TetrisGrid.currentPiece) {
                if (!movePiece('down')) {
                    lockPiece();
                    clearLines();
                    spawnNextPiece();
                }
            }
            lastDropTime = currentTime;
        }
    }

    function movePiece(direction) {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return false;
        }

        let dx = 0, dy = 0;
        
        switch (direction) {
            case 'left':
                dx = -1;
                break;
            case 'right':
                dx = 1;
                break;
            case 'down':
                dy = 1;
                break;
            default:
                return false;
        }

        if (!isCollision(TetrisGrid.currentPiece, dx, dy)) {
            TetrisGrid.currentPiece.x += dx;
            TetrisGrid.currentPiece.y += dy;
            return true;
        }

        return false;
    }

    function rotatePiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return false;
        }

        const rotatedShape = rotateMatrix(TetrisGrid.currentPiece.shape);
        const originalShape = TetrisGrid.currentPiece.shape;
        
        TetrisGrid.currentPiece.shape = rotatedShape;
        
        if (isCollision(TetrisGrid.currentPiece, 0, 0)) {
            // Try wall kicks
            const kicks = [
                [-1, 0], [1, 0], [0, -1], [-2, 0], [2, 0]
            ];
            
            let kicked = false;
            for (const [kickX, kickY] of kicks) {
                if (!isCollision(TetrisGrid.currentPiece, kickX, kickY)) {
                    TetrisGrid.currentPiece.x += kickX;
                    TetrisGrid.currentPiece.y += kickY;
                    kicked = true;
                    break;
                }
            }
            
            if (!kicked) {
                TetrisGrid.currentPiece.shape = originalShape;
                return false;
            }
        }
        
        return true;
    }

    function dropPiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return;
        }

        while (movePiece('down')) {
            // Keep dropping until collision
        }
        
        lockPiece();
        clearLines();
        spawnNextPiece();
    }

    function rotateMatrix(matrix) {
        const rows = matrix.length;
        const cols = matrix[0].length;
        const rotated = [];
        
        for (let i = 0; i < cols; i++) {
            rotated[i] = [];
            for (let j = 0; j < rows; j++) {
                rotated[i][j] = matrix[rows - 1 - j][i];
            }
        }
        
        return rotated;
    }

    function isCollision(piece, dx, dy) {
        const newX = piece.x + dx;
        const newY = piece.y + dy;
        
        for (let y = 0; y < piece.shape.length; y++) {
            for (let x = 0; x < piece.shape[y].length; x++) {
                if (piece.shape[y][x]) {
                    const gridX = newX + x;
                    const gridY = newY + y;
                    
                    // Check boundaries
                    if (gridX < 0 || gridX >= GRID_WIDTH || gridY >= GRID_HEIGHT) {
                        return true;
                    }
                    
                    // Check collision with placed blocks (but allow negative Y for spawning)
                    if (gridY >= 0 && TetrisGrid.grid[gridY][gridX]) {
                        return true;
                    }
                }
            }
        }
        
        return false;
    }

    function lockPiece() {
        if (!TetrisGrid.currentPiece) return;
        
        for (let y = 0; y < TetrisGrid.currentPiece.shape.length; y++) {
            for (let x = 0; x < TetrisGrid.currentPiece.shape[y].length; x++) {
                if (TetrisGrid.currentPiece.shape[y][x]) {
                    const gridX = TetrisGrid.currentPiece.x + x;
                    const gridY = TetrisGrid.currentPiece.y + y;
                    
                    if (gridY >= 0 && gridY < GRID_HEIGHT && gridX >= 0 && gridX < GRID_WIDTH) {
                        TetrisGrid.grid[gridY][gridX] = TetrisGrid.currentPiece.color;
                    }
                }
            }
        }
    }

    function clearLines() {
        let linesCleared = 0;
        
        for (let y = GRID_HEIGHT - 1; y >= 0; y--) {
            let isLineFull = true;
            
            for (let x = 0; x < GRID_WIDTH; x++) {
                if (!TetrisGrid.grid[y][x]) {
                    isLineFull = false;
                    break;
                }
            }
            
            if (isLineFull) {
                // Remove the line
                TetrisGrid.grid.splice(y, 1);
                // Add empty line at top
                const emptyLine = new Array(GRID_WIDTH).fill(0);
                TetrisGrid.grid.unshift(emptyLine);
                
                linesCleared++;
                y++; // Check the same row again since we shifted everything down
            }
        }
        
        if (linesCleared > 0) {
            // Calculate points based on lines cleared
            let points = 0;
            switch (linesCleared) {
                case 1:
                    points = POINTS_SINGLE;
                    break;
                case 2:
                    points = POINTS_DOUBLE;
                    break;
                case 3:
                    points = POINTS_TRIPLE;
                    break;
                case 4:
                    points = POINTS_TETRIS;
                    break;
            }
            
            // Emit lines cleared event
            EventBus.emit('LINES_CLEARED', {
                lines: linesCleared,
                points: points * GameState.level
            });
        }
    }

    function getGrid() {
        return TetrisGrid.grid;
    }

    function getCurrentPiece() {
        return TetrisGrid.currentPiece;
    }

    function getNextPiece() {
        return TetrisGrid.nextPiece;
    }

    return {
        init,
        update,
        movePiece,
        rotatePiece,
        dropPiece,
        getGrid,
        getCurrentPiece,
        getNextPiece
    };
})();

const UIManager = (function() {
    let canvas;
    let ctx;
    
    // UI element definitions
    const buttons = {
        mainMenu: {
            start: { x: 340, y: 1200, width: 400, height: 120 },
            leaderboard: { x: 340, y: 1400, width: 400, height: 120 }
        },
        gameOver: {
            retry: { x: 240, y: 1400, width: 200, height: 100 },
            menu: { x: 480, y: 1400, width: 200, height: 100 },
            leaderboard: { x: 340, y: 1550, width: 400, height: 100 }
        },
        leaderboard: {
            close: { x: 340, y: 1600, width: 400, height: 100 }
        }
    };
    
    // Colors
    const colors = {
        background: '#000011',
        neon: '#00FFFF',
        white: '#FFFFFF',
        gray: '#888888',
        darkGray: '#333333',
        red: '#FF0000',
        green: '#00FF00',
        blue: '#0000FF',
        yellow: '#FFFF00',
        orange: '#FF8800',
        purple: '#8800FF',
        pink: '#FF00FF'
    };
    
    const pieceColors = {
        'I': colors.neon,
        'O': colors.yellow,
        'T': colors.purple,
        'S': colors.green,
        'Z': colors.red,
        'J': colors.blue,
        'L': colors.orange
    };
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        if (canvas) {
            ctx = canvas.getContext('2d');
            canvas.width = CANVAS_WIDTH;
            canvas.height = CANVAS_HEIGHT;
        }
    }
    
    function render() {
        updateUI();
        
        if (!canvas || !ctx) return;
        
        // Clear canvas
        ctx.fillStyle = colors.background;
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        if (GameState.gameStatus === 'gameplay') {
            renderGameplay();
        }
    }
    
    function updateUI() {
        // Update high score display
        const highScoreEl = document.getElementById('high_score');
        if (highScoreEl && HighScores.scores.length > 0) {
            highScoreEl.textContent = `最高分: ${HighScores.scores[0]}`;
        }
        
        // Update gameplay UI
        const scoreEl = document.getElementById('score_value');
        if (scoreEl) scoreEl.textContent = GameState.score;
        
        const levelEl = document.getElementById('level_value');
        if (levelEl) levelEl.textContent = GameState.level;
        
        const linesEl = document.getElementById('lines_value');
        if (linesEl) linesEl.textContent = GameState.linesCleared;
        
        // Update game over UI
        const finalScoreEl = document.getElementById('final_score');
        if (finalScoreEl) finalScoreEl.textContent = `最终得分: ${GameState.score}`;
        
        const finalLinesEl = document.getElementById('final_lines');
        if (finalLinesEl) finalLinesEl.textContent = `消除行数: ${GameState.linesCleared}`;
        
        // Update leaderboard
        const scoreListEl = document.getElementById('score_list');
        if (scoreListEl) {
            const scores = HighScores.scores.slice(0, 5);
            scoreListEl.innerHTML = '';
            for (let i = 0; i < 5; i++) {
                const div = document.createElement('div');
                const rank = i + 1;
                const score = scores[i] || '---';
                div.innerHTML = `<span>${rank}.</span><span>${score}</span>`;
                scoreListEl.appendChild(div);
            }
        }
    }
    
    function renderGameplay() {
        if (!ctx) return;
        
        // Game grid background
        const gridX = (CANVAS_WIDTH - GRID_WIDTH * BLOCK_SIZE) / 2;
        const gridY = 200;
        
        ctx.strokeStyle = colors.darkGray;
        ctx.lineWidth = 1;
        
        // Draw grid lines
        for (let x = 0; x <= GRID_WIDTH; x++) {
            ctx.beginPath();
            ctx.moveTo(gridX + x * BLOCK_SIZE, gridY);
            ctx.lineTo(gridX + x * BLOCK_SIZE, gridY + GRID_HEIGHT * BLOCK_SIZE);
            ctx.stroke();
        }
        
        for (let y = 0; y <= GRID_HEIGHT; y++) {
            ctx.beginPath();
            ctx.moveTo(gridX, gridY + y * BLOCK_SIZE);
            ctx.lineTo(gridX + GRID_WIDTH * BLOCK_SIZE, gridY + y * BLOCK_SIZE);
            ctx.stroke();
        }
        
        // Draw placed blocks
        if (TetrisGrid.grid && TetrisGrid.grid.length > 0) {
            for (let y = 0; y < GRID_HEIGHT; y++) {
                for (let x = 0; x < GRID_WIDTH; x++) {
                    if (TetrisGrid.grid[y] && TetrisGrid.grid[y][x]) {
                        const blockType = TetrisGrid.grid[y][x];
                        drawBlock(gridX + x * BLOCK_SIZE, gridY + y * BLOCK_SIZE, blockType);
                    }
                }
            }
        }
        
        // Draw current piece
        if (TetrisGrid.currentPiece) {
            const piece = TetrisGrid.currentPiece;
            const color = piece.color;
            
            for (let y = 0; y < piece.shape.length; y++) {
                for (let x = 0; x < piece.shape[y].length; x++) {
                    if (piece.shape[y][x]) {
                        const blockX = gridX + (piece.x + x) * BLOCK_SIZE;
                        const blockY = gridY + (piece.y + y) * BLOCK_SIZE;
                        drawBlock(blockX, blockY, color);
                    }
                }
            }
        }
    }
    
    function drawBlock(x, y, color, size = BLOCK_SIZE) {
        if (!ctx) return;
        
        // Block fill
        ctx.fillStyle = color;
        ctx.fillRect(x, y, size, size);
        
        // Block border
        ctx.strokeStyle = colors.white;
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, size, size);
    }
    
    function handleMenuClick(x, y) {
        return '';
    }
    
    function handleGameOverClick(x, y) {
        return '';
    }
    
    function handleLeaderboardClick(x, y) {
        return '';
    }
    
    return {
        init,
        render,
        handleMenuClick,
        handleGameOverClick,
        handleLeaderboardClick
    };
})();

const InputController = (function() {
    let keysPressed = {};
    let keyRepeatTimers = {};
    let lastMoveTime = 0;
    let lastDropTime = 0;
    
    const REPEAT_DELAY = 150; // ms before key repeat starts
    const REPEAT_RATE = 50;   // ms between repeats
    const MOVE_THROTTLE = 100; // ms between moves
    const DROP_THROTTLE = 50;  // ms between soft drops

    function init() {
        keysPressed = {};
        keyRepeatTimers = {};
        lastMoveTime = 0;
        lastDropTime = 0;
    }

    function update() {
        const currentTime = Date.now();
        
        // Handle continuous key presses during gameplay
        if (GameState.gameStatus === 'gameplay') {
            // Left/Right movement with repeat
            if (keysPressed['ArrowLeft'] || keysPressed['a'] || keysPressed['A']) {
                if (currentTime - lastMoveTime > MOVE_THROTTLE) {
                    TetrisEngine.movePiece('left');
                    lastMoveTime = currentTime;
                }
            }
            if (keysPressed['ArrowRight'] || keysPressed['d'] || keysPressed['D']) {
                if (currentTime - lastMoveTime > MOVE_THROTTLE) {
                    TetrisEngine.movePiece('right');
                    lastMoveTime = currentTime;
                }
            }
            
            // Soft drop
            if (keysPressed['ArrowDown'] || keysPressed['s'] || keysPressed['S']) {
                if (currentTime - lastDropTime > DROP_THROTTLE) {
                    TetrisEngine.movePiece('down');
                    lastDropTime = currentTime;
                }
            }
        }
    }

    function handleKeyDown(key) {
        // Prevent repeat events for keys already pressed
        if (keysPressed[key]) {
            return;
        }
        
        keysPressed[key] = true;
        
        if (GameState.gameStatus === 'gameplay') {
            switch(key) {
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    TetrisEngine.movePiece('left');
                    lastMoveTime = Date.now();
                    break;
                    
                case 'ArrowRight':
                case 'd':
                case 'D':
                    TetrisEngine.movePiece('right');
                    lastMoveTime = Date.now();
                    break;
                    
                case 'ArrowDown':
                case 's':
                case 'S':
                    TetrisEngine.movePiece('down');
                    lastDropTime = Date.now();
                    break;
                    
                case 'ArrowUp':
                case 'w':
                case 'W':
                case ' ':
                    TetrisEngine.rotatePiece();
                    break;
                    
                case 'Enter':
                case 'Space':
                    TetrisEngine.dropPiece();
                    break;
                    
                case 'Escape':
                case 'p':
                case 'P':
                    // Pause functionality could be added here
                    break;
            }
        } else if (GameState.gameStatus === 'main_menu') {
            switch(key) {
                case 'Enter':
                case ' ':
                    startGame();
                    break;
                case 'l':
                case 'L':
                    showLeaderboard();
                    break;
            }
        } else if (GameState.gameStatus === 'game_over') {
            switch(key) {
                case 'Enter':
                case ' ':
                case 'r':
                case 'R':
                    retryGame();
                    break;
                case 'Escape':
                case 'm':
                case 'M':
                    returnToMenu();
                    break;
                case 'l':
                case 'L':
                    showLeaderboard();
                    break;
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            switch(key) {
                case 'Escape':
                case 'Enter':
                case ' ':
                    closeLeaderboard();
                    break;
            }
        }
    }

    function handleKeyUp(key) {
        keysPressed[key] = false;
        
        // Clear any repeat timers
        if (keyRepeatTimers[key]) {
            clearTimeout(keyRepeatTimers[key]);
            delete keyRepeatTimers[key];
        }
    }

    function handleClick(x, y) {
        if (GameState.gameStatus === 'main_menu') {
            // Handle menu clicks
        } else if (GameState.gameStatus === 'game_over') {
            // Handle game over clicks
        } else if (GameState.gameStatus === 'leaderboard') {
            // Handle leaderboard clicks
        } else if (GameState.gameStatus === 'gameplay') {
            // Touch controls for mobile - could implement virtual buttons here
            // For now, just handle basic tap to rotate
            TetrisEngine.rotatePiece();
        }
    }

    return {
        init,
        update,
        handleKeyDown,
        handleKeyUp,
        handleClick
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
let gameLoopRunning = false;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions in order
    InputController.update();
    TetrisEngine.update();
    
    // Render functions in order
    UIManager.render();
    
    if (gameLoopRunning) {
        requestAnimationFrame(gameLoop);
    }
}

// State transition functions
function startGame() {
    GameStateModule.startGame();
    showScreen('gameplay');
}

function gameOver() {
    GameStateModule.endGame();
    showScreen('game_over');
}

function retryGame() {
    GameStateModule.retryGame();
    showScreen('gameplay');
}

function returnToMenu() {
    GameStateModule.returnToMenu();
    showScreen('main_menu');
}

function showLeaderboard() {
    GameStateModule.showLeaderboard();
    showScreen('leaderboard');
}

function closeLeaderboard() {
    GameStateModule.closeLeaderboard();
    showScreen('main_menu');
}

// Event listeners for state changes
EventBus.on('GAME_START', () => showScreen('gameplay'));
EventBus.on('GAME_OVER', () => showScreen('game_over'));
EventBus.on('RETRY', () => showScreen('gameplay'));
EventBus.on('RETURN_MENU', () => showScreen('main_menu'));
EventBus.on('SHOW_LEADERBOARD', () => showScreen('leaderboard'));
EventBus.on('CLOSE_LEADERBOARD', () => showScreen('main_menu'));

// Input handlers
document.addEventListener('keydown', (e) => {
    e.preventDefault();
    InputController.handleKeyDown(e.key);
});

document.addEventListener('keyup', (e) => {
    e.preventDefault();
    InputController.handleKeyUp(e.key);
});

document.addEventListener('click', (e) => {
    const rect = document.body.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    InputController.handleClick(x, y);
});

// Button event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Main menu buttons
    const btnStart = document.getElementById('btn_start');
    if (btnStart) {
        btnStart.addEventListener('click', startGame);
    }
    
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    if (btnLeaderboard) {
        btnLeaderboard.addEventListener('click', showLeaderboard);
    }
    
    // Game over buttons
    const btnRetry = document.getElementById('btn_retry');
    if (btnRetry) {
        btnRetry.addEventListener('click', retryGame);
    }
    
    const btnLeaderboardGo = document.getElementById('btn_leaderboard_go');
    if (btnLeaderboardGo) {
        btnLeaderboardGo.addEventListener('click', showLeaderboard);
    }
    
    const btnMenu = document.getElementById('btn_menu');
    if (btnMenu) {
        btnMenu.addEventListener('click', returnToMenu);
    }
    
    // Leaderboard buttons
    const btnClose = document.getElementById('btn_close');
    if (btnClose) {
        btnClose.addEventListener('click', closeLeaderboard);
    }
    
    // Initialize modules in order
    GameStateModule.init();
    TetrisEngine.init();
    UIManager.init();
    InputController.init();
    
    // Start game loop
    gameLoopRunning = true;
    requestAnimationFrame(gameLoop);
    
    // Show initial screen
    showScreen('main_menu');
});