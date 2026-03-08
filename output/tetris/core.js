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
const CELL_SIZE = 40;
const LINES_PER_LEVEL = 10;

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

// Module: game_state
const game_state = (function() {
    // Event listeners for consuming events
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
        if (GameState.gameStatus === 'main_menu') {
            startGame();
        }
    }

    function handleGameOver() {
        if (GameState.gameStatus === 'gameplay') {
            gameOver();
        }
    }

    function handleRetry() {
        if (GameState.gameStatus === 'game_over') {
            retry();
        }
    }

    function handleReturnMenu() {
        if (GameState.gameStatus === 'game_over') {
            returnToMenu();
        }
    }

    function handleShowLeaderboard() {
        if (GameState.gameStatus === 'main_menu' || GameState.gameStatus === 'game_over') {
            showLeaderboard();
        }
    }

    function handleCloseLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            closeLeaderboard();
        }
    }

    function handleLinesCleared(event) {
        if (GameState.gameStatus === 'gameplay') {
            addLines(event.linesCleared);
            addScore(event.points);
        }
    }

    function handlePieceLocked(event) {
        if (GameState.gameStatus === 'gameplay') {
            addScore(event.points);
        }
    }

    function loadHighScores() {
        const saved = localStorage.getItem('tetris_high_scores');
        if (saved) {
            try {
                HighScores.scores = JSON.parse(saved);
            } catch (e) {
                HighScores.scores = [];
            }
        } else {
            HighScores.scores = [];
        }
    }

    function saveHighScores() {
        localStorage.setItem('tetris_high_scores', JSON.stringify(HighScores.scores));
    }

    function updateHighScore(score) {
        HighScores.scores.push(score);
        HighScores.scores.sort((a, b) => b - a);
        HighScores.scores = HighScores.scores.slice(0, 5);
        saveHighScores();
    }

    function init() {
        // Initialize GameState with default values
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.level = 1;
        GameState.lines = 0;
        GameState.isPaused = false;

        // Initialize HighScores
        loadHighScores();

        // Setup event listeners
        setupEventListeners();
    }

    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            GameState.level = 1;
            GameState.lines = 0;
            GameState.isPaused = false;
        }
    }

    function gameOver() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.gameStatus = 'game_over';
            updateHighScore(GameState.score);
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
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            GameState.level = 1;
            GameState.lines = 0;
            GameState.isPaused = false;
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

