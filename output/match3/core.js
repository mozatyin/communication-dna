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
const GRID_SIZE = 8;
const TILE_SIZE = 120;
const TILE_TYPES = 6;
const MIN_MATCH_SIZE = 3;

// Shared State Objects
const GameState = {
    gameStatus: 'main_menu',
    score: 0,
    lives: 3,
    level: 1,
    movesRemaining: 30,
    targetScore: 1000
};

const GridState = {
    grid: [],
    selectedTile: 'none',
    animating: false,
    lastMatchCount: 0
};

// Game State Module
const game_state = (function() {
    function init() {
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.lives = 3;
        GameState.level = 1;
        GameState.movesRemaining = 30;
        GameState.targetScore = 1000;
        
        // Set up event listeners
        EventBus.on('START_GAME', handleStartGame);
        EventBus.on('RETRY_GAME', handleRetryGame);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('SHOW_LEADERBOARD', handleShowLeaderboard);
        EventBus.on('CLOSE_LEADERBOARD', handleCloseLeaderboard);
        EventBus.on('MATCH_FOUND', handleMatchFound);
        EventBus.on('NO_MOVES_AVAILABLE', handleNoMovesAvailable);
    }
    
    function startGame() {
        if (GameState.gameStatus === 'main_menu') {
            GameState.gameStatus = 'gameplay';
            GameState.score = 0;
            GameState.lives = 3;
            GameState.level = 1;
            GameState.movesRemaining = 30;
            GameState.targetScore = 1000;
            
            EventBus.emit('GAME_START', {});
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.gameStatus = 'game_over';
            
            EventBus.emit('GAME_OVER', { 
                finalScore: GameState.score,
                reason: GameState.lives <= 0 ? 'no_lives' : 'no_moves'
            });
        }
    }
    
    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
            
            if (GameState.score >= GameState.targetScore) {
                const bonus = GameState.movesRemaining * 100;
                GameState.score += bonus;
                GameState.level++;
                GameState.movesRemaining = 30;
                GameState.targetScore = Math.floor(GameState.targetScore * 1.5);
                
                EventBus.emit('LEVEL_COMPLETE', { 
                    level: GameState.level - 1,
                    bonus: bonus
                });
            }
        }
    }
    
    function decrementLives() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.lives--;
            return GameState.lives <= 0;
        }
        return false;
    }
    
    function showLeaderboard() {
        if (GameState.gameStatus === 'main_menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
        }
    }
    
    function hideLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
        }
    }
    
    // Event handlers
    function handleStartGame(event) {
        startGame();
    }
    
    function handleRetryGame(event) {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'main_menu';
            startGame();
        }
    }
    
    function handleReturnMenu(event) {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'main_menu';
        }
    }
    
    function handleShowLeaderboard(event) {
        showLeaderboard();
    }
    
    function handleCloseLeaderboard(event) {
        hideLeaderboard();
    }
    
    function handleMatchFound(event) {
        const { points } = event;
        addScore(points);
        GameState.movesRemaining--;
        if (GameState.movesRemaining <= 0 && GameState.score < GameState.targetScore) {
            endGame();
        }
    }
    
    function handleNoMovesAvailable(event) {
        if (decrementLives()) {
            endGame();
        }
    }
    
    return {
        init,
        startGame,
        endGame,
        addScore,
        decrementLives,
        showLeaderboard,
        hideLeaderboard
    };
})();

