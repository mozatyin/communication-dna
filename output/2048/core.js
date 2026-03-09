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
const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const GRID_SIZE = 4;
const TILE_SIZE = 100;
const TILE_MARGIN = 10;
const WIN_TILE_VALUE = 2048;

// Shared state objects
const GameState = {
    gameStatus: 'menu',
    score: 0,
    bestScore: 0,
    hasWon: false,
    moveCount: 0
};

const GridState = {
    tiles: [[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]],
    previousTiles: [[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]],
    animationQueue: []
};

// Module code
const game_state = (function() {
    function init() {
        // Initialize GameState with default values
        GameState.gameStatus = 'menu';
        GameState.score = 0;
        GameState.bestScore = parseInt(localStorage.getItem('2048_bestScore')) || 0;
        GameState.hasWon = false;
        GameState.moveCount = 0;
        
        // Set up event listeners for events this module consumes
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('GAME_OVER', handleGameOver);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('SHOW_LEADERBOARD', handleShowLeaderboard);
        EventBus.on('CLOSE_LEADERBOARD', handleCloseLeaderboard);
        EventBus.on('TILES_MERGED', handleTilesMerged);
    }
    
    function startGame() {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.hasWon = false;
            GameState.moveCount = 0;
            grid_engine.resetGrid();
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            
            // Update best score if current score is higher
            if (GameState.score > GameState.bestScore) {
                GameState.bestScore = GameState.score;
                localStorage.setItem('2048_bestScore', GameState.bestScore.toString());
            }
            
            // Save score to leaderboard
            saveScoreToLeaderboard(GameState.score);
        }
    }
    
    function addScore(points) {
        if (GameState.gameStatus === 'playing') {
            GameState.score += points;
        }
    }
    
    function showLeaderboard() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'leaderboard';
        }
    }
    
    function returnToMenu() {
        GameState.gameStatus = 'menu';
    }
    
    function saveScoreToLeaderboard(score) {
        let scores = JSON.parse(localStorage.getItem('2048_leaderboard')) || [];
        scores.push(score);
        scores.sort((a, b) => b - a);
        scores = scores.slice(0, 5); // Keep top 5
        localStorage.setItem('2048_leaderboard', JSON.stringify(scores));
    }
    
    // Event handlers
    function handleGameStart(event) {
        startGame();
    }
    
    function handleGameOver(event) {
        endGame();
    }
    
    function handleRetry(event) {
        startGame();
    }
    
    function handleReturnMenu(event) {
        returnToMenu();
    }
    
    function handleShowLeaderboard(event) {
        showLeaderboard();
    }
    
    function handleCloseLeaderboard(event) {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'game_over';
        }
    }
    
    function handleTilesMerged(event) {
        if (GameState.gameStatus === 'playing') {
            addScore(event.points);
            GameState.moveCount++;
            
            // Check if player has won (reached 2048)
            if (event.newTileValue >= WIN_TILE_VALUE && !GameState.hasWon) {
                GameState.hasWon = true;
            }
        }
    }
    
    return {
        init,
        startGame,
        endGame,
        addScore,
        showLeaderboard,
        returnToMenu
    };
})();

