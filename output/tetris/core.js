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
const CANVAS_WIDTH = 600;
const CANVAS_HEIGHT = 1200;
const GRID_WIDTH = 10;
const GRID_HEIGHT = 20;
const BLOCK_SIZE = 30;
const LINES_PER_LEVEL = 10;

// Shared State Objects
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

// Module Code (concatenated exactly as provided)
const game_state = (function() {
    let eventListeners = [];

    function addEventListener(eventName, callback) {
        if (!eventListeners[eventName]) {
            eventListeners[eventName] = [];
        }
        eventListeners[eventName].push(callback);
    }

    function emitEvent(eventName, payload = {}) {
        if (eventListeners[eventName]) {
            eventListeners[eventName].forEach(callback => callback(payload));
        }
        EventBus.emit(eventName, payload);
    }

    function init() {
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.level = 1;
        GameState.linesCleared = 0;
        GameState.isPaused = false;

        HighScores.scores = loadHighScores();

        EventBus.on('GAME_OVER', handleGameOver);
        EventBus.on('LINES_CLEARED', handleLinesCleared);
    }

    function loadHighScores() {
        try {
            const saved = localStorage.getItem('tetris_high_scores');
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {
            console.warn('Failed to load high scores:', e);
        }
        return [];
    }

    function saveHighScores() {
        try {
            localStorage.setItem('tetris_high_scores', JSON.stringify(HighScores.scores));
        } catch (e) {
            console.warn('Failed to save high scores:', e);
        }
    }

    function updateHighScore(score) {
        HighScores.scores.push(score);
        HighScores.scores.sort((a, b) => b - a);
        HighScores.scores = HighScores.scores.slice(0, 5);
        saveHighScores();
    }

    function handleGameOver(payload) {
        if (GameState.gameStatus === 'gameplay') {
            updateHighScore(payload.finalScore);
            GameState.gameStatus = 'game_over';
        }
    }

    function handleLinesCleared(payload) {
        if (GameState.gameStatus === 'gameplay') {
            addScore(payload.points);
            addLines(payload.lines);
        }
    }

    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            GameState.level = 1;
            GameState.linesCleared = 0;
            GameState.isPaused = false;
            emitEvent('GAME_START');
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
            emitEvent('RETRY');
        }
    }

    function returnToMenu() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'main_menu';
            emitEvent('RETURN_MENU');
        }
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'main_menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
            emitEvent('SHOW_LEADERBOARD');
        }
    }

    function closeLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
            emitEvent('CLOSE_LEADERBOARD');
        }
    }

    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
        }
    }

    function addLines(lines) {
        if (GameState.gameStatus === 'gameplay') {
            const oldLevel = GameState.level;
            GameState.linesCleared += lines;
            
            const newLevel = Math.floor(GameState.linesCleared / LINES_PER_LEVEL) + 1;
            
            if (newLevel > oldLevel) {
                GameState.level = newLevel;
                emitEvent('LEVEL_UP', { newLevel: newLevel });
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
        closeLeaderboard,
        addScore,
        addLines
    };
})();

