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

// Global constants
const CANVAS_WIDTH = 600;
const CANVAS_HEIGHT = 800;
const GRID_SIZE = 4;
const TILE_SIZE = 100;
const TILE_MARGIN = 10;

// Module code
const game_state = (function() {
    function init() {
        // Initialize GameState with default values
        GameState.gameStatus = 'menu';
        GameState.score = 0;
        GameState.bestScore = parseInt(localStorage.getItem('2048-bestScore') || '0');
        GameState.hasWon = false;
        GameState.moveCount = 0;

        // Set up event listeners
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
        }
    }

    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            if (GameState.score > GameState.bestScore) {
                GameState.bestScore = GameState.score;
                localStorage.setItem('2048-bestScore', GameState.bestScore.toString());
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

    // Event handlers
    function handleGameStart(event) {
        startGame();
    }

    function handleGameOver(event) {
        endGame();
    }

    function handleRetry(event) {
        if (GameState.gameStatus === 'game_over') {
            startGame();
        }
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
            if (event.newValue === 2048 && !GameState.hasWon) {
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
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                GridState.tiles[row][col] = 0;
                GridState.previousTiles[row][col] = 0;
            }
        }
        GridState.animationQueue = [];
        
        // Spawn two initial tiles
        spawnRandomTile();
        spawnRandomTile();
    }

    function spawnRandomTile() {
        const emptyCells = [];
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                if (GridState.tiles[row][col] === 0) {
                    emptyCells.push({row, col});
                }
            }
        }
        
        if (emptyCells.length > 0) {
            const randomCell = emptyCells[Math.floor(Math.random() * emptyCells.length)];
            const value = Math.random() < 0.9 ? 2 : 4;
            GridState.tiles[randomCell.row][randomCell.col] = value;
        }
    }

    function copyGrid(source, destination) {
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                destination[row][col] = source[row][col];
            }
        }
    }

    function gridsEqual(grid1, grid2) {
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                if (grid1[row][col] !== grid2[row][col]) {
                    return false;
                }
            }
        }
        return true;
    }

    function processLine(line) {
        // Remove zeros
        const filtered = line.filter(val => val !== 0);
        const merged = [];
        let totalPoints = 0;
        
        let i = 0;
        while (i < filtered.length) {
            if (i < filtered.length - 1 && filtered[i] === filtered[i + 1]) {
                // Merge tiles
                const mergedValue = filtered[i] * 2;
                merged.push(mergedValue);
                totalPoints += mergedValue;
                
                // Emit merge event
                EventBus.emit('TILES_MERGED', {
                    points: mergedValue,
                    newValue: mergedValue
                });
                
                i += 2; // Skip both merged tiles
            } else {
                merged.push(filtered[i]);
                i++;
            }
        }
        
        // Pad with zeros
        while (merged.length < 4) {
            merged.push(0);
        }
        
        return merged;
    }

    function moveLeft() {
        if (GameState.gameStatus !== 'playing') return false;
        
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        for (let row = 0; row < 4; row++) {
            const line = [
                GridState.tiles[row][0],
                GridState.tiles[row][1],
                GridState.tiles[row][2],
                GridState.tiles[row][3]
            ];
            
            const processedLine = processLine(line);
            
            for (let col = 0; col < 4; col++) {
                GridState.tiles[row][col] = processedLine[col];
            }
        }
        
        const moved = !gridsEqual(GridState.tiles, GridState.previousTiles);
        
        if (moved) {
            spawnRandomTile();
            
            EventBus.emit('MOVE_COMPLETED', {
                direction: 'left',
                moved: true
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', {
                    finalScore: GameState.score
                });
            }
        }
        
        return moved;
    }

    function moveRight() {
        if (GameState.gameStatus !== 'playing') return false;
        
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        for (let row = 0; row < 4; row++) {
            const line = [
                GridState.tiles[row][3],
                GridState.tiles[row][2],
                GridState.tiles[row][1],
                GridState.tiles[row][0]
            ];
            
            const processedLine = processLine(line);
            
            for (let col = 0; col < 4; col++) {
                GridState.tiles[row][3 - col] = processedLine[col];
            }
        }
        
        const moved = !gridsEqual(GridState.tiles, GridState.previousTiles);
        
        if (moved) {
            spawnRandomTile();
            
            EventBus.emit('MOVE_COMPLETED', {
                direction: 'right',
                moved: true
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', {
                    finalScore: GameState.score
                });
            }
        }
        
        return moved;
    }

    function moveUp() {
        if (GameState.gameStatus !== 'playing') return false;
        
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        for (let col = 0; col < 4; col++) {
            const line = [
                GridState.tiles[0][col],
                GridState.tiles[1][col],
                GridState.tiles[2][col],
                GridState.tiles[3][col]
            ];
            
            const processedLine = processLine(line);
            
            for (let row = 0; row < 4; row++) {
                GridState.tiles[row][col] = processedLine[row];
            }
        }
        
        const moved = !gridsEqual(GridState.tiles, GridState.previousTiles);
        
        if (moved) {
            spawnRandomTile();
            
            EventBus.emit('MOVE_COMPLETED', {
                direction: 'up',
                moved: true
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', {
                    finalScore: GameState.score
                });
            }
        }
        
        return moved;
    }

    function moveDown() {
        if (GameState.gameStatus !== 'playing') return false;
        
        copyGrid(GridState.tiles, GridState.previousTiles);
        
        for (let col = 0; col < 4; col++) {
            const line = [
                GridState.tiles[3][col],
                GridState.tiles[2][col],
                GridState.tiles[1][col],
                GridState.tiles[0][col]
            ];
            
            const processedLine = processLine(line);
            
            for (let row = 0; row < 4; row++) {
                GridState.tiles[3 - row][col] = processedLine[row];
            }
        }
        
        const moved = !gridsEqual(GridState.tiles, GridState.previousTiles);
        
        if (moved) {
            spawnRandomTile();
            
            EventBus.emit('MOVE_COMPLETED', {
                direction: 'down',
                moved: true
            });
            
            if (checkGameOver()) {
                EventBus.emit('GAME_OVER', {
                    finalScore: GameState.score
                });
            }
        }
        
        return moved;
    }

    function checkGameOver() {
        // Check for empty cells
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                if (GridState.tiles[row][col] === 0) {
                    return false;
                }
            }
        }
        
        // Check for possible merges horizontally
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 3; col++) {
                if (GridState.tiles[row][col] === GridState.tiles[row][col + 1]) {
                    return false;
                }
            }
        }
        
        // Check for possible merges vertically
        for (let row = 0; row < 3; row++) {
            for (let col = 0; col < 4; col++) {
                if (GridState.tiles[row][col] === GridState.tiles[row + 1][col]) {
                    return false;
                }
            }
        }
        
        return true;
    }

    function hasWon() {
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                if (GridState.tiles[row][col] === 2048) {
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
                game_state.addScore(0); // Trigger win state update
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
    let keyPressed = {};
    let touchStartX = 0;
    let touchStartY = 0;
    let isTouch = false;

    function init() {
        // Register keyboard event listeners
        document.addEventListener('keydown', function(event) {
            if (!keyPressed[event.key]) {
                keyPressed[event.key] = true;
                handleKeyPress(event.key);
            }
            event.preventDefault();
        });

        document.addEventListener('keyup', function(event) {
            keyPressed[event.key] = false;
        });

        // Register touch event listeners
        document.addEventListener('touchstart', function(event) {
            if (event.touches.length === 1) {
                touchStartX = event.touches[0].clientX;
                touchStartY = event.touches[0].clientY;
                isTouch = true;
            }
            event.preventDefault();
        });

        document.addEventListener('touchend', function(event) {
            if (isTouch && event.changedTouches.length === 1) {
                const touchEndX = event.changedTouches[0].clientX;
                const touchEndY = event.changedTouches[0].clientY;
                handleTouch(touchStartX, touchStartY, touchEndX, touchEndY);
                isTouch = false;
            }
            event.preventDefault();
        });

        // Register mouse event listeners for click-based navigation
        document.addEventListener('mousedown', function(event) {
            touchStartX = event.clientX;
            touchStartY = event.clientY;
        });

        document.addEventListener('mouseup', function(event) {
            const mouseEndX = event.clientX;
            const mouseEndY = event.clientY;
            const deltaX = mouseEndX - touchStartX;
            const deltaY = mouseEndY - touchStartY;
            
            // If it's a small movement, treat as click, otherwise as swipe
            if (Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10) {
                // Handle click for menu navigation
                if (GameState.gameStatus === 'menu') {
                    EventBus.emit('GAME_START');
                } else if (GameState.gameStatus === 'game_over') {
                    // Simple click handling - could be enhanced with button detection
                    EventBus.emit('RETRY');
                }
            } else {
                handleTouch(touchStartX, touchStartY, mouseEndX, mouseEndY);
            }
        });

        // Listen for events that this module should respond to
        EventBus.on('GAME_START', function() {
            game_state.startGame();
            grid_engine.resetGrid();
        });

        EventBus.on('RETRY', function() {
            game_state.startGame();
            grid_engine.resetGrid();
        });

        EventBus.on('RETURN_MENU', function() {
            game_state.returnToMenu();
        });

        EventBus.on('SHOW_LEADERBOARD', function() {
            game_state.showLeaderboard();
        });

        EventBus.on('CLOSE_LEADERBOARD', function() {
            game_state.returnToMenu();
        });
    }

    function handleKeyPress(key) {
        if (GameState.gameStatus === 'menu') {
            if (key === 'Enter' || key === ' ') {
                EventBus.emit('GAME_START');
            }
        } else if (GameState.gameStatus === 'playing') {
            let moved = false;
            
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
            }

            if (moved && grid_engine.checkGameOver()) {
                EventBus.emit('GAME_OVER', {
                    finalScore: GameState.score
                });
            }
        } else if (GameState.gameStatus === 'game_over') {
            if (key === 'r' || key === 'R' || key === 'Enter') {
                EventBus.emit('RETRY');
            } else if (key === 'Escape' || key === 'm' || key === 'M') {
                EventBus.emit('RETURN_MENU');
            } else if (key === 'l' || key === 'L') {
                EventBus.emit('SHOW_LEADERBOARD');
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            if (key === 'Escape' || key === 'Enter') {
                EventBus.emit('CLOSE_LEADERBOARD');
            } else if (key === 'm' || key === 'M') {
                EventBus.emit('RETURN_MENU');
            }
        }
    }

    function handleTouch(startX, startY, endX, endY) {
        const deltaX = endX - startX;
        const deltaY = endY - startY;
        const minSwipeDistance = 30;

        // Only process swipes during gameplay
        if (GameState.gameStatus !== 'playing') {
            return;
        }

        // Check if swipe distance is significant enough
        if (Math.abs(deltaX) < minSwipeDistance && Math.abs(deltaY) < minSwipeDistance) {
            return;
        }

        let moved = false;

        // Determine swipe direction based on larger delta
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

        if (moved && grid_engine.checkGameOver()) {
            EventBus.emit('GAME_OVER', {
                finalScore: GameState.score
            });
        }
    }

    function update(dt) {
        // Input controller doesn't need continuous updates
        // All input is handled via event listeners
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
        // Initialize UI elements
        updateUI();
    }
    
    function renderMenu() {
        if (GameState.gameStatus !== 'menu') return;
        updateUI();
    }
    
    function renderGame() {
        if (GameState.gameStatus !== 'playing') return;
        updateUI();
        updateGrid();
    }
    
    function renderGameOver() {
        if (GameState.gameStatus !== 'game_over') return;
        updateUI();
        document.getElementById('final_score').textContent = `最终得分: ${GameState.score}`;
    }
    
    function renderLeaderboard() {
        if (GameState.gameStatus !== 'leaderboard') return;
        updateUI();
        document.getElementById('best_score_display').textContent = GameState.bestScore;
    }
    
    function animateTileMovement(fromRow, fromCol, toRow, toCol) {
        // Animation handling could be added here
    }
    
    function updateUI() {
        // Update score displays
        const scoreValue = document.getElementById('score_value');
        const bestValue = document.getElementById('best_value');
        
        if (scoreValue) scoreValue.textContent = GameState.score;
        if (bestValue) bestValue.textContent = GameState.bestScore;
    }
    
    function updateGrid() {
        const gameGrid = document.getElementById('game_grid');
        if (!gameGrid) return;
        
        // Clear existing tiles
        gameGrid.innerHTML = '';
        
        // Create tiles
        for (let row = 0; row < 4; row++) {
            for (let col = 0; col < 4; col++) {
                const tile = document.createElement('div');
                tile.className = 'tile';
                
                const value = GridState.tiles[row][col];
                if (value > 0) {
                    tile.textContent = value;
                    tile.classList.add(`tile-${value}`);
                }
                
                gameGrid.appendChild(tile);
            }
        }
    }
    
    function render() {
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

// Game loop
let lastTime = 0;
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Call update functions in update_order
    input_controller.update(dt);
    grid_engine.update(dt);
    
    // Call render functions in render_order
    ui_system.render();
    
    requestAnimationFrame(gameLoop);
}

// State transitions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START');
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('GAME_OVER', { finalScore: GameState.score });
    showScreen('game_over');
}

function retry() {
    GameState.gameStatus = 'playing';
    EventBus.emit('RETRY');
    showScreen('gameplay');
}

function returnToMenu() {
    GameState.gameStatus = 'menu';
    EventBus.emit('RETURN_MENU');
    showScreen('main_menu');
}

function showLeaderboard() {
    GameState.gameStatus = 'leaderboard';
    EventBus.emit('SHOW_LEADERBOARD');
    showScreen('leaderboard');
}

function closeLeaderboard() {
    GameState.gameStatus = 'game_over';
    EventBus.emit('CLOSE_LEADERBOARD');
    showScreen('game_over');
}

// Module initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in init_order
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
    document.getElementById('btn_close').addEventListener('click', function() {
        returnToMenu();
    });
    
    // Set up EventBus listeners for state transitions
    EventBus.on('GAME_START', function() {
        showScreen('gameplay');
    });
    
    EventBus.on('GAME_OVER', function() {
        showScreen('game_over');
    });
    
    EventBus.on('RETRY', function() {
        showScreen('gameplay');
    });
    
    EventBus.on('RETURN_MENU', function() {
        showScreen('main_menu');
    });
    
    EventBus.on('SHOW_LEADERBOARD', function() {
        showScreen('leaderboard');
    });
    
    EventBus.on('CLOSE_LEADERBOARD', function() {
        showScreen('game_over');
    });
    
    // Start game loop
    requestAnimationFrame(gameLoop);
    
    // Show initial screen
    showScreen('main_menu');
});