const grid_engine = (function() {
    function init() {
        // Initialize empty grid
        GridState.tiles = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ];
        GridState.previousTiles = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ];
        GridState.animationQueue = [];
    }

    function resetGrid() {
        // Clear the grid
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                GridState.tiles[row][col] = 0;
            }
        }
        
        // Spawn two initial tiles
        spawnRandomTile();
        spawnRandomTile();
        
        // Clear animation queue
        GridState.animationQueue = [];
    }

    function spawnRandomTile() {
        const emptyCells = [];
        
        // Find all empty cells
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (GridState.tiles[row][col] === 0) {
                    emptyCells.push({ row, col });
                }
            }
        }
        
        if (emptyCells.length === 0) return false;
        
        // Pick random empty cell
        const randomIndex = Math.floor(Math.random() * emptyCells.length);
        const { row, col } = emptyCells[randomIndex];
        
        // 90% chance of 2, 10% chance of 4
        GridState.tiles[row][col] = Math.random() < 0.9 ? 2 : 4;
        
        return true;
    }

    function copyGrid(source, destination) {
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                destination[row][col] = source[row][col];
            }
        }
    }

    function moveLeft() {
        if (GameState.gameStatus !== 'playing') return false;
        
        // Save previous state
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        let maxMergedValue = 0;
        
        for (let row = 0; row < GRID_SIZE; row++) {
            const originalRow = [...GridState.tiles[row]];
            const { newRow, scoreGained, maxValue } = processRowLeft(GridState.tiles[row]);
            GridState.tiles[row] = newRow;
            
            if (!arraysEqual(originalRow, newRow)) {
                moved = true;
            }
            
            totalScore += scoreGained;
            maxMergedValue = Math.max(maxMergedValue, maxValue);
        }
        
        if (moved) {
            spawnRandomTile();
            
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { 
                    points: totalScore, 
                    newTileValue: maxMergedValue 
                });
            }
            
            EventBus.emit('MOVE_COMPLETED', { 
                direction: 'left', 
                tilesChanged: true 
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        }
        
        return moved;
    }

    function moveRight() {
        if (GameState.gameStatus !== 'playing') return false;
        
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        let maxMergedValue = 0;
        
        for (let row = 0; row < GRID_SIZE; row++) {
            const originalRow = [...GridState.tiles[row]];
            const { newRow, scoreGained, maxValue } = processRowRight(GridState.tiles[row]);
            GridState.tiles[row] = newRow;
            
            if (!arraysEqual(originalRow, newRow)) {
                moved = true;
            }
            
            totalScore += scoreGained;
            maxMergedValue = Math.max(maxMergedValue, maxValue);
        }
        
        if (moved) {
            spawnRandomTile();
            
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { 
                    points: totalScore, 
                    newTileValue: maxMergedValue 
                });
            }
            
            EventBus.emit('MOVE_COMPLETED', { 
                direction: 'right', 
                tilesChanged: true 
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        }
        
        return moved;
    }

    function moveUp() {
        if (GameState.gameStatus !== 'playing') return false;
        
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        let maxMergedValue = 0;
        
        for (let col = 0; col < GRID_SIZE; col++) {
            const originalCol = [];
            for (let row = 0; row < GRID_SIZE; row++) {
                originalCol.push(GridState.tiles[row][col]);
            }
            
            const { newRow, scoreGained, maxValue } = processRowLeft(originalCol);
            
            for (let row = 0; row < GRID_SIZE; row++) {
                GridState.tiles[row][col] = newRow[row];
            }
            
            if (!arraysEqual(originalCol, newRow)) {
                moved = true;
            }
            
            totalScore += scoreGained;
            maxMergedValue = Math.max(maxMergedValue, maxValue);
        }
        
        if (moved) {
            spawnRandomTile();
            
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { 
                    points: totalScore, 
                    newTileValue: maxMergedValue 
                });
            }
            
            EventBus.emit('MOVE_COMPLETED', { 
                direction: 'up', 
                tilesChanged: true 
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        }
        
        return moved;
    }

    function moveDown() {
        if (GameState.gameStatus !== 'playing') return false;
        
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        let maxMergedValue = 0;
        
        for (let col = 0; col < GRID_SIZE; col++) {
            const originalCol = [];
            for (let row = 0; row < GRID_SIZE; row++) {
                originalCol.push(GridState.tiles[row][col]);
            }
            
            const { newRow, scoreGained, maxValue } = processRowRight(originalCol);
            
            for (let row = 0; row < GRID_SIZE; row++) {
                GridState.tiles[row][col] = newRow[row];
            }
            
            if (!arraysEqual(originalCol, newRow)) {
                moved = true;
            }
            
            totalScore += scoreGained;
            maxMergedValue = Math.max(maxMergedValue, maxValue);
        }
        
        if (moved) {
            spawnRandomTile();
            
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { 
                    points: totalScore, 
                    newTileValue: maxMergedValue 
                });
            }
            
            EventBus.emit('MOVE_COMPLETED', { 
                direction: 'down', 
                tilesChanged: true 
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        }
        
        return moved;
    }

    function processRowLeft(row) {
        const newRow = [0, 0, 0, 0];
        let scoreGained = 0;
        let maxValue = 0;
        let writeIndex = 0;
        
        // First pass: compact non-zero values
        const compacted = [];
        for (let i = 0; i < GRID_SIZE; i++) {
            if (row[i] !== 0) {
                compacted.push(row[i]);
            }
        }
        
        // Second pass: merge adjacent equal values
        let i = 0;
        while (i < compacted.length) {
            if (i < compacted.length - 1 && compacted[i] === compacted[i + 1]) {
                // Merge tiles
                const mergedValue = compacted[i] * 2;
                newRow[writeIndex] = mergedValue;
                scoreGained += mergedValue;
                maxValue = Math.max(maxValue, mergedValue);
                i += 2; // Skip both merged tiles
            } else {
                // No merge, just move tile
                newRow[writeIndex] = compacted[i];
                i += 1;
            }
            writeIndex++;
        }
        
        return { newRow, scoreGained, maxValue };
    }

    function processRowRight(row) {
        const newRow = [0, 0, 0, 0];
        let scoreGained = 0;
        let maxValue = 0;
        
        // First pass: compact non-zero values to the right
        const compacted = [];
        for (let i = 0; i < GRID_SIZE; i++) {
            if (row[i] !== 0) {
                compacted.push(row[i]);
            }
        }
        
        // Second pass: merge adjacent equal values from right
        let writeIndex = GRID_SIZE - 1;
        let i = compacted.length - 1;
        
        while (i >= 0) {
            if (i > 0 && compacted[i] === compacted[i - 1]) {
                // Merge tiles
                const mergedValue = compacted[i] * 2;
                newRow[writeIndex] = mergedValue;
                scoreGained += mergedValue;
                maxValue = Math.max(maxValue, mergedValue);
                i -= 2; // Skip both merged tiles
            } else {
                // No merge, just move tile
                newRow[writeIndex] = compacted[i];
                i -= 1;
            }
            writeIndex--;
        }
        
        return { newRow, scoreGained, maxValue };
    }

    function arraysEqual(arr1, arr2) {
        if (arr1.length !== arr2.length) return false;
        for (let i = 0; i < arr1.length; i++) {
            if (arr1[i] !== arr2[i]) return false;
        }
        return true;
    }

    function checkGameOver() {
        // Check if there are any empty cells
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (GridState.tiles[row][col] === 0) {
                    return false;
                }
            }
        }
        
        // Check if any horizontal merges are possible
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE - 1; col++) {
                if (GridState.tiles[row][col] === GridState.tiles[row][col + 1]) {
                    return false;
                }
            }
        }
        
        // Check if any vertical merges are possible
        for (let row = 0; row < GRID_SIZE - 1; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (GridState.tiles[row][col] === GridState.tiles[row + 1][col]) {
                    return false;
                }
            }
        }
        
        return true;
    }

    function hasWon() {
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (GridState.tiles[row][col] >= WIN_TILE_VALUE) {
                    return true;
                }
            }
        }
        return false;
    }

    function update(dt) {
        if (GameState.gameStatus === 'playing') {
            // Check for win condition
            if (hasWon() && !GameState.hasWon) {
                GameState.hasWon = true;
            }
        }
    }

    return {
        init,
        resetGrid,
        moveLeft,
        moveRight,
        moveUp,
        moveDown,
        checkGameOver,
        hasWon,
        update
    };
})();