const TetrisEngine = (function() {
    const TETROMINOS = {
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
    const SPAWN_X = 3;
    const SPAWN_Y = 0;
    
    let dropSpeed = 1000;
    let lastDropTime = 0;

    function init() {
        TetrisGrid.grid = [];
        for (let y = 0; y < GRID_HEIGHT; y++) {
            TetrisGrid.grid[y] = [];
            for (let x = 0; x < GRID_WIDTH; x++) {
                TetrisGrid.grid[y][x] = 0;
            }
        }
        
        TetrisGrid.currentPiece = null;
        TetrisGrid.nextPiece = generateRandomPiece();
        TetrisGrid.dropTimer = 0;
        
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('LEVEL_UP', handleLevelUp);
    }

    function handleGameStart() {
        resetGame();
        spawnNewPiece();
    }

    function handleRetry() {
        resetGame();
        spawnNewPiece();
    }

    function handleLevelUp(event) {
        const newLevel = event.newLevel;
        dropSpeed = Math.max(50, 1000 - (newLevel - 1) * 100);
    }

    function resetGame() {
        for (let y = 0; y < GRID_HEIGHT; y++) {
            for (let x = 0; x < GRID_WIDTH; x++) {
                TetrisGrid.grid[y][x] = 0;
            }
        }
        
        TetrisGrid.currentPiece = null;
        TetrisGrid.nextPiece = generateRandomPiece();
        TetrisGrid.dropTimer = 0;
        dropSpeed = 1000 - (GameState.level - 1) * 100;
        lastDropTime = Date.now();
    }

    function generateRandomPiece() {
        const type = PIECE_TYPES[Math.floor(Math.random() * PIECE_TYPES.length)];
        return {
            type: type,
            x: SPAWN_X,
            y: SPAWN_Y,
            rotation: 0,
            shape: TETROMINOS[type][0]
        };
    }

    function spawnNewPiece() {
        TetrisGrid.currentPiece = TetrisGrid.nextPiece;
        TetrisGrid.currentPiece.x = SPAWN_X;
        TetrisGrid.currentPiece.y = SPAWN_Y;
        TetrisGrid.nextPiece = generateRandomPiece();
        
        if (isColliding(TetrisGrid.currentPiece)) {
            EventBus.emit('GAME_OVER', {
                finalScore: GameState.score,
                linesCleared: GameState.linesCleared,
                level: GameState.level
            });
            return false;
        }
        
        return true;
    }

    function update() {
        if (GameState.gameStatus !== 'gameplay' || GameState.isPaused) {
            return;
        }

        const currentTime = Date.now();
        TetrisGrid.dropTimer += currentTime - lastDropTime;
        lastDropTime = currentTime;

        if (TetrisGrid.dropTimer >= dropSpeed) {
            if (TetrisGrid.currentPiece) {
                if (!movePiece('down')) {
                    lockPiece();
                    clearLines();
                    if (!spawnNewPiece()) {
                        return;
                    }
                }
            }
            TetrisGrid.dropTimer = 0;
        }
    }

    function movePiece(direction) {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return false;
        }

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
            default:
                return false;
        }

        const testPiece = {
            ...piece,
            x: newX,
            y: newY
        };

        if (!isColliding(testPiece)) {
            piece.x = newX;
            piece.y = newY;
            return true;
        }

        return false;
    }

    function rotatePiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return false;
        }

        const piece = TetrisGrid.currentPiece;
        const newRotation = (piece.rotation + 1) % 4;
        const newShape = TETROMINOS[piece.type][newRotation];

        const testPiece = {
            ...piece,
            rotation: newRotation,
            shape: newShape
        };

        if (!isColliding(testPiece)) {
            piece.rotation = newRotation;
            piece.shape = newShape;
            return true;
        }

        const wallKicks = [
            { x: -1, y: 0 },
            { x: 1, y: 0 },
            { x: -2, y: 0 },
            { x: 2, y: 0 },
            { x: 0, y: -1 }
        ];

        for (const kick of wallKicks) {
            const kickTestPiece = {
                ...testPiece,
                x: piece.x + kick.x,
                y: piece.y + kick.y
            };

            if (!isColliding(kickTestPiece)) {
                piece.x = kickTestPiece.x;
                piece.y = kickTestPiece.y;
                piece.rotation = newRotation;
                piece.shape = newShape;
                return true;
            }
        }

        return false;
    }

    function dropPiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return;
        }

        const piece = TetrisGrid.currentPiece;
        let dropDistance = 0;

        while (true) {
            const testPiece = {
                ...piece,
                y: piece.y + dropDistance + 1
            };

            if (isColliding(testPiece)) {
                break;
            }
            dropDistance++;
        }

        piece.y += dropDistance;
        
        lockPiece();
        clearLines();
        spawnNewPiece();
        
        TetrisGrid.dropTimer = 0;
    }

    function isColliding(piece) {
        const shape = piece.shape;
        
        for (let y = 0; y < shape.length; y++) {
            for (let x = 0; x < shape[y].length; x++) {
                if (shape[y][x]) {
                    const gridX = piece.x + x;
                    const gridY = piece.y + y;
                    
                    if (gridX < 0 || gridX >= GRID_WIDTH || gridY >= GRID_HEIGHT) {
                        return true;
                    }
                    
                    if (gridY >= 0 && TetrisGrid.grid[gridY][gridX]) {
                        return true;
                    }
                }
            }
        }
        
        return false;
    }

    function lockPiece() {
        const piece = TetrisGrid.currentPiece;
        const shape = piece.shape;
        
        for (let y = 0; y < shape.length; y++) {
            for (let x = 0; x < shape[y].length; x++) {
                if (shape[y][x]) {
                    const gridX = piece.x + x;
                    const gridY = piece.y + y;
                    
                    if (gridY >= 0 && gridY < GRID_HEIGHT && gridX >= 0 && gridX < GRID_WIDTH) {
                        TetrisGrid.grid[gridY][gridX] = piece.type;
                    }
                }
            }
        }
        
        TetrisGrid.currentPiece = null;
    }

    function clearLines() {
        let linesCleared = 0;
        
        for (let y = GRID_HEIGHT - 1; y >= 0; y--) {
            let isFullLine = true;
            
            for (let x = 0; x < GRID_WIDTH; x++) {
                if (!TetrisGrid.grid[y][x]) {
                    isFullLine = false;
                    break;
                }
            }
            
            if (isFullLine) {
                TetrisGrid.grid.splice(y, 1);
                const emptyLine = new Array(GRID_WIDTH).fill(0);
                TetrisGrid.grid.unshift(emptyLine);
                
                linesCleared++;
                y++;
            }
        }
        
        if (linesCleared > 0) {
            const pointsTable = [0, 100, 300, 500, 800];
            const points = pointsTable[Math.min(linesCleared, 4)] * GameState.level;
            
            EventBus.emit('LINES_CLEARED', {
                lines: linesCleared,
                points: points
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

const ui_manager = (function() {
    let canvas;
    let ctx;
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        if (canvas) {
            ctx = canvas.getContext('2d');
            canvas.width = CANVAS_WIDTH;
            canvas.height = CANVAS_HEIGHT;
        }
        
        EventBus.on('GAME_START', updateUI);
        EventBus.on('GAME_OVER', updateUI);
        EventBus.on('LINES_CLEARED', updateUI);
        EventBus.on('LEVEL_UP', updateUI);
        EventBus.on('SHOW_LEADERBOARD', updateUI);
        EventBus.on('CLOSE_LEADERBOARD', updateUI);
        EventBus.on('RETRY', updateUI);
        EventBus.on('RETURN_MENU', updateUI);
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
        if (linesValue) linesValue.textContent = GameState.linesCleared;
        
        if (highScore) {
            const best = HighScores.scores.length > 0 ? HighScores.scores[0] : 0;
            highScore.textContent = `最高分: ${best}`;
        }
        
        if (finalScore) finalScore.textContent = `最终得分: ${GameState.score}`;
        if (finalLines) finalLines.textContent = `消除行数: ${GameState.linesCleared}`;
        
        // Update leaderboard
        updateLeaderboard();
    }
    
    function updateLeaderboard() {
        const scoreList = document.getElementById('score_list');
        if (!scoreList) return;
        
        if (HighScores.scores.length === 0) {
            scoreList.innerHTML = '<div class="score-entry">暂无记录</div>';
        } else {
            scoreList.innerHTML = '';
            for (let i = 0; i < Math.min(5, HighScores.scores.length); i++) {
                const score = HighScores.scores[i];
                const entry = document.createElement('div');
                entry.className = 'score-entry';
                entry.innerHTML = `
                    <span>${i + 1}.</span>
                    <span>${score}</span>
                `;
                scoreList.appendChild(entry);
            }
        }
    }
    
    function renderGameplay() {
        if (!ctx) return;
        
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Draw grid background
        ctx.strokeStyle = '#333333';
        ctx.lineWidth = 1;
        for (let x = 0; x <= GRID_WIDTH; x++) {
            ctx.beginPath();
            ctx.moveTo(x * BLOCK_SIZE, 0);
            ctx.lineTo(x * BLOCK_SIZE, GRID_HEIGHT * BLOCK_SIZE);
            ctx.stroke();
        }
        for (let y = 0; y <= GRID_HEIGHT; y++) {
            ctx.beginPath();
            ctx.moveTo(0, y * BLOCK_SIZE);
            ctx.lineTo(GRID_WIDTH * BLOCK_SIZE, y * BLOCK_SIZE);
            ctx.stroke();
        }
        
        // Draw placed blocks
        if (TetrisGrid.grid && TetrisGrid.grid.length > 0) {
            for (let y = 0; y < GRID_HEIGHT; y++) {
                for (let x = 0; x < GRID_WIDTH; x++) {
                    if (TetrisGrid.grid[y] && TetrisGrid.grid[y][x]) {
                        const color = getBlockColor(TetrisGrid.grid[y][x]);
                        drawBlock(x * BLOCK_SIZE, y * BLOCK_SIZE, color);
                    }
                }
            }
        }
        
        // Draw current piece
        if (TetrisGrid.currentPiece) {
            const piece = TetrisGrid.currentPiece;
            const color = getBlockColor(piece.type);
            const shape = piece.shape;
            
            for (let y = 0; y < shape.length; y++) {
                for (let x = 0; x < shape[y].length; x++) {
                    if (shape[y][x] && piece.y + y >= 0) {
                        const blockX = (piece.x + x) * BLOCK_SIZE;
                        const blockY = (piece.y + y) * BLOCK_SIZE;
                        drawBlock(blockX, blockY, color);
                    }
                }
            }
        }
    }
    
    function drawBlock(x, y, color) {
        if (!ctx) return;
        
        ctx.fillStyle = color;
        ctx.fillRect(x + 1, y + 1, BLOCK_SIZE - 2, BLOCK_SIZE - 2);
        
        // Block highlight
        ctx.fillStyle = lightenColor(color, 0.3);
        ctx.fillRect(x + 1, y + 1, BLOCK_SIZE - 2, 6);
        ctx.fillRect(x + 1, y + 1, 6, BLOCK_SIZE - 2);
        
        // Block shadow
        ctx.fillStyle = darkenColor(color, 0.3);
        ctx.fillRect(x + BLOCK_SIZE - 6, y + 1, 5, BLOCK_SIZE - 2);
        ctx.fillRect(x + 1, y + BLOCK_SIZE - 6, BLOCK_SIZE - 2, 5);
    }
    
    function getBlockColor(type) {
        const colors = {
            'I': '#00FFFF',
            'O': '#FFFF00',
            'T': '#800080',
            'S': '#00FF00',
            'Z': '#FF0000',
            'J': '#0000FF',
            'L': '#FFA500'
        };
        return colors[type] || '#FFFFFF';
    }
    
    function lightenColor(color, amount) {
        const hex = color.replace('#', '');
        const r = Math.min(255, parseInt(hex.substr(0, 2), 16) + Math.floor(255 * amount));
        const g = Math.min(255, parseInt(hex.substr(2, 2), 16) + Math.floor(255 * amount));
        const b = Math.min(255, parseInt(hex.substr(4, 2), 16) + Math.floor(255 * amount));
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }
    
    function darkenColor(color, amount) {
        const hex = color.replace('#', '');
        const r = Math.max(0, parseInt(hex.substr(0, 2), 16) - Math.floor(255 * amount));
        const g = Math.max(0, parseInt(hex.substr(2, 2), 16) - Math.floor(255 * amount));
        const b = Math.max(0, parseInt(hex.substr(4, 2), 16) - Math.floor(255 * amount));
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }
    
    function handleMenuClick(buttonId) {
        if (GameState.gameStatus !== 'main_menu') return;
        
        switch (buttonId) {
            case 'start':
                game_state.startGame();
                break;
            case 'leaderboard':
                game_state.showLeaderboard();
                break;
        }
    }
    
    function handleGameOverClick(buttonId) {
        if (GameState.gameStatus !== 'game_over') return;
        
        switch (buttonId) {
            case 'retry':
                game_state.retryGame();
                break;
            case 'menu':
                game_state.returnToMenu();
                break;
            case 'leaderboard':
                game_state.showLeaderboard();
                break;
        }
    }
    
    function handleLeaderboardClick() {
        if (GameState.gameStatus !== 'leaderboard') return;
        
        game_state.closeLeaderboard();
    }
    
    return {
        init,
        render,
        handleMenuClick,
        handleGameOverClick,
        handleLeaderboardClick
    };
})();

const input_controller = (function() {
    let keyStates = {};
    let repeatTimers = {};
    let lastInputTime = 0;
    const REPEAT_DELAY = 150;
    const REPEAT_RATE = 50;
    
    function init() {
        keyStates = {};
        repeatTimers = {};
        lastInputTime = 0;
        
        document.addEventListener('keydown', (e) => {
            handleKeyDown(e.key);
            e.preventDefault();
        });
        
        document.addEventListener('keyup', (e) => {
            handleKeyUp(e.key);
            e.preventDefault();
        });
        
        document.addEventListener('click', (e) => {
            const rect = e.target.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            handleTouch(x, y);
        });
        
        document.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const rect = e.target.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            handleTouch(x, y);
        });
    }
    
    function update() {
        const currentTime = Date.now();
        
        if (GameState.gameStatus === 'gameplay') {
            for (const key in repeatTimers) {
                if (keyStates[key] && currentTime - repeatTimers[key] > REPEAT_RATE) {
                    processGameplayKey(key);
                    repeatTimers[key] = currentTime;
                }
            }
        }
    }
    
    function handleKeyDown(key) {
        const normalizedKey = normalizeKey(key);
        
        if (keyStates[normalizedKey]) {
            return;
        }
        
        keyStates[normalizedKey] = true;
        const currentTime = Date.now();
        
        if (GameState.gameStatus === 'gameplay') {
            processGameplayKey(normalizedKey);
            
            if (['ArrowLeft', 'ArrowRight', 'ArrowDown', 'a', 'd', 's'].includes(normalizedKey)) {
                repeatTimers[normalizedKey] = currentTime + REPEAT_DELAY;
            }
        } else if (GameState.gameStatus === 'main_menu') {
            processMenuKey(normalizedKey);
        } else if (GameState.gameStatus === 'game_over') {
            processGameOverKey(normalizedKey);
        } else if (GameState.gameStatus === 'leaderboard') {
            processLeaderboardKey(normalizedKey);
        }
    }
    
    function handleKeyUp(key) {
        const normalizedKey = normalizeKey(key);
        keyStates[normalizedKey] = false;
        delete repeatTimers[normalizedKey];
    }
    
    function handleTouch(x, y) {
        if (GameState.gameStatus === 'main_menu') {
            handleMenuTouch(x, y);
        } else if (GameState.gameStatus === 'gameplay') {
            handleGameplayTouch(x, y);
        } else if (GameState.gameStatus === 'game_over') {
            handleGameOverTouch(x, y);
        } else if (GameState.gameStatus === 'leaderboard') {
            handleLeaderboardTouch(x, y);
        }
    }
    
    function normalizeKey(key) {
        const keyMap = {
            'a': 'ArrowLeft',
            'A': 'ArrowLeft',
            'd': 'ArrowRight',
            'D': 'ArrowRight',
            's': 'ArrowDown',
            'S': 'ArrowDown',
            'w': 'ArrowUp',
            'W': 'ArrowUp',
            ' ': 'Space',
            'Enter': 'Enter',
            'Escape': 'Escape'
        };
        
        return keyMap[key] || key;
    }
    
    function processGameplayKey(key) {
        switch (key) {
            case 'ArrowLeft':
                TetrisEngine.movePiece('left');
                break;
            case 'ArrowRight':
                TetrisEngine.movePiece('right');
                break;
            case 'ArrowDown':
                TetrisEngine.movePiece('down');
                break;
            case 'ArrowUp':
                TetrisEngine.rotatePiece();
                break;
            case 'Space':
                TetrisEngine.dropPiece();
                break;
        }
    }
    
    function processMenuKey(key) {
        switch (key) {
            case 'Enter':
            case 'Space':
                ui_manager.handleMenuClick('start');
                break;
            case 'l':
            case 'L':
                ui_manager.handleMenuClick('leaderboard');
                break;
        }
    }
    
    function processGameOverKey(key) {
        switch (key) {
            case 'Enter':
            case 'Space':
                ui_manager.handleGameOverClick('retry');
                break;
            case 'Escape':
                ui_manager.handleGameOverClick('menu');
                break;
            case 'l':
            case 'L':
                ui_manager.handleGameOverClick('leaderboard');
                break;
        }
    }
    
    function processLeaderboardKey(key) {
        switch (key) {
            case 'Escape':
            case 'Enter':
            case 'Space':
                ui_manager.handleLeaderboardClick();
                break;
        }
    }
    
    function handleMenuTouch(x, y) {
        // Touch handling for menu buttons
    }
    
    function handleGameplayTouch(x, y) {
        // Touch handling for gameplay
    }
    
    function handleGameOverTouch(x, y) {
        // Touch handling for game over buttons
    }
    
    function handleLeaderboardTouch(x, y) {
        ui_manager.handleLeaderboardClick();
    }
    
    return {
        init,
        update,
        handleKeyDown,
        handleKeyUp,
        handleTouch
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
    
    // Update functions in order
    input_controller.update();
    TetrisEngine.update();
    
    // Render functions in order
    ui_manager.render();
    
    // Update screen visibility based on game state
    showScreen(GameState.gameStatus);
    
    if (GameState.gameStatus === 'gameplay') {
        requestAnimationFrame(gameLoop);
    } else {
        // Continue loop for other states too
        requestAnimationFrame(gameLoop);
    }
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('GAME_START');
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', {
        finalScore: GameState.score,
        linesCleared: GameState.linesCleared,
        level: GameState.level
    });
    showScreen('game_over');
}

function retry() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('RETRY');
    showScreen('gameplay');
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

// Initialize modules in order
document.addEventListener('DOMContentLoaded', function() {
    game_state.init();
    TetrisEngine.init();
    ui_manager.init();
    input_controller.init();
    
    // Set up button event listeners
    const btnStart = document.getElementById('btn_start');
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    const btnRetry = document.getElementById('btn_retry');
    const btnLeaderboardGo = document.getElementById('btn_leaderboard_go');
    const btnMenu = document.getElementById('btn_menu');
    const btnClose = document.getElementById('btn_close');
    
    if (btnStart) {
        btnStart.addEventListener('click', () => game_state.startGame());
    }
    
    if (btnLeaderboard) {
        btnLeaderboard.addEventListener('click', () => game_state.showLeaderboard());
    }
    
    if (btnRetry) {
        btnRetry.addEventListener('click', () => game_state.retryGame());
    }
    
    if (btnLeaderboardGo) {
        btnLeaderboardGo.addEventListener('click', () => game_state.showLeaderboard());
    }
    
    if (btnMenu) {
        btnMenu.addEventListener('click', () => game_state.returnToMenu());
    }
    
    if (btnClose) {
        btnClose.addEventListener('click', () => game_state.closeLeaderboard());
    }
    
    // Start the game loop
    requestAnimationFrame(gameLoop);
});