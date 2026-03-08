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
    level: 1,
    lines: 0,
    isPaused: false
};

const TetrisGrid = {
    grid: [],
    currentPiece: null,
    nextPiece: null,
    ghostPiece: null
};

const HighScores = {
    scores: []
};

// Global constants
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const GRID_WIDTH = 10;
const GRID_HEIGHT = 20;
const CELL_SIZE = 40;
const LINES_PER_LEVEL = 10;

// Module code
const GameStateModule = (function() {
    function setupEventListeners() {
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('GAME_OVER', handleGameOver);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('SHOW_LEADERBOARD', handleShowLeaderboard);
        EventBus.on('CLOSE_LEADERBOARD', handleCloseLeaderboard);
        EventBus.on('LINES_CLEARED', handleLinesCleared);
        EventBus.on('PIECE_LOCKED', handlePieceLocked);
    }

    function handleGameStart() {
        startGame();
    }

    function handleGameOver() {
        gameOver();
    }

    function handleRetry() {
        retry();
    }

    function handleReturnMenu() {
        returnToMenu();
    }

    function handleShowLeaderboard() {
        showLeaderboard();
    }

    function handleCloseLeaderboard() {
        closeLeaderboard();
    }

    function handleLinesCleared(data) {
        const { linesCleared, points } = data;
        addLines(linesCleared);
        addScore(points);
    }

    function handlePieceLocked(data) {
        const { points } = data;
        addScore(points);
    }

    function updateHighScore() {
        if (!HighScores.scores) {
            HighScores.scores = [];
        }
        
        HighScores.scores.push({
            score: GameState.score,
            level: GameState.level,
            lines: GameState.lines,
            date: new Date().toLocaleDateString()
        });
        
        HighScores.scores.sort((a, b) => b.score - a.score);
        HighScores.scores = HighScores.scores.slice(0, 5);
        
        try {
            localStorage.setItem('tetris_high_scores', JSON.stringify(HighScores.scores));
        } catch (e) {
            // Ignore localStorage errors
        }
    }

    function loadHighScores() {
        try {
            const saved = localStorage.getItem('tetris_high_scores');
            if (saved) {
                HighScores.scores = JSON.parse(saved);
            } else {
                HighScores.scores = [];
            }
        } catch (e) {
            HighScores.scores = [];
        }
    }

    function resetGameStats() {
        GameState.score = 0;
        GameState.level = 1;
        GameState.lines = 0;
        GameState.isPaused = false;
    }

    function init() {
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.level = 1;
        GameState.lines = 0;
        GameState.isPaused = false;
        
        loadHighScores();
        setupEventListeners();
    }

    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            resetGameStats();
            GameState.gameStatus = 'gameplay';
        }
    }

    function gameOver() {
        if (GameState.gameStatus === 'gameplay') {
            updateHighScore();
            GameState.gameStatus = 'game_over';
        }
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'main_menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
        }
    }

    function closeLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
        }
    }

    function retry() {
        if (GameState.gameStatus === 'game_over') {
            resetGameStats();
            GameState.gameStatus = 'gameplay';
        }
    }

    function returnToMenu() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'main_menu';
        }
    }

    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
        }
    }

    function addLines(linesCleared) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.lines += linesCleared;
            
            const newLevel = Math.floor(GameState.lines / LINES_PER_LEVEL) + 1;
            if (newLevel > GameState.level) {
                GameState.level = newLevel;
            }
        }
    }

    return {
        init,
        startGame,
        gameOver,
        showLeaderboard,
        closeLeaderboard,
        retry,
        returnToMenu,
        addScore,
        addLines
    };
})();