const input_controller = (function() {
    let keyPressQueue = [];
    let touchStartX = 0;
    let touchStartY = 0;
    let isProcessingInput = false;

    function init() {
        // Register keyboard event listeners
        document.addEventListener('keydown', function(event) {
            event.preventDefault();
            keyPressQueue.push(event.key);
        });

        // Register touch event listeners
        document.addEventListener('touchstart', function(event) {
            event.preventDefault();
            const touch = event.touches[0];
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
        });

        document.addEventListener('touchend', function(event) {
            event.preventDefault();
            if (event.changedTouches.length > 0) {
                const touch = event.changedTouches[0];
                handleTouch(touchStartX, touchStartY, touch.clientX, touch.clientY);
            }
        });

        // Register mouse event listeners for desktop
        let mouseStartX = 0;
        let mouseStartY = 0;
        let isMouseDown = false;

        document.addEventListener('mousedown', function(event) {
            event.preventDefault();
            mouseStartX = event.clientX;
            mouseStartY = event.clientY;
            isMouseDown = true;
        });

        document.addEventListener('mouseup', function(event) {
            event.preventDefault();
            if (isMouseDown) {
                handleTouch(mouseStartX, mouseStartY, event.clientX, event.clientY);
                isMouseDown = false;
            }
        });
    }

    function update(dt) {
        if (isProcessingInput) return;

        // Process queued key presses
        while (keyPressQueue.length > 0) {
            const key = keyPressQueue.shift();
            handleKeyPress(key);
        }
    }

    function handleKeyPress(key) {
        if (isProcessingInput) return;
        
        const currentState = GameState.gameStatus;
        
        switch (currentState) {
            case 'menu':
                if (key === 'Enter' || key === ' ') {
                    isProcessingInput = true;
                    EventBus.emit('GAME_START', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                }
                break;

            case 'playing':
                let moved = false;
                isProcessingInput = true;
                
                switch (key) {
                    case 'ArrowLeft':
                    case 'a':
                    case 'A':
                        moved = grid_engine.moveLeft();
                        break;
                    case 'ArrowRight':
                    case 'd':
                    case 'D':
                        moved = grid_engine.moveRight();
                        break;
                    case 'ArrowUp':
                    case 'w':
                    case 'W':
                        moved = grid_engine.moveUp();
                        break;
                    case 'ArrowDown':
                    case 's':
                    case 'S':
                        moved = grid_engine.moveDown();
                        break;
                    case 'Escape':
                        EventBus.emit('RETURN_MENU', {});
                        break;
                }
                
                setTimeout(() => { isProcessingInput = false; }, moved ? 200 : 50);
                break;

            case 'game_over':
                if (key === 'Enter' || key === ' ') {
                    isProcessingInput = true;
                    EventBus.emit('RETRY', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                } else if (key === 'l' || key === 'L') {
                    isProcessingInput = true;
                    EventBus.emit('SHOW_LEADERBOARD', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                } else if (key === 'Escape') {
                    isProcessingInput = true;
                    EventBus.emit('RETURN_MENU', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                }
                break;

            case 'leaderboard':
                if (key === 'Escape' || key === 'Enter' || key === ' ') {
                    isProcessingInput = true;
                    EventBus.emit('CLOSE_LEADERBOARD', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                } else if (key === 'm' || key === 'M') {
                    isProcessingInput = true;
                    EventBus.emit('RETURN_MENU', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                }
                break;
        }
    }

    function handleTouch(startX, startY, endX, endY) {
        if (isProcessingInput) return;
        
        const deltaX = endX - startX;
        const deltaY = endY - startY;
        const minSwipeDistance = 30;
        
        // Check if swipe distance is significant enough
        if (Math.abs(deltaX) < minSwipeDistance && Math.abs(deltaY) < minSwipeDistance) {
            // Treat as tap
            const currentState = GameState.gameStatus;
            
            switch (currentState) {
                case 'menu':
                    isProcessingInput = true;
                    EventBus.emit('GAME_START', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    break;
                case 'game_over':
                    isProcessingInput = true;
                    EventBus.emit('RETRY', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    break;
                case 'leaderboard':
                    isProcessingInput = true;
                    EventBus.emit('CLOSE_LEADERBOARD', {});
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    break;
            }
            return;
        }

        // Only process swipes during gameplay
        if (GameState.gameStatus !== 'playing') return;

        // Determine swipe direction
        let moved = false;
        isProcessingInput = true;
        
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            // Horizontal swipe
            if (deltaX > 0) {
                // Swipe right
                moved = grid_engine.moveRight();
            } else {
                // Swipe left
                moved = grid_engine.moveLeft();
            }
        } else {
            // Vertical swipe
            if (deltaY > 0) {
                // Swipe down
                moved = grid_engine.moveDown();
            } else {
                // Swipe up
                moved = grid_engine.moveUp();
            }
        }
        
        setTimeout(() => { isProcessingInput = false; }, moved ? 200 : 50);
    }

    return {
        init,
        handleKeyPress,
        handleTouch,
        update
    };
})();

const ui_system = (function() {
    function init() {
        // Initialize grid display
        initializeGrid();
    }
    
    function initializeGrid() {
        const gameGrid = document.getElementById('game_grid');
        gameGrid.innerHTML = '';
        
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                const cell = document.createElement('div');
                cell.className = 'grid_cell';
                cell.id = `cell_${row}_${col}`;
                gameGrid.appendChild(cell);
            }
        }
    }
    
    function render() {
        // Update UI based on current game state
        switch (GameState.gameStatus) {
            case 'menu':
                renderMenu();
                break;
            case 'playing':
                renderGame();
                break;
            case 'game_over':
                renderGameOver();
                break;
            case 'leaderboard':
                renderLeaderboard();
                break;
        }
    }
    
    function renderMenu() {
        // Menu is handled by CSS and HTML
    }
    
    function renderGame() {
        // Update score displays
        document.getElementById('score_value').textContent = GameState.score;
        document.getElementById('best_value').textContent = GameState.bestScore;
        
        // Update grid
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                const cell = document.getElementById(`cell_${row}_${col}`);
                const value = GridState.tiles[row][col];
                
                if (value === 0) {
                    cell.textContent = '';
                    cell.className = 'grid_cell';
                } else {
                    cell.textContent = value;
                    cell.className = `grid_cell tile tile-${value}`;
                }
            }
        }
    }
    
    function renderGameOver() {
        document.getElementById('final_score_value').textContent = GameState.score;
    }
    
    function renderLeaderboard() {
        const scores = JSON.parse(localStorage.getItem('2048_leaderboard')) || [];
        const scoreEntries = document.querySelectorAll('.score_entry');
        
        for (let i = 0; i < scoreEntries.length; i++) {
            if (i < scores.length) {
                scoreEntries[i].textContent = `${i + 1}. ${scores[i]}`;
            } else {
                scoreEntries[i].textContent = `${i + 1}. 暂无记录`;
            }
        }
    }
    
    function animateTileMovement(fromRow, fromCol, toRow, toCol) {
        // Simple animation implementation
    }
    
    return {
        init,
        renderMenu,
        renderGame,
        renderGameOver,
        renderLeaderboard,
        animateTileMovement,
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

// State transition functions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', { finalScore: GameState.score });
    showScreen('game_over');
}

function retry() {
    EventBus.emit('RETRY', {});
    showScreen('gameplay');
}

function returnToMenu() {
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

function showLeaderboard() {
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
}

function closeLeaderboard() {
    EventBus.emit('CLOSE_LEADERBOARD', {});
    showScreen('game_over');
}

// Game loop
let lastTime = 0;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update modules in order
    input_controller.update(dt);
    grid_engine.update(dt);
    
    // Render
    ui_system.render();
    
    // Continue loop
    requestAnimationFrame(gameLoop);
}

// Initialize game
window.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in order
    game_state.init();
    grid_engine.init();
    input_controller.init();
    ui_system.init();
    
    // Set up button event listeners
    document.getElementById('btn_play').addEventListener('click', startGame);
    document.getElementById('btn_leaderboard').addEventListener('click', showLeaderboard);
    document.getElementById('btn_new_game').addEventListener('click', retry);
    document.getElementById('btn_retry').addEventListener('click', retry);
    document.getElementById('btn_menu').addEventListener('click', returnToMenu);
    document.getElementById('btn_leaderboard_gameover').addEventListener('click', showLeaderboard);
    document.getElementById('btn_close').addEventListener('click', closeLeaderboard);
    
    // Start game loop
    requestAnimationFrame(gameLoop);
    
    // Show initial screen
    showScreen('main_menu');
});