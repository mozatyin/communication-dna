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
const GRID_SIZE = 8;
const TILE_SIZE = 100;
const TILE_TYPES = 6;
const MIN_MATCH_SIZE = 3;

// Shared state objects
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
    selectedTile: null,
    animating: false,
    gridWidth: 8,
    gridHeight: 8
};

// Module code
const game_state = (function() {
    function init() {
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.lives = 3;
        GameState.level = 1;
        GameState.movesRemaining = 30;
        GameState.targetScore = 1000;

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
            EventBus.emit('GAME_OVER', { finalScore: GameState.score });
        }
    }

    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
            
            if (GameState.score >= GameState.targetScore) {
                GameState.level++;
                GameState.targetScore = Math.floor(GameState.targetScore * 1.5);
                GameState.movesRemaining = 30;
                EventBus.emit('LEVEL_COMPLETE', { newLevel: GameState.level });
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

    function returnToMenu() {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'main_menu';
        }
    }

    function handleStartGame() {
        startGame();
    }

    function handleRetryGame() {
        if (GameState.gameStatus === 'game_over') {
            startGame();
        }
    }

    function handleReturnMenu() {
        returnToMenu();
    }

    function handleShowLeaderboard() {
        showLeaderboard();
    }

    function handleCloseLeaderboard() {
        returnToMenu();
    }

    function handleMatchFound(payload) {
        if (GameState.gameStatus === 'gameplay') {
            addScore(payload.points);
            GameState.movesRemaining--;
            
            if (GameState.movesRemaining <= 0) {
                endGame();
            }
        }
    }

    function handleNoMovesAvailable() {
        if (GameState.gameStatus === 'gameplay') {
            if (decrementLives()) {
                endGame();
            }
        }
    }

    return {
        init,
        startGame,
        endGame,
        addScore,
        decrementLives,
        showLeaderboard,
        returnToMenu
    };
})();