// Match Engine Module
const match_engine = (function() {
    function init() {
        GridState.grid = [];
        for (let row = 0; row < GRID_SIZE; row++) {
            GridState.grid[row] = [];
            for (let col = 0; col < GRID_SIZE; col++) {
                GridState.grid[row][col] = generateSafeTile(row, col);
            }
        }
        
        GridState.selectedTile = 'none';
        GridState.animating = false;
        GridState.lastMatchCount = 0;
    }
    
    function generateSafeTile(row, col) {
        let attempts = 0;
        let tileType;
        
        do {
            tileType = Math.floor(Math.random() * TILE_TYPES);
            attempts++;
        } while (attempts < 50 && wouldCreateMatch(row, col, tileType));
        
        return tileType;
    }
    
    function wouldCreateMatch(row, col, tileType) {
        let horizontalCount = 1;
        for (let c = col - 1; c >= 0 && GridState.grid[row] && GridState.grid[row][c] === tileType; c--) {
            horizontalCount++;
        }
        for (let c = col + 1; c < GRID_SIZE && GridState.grid[row] && GridState.grid[row][c] === tileType; c++) {
            horizontalCount++;
        }
        
        let verticalCount = 1;
        for (let r = row - 1; r >= 0 && GridState.grid[r] && GridState.grid[r][col] === tileType; r--) {
            verticalCount++;
        }
        for (let r = row + 1; r < GRID_SIZE && GridState.grid[r] && GridState.grid[r][col] === tileType; r++) {
            verticalCount++;
        }
        
        return horizontalCount >= MIN_MATCH_SIZE || verticalCount >= MIN_MATCH_SIZE;
    }
    
    function swapTiles(x1, y1, x2, y2) {
        if (GameState.gameStatus !== 'gameplay' || GridState.animating) {
            return false;
        }
        
        const dx = Math.abs(x2 - x1);
        const dy = Math.abs(y2 - y1);
        if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
            if (x1 >= 0 && x1 < GRID_SIZE && y1 >= 0 && y1 < GRID_SIZE &&
                x2 >= 0 && x2 < GRID_SIZE && y2 >= 0 && y2 < GRID_SIZE) {
                
                const temp = GridState.grid[y1][x1];
                GridState.grid[y1][x1] = GridState.grid[y2][x2];
                GridState.grid[y2][x2] = temp;
                
                const matchesFound = findMatches().length > 0;
                
                if (matchesFound) {
                    GridState.selectedTile = 'none';
                    processMatches();
                    return true;
                } else {
                    GridState.grid[y2][x2] = GridState.grid[y1][x1];
                    GridState.grid[y1][x1] = temp;
                    return false;
                }
            }
        }
        return false;
    }
    
    function findMatches() {
        const matches = [];
        const visited = Array(GRID_SIZE).fill().map(() => Array(GRID_SIZE).fill(false));
        
        for (let row = 0; row < GRID_SIZE; row++) {
            let count = 1;
            let currentType = GridState.grid[row][0];
            
            for (let col = 1; col < GRID_SIZE; col++) {
                if (GridState.grid[row][col] === currentType) {
                    count++;
                } else {
                    if (count >= MIN_MATCH_SIZE) {
                        for (let c = col - count; c < col; c++) {
                            if (!visited[row][c]) {
                                matches.push({row: row, col: c, type: currentType});
                                visited[row][c] = true;
                            }
                        }
                    }
                    count = 1;
                    currentType = GridState.grid[row][col];
                }
            }
            
            if (count >= MIN_MATCH_SIZE) {
                for (let c = GRID_SIZE - count; c < GRID_SIZE; c++) {
                    if (!visited[row][c]) {
                        matches.push({row: row, col: c, type: currentType});
                        visited[row][c] = true;
                    }
                }
            }
        }
        
        for (let col = 0; col < GRID_SIZE; col++) {
            let count = 1;
            let currentType = GridState.grid[0][col];
            
            for (let row = 1; row < GRID_SIZE; row++) {
                if (GridState.grid[row][col] === currentType) {
                    count++;
                } else {
                    if (count >= MIN_MATCH_SIZE) {
                        for (let r = row - count; r < row; r++) {
                            if (!visited[r][col]) {
                                matches.push({row: r, col: col, type: currentType});
                                visited[r][col] = true;
                            }
                        }
                    }
                    count = 1;
                    currentType = GridState.grid[row][col];
                }
            }
            
            if (count >= MIN_MATCH_SIZE) {
                for (let r = GRID_SIZE - count; r < GRID_SIZE; r++) {
                    if (!visited[r][col]) {
                        matches.push({row: r, col: col, type: currentType});
                        visited[r][col] = true;
                    }
                }
            }
        }
        
        return matches;
    }
    
    function processMatches() {
        if (GameState.gameStatus !== 'gameplay') {
            return 0;
        }
        
        let totalMatches = 0;
        let cascadeCount = 0;
        
        do {
            const matches = findMatches();
            if (matches.length === 0) break;
            
            matches.forEach(match => {
                GridState.grid[match.row][match.col] = -1;
            });
            
            if (matches.length > 0) {
                const matchCount = matches.length;
                const tileType = matches[0].type;
                const basePoints = matchCount * 10;
                const cascadeBonus = cascadeCount * 5;
                const points = basePoints + cascadeBonus;
                
                EventBus.emit('MATCH_FOUND', {
                    matchCount: matchCount,
                    tileType: tileType.toString(),
                    points: points
                });
                
                totalMatches += matchCount;
            }
            
            applyGravity();
            fillEmptySpaces();
            cascadeCount++;
            
        } while (true);
        
        GridState.lastMatchCount = totalMatches;
        GridState.animating = false;
        
        if (!hasValidMoves()) {
            EventBus.emit('NO_MOVES_AVAILABLE', {});
        }
        
        return totalMatches;
    }
    
    function applyGravity() {
        for (let col = 0; col < GRID_SIZE; col++) {
            const column = [];
            for (let row = GRID_SIZE - 1; row >= 0; row--) {
                if (GridState.grid[row][col] !== -1) {
                    column.push(GridState.grid[row][col]);
                }
            }
            
            for (let row = GRID_SIZE - 1; row >= 0; row--) {
                if (column.length > 0) {
                    GridState.grid[row][col] = column.shift();
                } else {
                    GridState.grid[row][col] = -1;
                }
            }
        }
    }
    
    function fillEmptySpaces() {
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (GridState.grid[row][col] === -1) {
                    GridState.grid[row][col] = Math.floor(Math.random() * TILE_TYPES);
                }
            }
        }
    }
    
    function hasValidMoves() {
        if (GameState.gameStatus !== 'gameplay') {
            return false;
        }
        
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (col < GRID_SIZE - 1) {
                    const temp = GridState.grid[row][col];
                    GridState.grid[row][col] = GridState.grid[row][col + 1];
                    GridState.grid[row][col + 1] = temp;
                    
                    const hasMatch = findMatches().length > 0;
                    
                    GridState.grid[row][col + 1] = GridState.grid[row][col];
                    GridState.grid[row][col] = temp;
                    
                    if (hasMatch) return true;
                }
                
                if (row < GRID_SIZE - 1) {
                    const temp = GridState.grid[row][col];
                    GridState.grid[row][col] = GridState.grid[row + 1][col];
                    GridState.grid[row + 1][col] = temp;
                    
                    const hasMatch = findMatches().length > 0;
                    
                    GridState.grid[row + 1][col] = GridState.grid[row][col];
                    GridState.grid[row][col] = temp;
                    
                    if (hasMatch) return true;
                }
            }
        }
        
        return false;
    }
    
    function shuffleBoard() {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        const tiles = [];
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                tiles.push(GridState.grid[row][col]);
            }
        }
        
        for (let i = tiles.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [tiles[i], tiles[j]] = [tiles[j], tiles[i]];
        }
        
        let tileIndex = 0;
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                GridState.grid[row][col] = tiles[tileIndex++];
            }
        }
        
        GridState.selectedTile = 'none';
    }
    
    function update(dt) {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
    }
    
    return {
        init,
        swapTiles,
        processMatches,
        hasValidMoves,
        shuffleBoard,
        update
    };
})();