const TetrisEngine = (function() {
    const PIECES = {
        I: [
            [[0,0,0,0], [1,1,1,1], [0,0,0,0], [0,0,0,0]],
            [[0,0,1,0], [0,0,1,0], [0,0,1,0], [0,0,1,0]],
            [[0,0,0,0], [0,0,0,0], [1,1,1,1], [0,0,0,0]],
            [[0,1,0,0], [0,1,0,0], [0,1,0,0], [0,1,0,0]]
        ],
        O: [
            [[1,1], [1,1]],
            [[1,1], [1,1]],
            [[1,1], [1,1]],
            [[1,1], [1,1]]
        ],
        T: [
            [[0,1,0], [1,1,1], [0,0,0]],
            [[0,1,0], [0,1,1], [0,1,0]],
            [[0,0,0], [1,1,1], [0,1,0]],
            [[0,1,0], [1,1,0], [0,1,0]]
        ],
        S: [
            [[0,1,1], [1,1,0], [0,0,0]],
            [[0,1,0], [0,1,1], [0,0,1]],
            [[0,0,0], [0,1,1], [1,1,0]],
            [[1,0,0], [1,1,0], [0,1,0]]
        ],
        Z: [
            [[1,1,0], [0,1,1], [0,0,0]],
            [[0,0,1], [0,1,1], [0,1,0]],
            [[0,0,0], [1,1,0], [0,1,1]],
            [[0,1,0], [1,1,0], [1,0,0]]
        ],
        J: [
            [[1,0,0], [1,1,1], [0,0,0]],
            [[0,1,1], [0,1,0], [0,1,0]],
            [[0,0,0], [1,1,1], [0,0,1]],
            [[0,1,0], [0,1,0], [1,1,0]]
        ],
        L: [
            [[0,0,1], [1,1,1], [0,0,0]],
            [[0,1,0], [0,1,0], [0,1,1]],
            [[0,0,0], [1,1,1], [1,0,0]],
            [[1,1,0], [0,1,0], [0,1,0]]
        ]
    };

    const PIECE_TYPES = ['I', 'O', 'T', 'S', 'Z', 'J', 'L'];
    const COLORS = {
        I: '#00FFFF', O: '#FFFF00', T: '#800080', 
        S: '#00FF00', Z: '#FF0000', J: '#0000FF', L: '#FFA500'
    };

    let dropTimer = 0;
    let dropInterval = 1000;
    let lastTime = 0;

    function init() {
        TetrisGrid.grid = [];
        for (let row = 0; row < GRID_HEIGHT; row++) {
            TetrisGrid.grid[row] = [];
            for (let col = 0; col < GRID_WIDTH; col++) {
                TetrisGrid.grid[row][col] = 0;
            }
        }

        TetrisGrid.currentPiece = null;
        TetrisGrid.nextPiece = generateRandomPiece();
        TetrisGrid.ghostPiece = null;
        
        dropTimer = 0;
        lastTime = Date.now();
        
        spawnNewPiece();
    }

    function generateRandomPiece() {
        const type = PIECE_TYPES[Math.floor(Math.random() * PIECE_TYPES.length)];
        return {
            type: type,
            shape: PIECES[type][0],
            rotation: 0,
            x: Math.floor(GRID_WIDTH / 2) - Math.floor(PIECES[type][0][0].length / 2),
            y: 0,
            color: COLORS[type]
        };
    }

    function spawnNewPiece() {
        TetrisGrid.currentPiece = TetrisGrid.nextPiece;
        TetrisGrid.nextPiece = generateRandomPiece();
        
        if (isCollision(TetrisGrid.currentPiece, TetrisGrid.currentPiece.x, TetrisGrid.currentPiece.y)) {
            EventBus.emit('GAME_OVER');
            return;
        }
        
        updateGhostPiece();
    }

    function isCollision(piece, x, y) {
        for (let row = 0; row < piece.shape.length; row++) {
            for (let col = 0; col < piece.shape[row].length; col++) {
                if (piece.shape[row][col]) {
                    const newX = x + col;
                    const newY = y + row;
                    
                    if (newX < 0 || newX >= GRID_WIDTH || newY >= GRID_HEIGHT) {
                        return true;
                    }
                    
                    if (newY >= 0 && TetrisGrid.grid[newY][newX]) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    function lockPiece() {
        const piece = TetrisGrid.currentPiece;
        let points = 0;
        
        for (let row = 0; row < piece.shape.length; row++) {
            for (let col = 0; col < piece.shape[row].length; col++) {
                if (piece.shape[row][col]) {
                    const x = piece.x + col;
                    const y = piece.y + row;
                    if (y >= 0) {
                        TetrisGrid.grid[y][x] = piece.color;
                    }
                }
            }
        }

        const linesCleared = clearLines();
        
        points += 10;
        
        if (linesCleared > 0) {
            const linePoints = [0, 100, 300, 500, 800][linesCleared] || 800;
            points += linePoints * GameState.level;
            
            EventBus.emit('LINES_CLEARED', { linesCleared, points: linePoints * GameState.level });
        }

        if (points > 10) {
            EventBus.emit('PIECE_LOCKED', { points: 10 });
        }

        spawnNewPiece();
    }

    function clearLines() {
        let linesCleared = 0;
        
        for (let row = GRID_HEIGHT - 1; row >= 0; row--) {
            let fullLine = true;
            for (let col = 0; col < GRID_WIDTH; col++) {
                if (!TetrisGrid.grid[row][col]) {
                    fullLine = false;
                    break;
                }
            }
            
            if (fullLine) {
                TetrisGrid.grid.splice(row, 1);
                const emptyLine = new Array(GRID_WIDTH).fill(0);
                TetrisGrid.grid.unshift(emptyLine);
                
                linesCleared++;
                row++;
            }
        }
        
        return linesCleared;
    }

    function updateGhostPiece() {
        if (!TetrisGrid.currentPiece) return;
        
        const piece = TetrisGrid.currentPiece;
        let ghostY = piece.y;
        
        while (!isCollision(piece, piece.x, ghostY + 1)) {
            ghostY++;
        }
        
        TetrisGrid.ghostPiece = {
            type: piece.type,
            shape: piece.shape,
            rotation: piece.rotation,
            x: piece.x,
            y: ghostY,
            color: piece.color
        };
    }

    function update() {
        if (GameState.gameStatus !== 'gameplay' || GameState.isPaused) return;
        
        const currentTime = Date.now();
        const deltaTime = currentTime - lastTime;
        lastTime = currentTime;
        
        dropInterval = Math.max(50, 1000 - (GameState.level - 1) * 50);
        
        dropTimer += deltaTime;
        
        if (dropTimer >= dropInterval) {
            if (TetrisGrid.currentPiece) {
                if (!movePiece('down')) {
                    lockPiece();
                }
            }
            dropTimer = 0;
        }
    }

    function movePiece(direction) {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) return false;
        
        const piece = TetrisGrid.currentPiece;
        let newX = piece.x;
        let newY = piece.y;
        
        switch (direction) {
            case 'left':
                newX--;
                break;
            case 'right':
                newX++;
                break;
            case 'down':
                newY++;
                break;
        }
        
        if (!isCollision(piece, newX, newY)) {
            piece.x = newX;
            piece.y = newY;
            updateGhostPiece();
            return true;
        }
        
        return false;
    }

    function rotatePiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) return false;
        
        const piece = TetrisGrid.currentPiece;
        const newRotation = (piece.rotation + 1) % 4;
        const newShape = PIECES[piece.type][newRotation];
        
        const testPiece = { ...piece, shape: newShape, rotation: newRotation };
        
        if (!isCollision(testPiece, piece.x, piece.y)) {
            piece.shape = newShape;
            piece.rotation = newRotation;
            updateGhostPiece();
            return true;
        }
        
        const kicks = [
            { x: -1, y: 0 }, { x: 1, y: 0 },
            { x: -2, y: 0 }, { x: 2, y: 0 },
            { x: 0, y: -1 }
        ];
        
        for (const kick of kicks) {
            if (!isCollision(testPiece, piece.x + kick.x, piece.y + kick.y)) {
                piece.shape = newShape;
                piece.rotation = newRotation;
                piece.x += kick.x;
                piece.y += kick.y;
                updateGhostPiece();
                return true;
            }
        }
        
        return false;
    }

    function dropPiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) return;
        
        const piece = TetrisGrid.currentPiece;
        let dropDistance = 0;
        
        while (!isCollision(piece, piece.x, piece.y + 1)) {
            piece.y++;
            dropDistance++;
        }
        
        if (dropDistance > 0) {
            EventBus.emit('PIECE_LOCKED', { points: dropDistance * 2 });
        }
        
        lockPiece();
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
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        if (canvas) {
            ctx = canvas.getContext('2d');
            canvas.width = 600;
            canvas.height = 1200;
        }
    }
    
    function render() {
        updateUI();
        
        if (GameState.gameStatus === 'gameplay' && canvas && ctx) {
            renderGameplay();
        }
    }
    
    function updateUI() {
        // Update score displays
        const scoreValue = document.getElementById('score_value');
        const levelValue = document.getElementById('level_value');
        const linesValue = document.getElementById('lines_value');
        const highScore = document.getElementById('high_score');
        const finalScore = document.getElementById('final_score');
        const finalLines = document.getElementById('final_lines');
        
        if (scoreValue) scoreValue.textContent = GameState.score;
        if (levelValue) levelValue.textContent = GameState.level;
        if (linesValue) linesValue.textContent = GameState.lines;
        if (finalScore) finalScore.textContent = '得分: ' + GameState.score;
        if (finalLines) finalLines.textContent = '消除行数: ' + GameState.lines;
        
        if (highScore && HighScores.scores.length > 0) {
            highScore.textContent = '最高分: ' + HighScores.scores[0].score;
        }
        
        // Update leaderboard
        const scoreList = document.getElementById('score_list');
        if (scoreList) {
            if (HighScores.scores.length === 0) {
                scoreList.textContent = '暂无记录';
            } else {
                scoreList.innerHTML = HighScores.scores.map((score, index) => 
                    `${index + 1}. ${score.score} 分`
                ).join('<br>');
            }
        }
    }
    
    function renderGameplay() {
        if (!ctx) return;
        
        ctx.fillStyle = '#000011';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        const cellSize = Math.min(canvas.width / GRID_WIDTH, canvas.height / GRID_HEIGHT);
        const offsetX = (canvas.width - GRID_WIDTH * cellSize) / 2;
        const offsetY = (canvas.height - GRID_HEIGHT * cellSize) / 2;
        
        // Draw grid lines
        ctx.strokeStyle = '#333333';
        ctx.lineWidth = 1;
        
        for (let x = 0; x <= GRID_WIDTH; x++) {
            ctx.beginPath();
            ctx.moveTo(offsetX + x * cellSize, offsetY);
            ctx.lineTo(offsetX + x * cellSize, offsetY + GRID_HEIGHT * cellSize);
            ctx.stroke();
        }
        
        for (let y = 0; y <= GRID_HEIGHT; y++) {
            ctx.beginPath();
            ctx.moveTo(offsetX, offsetY + y * cellSize);
            ctx.lineTo(offsetX + GRID_WIDTH * cellSize, offsetY + y * cellSize);
            ctx.stroke();
        }
        
        // Draw placed blocks
        if (TetrisGrid.grid) {
            for (let y = 0; y < GRID_HEIGHT; y++) {
                for (let x = 0; x < GRID_WIDTH; x++) {
                    if (TetrisGrid.grid[y] && TetrisGrid.grid[y][x]) {
                        drawBlock(offsetX + x * cellSize, offsetY + y * cellSize, cellSize, TetrisGrid.grid[y][x]);
                    }
                }
            }
        }
        
        // Draw ghost piece
        if (TetrisGrid.ghostPiece) {
            ctx.globalAlpha = 0.3;
            drawPiece(TetrisGrid.ghostPiece, offsetX, offsetY, cellSize, '#AAAAAA');
            ctx.globalAlpha = 1.0;
        }
        
        // Draw current piece
        if (TetrisGrid.currentPiece) {
            drawPiece(TetrisGrid.currentPiece, offsetX, offsetY, cellSize);
        }
    }
    
    function drawBlock(x, y, size, color) {
        if (!ctx) return;
        
        ctx.fillStyle = color || '#FFFFFF';
        ctx.fillRect(x + 1, y + 1, size - 2, size - 2);
        
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;
        ctx.strokeRect(x + 1, y + 1, size - 2, size - 2);
    }
    
    function drawPiece(piece, offsetX, offsetY, cellSize, color) {
        if (!ctx || !piece || !piece.shape) return;
        
        const pieceColor = color || piece.color || '#FFFFFF';
        
        for (let row = 0; row < piece.shape.length; row++) {
            for (let col = 0; col < piece.shape[row].length; col++) {
                if (piece.shape[row][col]) {
                    const x = offsetX + (piece.x + col) * cellSize;
                    const y = offsetY + (piece.y + row) * cellSize;
                    
                    if (piece.y + row >= 0) {
                        drawBlock(x, y, cellSize, pieceColor);
                    }
                }
            }
        }
    }
    
    function handleMenuClick(buttonId) {
        if (GameState.gameStatus !== 'main_menu') return;
        
        switch (buttonId) {
            case 'start':
                EventBus.emit('GAME_START');
                break;
            case 'leaderboard':
                EventBus.emit('SHOW_LEADERBOARD');
                break;
        }
    }
    
    function handleGameOverClick(buttonId) {
        if (GameState.gameStatus !== 'game_over') return;
        
        switch (buttonId) {
            case 'retry':
                EventBus.emit('RETRY');
                break;
            case 'menu':
                EventBus.emit('RETURN_MENU');
                break;
            case 'leaderboard':
                EventBus.emit('SHOW_LEADERBOARD');
                break;
        }
    }
    
    return {
        init,
        render,
        handleMenuClick,
        handleGameOverClick
    };
})();