const match_engine = (function() {
    function init() {
        GridState.gridWidth = GRID_SIZE;
        GridState.gridHeight = GRID_SIZE;
        GridState.animating = false;
        GridState.grid = createInitialGrid();
        
        while (findAllMatches().length > 0) {
            GridState.grid = createInitialGrid();
        }
    }
    
    function createInitialGrid() {
        const grid = [];
        for (let y = 0; y < GRID_SIZE; y++) {
            grid[y] = [];
            for (let x = 0; x < GRID_SIZE; x++) {
                grid[y][x] = Math.floor(Math.random() * TILE_TYPES) + 1;
            }
        }
        return grid;
    }
    
    function swapTiles(x1, y1, x2, y2) {
        if (GameState.gameStatus !== 'gameplay' || GridState.animating) {
            return false;
        }
        
        const dx = Math.abs(x2 - x1);
        const dy = Math.abs(y2 - y1);
        if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
            const temp = GridState.grid[y1][x1];
            GridState.grid[y1][x1] = GridState.grid[y2][x2];
            GridState.grid[y2][x2] = temp;
            
            const matches = findAllMatches();
            if (matches.length > 0) {
                processMatches();
                return true;
            } else {
                GridState.grid[y2][x2] = GridState.grid[y1][x1];
                GridState.grid[y1][x1] = temp;
                return false;
            }
        }
        return false;
    }
    
    function processMatches() {
        if (GameState.gameStatus !== 'gameplay') {
            return 0;
        }
        
        GridState.animating = true;
        let totalMatches = 0;
        let matches;
        
        do {
            matches = findAllMatches();
            if (matches.length > 0) {
                totalMatches += matches.length;
                removeMatches(matches);
                dropTiles();
                fillEmptySpaces();
            }
        } while (matches.length > 0);
        
        GridState.animating = false;
        
        if (!hasValidMoves()) {
            EventBus.emit('NO_MOVES_AVAILABLE', {});
        }
        
        return totalMatches;
    }
    
    function findAllMatches() {
        const matches = [];
        const grid = GridState.grid;
        
        for (let y = 0; y < GRID_SIZE; y++) {
            let count = 1;
            let currentTile = grid[y][0];
            
            for (let x = 1; x < GRID_SIZE; x++) {
                if (grid[y][x] === currentTile && currentTile !== 0) {
                    count++;
                } else {
                    if (count >= MIN_MATCH_SIZE) {
                        for (let i = x - count; i < x; i++) {
                            matches.push({x: i, y: y, type: currentTile});
                        }
                    }
                    count = 1;
                    currentTile = grid[y][x];
                }
            }
            
            if (count >= MIN_MATCH_SIZE) {
                for (let i = GRID_SIZE - count; i < GRID_SIZE; i++) {
                    matches.push({x: i, y: y, type: currentTile});
                }
            }
        }
        
        for (let x = 0; x < GRID_SIZE; x++) {
            let count = 1;
            let currentTile = grid[0][x];
            
            for (let y = 1; y < GRID_SIZE; y++) {
                if (grid[y][x] === currentTile && currentTile !== 0) {
                    count++;
                } else {
                    if (count >= MIN_MATCH_SIZE) {
                        for (let i = y - count; i < y; i++) {
                            matches.push({x: x, y: i, type: currentTile});
                        }
                    }
                    count = 1;
                    currentTile = grid[y][x];
                }
            }
            
            if (count >= MIN_MATCH_SIZE) {
                for (let i = GRID_SIZE - count; i < GRID_SIZE; i++) {
                    matches.push({x: x, y: i, type: currentTile});
                }
            }
        }
        
        return matches;
    }
    
    function removeMatches(matches) {
        const matchGroups = {};
        
        matches.forEach(match => {
            if (!matchGroups[match.type]) {
                matchGroups[match.type] = [];
            }
            matchGroups[match.type].push(match);
        });
        
        Object.keys(matchGroups).forEach(tileType => {
            const group = matchGroups[tileType];
            const points = group.length * 10 * (group.length - 2);
            
            group.forEach(match => {
                GridState.grid[match.y][match.x] = 0;
            });
            
            EventBus.emit('MATCH_FOUND', {
                matchSize: group.length,
                tileType: tileType,
                points: points
            });
        });
    }
    
    function dropTiles() {
        for (let x = 0; x < GRID_SIZE; x++) {
            let writePos = GRID_SIZE - 1;
            
            for (let y = GRID_SIZE - 1; y >= 0; y--) {
                if (GridState.grid[y][x] !== 0) {
                    if (y !== writePos) {
                        GridState.grid[writePos][x] = GridState.grid[y][x];
                        GridState.grid[y][x] = 0;
                    }
                    writePos--;
                }
            }
        }
    }
    
    function fillEmptySpaces() {
        for (let x = 0; x < GRID_SIZE; x++) {
            for (let y = 0; y < GRID_SIZE; y++) {
                if (GridState.grid[y][x] === 0) {
                    GridState.grid[y][x] = Math.floor(Math.random() * TILE_TYPES) + 1;
                }
            }
        }
    }
    
    function hasValidMoves() {
        if (GameState.gameStatus !== 'gameplay') {
            return false;
        }
        
        const grid = GridState.grid;
        
        for (let y = 0; y < GRID_SIZE; y++) {
            for (let x = 0; x < GRID_SIZE; x++) {
                if (x < GRID_SIZE - 1) {
                    const temp = grid[y][x];
                    grid[y][x] = grid[y][x + 1];
                    grid[y][x + 1] = temp;
                    
                    if (findAllMatches().length > 0) {
                        grid[y][x + 1] = grid[y][x];
                        grid[y][x] = temp;
                        return true;
                    }
                    
                    grid[y][x + 1] = grid[y][x];
                    grid[y][x] = temp;
                }
                
                if (y < GRID_SIZE - 1) {
                    const temp = grid[y][x];
                    grid[y][x] = grid[y + 1][x];
                    grid[y + 1][x] = temp;
                    
                    if (findAllMatches().length > 0) {
                        grid[y + 1][x] = grid[y][x];
                        grid[y][x] = temp;
                        return true;
                    }
                    
                    grid[y + 1][x] = grid[y][x];
                    grid[y][x] = temp;
                }
            }
        }
        
        return false;
    }
    
    function shuffleBoard() {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        GridState.animating = true;
        
        const tiles = [];
        for (let y = 0; y < GRID_SIZE; y++) {
            for (let x = 0; x < GRID_SIZE; x++) {
                if (GridState.grid[y][x] !== 0) {
                    tiles.push(GridState.grid[y][x]);
                }
            }
        }
        
        for (let i = tiles.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [tiles[i], tiles[j]] = [tiles[j], tiles[i]];
        }
        
        let tileIndex = 0;
        for (let y = 0; y < GRID_SIZE; y++) {
            for (let x = 0; x < GRID_SIZE; x++) {
                if (tileIndex < tiles.length) {
                    GridState.grid[y][x] = tiles[tileIndex++];
                } else {
                    GridState.grid[y][x] = Math.floor(Math.random() * TILE_TYPES) + 1;
                }
            }
        }
        
        let attempts = 0;
        while (!hasValidMoves() && attempts < 10) {
            for (let i = tiles.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [tiles[i], tiles[j]] = [tiles[j], tiles[i]];
            }
            
            tileIndex = 0;
            for (let y = 0; y < GRID_SIZE; y++) {
                for (let x = 0; x < GRID_SIZE; x++) {
                    if (tileIndex < tiles.length) {
                        GridState.grid[y][x] = tiles[tileIndex++];
                    } else {
                        GridState.grid[y][x] = Math.floor(Math.random() * TILE_TYPES) + 1;
                    }
                }
            }
            attempts++;
        }
        
        GridState.animating = false;
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

const ui_system = (function() {
    let canvas;
    let ctx;
    
    const GRID_OFFSET_X = (CANVAS_WIDTH - (GRID_SIZE * TILE_SIZE)) / 2;
    const GRID_OFFSET_Y = 300;
    const HUD_HEIGHT = 200;
    
    const TILE_COLORS = [
        '#FF6B6B',
        '#4ECDC4',
        '#45B7D1',
        '#96CEB4',
        '#FFEAA7',
        '#DDA0DD'
    ];
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.id = 'gameCanvas';
            canvas.width = CANVAS_WIDTH;
            canvas.height = CANVAS_HEIGHT;
            document.body.appendChild(canvas);
        }
        ctx = canvas.getContext('2d');
        
        canvas.style.border = '2px solid #333';
        canvas.style.display = 'block';
        canvas.style.margin = '0 auto';
        canvas.style.backgroundColor = '#1a1a2e';
    }
    
    function renderMainMenu() {
        if (GameState.gameStatus !== 'main_menu') return;
        
        ctx.fillStyle = '#0f0f23';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 80px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('MATCH 3', CANVAS_WIDTH / 2, 300);
        
        ctx.font = '32px Arial';
        ctx.fillStyle = '#cccccc';
        ctx.fillText('Match tiles to score points!', CANVAS_WIDTH / 2, 380);
        
        ctx.fillStyle = '#4CAF50';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 600, 300, 80);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 36px Arial';
        ctx.fillText('START GAME', CANVAS_WIDTH / 2, 650);
        
        ctx.fillStyle = '#2196F3';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 720, 300, 80);
        ctx.fillStyle = '#ffffff';
        ctx.fillText('LEADERBOARD', CANVAS_WIDTH / 2, 770);
        
        ctx.font = '24px Arial';
        ctx.fillStyle = '#888888';
        ctx.fillText('Tap tiles to select and swap', CANVAS_WIDTH / 2, 1000);
        ctx.fillText('Match 3 or more to score', CANVAS_WIDTH / 2, 1040);
    }
    
    function renderGameplay() {
        if (GameState.gameStatus !== 'gameplay') return;
        
        ctx.fillStyle = '#0f0f23';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        renderHUD();
        renderGrid();
        
        if (GridState.selectedTile && GridState.selectedTile !== 'null') {
            const coords = GridState.selectedTile.split(',');
            const x = parseInt(coords[0]);
            const y = parseInt(coords[1]);
            
            ctx.strokeStyle = '#FFD700';
            ctx.lineWidth = 4;
            ctx.strokeRect(
                GRID_OFFSET_X + x * TILE_SIZE,
                GRID_OFFSET_Y + y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE
            );
        }
    }
    
    function renderHUD() {
        ctx.fillStyle = '#16213e';
        ctx.fillRect(0, 0, CANVAS_WIDTH, HUD_HEIGHT);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 36px Arial';
        ctx.textAlign = 'left';
        ctx.fillText('Score: ' + GameState.score, 50, 60);
        
        ctx.fillText('Lives: ' + GameState.lives, 50, 110);
        
        ctx.textAlign = 'right';
        ctx.fillText('Level: ' + GameState.level, CANVAS_WIDTH - 50, 60);
        
        ctx.fillText('Moves: ' + GameState.movesRemaining, CANVAS_WIDTH - 50, 110);
        
        ctx.textAlign = 'center';
        ctx.font = '24px Arial';
        ctx.fillStyle = '#cccccc';
        ctx.fillText('Target: ' + GameState.targetScore, CANVAS_WIDTH / 2, 160);
    }
    
    function renderGrid() {
        if (!GridState.grid || GridState.grid.length === 0) return;
        
        for (let y = 0; y < GridState.gridHeight; y++) {
            for (let x = 0; x < GridState.gridWidth; x++) {
                const tileType = GridState.grid[y][x];
                const tileX = GRID_OFFSET_X + x * TILE_SIZE;
                const tileY = GRID_OFFSET_Y + y * TILE_SIZE;
                
                ctx.fillStyle = '#2c3e50';
                ctx.fillRect(tileX, tileY, TILE_SIZE, TILE_SIZE);
                
                ctx.strokeStyle = '#34495e';
                ctx.lineWidth = 2;
                ctx.strokeRect(tileX, tileY, TILE_SIZE, TILE_SIZE);
                
                if (tileType >= 1 && tileType <= TILE_COLORS.length) {
                    ctx.fillStyle = TILE_COLORS[tileType - 1];
                    ctx.fillRect(tileX + 10, tileY + 10, TILE_SIZE - 20, TILE_SIZE - 20);
                    
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                    ctx.fillRect(tileX + 10, tileY + 10, TILE_SIZE - 20, 20);
                }
            }
        }
    }
    
    function renderGameOver() {
        if (GameState.gameStatus !== 'game_over') return;
        
        ctx.fillStyle = '#0f0f23';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#ff4757';
        ctx.font = 'bold 72px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('GAME OVER', CANVAS_WIDTH / 2, 300);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 48px Arial';
        ctx.fillText('Final Score: ' + GameState.score, CANVAS_WIDTH / 2, 400);
        
        ctx.font = '36px Arial';
        ctx.fillStyle = '#cccccc';
        ctx.fillText('Level Reached: ' + GameState.level, CANVAS_WIDTH / 2, 460);
        
        ctx.fillStyle = '#4CAF50';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 600, 300, 80);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 32px Arial';
        ctx.fillText('RETRY', CANVAS_WIDTH / 2, 650);
        
        ctx.fillStyle = '#2196F3';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 720, 300, 80);
        ctx.fillStyle = '#ffffff';
        ctx.fillText('MAIN MENU', CANVAS_WIDTH / 2, 770);
        
        ctx.fillStyle = '#FF9800';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 840, 300, 80);
        ctx.fillStyle = '#ffffff';
        ctx.fillText('LEADERBOARD', CANVAS_WIDTH / 2, 890);
    }
    
    function renderLeaderboard() {
        if (GameState.gameStatus !== 'leaderboard') return;
        
        ctx.fillStyle = '#0f0f23';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 64px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('LEADERBOARD', CANVAS_WIDTH / 2, 200);
        
        const leaderboard = [
            { name: 'Player 1', score: 15000 },
            { name: 'Player 2', score: 12500 },
            { name: 'Player 3', score: 10000 },
            { name: 'Player 4', score: 8500 },
            { name: 'Player 5', score: 7000 }
        ];
        
        ctx.font = '36px Arial';
        ctx.textAlign = 'left';
        for (let i = 0; i < leaderboard.length; i++) {
            const y = 320 + i * 80;
            const entry = leaderboard[i];
            
            ctx.fillStyle = '#FFD700';
            ctx.fillText((i + 1) + '.', 200, y);
            
            ctx.fillStyle = '#ffffff';
            ctx.fillText(entry.name, 280, y);
            
            ctx.textAlign = 'right';
            ctx.fillText(entry.score.toLocaleString(), CANVAS_WIDTH - 200, y);
            ctx.textAlign = 'left';
        }
        
        ctx.fillStyle = '#2196F3';
        ctx.fillRect(CANVAS_WIDTH / 2 - 100, 800, 200, 60);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 28px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('BACK', CANVAS_WIDTH / 2, 840);
    }
    
    function getClickedTile(x, y) {
        if (GameState.gameStatus !== 'gameplay') return 'none';
        
        if (x < GRID_OFFSET_X || x > GRID_OFFSET_X + (GridState.gridWidth * TILE_SIZE) ||
            y < GRID_OFFSET_Y || y > GRID_OFFSET_Y + (GridState.gridHeight * TILE_SIZE)) {
            return 'none';
        }
        
        const gridX = Math.floor((x - GRID_OFFSET_X) / TILE_SIZE);
        const gridY = Math.floor((y - GRID_OFFSET_Y) / TILE_SIZE);
        
        if (gridX >= 0 && gridX < GridState.gridWidth && 
            gridY >= 0 && gridY < GridState.gridHeight) {
            return gridX + ',' + gridY;
        }
        
        return 'none';
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

const input_handler = (function() {
    function init() {
        document.addEventListener('click', function(e) {
            const rect = document.querySelector('canvas').getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            handleClick(x, y);
        });
        
        document.addEventListener('touchstart', function(e) {
            e.preventDefault();
            const rect = document.querySelector('canvas').getBoundingClientRect();
            const touch = e.touches[0];
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            handleClick(x, y);
        });
        
        document.addEventListener('keydown', function(e) {
            handleKeyPress(e.key);
        });
    }
    
    function handleClick(x, y) {
        if (GameState.gameStatus === 'main_menu') {
            handleMainMenuClick(x, y);
        } else if (GameState.gameStatus === 'gameplay') {
            handleGameplayClick(x, y);
        } else if (GameState.gameStatus === 'game_over') {
            handleGameOverClick(x, y);
        } else if (GameState.gameStatus === 'leaderboard') {
            handleLeaderboardClick(x, y);
        }
    }
    
    function handleMainMenuClick(x, y) {
        if (x >= 340 && x <= 740 && y >= 750 && y <= 850) {
            EventBus.emit('START_GAME', {});
        }
        else if (x >= 340 && x <= 740 && y >= 900 && y <= 1000) {
            EventBus.emit('SHOW_LEADERBOARD', {});
        }
    }
    
    function handleGameplayClick(x, y) {
        if (GridState.animating) {
            return;
        }
        
        const tileCoords = ui_system.getClickedTile(x, y);
        if (tileCoords === 'none') {
            return;
        }
        
        const [tileX, tileY] = tileCoords.split(',').map(Number);
        
        if (GridState.selectedTile === null) {
            GridState.selectedTile = `${tileX},${tileY}`;
        } else {
            const [selectedX, selectedY] = GridState.selectedTile.split(',').map(Number);
            
            if (selectedX === tileX && selectedY === tileY) {
                GridState.selectedTile = null;
            } else {
                const dx = Math.abs(selectedX - tileX);
                const dy = Math.abs(selectedY - tileY);
                
                if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
                    const swapSuccessful = match_engine.swapTiles(selectedX, selectedY, tileX, tileY);
                    GridState.selectedTile = null;
                } else {
                    GridState.selectedTile = `${tileX},${tileY}`;
                }
            }
        }
    }
    
    function handleGameOverClick(x, y) {
        if (x >= 140 && x <= 440 && y >= 1200 && y <= 1300) {
            EventBus.emit('RETRY_GAME', {});
        }
        else if (x >= 640 && x <= 940 && y >= 1200 && y <= 1300) {
            EventBus.emit('RETURN_MENU', {});
        }
        else if (x >= 340 && x <= 740 && y >= 1350 && y <= 1450) {
            EventBus.emit('SHOW_LEADERBOARD', {});
        }
    }
    
    function handleLeaderboardClick(x, y) {
        if (x >= 340 && x <= 740 && y >= 1600 && y <= 1700) {
            EventBus.emit('CLOSE_LEADERBOARD', {});
        }
    }
    
    function handleKeyPress(key) {
        if (GameState.gameStatus === 'main_menu') {
            if (key === 'Enter' || key === ' ') {
                EventBus.emit('START_GAME', {});
            } else if (key === 'l' || key === 'L') {
                EventBus.emit('SHOW_LEADERBOARD', {});
            }
        } else if (GameState.gameStatus === 'gameplay') {
            if (key === 'Escape') {
                EventBus.emit('RETURN_MENU', {});
            }
        } else if (GameState.gameStatus === 'game_over') {
            if (key === 'r' || key === 'R') {
                EventBus.emit('RETRY_GAME', {});
            } else if (key === 'm' || key === 'M') {
                EventBus.emit('RETURN_MENU', {});
            } else if (key === 'l' || key === 'L') {
                EventBus.emit('SHOW_LEADERBOARD', {});
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            if (key === 'Escape' || key === 'Enter') {
                EventBus.emit('CLOSE_LEADERBOARD', {});
            }
        }
    }
    
    function update(dt) {
    }
    
    return {
        init,
        handleClick,
        handleKeyPress,
        update
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
    
    // Update UI elements based on current game state
    updateUI();
}

// Update UI elements
function updateUI() {
    const scoreDisplay = document.getElementById('score_display');
    const movesLeft = document.getElementById('moves_left');
    const target = document.getElementById('target');
    const levelLabel = document.getElementById('level_label');
    const finalScore = document.getElementById('final_score');
    
    if (scoreDisplay) scoreDisplay.textContent = `得分: ${GameState.score}`;
    if (movesLeft) movesLeft.textContent = `步数: ${GameState.movesRemaining}`;
    if (target) target.textContent = `目标: ${GameState.targetScore}`;
    if (levelLabel) levelLabel.textContent = `第 ${GameState.level} 关`;
    if (finalScore) finalScore.textContent = `最终得分: ${GameState.score}`;
}

// Game loop
let lastTime = 0;
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions
    input_handler.update(dt);
    match_engine.update(dt);
    
    // Render functions
    ui_system.render();
    
    if (GameState.gameStatus === 'playing' || GameState.gameStatus === 'gameplay') {
        requestAnimationFrame(gameLoop);
    }
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('START_GAME', {});
    showScreen('gameplay');
    requestAnimationFrame(gameLoop);
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', { finalScore: GameState.score });
    showScreen('game_over');
}

function retry() {
    GameState.gameStatus = 'gameplay';
    EventBus.emit('RETRY_GAME', {});
    showScreen('gameplay');
    requestAnimationFrame(gameLoop);
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

// Input handlers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules
    game_state.init();
    match_engine.init();
    ui_system.init();
    input_handler.init();
    
    // Set up button event listeners
    const btnPlay = document.getElementById('btn_play');
    const btnLeaderboard = document.querySelectorAll('#btn_leaderboard');
    const btnRetry = document.getElementById('btn_retry');
    const btnMenu = document.getElementById('btn_menu');
    const btnClose = document.getElementById('btn_close');
    
    if (btnPlay) {
        btnPlay.addEventListener('click', startGame);
    }
    
    btnLeaderboard.forEach(btn => {
        btn.addEventListener('click', showLeaderboard);
    });
    
    if (btnRetry) {
        btnRetry.addEventListener('click', retry);
    }
    
    if (btnMenu) {
        btnMenu.addEventListener('click', returnToMenu);
    }
    
    if (btnClose) {
        btnClose.addEventListener('click', closeLeaderboard);
    }
    
    // Listen for state changes
    EventBus.on('GAME_START', () => {
        showScreen('gameplay');
        requestAnimationFrame(gameLoop);
    });
    
    EventBus.on('GAME_OVER', () => {
        showScreen('game_over');
    });
    
    EventBus.on('START_GAME', startGame);
    EventBus.on('RETRY_GAME', retry);
    EventBus.on('RETURN_MENU', returnToMenu);
    EventBus.on('SHOW_LEADERBOARD', showLeaderboard);
    EventBus.on('CLOSE_LEADERBOARD', closeLeaderboard);
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start render loop
    requestAnimationFrame(gameLoop);
});