// UI System Module
const ui_system = (function() {
    let canvas;
    let ctx;
    
    const GRID_OFFSET_X = 90;
    const GRID_OFFSET_Y = 300;
    
    const TILE_COLORS = {
        '0': '#FF6B6B',
        '1': '#4ECDC4',
        '2': '#45B7D1',
        '3': '#96CEB4',
        '4': '#FFEAA7',
        '5': '#DDA0DD'
    };

    function init() {
        canvas = document.getElementById('gameCanvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.id = 'gameCanvas';
            document.getElementById('gameplay').appendChild(canvas);
        }
        canvas.width = 980;
        canvas.height = 980;
        ctx = canvas.getContext('2d');
        
        canvas.style.display = 'block';
        canvas.style.backgroundColor = 'transparent';
    }

    function renderMainMenu() {
        // Main menu is handled by HTML/CSS
    }

    function renderGameplay() {
        if (GameState.gameStatus !== 'gameplay') return;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Update UI text elements
        document.getElementById('score_display').textContent = `得分: ${GameState.score}`;
        document.getElementById('moves_left').textContent = `步数: ${GameState.movesRemaining}`;
        document.getElementById('target').textContent = `目标: ${GameState.targetScore}`;
        document.getElementById('level_label').textContent = `第 ${GameState.level} 关`;
        
        renderGrid();
    }

    function renderGrid() {
        if (!GridState.grid || GridState.grid.length === 0) return;
        
        const tileSize = 120;
        
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                const tileType = GridState.grid[row][col];
                const x = col * tileSize + 10;
                const y = row * tileSize + 10;
                
                ctx.fillStyle = TILE_COLORS[tileType] || '#95A5A6';
                ctx.fillRect(x, y, tileSize - 4, tileSize - 4);
                
                ctx.strokeStyle = '#2C3E50';
                ctx.lineWidth = 2;
                ctx.strokeRect(x, y, tileSize - 4, tileSize - 4);
                
                if (GridState.selectedTile === `${col},${row}`) {
                    ctx.strokeStyle = '#F39C12';
                    ctx.lineWidth = 6;
                    ctx.strokeRect(x - 2, y - 2, tileSize, tileSize);
                }
                
                ctx.fillStyle = '#2C3E50';
                ctx.font = 'bold 48px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(tileType, x + tileSize / 2 - 2, y + tileSize / 2 + 16);
            }
        }
    }

    function renderGameOver() {
        document.getElementById('final_score').textContent = `最终得分: ${GameState.score}`;
    }

    function renderLeaderboard() {
        // Leaderboard is handled by HTML/CSS
    }

    function getClickedTile(x, y) {
        if (GameState.gameStatus !== 'gameplay') return 'none';
        
        const tileSize = 120;
        const gridStartX = 10;
        const gridStartY = 10;
        
        if (x < gridStartX || x > gridStartX + GRID_SIZE * tileSize ||
            y < gridStartY || y > gridStartY + GRID_SIZE * tileSize) {
            return 'none';
        }
        
        const col = Math.floor((x - gridStartX) / tileSize);
        const row = Math.floor((y - gridStartY) / tileSize);
        
        if (col < 0 || col >= GRID_SIZE || row < 0 || row >= GRID_SIZE) {
            return 'none';
        }
        
        return `${col},${row}`;
    }

    function render() {
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

    return {
        init,
        renderMainMenu,
        renderGameplay,
        renderGameOver,
        renderLeaderboard,
        getClickedTile,
        render
    };
})();

