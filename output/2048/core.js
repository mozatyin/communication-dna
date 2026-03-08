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
const GRID_SIZE = 4;
const TILE_SIZE = 100;
const TILE_MARGIN = 10;
const WIN_VALUE = 2048;

// Shared State Objects
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

// Module Code
const game_state = (function() {
    function init() {
        // Set up event listeners
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('GAME_OVER', handleGameOver);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('SHOW_LEADERBOARD', handleShowLeaderboard);
        EventBus.on('CLOSE_LEADERBOARD', handleCloseLeaderboard);
        EventBus.on('TILES_MERGED', handleTilesMerged);
    }
    
    function handleGameStart() {
        if (GameState.gameStatus === 'menu') {
            startGame();
        }
    }
    
    function handleGameOver(event) {
        if (GameState.gameStatus === 'playing') {
            endGame();
        }
    }
    
    function handleRetry() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.hasWon = false;
            GameState.moveCount = 0;
        }
    }
    
    function handleReturnMenu() {
        returnToMenu();
    }
    
    function handleShowLeaderboard() {
        if (GameState.gameStatus === 'game_over') {
            showLeaderboard();
        }
    }
    
    function handleCloseLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = 'game_over';
        }
    }
    
    function handleTilesMerged(event) {
        if (GameState.gameStatus === 'playing') {
            addScore(event.points);
            if (event.newValue === 2048) {
                GameState.hasWon = true;
            }
        }
    }
    
    function startGame() {
        if (GameState.gameStatus === 'menu') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            GameState.hasWon = false;
            GameState.moveCount = 0;
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            if (GameState.score > GameState.bestScore) {
                GameState.bestScore = GameState.score;
            }
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
        // Initialize grid with empty tiles
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
        // Clear grid
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

    function gridsEqual(grid1, grid2) {
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (grid1[row][col] !== grid2[row][col]) {
                    return false;
                }
            }
        }
        return true;
    }

    function moveLeft() {
        if (GameState.gameStatus !== 'playing') return false;
        
        // Save previous state
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        
        for (let row = 0; row < GRID_SIZE; row++) {
            const line = GridState.tiles[row].slice();
            const { newLine, score, hasMoved } = processLine(line);
            
            if (hasMoved) {
                moved = true;
                GridState.tiles[row] = newLine;
                totalScore += score;
            }
        }
        
        if (moved) {
            spawnRandomTile();
            GameState.moveCount++;
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { points: totalScore, newValue: getHighestValue() });
            }
            EventBus.emit('MOVE_COMPLETED', { direction: 'left', moved: true });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        } else {
            EventBus.emit('MOVE_COMPLETED', { direction: 'left', moved: false });
        }
        
        return moved;
    }

    function moveRight() {
        if (GameState.gameStatus !== 'playing') return false;
        
        // Save previous state
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        
        for (let row = 0; row < GRID_SIZE; row++) {
            const line = GridState.tiles[row].slice().reverse();
            const { newLine, score, hasMoved } = processLine(line);
            
            if (hasMoved) {
                moved = true;
                GridState.tiles[row] = newLine.reverse();
                totalScore += score;
            }
        }
        
        if (moved) {
            spawnRandomTile();
            GameState.moveCount++;
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { points: totalScore, newValue: getHighestValue() });
            }
            EventBus.emit('MOVE_COMPLETED', { direction: 'right', moved: true });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        } else {
            EventBus.emit('MOVE_COMPLETED', { direction: 'right', moved: false });
        }
        
        return moved;
    }

    function moveUp() {
        if (GameState.gameStatus !== 'playing') return false;
        
        // Save previous state
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        
        for (let col = 0; col < GRID_SIZE; col++) {
            const line = [];
            for (let row = 0; row < GRID_SIZE; row++) {
                line.push(GridState.tiles[row][col]);
            }
            
            const { newLine, score, hasMoved } = processLine(line);
            
            if (hasMoved) {
                moved = true;
                for (let row = 0; row < GRID_SIZE; row++) {
                    GridState.tiles[row][col] = newLine[row];
                }
                totalScore += score;
            }
        }
        
        if (moved) {
            spawnRandomTile();
            GameState.moveCount++;
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { points: totalScore, newValue: getHighestValue() });
            }
            EventBus.emit('MOVE_COMPLETED', { direction: 'up', moved: true });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        } else {
            EventBus.emit('MOVE_COMPLETED', { direction: 'up', moved: false });
        }
        
        return moved;
    }

    function moveDown() {
        if (GameState.gameStatus !== 'playing') return false;
        
        // Save previous state
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        let moved = false;
        let totalScore = 0;
        
        for (let col = 0; col < GRID_SIZE; col++) {
            const line = [];
            for (let row = GRID_SIZE - 1; row >= 0; row--) {
                line.push(GridState.tiles[row][col]);
            }
            
            const { newLine, score, hasMoved } = processLine(line);
            
            if (hasMoved) {
                moved = true;
                for (let row = 0; row < GRID_SIZE; row++) {
                    GridState.tiles[GRID_SIZE - 1 - row][col] = newLine[row];
                }
                totalScore += score;
            }
        }
        
        if (moved) {
            spawnRandomTile();
            GameState.moveCount++;
            if (totalScore > 0) {
                EventBus.emit('TILES_MERGED', { points: totalScore, newValue: getHighestValue() });
            }
            EventBus.emit('MOVE_COMPLETED', { direction: 'down', moved: true });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', { finalScore: GameState.score });
            }
        } else {
            EventBus.emit('MOVE_COMPLETED', { direction: 'down', moved: false });
        }
        
        return moved;
    }

    function processLine(line) {
        // Remove zeros
        const filtered = line.filter(val => val !== 0);
        const newLine = [0, 0, 0, 0];
        let score = 0;
        let pos = 0;
        
        for (let i = 0; i < filtered.length; i++) {
            if (i < filtered.length - 1 && filtered[i] === filtered[i + 1]) {
                // Merge tiles
                const mergedValue = filtered[i] * 2;
                newLine[pos] = mergedValue;
                score += mergedValue;
                i++; // Skip next tile as it was merged
            } else {
                newLine[pos] = filtered[i];
            }
            pos++;
        }
        
        // Check if line changed
        const hasMoved = !arraysEqual(line, newLine);
        
        return { newLine, score, hasMoved };
    }

    function arraysEqual(arr1, arr2) {
        if (arr1.length !== arr2.length) return false;
        for (let i = 0; i < arr1.length; i++) {
            if (arr1[i] !== arr2[i]) return false;
        }
        return true;
    }

    function getHighestValue() {
        let highest = 0;
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (GridState.tiles[row][col] > highest) {
                    highest = GridState.tiles[row][col];
                }
            }
        }
        return highest;
    }

    function checkGameOver() {
        // Check for empty cells
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (GridState.tiles[row][col] === 0) {
                    return false;
                }
            }
        }
        
        // Check for possible merges horizontally
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE - 1; col++) {
                if (GridState.tiles[row][col] === GridState.tiles[row][col + 1]) {
                    return false;
                }
            }
        }
        
        // Check for possible merges vertically
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
                if (GridState.tiles[row][col] >= WIN_VALUE) {
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
    let keyBuffer = [];
    let touchStartX = 0;
    let touchStartY = 0;
    let isProcessingInput = false;

    function init() {
        // Register keyboard event listeners
        document.addEventListener('keydown', function(event) {
            keyBuffer.push(event.key);
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

        // Register mouse events for desktop
        let mouseStartX = 0;
        let mouseStartY = 0;
        let isMouseDown = false;

        document.addEventListener('mousedown', function(event) {
            mouseStartX = event.clientX;
            mouseStartY = event.clientY;
            isMouseDown = true;
        });

        document.addEventListener('mouseup', function(event) {
            if (isMouseDown) {
                handleTouch(mouseStartX, mouseStartY, event.clientX, event.clientY);
                isMouseDown = false;
            }
        });
    }

    function update(dt) {
        // Process buffered key inputs
        while (keyBuffer.length > 0 && !isProcessingInput) {
            const key = keyBuffer.shift();
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
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    
                    EventBus.emit('GAME_START', {});
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
                if (key === 'Enter' || key === ' ' || key === 'r' || key === 'R') {
                    isProcessingInput = true;
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    
                    EventBus.emit('RETRY', {});
                } else if (key === 'l' || key === 'L') {
                    isProcessingInput = true;
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    
                    EventBus.emit('SHOW_LEADERBOARD', {});
                } else if (key === 'Escape' || key === 'm' || key === 'M') {
                    isProcessingInput = true;
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    
                    EventBus.emit('RETURN_MENU', {});
                }
                break;

            case 'leaderboard':
                if (key === 'Escape' || key === 'Enter' || key === ' ') {
                    isProcessingInput = true;
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    
                    EventBus.emit('CLOSE_LEADERBOARD', {});
                } else if (key === 'm' || key === 'M') {
                    isProcessingInput = true;
                    setTimeout(() => { isProcessingInput = false; }, 100);
                    
                    EventBus.emit('RETURN_MENU', {});
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
            // Handle tap for menu navigation
            const currentState = GameState.gameStatus;
            
            if (currentState === 'menu') {
                isProcessingInput = true;
                setTimeout(() => { isProcessingInput = false; }, 100);
                
                EventBus.emit('GAME_START', {});
            } else if (currentState === 'game_over') {
                isProcessingInput = true;
                setTimeout(() => { isProcessingInput = false; }, 100);
                
                EventBus.emit('RETRY', {});
            } else if (currentState === 'leaderboard') {
                isProcessingInput = true;
                setTimeout(() => { isProcessingInput = false; }, 100);
                
                EventBus.emit('CLOSE_LEADERBOARD', {});
            }
            return;
        }

        // Determine swipe direction
        if (GameState.gameStatus === 'playing') {
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
    }

    return {
        init,
        handleKeyPress,
        handleTouch,
        update
    };
})();

const ui_system = (function() {
    let canvas;
    let ctx;
    let animations = [];
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        canvas.width = CANVAS_WIDTH;
        canvas.height = CANVAS_HEIGHT;
        ctx = canvas.getContext('2d');
        
        // Listen for move completed events to trigger animations
        EventBus.on('MOVE_COMPLETED', function(event) {
            processAnimationQueue();
        });
    }
    
    function render(dt) {
        // Clear canvas
        ctx.fillStyle = '#faf8ef';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Update animations
        updateAnimations(dt);
        
        // Render based on current game status
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
        
        // Update UI elements
        updateUIElements();
    }
    
    function updateUIElements() {
        // Update score displays
        const scoreValue = document.getElementById('score_value');
        const bestValue = document.getElementById('best_value');
        const finalScore = document.getElementById('final_score');
        const bestScoreDisplay = document.getElementById('best_score_display');
        const currentScoreDisplay = document.getElementById('current_score_display');
        
        if (scoreValue) scoreValue.textContent = GameState.score;
        if (bestValue) bestValue.textContent = GameState.bestScore;
        if (finalScore) finalScore.textContent = '最终得分: ' + GameState.score;
        if (bestScoreDisplay) bestScoreDisplay.textContent = GameState.bestScore;
        if (currentScoreDisplay) currentScoreDisplay.textContent = GameState.score;
    }
    
    function renderMenu() {
        if (GameState.gameStatus !== 'menu') return;
        
        ctx.fillStyle = '#776e65';
        ctx.font = 'bold 48px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('2048', CANVAS_WIDTH / 2, 150);
        
        ctx.font = '24px Arial';
        ctx.fillText('Press SPACE to start', CANVAS_WIDTH / 2, 250);
        ctx.fillText('Use arrow keys or WASD to move', CANVAS_WIDTH / 2, 300);
        
        if (GameState.bestScore > 0) {
            ctx.fillText('Best Score: ' + GameState.bestScore, CANVAS_WIDTH / 2, 400);
        }
    }
    
    function renderGame() {
        if (GameState.gameStatus !== 'playing') return;
        
        // Render grid background
        const gridStartX = (CANVAS_WIDTH - (GRID_SIZE * TILE_SIZE + (GRID_SIZE - 1) * TILE_MARGIN)) / 2;
        const gridStartY = 100;
        
        ctx.fillStyle = '#bbada0';
        ctx.fillRect(gridStartX - TILE_MARGIN, gridStartY - TILE_MARGIN, 
                    GRID_SIZE * TILE_SIZE + (GRID_SIZE + 1) * TILE_MARGIN, 
                    GRID_SIZE * TILE_SIZE + (GRID_SIZE + 1) * TILE_MARGIN);
        
        // Render empty grid cells
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                const x = gridStartX + col * (TILE_SIZE + TILE_MARGIN);
                const y = gridStartY + row * (TILE_SIZE + TILE_MARGIN);
                
                ctx.fillStyle = '#cdc1b4';
                ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
            }
        }
        
        // Render tiles
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                const value = GridState.tiles[row][col];
                if (value > 0) {
                    renderTile(gridStartX + col * (TILE_SIZE + TILE_MARGIN), 
                              gridStartY + row * (TILE_SIZE + TILE_MARGIN), 
                              value);
                }
            }
        }
        
        // Render animations
        renderAnimations(gridStartX, gridStartY);
        
        if (GameState.hasWon) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
            ctx.fillStyle = '#776e65';
            ctx.font = 'bold 48px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('You Win!', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2);
            ctx.font = '24px Arial';
            ctx.fillText('Press R to continue or ESC for menu', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 50);
        }
    }
    
    function renderGameOver() {
        if (GameState.gameStatus !== 'game_over') return;
        
        // Render the game grid in background (dimmed)
        renderGame();
        
        // Overlay
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        ctx.fillStyle = '#776e65';
        ctx.font = 'bold 48px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Game Over', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 50);
        
        ctx.font = '24px Arial';
        ctx.fillText('Final Score: ' + GameState.score, CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2);
        ctx.fillText('Press R to retry', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 50);
        ctx.fillText('Press L for leaderboard', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 80);
        ctx.fillText('Press ESC for menu', CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 110);
    }
    
    function renderLeaderboard() {
        if (GameState.gameStatus !== 'leaderboard') return;
        
        ctx.fillStyle = '#776e65';
        ctx.font = 'bold 36px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Leaderboard', CANVAS_WIDTH / 2, 100);
        
        ctx.font = '24px Arial';
        ctx.fillText('Best Score: ' + GameState.bestScore, CANVAS_WIDTH / 2, 200);
        ctx.fillText('Current Score: ' + GameState.score, CANVAS_WIDTH / 2, 250);
        
        ctx.font = '18px Arial';
        ctx.fillText('Press ESC to return', CANVAS_WIDTH / 2, 400);
    }
    
    function renderTile(x, y, value) {
        // Tile background
        const tileColor = getTileColor(value);
        const textColor = value <= 4 ? '#776e65' : '#f9f6f2';
        
        ctx.fillStyle = tileColor;
        ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        // Tile text
        ctx.fillStyle = textColor;
        ctx.font = 'bold ' + getTileFont(value) + 'px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(value.toString(), x + TILE_SIZE / 2, y + TILE_SIZE / 2 + 8);
    }
    
    function getTileColor(value) {
        const colors = {
            2: '#eee4da',
            4: '#ede0c8',
            8: '#f2b179',
            16: '#f59563',
            32: '#f67c5f',
            64: '#f65e3b',
            128: '#edcf72',
            256: '#edcc61',
            512: '#edc850',
            1024: '#edc53f',
            2048: '#edc22e'
        };
        return colors[value] || '#3c3a32';
    }
    
    function getTileFont(value) {
        if (value < 100) return 32;
        if (value < 1000) return 28;
        return 24;
    }
    
    function animateTileMovement(fromRow, fromCol, toRow, toCol) {
        const animation = {
            fromRow: fromRow,
            fromCol: fromCol,
            toRow: toRow,
            toCol: toCol,
            progress: 0,
            duration: 150 // milliseconds
        };
        animations.push(animation);
    }
    
    function updateAnimations(dt) {
        for (let i = animations.length - 1; i >= 0; i--) {
            const anim = animations[i];
            anim.progress += dt * 1000;
            
            if (anim.progress >= anim.duration) {
                animations.splice(i, 1);
            }
        }
    }
    
    function renderAnimations(gridStartX, gridStartY) {
        for (const anim of animations) {
            const t = Math.min(anim.progress / anim.duration, 1);
            const easeT = 1 - Math.pow(1 - t, 3); // ease out cubic
            
            const fromX = gridStartX + anim.fromCol * (TILE_SIZE + TILE_MARGIN);
            const fromY = gridStartY + anim.fromRow * (TILE_SIZE + TILE_MARGIN);
            const toX = gridStartX + anim.toCol * (TILE_SIZE + TILE_MARGIN);
            const toY = gridStartY + anim.toRow * (TILE_SIZE + TILE_MARGIN);
            
            const currentX = fromX + (toX - fromX) * easeT;
            const currentY = fromY + (toY - fromY) * easeT;
            
            // Get the tile value from previous state
            const value = GridState.previousTiles[anim.fromRow][anim.fromCol];
            if (value > 0) {
                renderTile(currentX, currentY, value);
            }
        }
    }
    
    function processAnimationQueue() {
        // Process animations from GridState.animationQueue
        for (const animData of GridState.animationQueue) {
            if (animData.type === 'move') {
                animateTileMovement(animData.fromRow, animData.fromCol, animData.toRow, animData.toCol);
            }
        }
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

// State transition functions
function startGame() {
    GameState.gameStatus = 'playing';
    grid_engine.resetGrid();
    EventBus.emit('GAME_START', {});
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', { finalScore: GameState.score });
    showScreen('game_over');
}

function retry() {
    GameState.gameStatus = 'playing';
    GameState.score = 0;
    GameState.hasWon = false;
    GameState.moveCount = 0;
    grid_engine.resetGrid();
    EventBus.emit('RETRY', {});
    showScreen('gameplay');
}

function returnToMenu() {
    GameState.gameStatus = 'menu';
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

function showLeaderboard() {
    GameState.gameStatus = 'leaderboard';
    EventBus.emit('SHOW_LEADERBOARD', {});
    showScreen('leaderboard');
}

function closeLeaderboard() {
    GameState.gameStatus = 'game_over';
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
    ui_system.render(dt);
    
    if (GameState.gameStatus !== 'menu' || GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    } else {
        requestAnimationFrame(gameLoop);
    }
}

// Event listeners for UI buttons
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules
    game_state.init();
    grid_engine.init();
    input_controller.init();
    ui_system.init();
    
    // Set up button event listeners
    const btnPlay = document.getElementById('btn_play');
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    const btnNewGame = document.getElementById('btn_new_game');
    const btnRetry = document.getElementById('btn_retry');
    const btnMenu = document.getElementById('btn_menu');
    const btnLeaderboardGo = document.getElementById('btn_leaderboard_go');
    const btnClose = document.getElementById('btn_close');
    
    if (btnPlay) btnPlay.addEventListener('click', startGame);
    if (btnLeaderboard) btnLeaderboard.addEventListener('click', showLeaderboard);
    if (btnNewGame) btnNewGame.addEventListener('click', retry);
    if (btnRetry) btnRetry.addEventListener('click', retry);
    if (btnMenu) btnMenu.addEventListener('click', returnToMenu);
    if (btnLeaderboardGo) btnLeaderboardGo.addEventListener('click', showLeaderboard);
    if (btnClose) btnClose.addEventListener('click', closeLeaderboard);
    
    // Set up EventBus listeners for state transitions
    EventBus.on('GAME_START', () => {
        if (GameState.gameStatus === 'menu') {
            startGame();
        }
    });
    
    EventBus.on('GAME_OVER', () => {
        if (GameState.gameStatus === 'playing') {
            gameOver();
        }
    });
    
    EventBus.on('RETRY', () => {
        if (GameState.gameStatus === 'game_over') {
            retry();
        }
    });
    
    EventBus.on('RETURN_MENU', () => {
        returnToMenu();
    });
    
    EventBus.on('SHOW_LEADERBOARD', () => {
        if (GameState.gameStatus === 'game_over') {
            showLeaderboard();
        }
    });
    
    EventBus.on('CLOSE_LEADERBOARD', () => {
        if (GameState.gameStatus === 'leaderboard') {
            closeLeaderboard();
        }
    });
    
    // Start the game loop
    requestAnimationFrame(gameLoop);
});