const InputController = (function() {
    let keysPressed = {};
    let lastMoveTime = 0;
    let lastDropTime = 0;
    const MOVE_REPEAT_DELAY = 150;
    const DROP_REPEAT_DELAY = 50;
    
    function init() {
        document.addEventListener('keydown', (e) => handleKeyDown(e.code));
        document.addEventListener('keyup', (e) => handleKeyUp(e.code));
        
        // Button event listeners
        const btnStart = document.getElementById('btn_start');
        const btnLeaderboard = document.querySelectorAll('#btn_leaderboard');
        const btnRetry = document.getElementById('btn_retry');
        const btnMenu = document.getElementById('btn_menu');
        const btnClose = document.getElementById('btn_close');
        
        if (btnStart) {
            btnStart.addEventListener('click', () => EventBus.emit('GAME_START'));
        }
        
        btnLeaderboard.forEach(btn => {
            btn.addEventListener('click', () => EventBus.emit('SHOW_LEADERBOARD'));
        });
        
        if (btnRetry) {
            btnRetry.addEventListener('click', () => EventBus.emit('RETRY'));
        }
        
        if (btnMenu) {
            btnMenu.addEventListener('click', () => EventBus.emit('RETURN_MENU'));
        }
        
        if (btnClose) {
            btnClose.addEventListener('click', () => EventBus.emit('CLOSE_LEADERBOARD'));
        }
    }
    
    function update() {
        const currentTime = Date.now();
        
        if (GameState.gameStatus === 'gameplay') {
            if (keysPressed['ArrowLeft'] || keysPressed['KeyA']) {
                if (currentTime - lastMoveTime > MOVE_REPEAT_DELAY) {
                    TetrisEngine.movePiece('left');
                    lastMoveTime = currentTime;
                }
            }
            if (keysPressed['ArrowRight'] || keysPressed['KeyD']) {
                if (currentTime - lastMoveTime > MOVE_REPEAT_DELAY) {
                    TetrisEngine.movePiece('right');
                    lastMoveTime = currentTime;
                }
            }
            
            if (keysPressed['ArrowDown'] || keysPressed['KeyS']) {
                if (currentTime - lastDropTime > DROP_REPEAT_DELAY) {
                    TetrisEngine.movePiece('down');
                    lastDropTime = currentTime;
                }
            }
        }
    }
    
    function handleKeyDown(keyCode) {
        if (keysPressed[keyCode]) {
            return;
        }
        
        keysPressed[keyCode] = true;
        
        if (GameState.gameStatus === 'gameplay') {
            switch (keyCode) {
                case 'ArrowLeft':
                case 'KeyA':
                    TetrisEngine.movePiece('left');
                    lastMoveTime = Date.now();
                    break;
                case 'ArrowRight':
                case 'KeyD':
                    TetrisEngine.movePiece('right');
                    lastMoveTime = Date.now();
                    break;
                case 'ArrowDown':
                case 'KeyS':
                    TetrisEngine.movePiece('down');
                    lastDropTime = Date.now();
                    break;
                case 'ArrowUp':
                case 'KeyW':
                case 'KeyX':
                    TetrisEngine.rotatePiece();
                    break;
                case 'Space':
                    TetrisEngine.dropPiece();
                    break;
            }
        } else if (GameState.gameStatus === 'main_menu') {
            switch (keyCode) {
                case 'Enter':
                case 'Space':
                    EventBus.emit('GAME_START');
                    break;
                case 'KeyL':
                    EventBus.emit('SHOW_LEADERBOARD');
                    break;
            }
        } else if (GameState.gameStatus === 'game_over') {
            switch (keyCode) {
                case 'Enter':
                case 'KeyR':
                    EventBus.emit('RETRY');
                    break;
                case 'Escape':
                case 'KeyM':
                    EventBus.emit('RETURN_MENU');
                    break;
                case 'KeyL':
                    EventBus.emit('SHOW_LEADERBOARD');
                    break;
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            switch (keyCode) {
                case 'Escape':
                case 'Enter':
                    EventBus.emit('CLOSE_LEADERBOARD');
                    break;
            }
        }
    }
    
    function handleKeyUp(keyCode) {
        keysPressed[keyCode] = false;
    }
    
    function handleTouch(x, y) {
        // Touch handling implementation
    }
    
    return {
        init,
        update,
        handleKeyDown,
        handleKeyUp,
        handleTouch
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
    
    // Update modules in order
    InputController.update();
    TetrisEngine.update();
    
    // Render modules in order
    UIManager.render();
    
    // Update screen visibility based on game state
    showScreen(GameState.gameStatus);
    
    if (GameState.gameStatus === 'gameplay' || GameState.gameStatus === 'main_menu' || 
        GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
        requestAnimationFrame(gameLoop);
    }
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('GAME_START');
    showScreen('gameplay');
    TetrisEngine.init();
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER');
    showScreen('game_over');
}

function retry() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('RETRY');
    showScreen('gameplay');
    TetrisEngine.init();
}

function returnToMenu() {
    GameState.gameStatus = 'main_menu';
    EventBus.emit('RETURN_MENU');
    showScreen('main_menu');
}

function showLeaderboard() {
    GameState.gameStatus = 'leaderboard';
    EventBus.emit('SHOW_LEADERBOARD');
    showScreen('leaderboard');
}

function closeLeaderboard() {
    GameState.gameStatus = 'main_menu';
    EventBus.emit('CLOSE_LEADERBOARD');
    showScreen('main_menu');
}

// Initialize game
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in order
    GameStateModule.init();
    TetrisEngine.init();
    UIManager.init();
    InputController.init();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
});