// Input Handler Module
const input_handler = (function() {
    let selectedTile = null;
    
    function init() {
        const canvas = document.getElementById('gameCanvas');
        if (canvas) {
            canvas.addEventListener('click', function(event) {
                const rect = canvas.getBoundingClientRect();
                const x = event.clientX - rect.left;
                const y = event.clientY - rect.top;
                handleClick(x, y);
            });
            
            canvas.addEventListener('touchstart', function(event) {
                event.preventDefault();
                const rect = canvas.getBoundingClientRect();
                const touch = event.touches[0];
                const x = touch.clientX - rect.left;
                const y = touch.clientY - rect.top;
                handleClick(x, y);
            });
        }
        
        document.addEventListener('keydown', function(event) {
            handleKeyPress(event.key);
        });
        
        EventBus.on('GAME_START', function() {
            selectedTile = null;
        });
    }
    
    function handleClick(x, y) {
        if (GameState.gameStatus === 'gameplay') {
            handleGameplayClick(x, y);
        }
    }
    
    function handleGameplayClick(x, y) {
        if (GridState.animating) {
            return;
        }
        
        const tilePos = ui_system.getClickedTile(x, y);
        if (tilePos === 'none') {
            selectedTile = null;
            return;
        }
        
        const [tileX, tileY] = tilePos.split(',').map(Number);
        
        if (selectedTile === null) {
            selectedTile = { x: tileX, y: tileY };
        } else {
            const dx = Math.abs(selectedTile.x - tileX);
            const dy = Math.abs(selectedTile.y - tileY);
            
            if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
                const swapSuccessful = match_engine.swapTiles(
                    selectedTile.x, selectedTile.y, 
                    tileX, tileY
                );
                
                if (swapSuccessful) {
                    selectedTile = null;
                } else {
                    selectedTile = { x: tileX, y: tileY };
                }
            } else {
                selectedTile = { x: tileX, y: tileY };
            }
        }
    }
    
    function handleKeyPress(key) {
        if (GameState.gameStatus === 'gameplay') {
            if (key === 'Escape') {
                selectedTile = null;
            }
        }
    }
    
    function update(dt) {
        if (GameState.gameStatus === 'gameplay') {
            if (selectedTile) {
                GridState.selectedTile = selectedTile.x + ',' + selectedTile.y;
            } else {
                GridState.selectedTile = 'none';
            }
        } else {
            GridState.selectedTile = 'none';
            selectedTile = null;
        }
    }
    
    return {
        init,
        handleClick,
        handleKeyPress,
        update
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

// State Transition Functions
function startGame() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('START_GAME', {});
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', { finalScore: GameState.score, reason: 'no_moves' });
    showScreen('game_over');
}

function retry() {
    GameState.gameStatus = 'main_menu';
    EventBus.emit('RETRY_GAME', {});
    startGame();
}

function returnToMenu() {
    GameState.gameStatus = 'main_menu';
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

function showLeaderboard() {
    GameState.gameStatus = 'leaderboard';
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
}

function closeLeaderboard() {
    GameState.gameStatus = 'main_menu';
    EventBus.emit('CLOSE_LEADERBOARD', {});
    showScreen('main_menu');
}

// Game Loop
let lastTime = 0;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions in order
    input_handler.update(dt);
    match_engine.update(dt);
    
    // Render functions in order
    ui_system.render();
    
    if (GameState.gameStatus === 'playing' || GameState.gameStatus === 'gameplay') {
        requestAnimationFrame(gameLoop);
    } else {
        requestAnimationFrame(gameLoop);
    }
}

// Initialize Game
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in order
    game_state.init();
    match_engine.init();
    ui_system.init();
    input_handler.init();
    
    // Set up button event listeners
    document.getElementById('btn_play').addEventListener('click', startGame);
    document.getElementById('btn_leaderboard').addEventListener('click', showLeaderboard);
    document.getElementById('btn_retry').addEventListener('click', retry);
    document.getElementById('btn_menu').addEventListener('click', returnToMenu);
    document.querySelectorAll('#btn_leaderboard').forEach(btn => {
        btn.addEventListener('click', showLeaderboard);
    });
    document.getElementById('btn_close').addEventListener('click', closeLeaderboard);
    
    // Start game loop
    requestAnimationFrame(gameLoop);
    
    // Show initial screen
    showScreen('main_menu');
});