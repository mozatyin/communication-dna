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

// Global constants
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const GRID_SIZE = 8;
const TILE_SIZE = 100;
const TILE_TYPES = 6;
const MIN_MATCH_SIZE = 3;

// Module: game_state
const game_state = (function() {
    let highScores = [];
    
    function init() {
        GameState.gameStatus = 'main_menu';
        GameState.score = 0;
        GameState.lives = 3;
        GameState.level = 1;
        GameState.movesRemaining = 30;
        GameState.targetScore = 1000;
        
        // Load high scores from localStorage
        const savedScores = localStorage.getItem('match3_highscores');
        if (savedScores) {
            highScores = JSON.parse(savedScores);
        } else {
            highScores = [];
        }
        
        // Set up event listeners
        EventBus.on('MATCH_FOUND', handleMatchFound);
        EventBus.on('NO_MOVES_AVAILABLE', handleNoMovesAvailable);
        EventBus.on('START_GAME', handleStartGame);
        EventBus.on('RETRY_GAME', handleRetryGame);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('SHOW_LEADERBOARD', handleShowLeaderboard);
        EventBus.on('CLOSE_LEADERBOARD', handleCloseLeaderboard);
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
            
            saveHighScore(GameState.score);
            
            EventBus.emit('GAME_OVER', { finalScore: GameState.score });
        }
    }
    
    function addScore(points) {
        if (GameState.gameStatus === 'gameplay') {
            GameState.score += points;
            
            if (GameState.score >= GameState.targetScore) {
                levelUp();
            }
        }
    }
    
    function decrementLives() {
        if (GameState.gameStatus === 'gameplay') {
            GameState.lives--;
            
            if (GameState.lives <= 0) {
                endGame();
                return true;
            }
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
    
    function levelUp() {
        GameState.level++;
        GameState.targetScore = Math.floor(GameState.targetScore * 1.5);
        GameState.movesRemaining = Math.max(20, 30 - GameState.level);
        
        EventBus.emit('LEVEL_COMPLETE', { newLevel: GameState.level });
    }
    
    function saveHighScore(score) {
        highScores.push(score);
        highScores.sort((a, b) => b - a);
        highScores = highScores.slice(0, 10);
        localStorage.setItem('match3_highscores', JSON.stringify(highScores));
    }
    
    function getHighScores() {
        return [...highScores];
    }
    
    function handleMatchFound(data) {
        addScore(data.points);
    }
    
    function handleNoMovesAvailable() {
        decrementLives();
    }
    
    function handleStartGame() {
        startGame();
    }
    
    function handleRetryGame() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'main_menu';
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
    
    return {
        init,
        startGame,
        endGame,
        addScore,
        decrementLives,
        showLeaderboard,
        returnToMenu,
        getHighScores
    };
})();

// Module: match_engine
const match_engine = (function() {
    function init() {
        GridState.gridWidth = GRID_SIZE;
        GridState.gridHeight = GRID_SIZE;
        
        GridState.grid = [];
        for (let row = 0; row < GridState.gridHeight; row++) {
            GridState.grid[row] = [];
            for (let col = 0; col < GridState.gridWidth; col++) {
                GridState.grid[row][col] = 0;
            }
        }
        
        fillGridWithoutMatches();
        
        GridState.selectedTile = null;
        GridState.animating = false;
    }
    
    function fillGridWithoutMatches() {
        for (let row = 0; row < GridState.gridHeight; row++) {
            for (let col = 0; col < GridState.gridWidth; col++) {
                let tileType;
                let attempts = 0;
                do {
                    tileType = Math.floor(Math.random() * TILE_TYPES) + 1;
                    attempts++;
                } while (attempts < 50 && wouldCreateMatch(row, col, tileType));
                
                GridState.grid[row][col] = tileType;
            }
        }
    }
    
    function wouldCreateMatch(row, col, tileType) {
        let horizontalCount = 1;
        for (let c = col - 1; c >= 0 && GridState.grid[row][c] === tileType; c--) {
            horizontalCount++;
        }
        for (let c = col + 1; c < GridState.gridWidth && GridState.grid[row][c] === tileType; c++) {
            horizontalCount++;
        }
        
        if (horizontalCount >= MIN_MATCH_SIZE) return true;
        
        let verticalCount = 1;
        for (let r = row - 1; r >= 0 && GridState.grid[r][col] === tileType; r--) {
            verticalCount++;
        }
        for (let r = row + 1; r < GridState.gridHeight && GridState.grid[r][col] === tileType; r++) {
            verticalCount++;
        }
        
        return verticalCount >= MIN_MATCH_SIZE;
    }
    
    function swapTiles(x1, y1, x2, y2) {
        if (GameState.gameStatus !== 'gameplay' || GridState.animating) {
            return false;
        }
        
        if (x1 < 0 || x1 >= GridState.gridWidth || y1 < 0 || y1 >= GridState.gridHeight ||
            x2 < 0 || x2 >= GridState.gridWidth || y2 < 0 || y2 >= GridState.gridHeight) {
            return false;
        }
        
        const dx = Math.abs(x2 - x1);
        const dy = Math.abs(y2 - y1);
        if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
            const temp = GridState.grid[y1][x1];
            GridState.grid[y1][x1] = GridState.grid[y2][x2];
            GridState.grid[y2][x2] = temp;
            
            const matchesFound = findMatches().length > 0;
            
            if (matchesFound) {
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
    
    function findMatches() {
        const matches = [];
        const visited = [];
        
        for (let row = 0; row < GridState.gridHeight; row++) {
            visited[row] = [];
            for (let col = 0; col < GridState.gridWidth; col++) {
                visited[row][col] = false;
            }
        }
        
        for (let row = 0; row < GridState.gridHeight; row++) {
            let count = 1;
            let currentType = GridState.grid[row][0];
            
            for (let col = 1; col < GridState.gridWidth; col++) {
                if (GridState.grid[row][col] === currentType && currentType !== 0) {
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
                for (let c = GridState.gridWidth - count; c < GridState.gridWidth; c++) {
                    if (!visited[row][c]) {
                        matches.push({row: row, col: c, type: currentType});
                        visited[row][c] = true;
                    }
                }
            }
        }
        
        for (let col = 0; col < GridState.gridWidth; col++) {
            let count = 1;
            let currentType = GridState.grid[0][col];
            
            for (let row = 1; row < GridState.gridHeight; row++) {
                if (GridState.grid[row][col] === currentType && currentType !== 0) {
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
                for (let r = GridState.gridHeight - count; r < GridState.gridHeight; r++) {
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
        
        while (true) {
            const matches = findMatches();
            if (matches.length === 0) break;
            
            const matchGroups = {};
            matches.forEach(match => {
                if (!matchGroups[match.type]) {
                    matchGroups[match.type] = [];
                }
                matchGroups[match.type].push(match);
            });
            
            matches.forEach(match => {
                GridState.grid[match.row][match.col] = 0;
            });
            
            Object.keys(matchGroups).forEach(tileType => {
                const matchSize = matchGroups[tileType].length;
                const basePoints = matchSize * 10;
                const cascadeBonus = cascadeCount * 5;
                const points = basePoints + cascadeBonus;
                
                EventBus.emit('MATCH_FOUND', {
                    matchSize: matchSize,
                    tileType: tileType,
                    points: points
                });
            });
            
            totalMatches += matches.length;
            cascadeCount++;
            
            applyGravity();
            fillEmptySpaces();
        }
        
        return totalMatches;
    }
    
    function applyGravity() {
        for (let col = 0; col < GridState.gridWidth; col++) {
            const tiles = [];
            for (let row = GridState.gridHeight - 1; row >= 0; row--) {
                if (GridState.grid[row][col] !== 0) {
                    tiles.push(GridState.grid[row][col]);
                }
            }
            
            for (let row = 0; row < GridState.gridHeight; row++) {
                GridState.grid[row][col] = 0;
            }
            
            for (let i = 0; i < tiles.length; i++) {
                GridState.grid[GridState.gridHeight - 1 - i][col] = tiles[i];
            }
        }
    }
    
    function fillEmptySpaces() {
        for (let col = 0; col < GridState.gridWidth; col++) {
            for (let row = 0; row < GridState.gridHeight; row++) {
                if (GridState.grid[row][col] === 0) {
                    GridState.grid[row][col] = Math.floor(Math.random() * TILE_TYPES) + 1;
                }
            }
        }
    }
    
    function hasValidMoves() {
        if (GameState.gameStatus !== 'gameplay') {
            return false;
        }
        
        for (let row = 0; row < GridState.gridHeight; row++) {
            for (let col = 0; col < GridState.gridWidth; col++) {
                if (col < GridState.gridWidth - 1) {
                    const temp = GridState.grid[row][col];
                    GridState.grid[row][col] = GridState.grid[row][col + 1];
                    GridState.grid[row][col + 1] = temp;
                    
                    const hasMatch = findMatches().length > 0;
                    
                    GridState.grid[row][col + 1] = GridState.grid[row][col];
                    GridState.grid[row][col] = temp;
                    
                    if (hasMatch) return true;
                }
                
                if (row < GridState.gridHeight - 1) {
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
        for (let row = 0; row < GridState.gridHeight; row++) {
            for (let col = 0; col < GridState.gridWidth; col++) {
                tiles.push(GridState.grid[row][col]);
            }
        }
        
        for (let i = tiles.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [tiles[i], tiles[j]] = [tiles[j], tiles[i]];
        }
        
        let tileIndex = 0;
        for (let row = 0; row < GridState.gridHeight; row++) {
            for (let col = 0; col < GridState.gridWidth; col++) {
                GridState.grid[row][col] = tiles[tileIndex++];
            }
        }
        
        processMatches();
        
        if (!hasValidMoves()) {
            fillGridWithoutMatches();
        }
    }
    
    function update(dt) {
        if (GameState.gameStatus !== 'gameplay') {
            return;
        }
        
        if (!GridState.animating && !hasValidMoves()) {
            EventBus.emit('NO_MOVES_AVAILABLE', {});
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

// Module: ui_system
const ui_system = (function() {
    let canvas;
    let ctx;
    let gridOffsetX;
    let gridOffsetY;
    let tileColors;
    let highScores;

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
        
        gridOffsetX = (CANVAS_WIDTH - (GRID_SIZE * TILE_SIZE)) / 2;
        gridOffsetY = 300;
        
        tileColors = {
            '1': '#FF6B6B',
            '2': '#4ECDC4',
            '3': '#45B7D1',
            '4': '#96CEB4',
            '5': '#FFEAA7',
            '6': '#DDA0DD'
        };
        
        highScores = JSON.parse(localStorage.getItem('match3HighScores') || '[]');
        
        canvas.style.display = 'block';
        canvas.style.margin = '0 auto';
        canvas.style.border = '2px solid #333';
        canvas.style.backgroundColor = '#f0f0f0';
    }

    function renderMainMenu() {
        if (GameState.gameStatus !== 'main_menu') return;
        
        ctx.fillStyle = '#2C3E50';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#ECF0F1';
        ctx.font = 'bold 80px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('MATCH 3', CANVAS_WIDTH / 2, 300);
        
        ctx.font = '32px Arial';
        ctx.fillStyle = '#BDC3C7';
        ctx.fillText('Match tiles to score points!', CANVAS_WIDTH / 2, 380);
        
        ctx.fillStyle = '#27AE60';
        ctx.fillRect(CANVAS_WIDTH / 2 - 200, 600, 400, 100);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 36px Arial';
        ctx.fillText('START GAME', CANVAS_WIDTH / 2, 665);
        
        ctx.fillStyle = '#3498DB';
        ctx.fillRect(CANVAS_WIDTH / 2 - 200, 750, 400, 100);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText('LEADERBOARD', CANVAS_WIDTH / 2, 815);
        
        ctx.font = '24px Arial';
        ctx.fillStyle = '#95A5A6';
        ctx.fillText('Tap adjacent tiles to swap them', CANVAS_WIDTH / 2, 1000);
        ctx.fillText('Match 3 or more to score!', CANVAS_WIDTH / 2, 1040);
    }

    function renderGameplay() {
        if (GameState.gameStatus !== 'gameplay') return;
        
        ctx.fillStyle = '#34495E';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        renderHUD();
        renderGrid();
        
        if (GridState.selectedTile && GridState.selectedTile !== 'null') {
            const coords = GridState.selectedTile.split(',');
            const col = parseInt(coords[0]);
            const row = parseInt(coords[1]);
            
            ctx.strokeStyle = '#F39C12';
            ctx.lineWidth = 6;
            ctx.strokeRect(
                gridOffsetX + col * TILE_SIZE + 3,
                gridOffsetY + row * TILE_SIZE + 3,
                TILE_SIZE - 6,
                TILE_SIZE - 6
            );
        }
    }

    function renderHUD() {
        ctx.fillStyle = '#ECF0F1';
        ctx.font = 'bold 32px Arial';
        ctx.textAlign = 'left';
        ctx.fillText('Score: ' + GameState.score, 50, 80);
        
        ctx.fillText('Target: ' + GameState.targetScore, 50, 120);
        
        ctx.textAlign = 'right';
        ctx.fillText('Lives: ' + GameState.lives, CANVAS_WIDTH - 50, 80);
        
        ctx.fillText('Moves: ' + GameState.movesRemaining, CANVAS_WIDTH - 50, 120);
        
        ctx.textAlign = 'center';
        ctx.fillText('Level ' + GameState.level, CANVAS_WIDTH / 2, 80);
        
        const progress = Math.min(GameState.score / GameState.targetScore, 1);
        const barWidth = CANVAS_WIDTH - 100;
        const barHeight = 20;
        const barX = 50;
        const barY = 160;
        
        ctx.fillStyle = '#7F8C8D';
        ctx.fillRect(barX, barY, barWidth, barHeight);
        
        ctx.fillStyle = '#27AE60';
        ctx.fillRect(barX, barY, barWidth * progress, barHeight);
        
        ctx.strokeStyle = '#2C3E50';
        ctx.lineWidth = 2;
        ctx.strokeRect(barX, barY, barWidth, barHeight);
    }

    function renderGrid() {
        if (!GridState.grid || GridState.grid.length === 0) return;
        
        for (let row = 0; row < GridState.gridHeight; row++) {
            for (let col = 0; col < GridState.gridWidth; col++) {
                const tileType = GridState.grid[row][col];
                const x = gridOffsetX + col * TILE_SIZE;
                const y = gridOffsetY + row * TILE_SIZE;
                
                ctx.fillStyle = tileColors[tileType] || '#95A5A6';
                ctx.fillRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);
                
                ctx.strokeStyle = '#2C3E50';
                ctx.lineWidth = 2;
                ctx.strokeRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);
                
                ctx.fillStyle = '#2C3E50';
                ctx.font = 'bold 24px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(
                    tileType,
                    x + TILE_SIZE / 2,
                    y + TILE_SIZE / 2 + 8
                );
            }
        }
        
        ctx.strokeStyle = '#2C3E50';
        ctx.lineWidth = 4;
        ctx.strokeRect(
            gridOffsetX,
            gridOffsetY,
            GridState.gridWidth * TILE_SIZE,
            GridState.gridHeight * TILE_SIZE
        );
    }

    function renderGameOver() {
        if (GameState.gameStatus !== 'game_over') return;
        
        ctx.fillStyle = '#2C3E50';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#E74C3C';
        ctx.font = 'bold 72px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('GAME OVER', CANVAS_WIDTH / 2, 300);
        
        ctx.fillStyle = '#ECF0F1';
        ctx.font = 'bold 48px Arial';
        ctx.fillText('Final Score: ' + GameState.score, CANVAS_WIDTH / 2, 400);
        
        ctx.font = '36px Arial';
        ctx.fillStyle = '#BDC3C7';
        ctx.fillText('Level Reached: ' + GameState.level, CANVAS_WIDTH / 2, 460);
        
        const isHighScore = highScores.length < 10 || GameState.score > highScores[highScores.length - 1].score;
        if (isHighScore) {
            ctx.fillStyle = '#F39C12';
            ctx.font = 'bold 32px Arial';
            ctx.fillText('NEW HIGH SCORE!', CANVAS_WIDTH / 2, 520);
            
            saveHighScore();
        }
        
        ctx.fillStyle = '#27AE60';
        ctx.fillRect(CANVAS_WIDTH / 2 - 200, 650, 400, 80);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 32px Arial';
        ctx.fillText('PLAY AGAIN', CANVAS_WIDTH / 2, 705);
        
        ctx.fillStyle = '#3498DB';
        ctx.fillRect(CANVAS_WIDTH / 2 - 200, 750, 400, 80);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText('MAIN MENU', CANVAS_WIDTH / 2, 805);
        
        ctx.fillStyle = '#9B59B6';
        ctx.fillRect(CANVAS_WIDTH / 2 - 200, 850, 400, 80);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText('LEADERBOARD', CANVAS_WIDTH / 2, 905);
    }

    function renderLeaderboard() {
        if (GameState.gameStatus !== 'leaderboard') return;
        
        ctx.fillStyle = '#2C3E50';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#ECF0F1';
        ctx.font = 'bold 64px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('LEADERBOARD', CANVAS_WIDTH / 2, 150);
        
        ctx.font = '32px Arial';
        const startY = 250;
        const lineHeight = 60;
        
        if (highScores.length === 0) {
            ctx.fillStyle = '#95A5A6';
            ctx.fillText('No high scores yet!', CANVAS_WIDTH / 2, startY + 100);
        } else {
            for (let i = 0; i < Math.min(highScores.length, 10); i++) {
                const score = highScores[i];
                const y = startY + i * lineHeight;
                
                ctx.fillStyle = '#F39C12';
                ctx.textAlign = 'left';
                ctx.fillText((i + 1) + '.', 200, y);
                
                ctx.fillStyle = '#ECF0F1';
                ctx.textAlign = 'center';
                ctx.fillText(score.toLocaleString(), CANVAS_WIDTH / 2, y);
            }
        }
        
        ctx.fillStyle = '#3498DB';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, CANVAS_HEIGHT - 200, 300, 80);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 32px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('BACK', CANVAS_WIDTH / 2, CANVAS_HEIGHT - 145);
    }

    function getClickedTile(x, y) {
        if (GameState.gameStatus !== 'gameplay') return 'none';
        
        if (x < gridOffsetX || x > gridOffsetX + GridState.gridWidth * TILE_SIZE ||
            y < gridOffsetY || y > gridOffsetY + GridState.gridHeight * TILE_SIZE) {
            return 'none';
        }
        
        const col = Math.floor((x - gridOffsetX) / TILE_SIZE);
        const row = Math.floor((y - gridOffsetY) / TILE_SIZE);
        
        if (col < 0 || col >= GridState.gridWidth || row < 0 || row >= GridState.gridHeight) {
            return 'none';
        }
        
        return col + ',' + row;
    }

    function saveHighScore() {
        const newScore = GameState.score;
        
        highScores.push(newScore);
        highScores.sort((a, b) => b - a);
        
        if (highScores.length > 10) {
            highScores = highScores.slice(0, 10);
        }
        
        localStorage.setItem('match3HighScores', JSON.stringify(highScores));
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

// Module: input_handler
const input_handler = (function() {
    let canvas;
    let isInitialized = false;

    function init() {
        if (isInitialized) return;
        
        canvas = document.getElementById('gameCanvas') || document.querySelector('canvas');
        if (!canvas) {
            console.error('Canvas element not found');
            return;
        }

        canvas.addEventListener('click', onCanvasClick);
        canvas.addEventListener('touchstart', onTouchStart);
        document.addEventListener('keydown', onKeyDown);

        // Button event listeners
        const btnPlay = document.getElementById('btn_play');
        const btnLeaderboard = document.querySelectorAll('#btn_leaderboard');
        const btnRetry = document.getElementById('btn_retry');
        const btnMenu = document.getElementById('btn_menu');
        const btnClose = document.getElementById('btn_close');

        if (btnPlay) btnPlay.addEventListener('click', () => EventBus.emit('START_GAME', {}));
        btnLeaderboard.forEach(btn => btn.addEventListener('click', () => EventBus.emit('SHOW_LEADERBOARD', {})));
        if (btnRetry) btnRetry.addEventListener('click', () => EventBus.emit('RETRY_GAME', {}));
        if (btnMenu) btnMenu.addEventListener('click', () => EventBus.emit('RETURN_MENU', {}));
        if (btnClose) btnClose.addEventListener('click', () => EventBus.emit('CLOSE_LEADERBOARD', {}));

        isInitialized = true;
    }

    function onCanvasClick(event) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = (event.clientX - rect.left) * scaleX;
        const y = (event.clientY - rect.top) * scaleY;
        handleClick(x, y);
    }

    function onTouchStart(event) {
        event.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const touch = event.touches[0];
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = (touch.clientX - rect.left) * scaleX;
        const y = (touch.clientY - rect.top) * scaleY;
        handleClick(x, y);
    }

    function onKeyDown(event) {
        handleKeyPress(event.key);
    }

    function handleClick(x, y) {
        if (!GameState) return;

        switch (GameState.gameStatus) {
            case 'main_menu':
                handleMainMenuClick(x, y);
                break;
            case 'gameplay':
                handleGameplayClick(x, y);
                break;
            case 'game_over':
                handleGameOverClick(x, y);
                break;
            case 'leaderboard':
                handleLeaderboardClick(x, y);
                break;
        }
    }

    function handleMainMenuClick(x, y) {
        const centerX = CANVAS_WIDTH / 2;
        const buttonWidth = 400;
        const buttonHeight = 100;
        
        if (x >= centerX - buttonWidth/2 && x <= centerX + buttonWidth/2 &&
            y >= 600 && y <= 600 + buttonHeight) {
            EventBus.emit('START_GAME', {});
        }
        
        if (x >= centerX - buttonWidth/2 && x <= centerX + buttonWidth/2 &&
            y >= 750 && y <= 750 + buttonHeight) {
            EventBus.emit('SHOW_LEADERBOARD', {});
        }
    }

    function handleGameplayClick(x, y) {
        if (!GridState || GridState.animating) return;

        const tileCoords = ui_system.getClickedTile(x, y);
        
        if (tileCoords === 'none') return;

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
                    
                    if (swapSuccessful) {
                        if (GameState.movesRemaining > 0) {
                            GameState.movesRemaining--;
                            
                            if (GameState.movesRemaining <= 0) {
                                setTimeout(() => {
                                    game_state.endGame();
                                }, 500);
                            }
                        }
                    }
                } else {
                    GridState.selectedTile = `${tileX},${tileY}`;
                }
            }
        }
    }

    function handleGameOverClick(x, y) {
        const centerX = CANVAS_WIDTH / 2;
        const buttonWidth = 400;
        const buttonHeight = 80;
        
        if (x >= centerX - buttonWidth/2 && x <= centerX + buttonWidth/2 &&
            y >= 650 && y <= 650 + buttonHeight) {
            EventBus.emit('RETRY_GAME', {});
        }
        
        if (x >= centerX - buttonWidth/2 && x <= centerX + buttonWidth/2 &&
            y >= 750 && y <= 750 + buttonHeight) {
            EventBus.emit('RETURN_MENU', {});
        }
        
        if (x >= centerX - buttonWidth/2 && x <= centerX + buttonWidth/2 &&
            y >= 850 && y <= 850 + buttonHeight) {
            EventBus.emit('SHOW_LEADERBOARD', {});
        }
    }

    function handleLeaderboardClick(x, y) {
        const centerX = CANVAS_WIDTH / 2;
        const buttonWidth = 300;
        const buttonHeight = 80;
        
        if (x >= centerX - buttonWidth/2 && x <= centerX + buttonWidth/2 &&
            y >= CANVAS_HEIGHT - 200 && y <= CANVAS_HEIGHT - 120) {
            EventBus.emit('CLOSE_LEADERBOARD', {});
        }
    }

    function handleKeyPress(key) {
        if (!GameState) return;

        switch (GameState.gameStatus) {
            case 'main_menu':
                if (key === 'Enter' || key === ' ') {
                    EventBus.emit('START_GAME', {});
                } else if (key === 'l' || key === 'L') {
                    EventBus.emit('SHOW_LEADERBOARD', {});
                }
                break;
                
            case 'gameplay':
                if (key === 'Escape') {
                    game_state.endGame();
                } else if (key === 'r' || key === 'R') {
                    if (!match_engine.hasValidMoves()) {
                        match_engine.shuffleBoard();
                    }
                }
                break;
                
            case 'game_over':
                if (key === 'Enter' || key === ' ') {
                    EventBus.emit('RETRY_GAME', {});
                } else if (key === 'Escape') {
                    EventBus.emit('RETURN_MENU', {});
                } else if (key === 'l' || key === 'L') {
                    EventBus.emit('SHOW_LEADERBOARD', {});
                }
                break;
                
            case 'leaderboard':
                if (key === 'Escape' || key === 'Enter') {
                    EventBus.emit('CLOSE_LEADERBOARD', {});
                }
                break;
        }
    }

    function update(dt) {
        // Input handler doesn't need continuous updates
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
    
    // Update UI elements based on game state
    updateUI();
}

function updateUI() {
    const scoreDisplay = document.getElementById('score_display');
    const movesLeft = document.getElementById('moves_left');
    const target = document.getElementById('target');
    const levelLabel = document.getElementById('level_label');
    const finalScore = document.getElementById('final_score');
    const scoreList = document.getElementById('score_list');
    
    if (scoreDisplay) scoreDisplay.textContent = `得分: ${GameState.score}`;
    if (movesLeft) movesLeft.textContent = `步数: ${GameState.movesRemaining}`;
    if (target) target.textContent = `目标: ${GameState.targetScore}`;
    if (levelLabel) levelLabel.textContent = `第 ${GameState.level} 关`;
    if (finalScore) finalScore.textContent = `最终得分: ${GameState.score}`;
    
    if (scoreList) {
        const highScores = game_state.getHighScores();
        if (highScores.length === 0) {
            scoreList.textContent = '暂无记录';
        } else {
            scoreList.innerHTML = highScores.slice(0, 5).map((score, index) => 
                `${index + 1}. ${score.toLocaleString()}`
            ).join('<br>');
        }
    }
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
    
    // Update UI elements
    updateUI();
    
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
    showScreen('gameplay');
}

function gameOver() {
    game_state.endGame();
    showScreen('game_over');
}

function retry() {
    EventBus.emit('RETRY_GAME', {});
    showScreen('gameplay');
}

function returnToMenu() {
    game_state.returnToMenu();
    showScreen('main_menu');
}

function showLeaderboard() {
    game_state.showLeaderboard();
    showScreen('leaderboard');
}

function closeLeaderboard() {
    game_state.returnToMenu();
    showScreen('main_menu');
}

// Event listeners for state transitions
EventBus.on('GAME_START', () => showScreen('gameplay'));
EventBus.on('GAME_OVER', () => showScreen('game_over'));
EventBus.on('START_GAME', startGame);
EventBus.on('RETRY_GAME', retry);
EventBus.on('RETURN_MENU', returnToMenu);
EventBus.on('SHOW_LEADERBOARD', showLeaderboard);
EventBus.on('CLOSE_LEADERBOARD', closeLeaderboard);

// Initialize game
function initGame() {
    // Initialize modules in order
    game_state.init();
    match_engine.init();
    ui_system.init();
    input_handler.init();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

// Start the game when page loads
document.addEventListener('DOMContentLoaded', initGame);