// Module: tetris_engine
const tetris_engine = (function() {
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

    const PIECE_TYPES = Object.keys(TETROMINOES);
    
    let fallTimer = 0;
    let fallSpeed = 1000; // milliseconds
    let lastTime = 0;

    function init() {
        // Initialize grid
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
        
        fallTimer = 0;
        lastTime = Date.now();
    }

    function generateRandomPiece() {
        const type = PIECE_TYPES[Math.floor(Math.random() * PIECE_TYPES.length)];
        const tetromino = TETROMINOES[type];
        
        return {
            type: type,
            shape: tetromino.shape.map(row => [...row]),
            color: tetromino.color,
            x: Math.floor(GRID_WIDTH / 2) - Math.floor(tetromino.shape[0].length / 2),
            y: 0
        };
    }

    function spawnNewPiece() {
        TetrisGrid.currentPiece = TetrisGrid.nextPiece;
        TetrisGrid.nextPiece = generateRandomPiece();
        
        // Check if game over
        if (isCollision(TetrisGrid.currentPiece, TetrisGrid.currentPiece.x, TetrisGrid.currentPiece.y)) {
            // Emit game over event
            EventBus.emit('GAME_OVER', {});
            return false;
        }
        
        updateGhostPiece();
        return true;
    }

    function updateGhostPiece() {
        if (!TetrisGrid.currentPiece) return;
        
        TetrisGrid.ghostPiece = {
            ...TetrisGrid.currentPiece,
            shape: TetrisGrid.currentPiece.shape.map(row => [...row])
        };
        
        // Drop ghost piece to bottom
        while (!isCollision(TetrisGrid.ghostPiece, TetrisGrid.ghostPiece.x, TetrisGrid.ghostPiece.y + 1)) {
            TetrisGrid.ghostPiece.y++;
        }
    }

    function isCollision(piece, newX, newY) {
        if (!piece) return false;
        
        for (let row = 0; row < piece.shape.length; row++) {
            for (let col = 0; col < piece.shape[row].length; col++) {
                if (piece.shape[row][col]) {
                    const gridX = newX + col;
                    const gridY = newY + row;
                    
                    // Check boundaries
                    if (gridX < 0 || gridX >= GRID_WIDTH || gridY >= GRID_HEIGHT) {
                        return true;
                    }
                    
                    // Check collision with existing blocks
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
        
        // Place piece on grid
        for (let row = 0; row < TetrisGrid.currentPiece.shape.length; row++) {
            for (let col = 0; col < TetrisGrid.currentPiece.shape[row].length; col++) {
                if (TetrisGrid.currentPiece.shape[row][col]) {
                    const gridX = TetrisGrid.currentPiece.x + col;
                    const gridY = TetrisGrid.currentPiece.y + row;
                    
                    if (gridY >= 0) {
                        TetrisGrid.grid[gridY][gridX] = TetrisGrid.currentPiece.color;
                    }
                }
            }
        }
        
        // Emit piece locked event
        EventBus.emit('PIECE_LOCKED', { points: 10 });
        
        // Clear completed lines
        clearLines();
        
        // Spawn new piece
        spawnNewPiece();
    }

    function clearLines() {
        let linesCleared = 0;
        let completedLines = [];
        
        // Find completed lines
        for (let row = GRID_HEIGHT - 1; row >= 0; row--) {
            let isComplete = true;
            for (let col = 0; col < GRID_WIDTH; col++) {
                if (!TetrisGrid.grid[row][col]) {
                    isComplete = false;
                    break;
                }
            }
            if (isComplete) {
                completedLines.push(row);
            }
        }
        
        // Remove completed lines and drop above rows
        for (let lineIndex of completedLines) {
            TetrisGrid.grid.splice(lineIndex, 1);
            TetrisGrid.grid.unshift(new Array(GRID_WIDTH).fill(0));
            linesCleared++;
        }
        
        if (linesCleared > 0) {
            // Calculate points based on lines cleared
            const pointsTable = [0, 100, 300, 500, 800];
            const points = pointsTable[Math.min(linesCleared, 4)] * GameState.level;
            
            // Emit lines cleared event
            EventBus.emit('LINES_CLEARED', {
                linesCleared: linesCleared,
                points: points
            });
        }
    }

    function rotatePieceClockwise(piece) {
        const rotated = [];
        const size = piece.shape.length;
        
        for (let row = 0; row < size; row++) {
            rotated[row] = [];
            for (let col = 0; col < size; col++) {
                rotated[row][col] = piece.shape[size - 1 - col][row];
            }
        }
        
        return {
            ...piece,
            shape: rotated
        };
    }

    function updateFallSpeed() {
        // Increase speed based on level
        fallSpeed = Math.max(50, 1000 - (GameState.level - 1) * 100);
    }

    function update() {
        if (GameState.gameStatus !== 'gameplay' || GameState.isPaused) {
            return;
        }
        
        const currentTime = Date.now();
        const deltaTime = currentTime - lastTime;
        lastTime = currentTime;
        
        // Initialize first piece if needed
        if (!TetrisGrid.currentPiece && !TetrisGrid.nextPiece) {
            TetrisGrid.nextPiece = generateRandomPiece();
        }
        
        if (!TetrisGrid.currentPiece) {
            spawnNewPiece();
            return;
        }
        
        updateFallSpeed();
        
        // Handle automatic falling
        fallTimer += deltaTime;
        if (fallTimer >= fallSpeed) {
            if (!movePiece('down')) {
                lockPiece();
            }
            fallTimer = 0;
        }
    }

    function movePiece(direction) {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return false;
        }
        
        let newX = TetrisGrid.currentPiece.x;
        let newY = TetrisGrid.currentPiece.y;
        
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
        
        if (!isCollision(TetrisGrid.currentPiece, newX, newY)) {
            TetrisGrid.currentPiece.x = newX;
            TetrisGrid.currentPiece.y = newY;
            updateGhostPiece();
            return true;
        }
        
        return false;
    }

    function rotatePiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return false;
        }
        
        const rotatedPiece = rotatePieceClockwise(TetrisGrid.currentPiece);
        
        if (!isCollision(rotatedPiece, rotatedPiece.x, rotatedPiece.y)) {
            TetrisGrid.currentPiece = rotatedPiece;
            updateGhostPiece();
            return true;
        }
        
        // Try wall kicks
        const wallKicks = [
            { x: -1, y: 0 },
            { x: 1, y: 0 },
            { x: 0, y: -1 },
            { x: -2, y: 0 },
            { x: 2, y: 0 }
        ];
        
        for (let kick of wallKicks) {
            const kickX = rotatedPiece.x + kick.x;
            const kickY = rotatedPiece.y + kick.y;
            
            if (!isCollision(rotatedPiece, kickX, kickY)) {
                TetrisGrid.currentPiece = rotatedPiece;
                TetrisGrid.currentPiece.x = kickX;
                TetrisGrid.currentPiece.y = kickY;
                updateGhostPiece();
                return true;
            }
        }
        
        return false;
    }

    function dropPiece() {
        if (GameState.gameStatus !== 'gameplay' || !TetrisGrid.currentPiece) {
            return;
        }
        
        let dropDistance = 0;
        while (!isCollision(TetrisGrid.currentPiece, TetrisGrid.currentPiece.x, TetrisGrid.currentPiece.y + 1)) {
            TetrisGrid.currentPiece.y++;
            dropDistance++;
        }
        
        // Award points for hard drop
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

// Module: ui_manager
const ui_manager = (function() {
    let canvas;
    let ctx;
    let buttons = {};
    
    const COLORS = {
        background: '#0a0a0a',
        neon: '#00ffff',
        neonGlow: '#0088ff',
        text: '#ffffff',
        grid: '#333333',
        gridBorder: '#666666',
        button: '#1a1a1a',
        buttonHover: '#2a2a2a',
        buttonBorder: '#00ffff',
        I: '#00ffff',
        O: '#ffff00',
        T: '#800080',
        S: '#00ff00',
        Z: '#ff0000',
        J: '#0000ff',
        L: '#ffa500',
        ghost: 'rgba(255, 255, 255, 0.3)'
    };
    
    const PIECE_COLORS = {
        'I': COLORS.I,
        'O': COLORS.O,
        'T': COLORS.T,
        'S': COLORS.S,
        'Z': COLORS.Z,
        'J': COLORS.J,
        'L': COLORS.L
    };
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        ctx = canvas.getContext('2d');
        canvas.width = CANVAS_WIDTH;
        canvas.height = CANVAS_HEIGHT;
        
        setupButtons();
    }
    
    function setupButtons() {
        buttons = {
            mainMenu: {
                start: { x: 340, y: 800, width: 400, height: 80, text: '开始游戏' },
                leaderboard: { x: 340, y: 920, width: 400, height: 80, text: '排行榜' }
            },
            gameOver: {
                retry: { x: 240, y: 1200, width: 200, height: 80, text: '重试' },
                menu: { x: 640, y: 1200, width: 200, height: 80, text: '主菜单' },
                leaderboard: { x: 340, y: 1320, width: 400, height: 80, text: '查看排行榜' }
            },
            leaderboard: {
                close: { x: 340, y: 1400, width: 400, height: 80, text: '返回' }
            }
        };
    }
    
    function render() {
        clearCanvas();
        
        switch (GameState.gameStatus) {
            case 'main_menu':
                renderMainMenu();
                break;
            case 'gameplay':
                renderGameplay();
                break;
            case 'game_over':
                renderGameOver();
                break;
            case 'leaderboard':
                renderLeaderboard();
                break;
        }
    }
    
    function clearCanvas() {
        ctx.fillStyle = COLORS.background;
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    }
    
    function renderMainMenu() {
        // Title with neon effect
        ctx.save();
        ctx.shadowColor = COLORS.neonGlow;
        ctx.shadowBlur = 20;
        ctx.fillStyle = COLORS.neon;
        ctx.font = 'bold 120px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('TETRIS', CANVAS_WIDTH / 2, 300);
        
        ctx.shadowBlur = 10;
        ctx.font = 'bold 60px Arial';
        ctx.fillText('俄罗斯方块', CANVAS_WIDTH / 2, 400);
        ctx.restore();
        
        // Buttons
        renderButton(buttons.mainMenu.start);
        renderButton(buttons.mainMenu.leaderboard);
    }
    
    function renderGameplay() {
        // Game grid
        renderGrid();
        
        // Current piece
        if (TetrisGrid.currentPiece) {
            renderPiece(TetrisGrid.currentPiece, false);
        }
        
        // Ghost piece
        if (TetrisGrid.ghostPiece) {
            renderPiece(TetrisGrid.ghostPiece, true);
        }
        
        // Next piece preview
        renderNextPiece();
        
        // Score display
        renderGameStats();
    }
    
    function renderGrid() {
        const gridX = (CANVAS_WIDTH - GRID_WIDTH * CELL_SIZE) / 2;
        const gridY = 200;
        
        // Grid background
        ctx.fillStyle = COLORS.grid;
        ctx.fillRect(gridX, gridY, GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE);
        
        // Grid lines
        ctx.strokeStyle = COLORS.gridBorder;
        ctx.lineWidth = 1;
        
        for (let x = 0; x <= GRID_WIDTH; x++) {
            ctx.beginPath();
            ctx.moveTo(gridX + x * CELL_SIZE, gridY);
            ctx.lineTo(gridX + x * CELL_SIZE, gridY + GRID_HEIGHT * CELL_SIZE);
            ctx.stroke();
        }
        
        for (let y = 0; y <= GRID_HEIGHT; y++) {
            ctx.beginPath();
            ctx.moveTo(gridX, gridY + y * CELL_SIZE);
            ctx.lineTo(gridX + GRID_WIDTH * CELL_SIZE, gridY + y * CELL_SIZE);
            ctx.stroke();
        }
        
        // Placed blocks
        if (TetrisGrid.grid && TetrisGrid.grid.length > 0) {
            for (let y = 0; y < GRID_HEIGHT; y++) {
                for (let x = 0; x < GRID_WIDTH; x++) {
                    if (TetrisGrid.grid[y] && TetrisGrid.grid[y][x]) {
                        const color = PIECE_COLORS[TetrisGrid.grid[y][x]] || COLORS.text;
                        ctx.fillStyle = color;
                        ctx.fillRect(
                            gridX + x * CELL_SIZE + 1,
                            gridY + y * CELL_SIZE + 1,
                            CELL_SIZE - 2,
                            CELL_SIZE - 2
                        );
                    }
                }
            }
        }
    }
    
    function renderPiece(piece, isGhost) {
        if (!piece || !piece.shape || !piece.shape.length) return;
        
        const gridX = (CANVAS_WIDTH - GRID_WIDTH * CELL_SIZE) / 2;
        const gridY = 200;
        const color = isGhost ? COLORS.ghost : (PIECE_COLORS[piece.type] || COLORS.text);
        
        ctx.fillStyle = color;
        
        for (let y = 0; y < piece.shape.length; y++) {
            for (let x = 0; x < piece.shape[y].length; x++) {
                if (piece.shape[y][x]) {
                    const drawX = gridX + (piece.x + x) * CELL_SIZE + 1;
                    const drawY = gridY + (piece.y + y) * CELL_SIZE + 1;
                    
                    if (isGhost) {
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 2;
                        ctx.strokeRect(drawX, drawY, CELL_SIZE - 2, CELL_SIZE - 2);
                    } else {
                        ctx.fillRect(drawX, drawY, CELL_SIZE - 2, CELL_SIZE - 2);
                    }
                }
            }
        }
    }
    
    function renderNextPiece() {
        if (!TetrisGrid.nextPiece) return;
        
        const previewX = 800;
        const previewY = 300;
        const previewSize = 30;
        
        // Preview box
        ctx.strokeStyle = COLORS.gridBorder;
        ctx.lineWidth = 2;
        ctx.strokeRect(previewX - 10, previewY - 10, 140, 140);
        
        // Next piece label
        ctx.fillStyle = COLORS.text;
        ctx.font = '24px Arial';
        ctx.textAlign = 'left';
        ctx.fillText('下一个:', previewX, previewY - 20);
        
        // Next piece
        const piece = TetrisGrid.nextPiece;
        const color = PIECE_COLORS[piece.type] || COLORS.text;
        ctx.fillStyle = color;
        
        if (piece.shape) {
            for (let y = 0; y < piece.shape.length; y++) {
                for (let x = 0; x < piece.shape[y].length; x++) {
                    if (piece.shape[y][x]) {
                        ctx.fillRect(
                            previewX + x * previewSize,
                            previewY + y * previewSize,
                            previewSize - 2,
                            previewSize - 2
                        );
                    }
                }
            }
        }
    }
    
    function renderGameStats() {
        ctx.fillStyle = COLORS.text;
        ctx.font = '32px Arial';
        ctx.textAlign = 'left';
        
        const statsX = 50;
        let statsY = 300;
        const lineHeight = 50;
        
        ctx.fillText(`分数: ${GameState.score}`, statsX, statsY);
        statsY += lineHeight;
        ctx.fillText(`等级: ${GameState.level}`, statsX, statsY);
        statsY += lineHeight;
        ctx.fillText(`行数: ${GameState.lines}`, statsX, statsY);
        
        if (GameState.isPaused) {
            ctx.fillStyle = COLORS.neon;
            ctx.font = 'bold 48px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('暂停', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2);
        }
    }
    
    function renderGameOver() {
        // Semi-transparent overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Game Over title
        ctx.fillStyle = COLORS.neon;
        ctx.font = 'bold 80px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('游戏结束', CANVAS_WIDTH / 2, 400);
        
        // Final stats
        ctx.fillStyle = COLORS.text;
        ctx.font = '36px Arial';
        let y = 600;
        const lineHeight = 60;
        
        ctx.fillText(`最终分数: ${GameState.score}`, CANVAS_WIDTH / 2, y);
        y += lineHeight;
        ctx.fillText(`清除行数: ${GameState.lines}`, CANVAS_WIDTH / 2, y);
        y += lineHeight;
        ctx.fillText(`达到等级: ${GameState.level}`, CANVAS_WIDTH / 2, y);
        
        // Buttons
        renderButton(buttons.gameOver.retry);
        renderButton(buttons.gameOver.menu);
        renderButton(buttons.gameOver.leaderboard);
    }
    
    function renderLeaderboard() {
        // Semi-transparent overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.9)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Leaderboard title
        ctx.fillStyle = COLORS.neon;
        ctx.font = 'bold 60px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('排行榜', CANVAS_WIDTH / 2, 300);
        
        // High scores
        ctx.fillStyle = COLORS.text;
        ctx.font = '32px Arial';
        
        let y = 450;
        const lineHeight = 80;
        
        if (HighScores.scores && HighScores.scores.length > 0) {
            for (let i = 0; i < Math.min(5, HighScores.scores.length); i++) {
                const score = HighScores.scores[i];
                ctx.fillText(`${i + 1}. ${score} 分`, CANVAS_WIDTH / 2, y);
                y += lineHeight;
            }
        } else {
            ctx.fillText('暂无记录', CANVAS_WIDTH / 2, y);
        }
        
        // Close button
        renderButton(buttons.leaderboard.close);
    }
    
    function renderButton(button) {
        // Button background
        ctx.fillStyle = COLORS.button;
        ctx.fillRect(button.x, button.y, button.width, button.height);
        
        // Button border
        ctx.strokeStyle = COLORS.buttonBorder;
        ctx.lineWidth = 2;
        ctx.strokeRect(button.x, button.y, button.width, button.height);
        
        // Button text
        ctx.fillStyle = COLORS.text;
        ctx.font = '32px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(
            button.text,
            button.x + button.width / 2,
            button.y + button.height / 2 + 10
        );
    }
    
    function handleMenuClick(buttonId) {
        if (GameState.gameStatus !== 'main_menu') return;
        
        switch (buttonId) {
            case 'start':
                EventBus.emit('GAME_START', {});
                break;
            case 'leaderboard':
                EventBus.emit('SHOW_LEADERBOARD', {});
                break;
        }
    }
    
    function handleGameOverClick(buttonId) {
        if (GameState.gameStatus !== 'game_over') return;
        
        switch (buttonId) {
            case 'retry':
                EventBus.emit('RETRY', {});
                break;
            case 'menu':
                EventBus.emit('RETURN_MENU', {});
                break;
            case 'leaderboard':
                EventBus.emit('SHOW_LEADERBOARD', {});
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

// Module: input_controller
const input_controller = (function() {
    let pressedKeys = {};
    let keyRepeatTimers = {};
    let lastMoveTime = 0;
    let lastDropTime = 0;
    const MOVE_REPEAT_DELAY = 150;
    const DROP_REPEAT_DELAY = 50;
    
    function init() {
        // Event listeners will be attached by the main game loop
        // This just initializes internal state
        pressedKeys = {};
        keyRepeatTimers = {};
        lastMoveTime = 0;
        lastDropTime = 0;
    }
    
    function update() {
        const currentTime = Date.now();
        
        // Handle continuous key presses during gameplay
        if (GameState.gameStatus === 'gameplay') {
            // Left/Right movement with repeat
            if (pressedKeys['ArrowLeft'] && currentTime - lastMoveTime > MOVE_REPEAT_DELAY) {
                tetris_engine.movePiece('left');
                lastMoveTime = currentTime;
            }
            if (pressedKeys['ArrowRight'] && currentTime - lastMoveTime > MOVE_REPEAT_DELAY) {
                tetris_engine.movePiece('right');
                lastMoveTime = currentTime;
            }
            
            // Soft drop with faster repeat
            if (pressedKeys['ArrowDown'] && currentTime - lastDropTime > DROP_REPEAT_DELAY) {
                tetris_engine.movePiece('down');
                lastDropTime = currentTime;
            }
        }
    }
    
    function handleKeyDown(keyCode) {
        // Prevent repeat for keys that were already pressed
        const wasPressed = pressedKeys[keyCode];
        pressedKeys[keyCode] = true;
        
        if (GameState.gameStatus === 'gameplay') {
            switch (keyCode) {
                case 'ArrowLeft':
                    if (!wasPressed) {
                        tetris_engine.movePiece('left');
                        lastMoveTime = Date.now();
                    }
                    break;
                case 'ArrowRight':
                    if (!wasPressed) {
                        tetris_engine.movePiece('right');
                        lastMoveTime = Date.now();
                    }
                    break;
                case 'ArrowDown':
                    if (!wasPressed) {
                        tetris_engine.movePiece('down');
                        lastDropTime = Date.now();
                    }
                    break;
                case 'ArrowUp':
                case ' ':
                    if (!wasPressed) {
                        tetris_engine.rotatePiece();
                    }
                    break;
                case 'Enter':
                    if (!wasPressed) {
                        tetris_engine.dropPiece();
                    }
                    break;
                case 'Escape':
                    if (!wasPressed) {
                        // Emit event to return to menu
                        EventBus.emit('RETURN_MENU', {});
                    }
                    break;
            }
        } else if (GameState.gameStatus === 'main_menu') {
            switch (keyCode) {
                case 'Enter':
                case ' ':
                    if (!wasPressed) {
                        EventBus.emit('GAME_START', {});
                    }
                    break;
                case 'l':
                case 'L':
                    if (!wasPressed) {
                        EventBus.emit('SHOW_LEADERBOARD', {});
                    }
                    break;
            }
        } else if (GameState.gameStatus === 'game_over') {
            switch (keyCode) {
                case 'r':
                case 'R':
                case 'Enter':
                    if (!wasPressed) {
                        EventBus.emit('RETRY', {});
                    }
                    break;
                case 'Escape':
                case 'm':
                case 'M':
                    if (!wasPressed) {
                        EventBus.emit('RETURN_MENU', {});
                    }
                    break;
                case 'l':
                case 'L':
                    if (!wasPressed) {
                        EventBus.emit('SHOW_LEADERBOARD', {});
                    }
                    break;
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            switch (keyCode) {
                case 'Escape':
                case 'Enter':
                case ' ':
                    if (!wasPressed) {
                        EventBus.emit('CLOSE_LEADERBOARD', {});
                    }
                    break;
            }
        }
    }
    
    function handleKeyUp(keyCode) {
        pressedKeys[keyCode] = false;
        
        // Clear any repeat timers
        if (keyRepeatTimers[keyCode]) {
            clearTimeout(keyRepeatTimers[keyCode]);
            delete keyRepeatTimers[keyCode];
        }
    }
    
    function handleTouch(x, y) {
        // Convert touch coordinates to game actions based on screen regions
        const canvasWidth = CANVAS_WIDTH;
        const canvasHeight = CANVAS_HEIGHT;
        
        if (GameState.gameStatus === 'main_menu') {
            // Check if touch is on start button area (center of screen)
            if (x > canvasWidth * 0.2 && x < canvasWidth * 0.8 && 
                y > canvasHeight * 0.5 && y < canvasHeight * 0.65) {
                ui_manager.handleMenuClick('start');
            }
            // Check if touch is on leaderboard button area
            else if (x > canvasWidth * 0.2 && x < canvasWidth * 0.8 && 
                     y > canvasHeight * 0.7 && y < canvasHeight * 0.85) {
                ui_manager.handleMenuClick('leaderboard');
            }
        } else if (GameState.gameStatus === 'gameplay') {
            // Divide screen into touch zones for gameplay
            const leftZone = canvasWidth * 0.25;
            const rightZone = canvasWidth * 0.75;
            const topZone = canvasHeight * 0.3;
            const bottomZone = canvasHeight * 0.8;
            
            if (y < topZone) {
                // Top area - rotate
                tetris_engine.rotatePiece();
            } else if (y > bottomZone) {
                // Bottom area - hard drop
                tetris_engine.dropPiece();
            } else if (x < leftZone) {
                // Left area - move left
                tetris_engine.movePiece('left');
            } else if (x > rightZone) {
                // Right area - move right
                tetris_engine.movePiece('right');
            } else {
                // Center area - soft drop
                tetris_engine.movePiece('down');
            }
        } else if (GameState.gameStatus === 'game_over') {
            // Check retry button area
            if (x > canvasWidth * 0.1 && x < canvasWidth * 0.45 && 
                y > canvasHeight * 0.7 && y < canvasHeight * 0.85) {
                ui_manager.handleGameOverClick('retry');
            }
            // Check menu button area
            else if (x > canvasWidth * 0.55 && x < canvasWidth * 0.9 && 
                     y > canvasHeight * 0.7 && y < canvasHeight * 0.85) {
                ui_manager.handleGameOverClick('menu');
            }
            // Check leaderboard button area
            else if (x > canvasWidth * 0.2 && x < canvasWidth * 0.8 && 
                     y > canvasHeight * 0.9 && y < canvasHeight * 0.95) {
                ui_manager.handleGameOverClick('leaderboard');
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            // Any touch closes leaderboard
            EventBus.emit('CLOSE_LEADERBOARD', {});
        }
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
function showScreen(screenId) {
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.style.display = 'none';
        screen.classList.remove('active');
    });
    
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.style.display = 'flex';
        targetScreen.classList.add('active');
    }
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
    tetris_engine.init();
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', {});
    showScreen('game_over');
    updateGameOverDisplay();
}

function retry() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('RETRY', {});
    showScreen('gameplay');
    tetris_engine.init();
}

function returnToMenu() {
    GameState.gameStatus = 'main_menu';
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
    updateHighScoreDisplay();
}

function showLeaderboard() {
    GameState.gameStatus = 'leaderboard';
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
    updateLeaderboardDisplay();
}

function closeLeaderboard() {
    GameState.gameStatus = 'main_menu';
    EventBus.emit('CLOSE_LEADERBOARD', {});
    showScreen('main_menu');
}

// UI update functions
function updateHighScoreDisplay() {
    const highScoreElement = document.getElementById('high_score');
    if (highScoreElement && HighScores.scores.length > 0) {
        highScoreElement.textContent = `最高分: ${HighScores.scores[0]}`;
    }
}

function updateGameOverDisplay() {
    const finalScore = document.getElementById('final_score');
    const finalLines = document.getElementById('final_lines');
    const finalLevel = document.getElementById('final_level');
    
    if (finalScore) finalScore.textContent = `最终分数: ${GameState.score}`;
    if (finalLines) finalLines.textContent = `清除行数: ${GameState.lines}`;
    if (finalLevel) finalLevel.textContent = `达到等级: ${GameState.level}`;
}

function updateLeaderboardDisplay() {
    const scoresList = document.getElementById('scores_list');
    if (!scoresList) return;
    
    scoresList.innerHTML = '';
    
    if (HighScores.scores.length === 0) {
        const noScores = document.createElement('div');
        noScores.className = 'score-item';
        noScores.textContent = '暂无记录';
        scoresList.appendChild(noScores);
    } else {
        for (let i = 0; i < Math.min(5, HighScores.scores.length); i++) {
            const scoreItem = document.createElement('div');
            scoreItem.className = 'score-item';
            scoreItem.textContent = `${i + 1}. ${HighScores.scores[i]} 分`;
            scoresList.appendChild(scoreItem);
        }
    }
}

// Game loop
let lastTime = 0;
let gameRunning = false;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions in order
    input_controller.update();
    tetris_engine.update();
    
    // Render functions in order
    ui_manager.render();
    
    if (gameRunning) {
        requestAnimationFrame(gameLoop);
    }
}

// Input handlers
function setupInputHandlers() {
    // Keyboard events
    document.addEventListener('keydown', (e) => {
        e.preventDefault();
        input_controller.handleKeyDown(e.code);
    });
    
    document.addEventListener('keyup', (e) => {
        e.preventDefault();
        input_controller.handleKeyUp(e.code);
    });
    
    // Mouse/touch events for canvas
    const canvas = document.getElementById('gameCanvas');
    if (canvas) {
        canvas.addEventListener('click', (e) => {
            const rect = canvas.getBoundingClientRect();
            const scaleX = CANVAS_WIDTH / rect.width;
            const scaleY = CANVAS_HEIGHT / rect.height;
            const x = (e.clientX - rect.left) * scaleX;
            const y = (e.clientY - rect.top) * scaleY;
            input_controller.handleTouch(x, y);
        });
        
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const touch = e.touches[0];
            const scaleX = CANVAS_WIDTH / rect.width;
            const scaleY = CANVAS_HEIGHT / rect.height;
            const x = (touch.clientX - rect.left) * scaleX;
            const y = (touch.clientY - rect.top) * scaleY;
            input_controller.handleTouch(x, y);
        });
    }
    
    // Button click handlers
    document.getElementById('btn_start')?.addEventListener('click', () => {
        EventBus.emit('GAME_START', {});
    });
    
    document.getElementById('btn_leaderboard')?.addEventListener('click', () => {
        EventBus.emit('SHOW_LEADERBOARD', {});
    });
    
    document.getElementById('btn_retry')?.addEventListener('click', () => {
        EventBus.emit('RETRY', {});
    });
    
    document.getElementById('btn_menu')?.addEventListener('click', () => {
        EventBus.emit('RETURN_MENU', {});
    });
    
    document.getElementById('btn_game_over_leaderboard')?.addEventListener('click', () => {
        EventBus.emit('SHOW_LEADERBOARD', {});
    });
    
    document.getElementById('btn_close_leaderboard')?.addEventListener('click', () => {
        EventBus.emit('CLOSE_LEADERBOARD', {});
    });
}

// EventBus listeners for state transitions
EventBus.on('GAME_START', startGame);
EventBus.on('GAME_OVER', gameOver);
EventBus.on('RETRY', retry);
EventBus.on('RETURN_MENU', returnToMenu);
EventBus.on('SHOW_LEADERBOARD', showLeaderboard);
EventBus.on('CLOSE_LEADERBOARD', closeLeaderboard);

// Initialize game
function initGame() {
    // Initialize modules in order
    game_state.init();
    tetris_engine.init();
    ui_manager.init();
    input_controller.init();
    
    // Setup input handlers
    setupInputHandlers();
    
    // Show initial screen
    showScreen('main_menu');
    updateHighScoreDisplay();
    
    // Start game loop
    gameRunning = true;
    lastTime = performance.now();
    requestAnimationFrame(gameLoop);
}

// Start the game when page loads
document.addEventListener('DOMContentLoaded', initGame);