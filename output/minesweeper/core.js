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

// Make EventBus globally available
window.eventBus = EventBus;

// Shared state objects
const GameState = {
    gameStatus: 'menu',
    gameTime: 0,
    difficulty: 'beginner',
    gameWon: false,
    flagsRemaining: 10
};

const MinefieldState = {
    width: 9,
    height: 9,
    mineCount: 10,
    revealedCells: 0
};

// Global constants
const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const CELL_SIZE = 30;
const BEGINNER_WIDTH = 9;
const BEGINNER_HEIGHT = 9;
const BEGINNER_MINES = 10;
const INTERMEDIATE_WIDTH = 16;
const INTERMEDIATE_HEIGHT = 16;
const INTERMEDIATE_MINES = 40;
const EXPERT_WIDTH = 30;
const EXPERT_HEIGHT = 16;
const EXPERT_MINES = 99;

// Module code
const game_state = (function() {
    let timerInterval = null;
    let lastUpdateTime = Date.now();

    function init() {
        GameState.gameStatus = 'menu';
        GameState.gameTime = 0;
        GameState.difficulty = 'beginner';
        GameState.gameWon = false;
        GameState.flagsRemaining = 10;

        // Listen for events
        EventBus.on('GAME_START', handleGameStart);
        EventBus.on('GAME_WON', handleGameWon);
        EventBus.on('GAME_LOST', handleGameLost);
        EventBus.on('RETRY', handleRetry);
        EventBus.on('RETURN_MENU', handleReturnMenu);
        EventBus.on('SHOW_LEADERBOARD', handleShowLeaderboard);
        EventBus.on('CLOSE_LEADERBOARD', handleCloseLeaderboard);
        EventBus.on('PLAY_AGAIN', handlePlayAgain);
    }

    function startGame(difficulty) {
        if (GameState.gameStatus !== 'menu') return;
        
        GameState.gameStatus = 'playing';
        GameState.difficulty = difficulty;
        GameState.gameTime = 0;
        GameState.gameWon = false;
        
        // Set flags remaining based on difficulty
        switch (difficulty) {
            case 'beginner':
                GameState.flagsRemaining = BEGINNER_MINES;
                break;
            case 'intermediate':
                GameState.flagsRemaining = INTERMEDIATE_MINES;
                break;
            case 'expert':
                GameState.flagsRemaining = EXPERT_MINES;
                break;
            default:
                GameState.flagsRemaining = 10;
        }
        
        startTimer();
    }

    function endGame(won) {
        if (GameState.gameStatus !== 'playing') return;
        
        GameState.gameStatus = 'game_over';
        GameState.gameWon = won;
        stopTimer();
    }

    function updateTimer() {
        if (GameState.gameStatus !== 'playing') return;
        
        const currentTime = Date.now();
        const deltaTime = (currentTime - lastUpdateTime) / 1000;
        lastUpdateTime = currentTime;
        
        GameState.gameTime += deltaTime;
    }

    function setState(newState) {
        GameState.gameStatus = newState;
    }

    function startTimer() {
        lastUpdateTime = Date.now();
    }

    function stopTimer() {
        // Timer is stopped by changing game status, no additional action needed
    }

    // Event handlers
    function handleGameStart(data) {
        startGame(data.difficulty);
    }

    function handleGameWon(data) {
        endGame(true);
    }

    function handleGameLost(data) {
        endGame(false);
    }

    function handleRetry(data) {
        if (GameState.gameStatus === 'game_over') {
            startGame(GameState.difficulty);
        }
    }

    function handleReturnMenu(data) {
        if (GameState.gameStatus === 'game_over') {
            setState('menu');
        }
    }

    function handleShowLeaderboard(data) {
        if (GameState.gameStatus === 'game_over') {
            setState('leaderboard');
        }
    }

    function handleCloseLeaderboard(data) {
        if (GameState.gameStatus === 'leaderboard') {
            setState('menu');
        }
    }

    function handlePlayAgain(data) {
        if (GameState.gameStatus === 'leaderboard') {
            startGame(data.difficulty);
        }
    }

    return {
        init,
        startGame,
        endGame,
        updateTimer,
        setState
    };
})();

const minefield = (function() {
    let grid = [];
    let mines = [];
    let adjacentCounts = [];
    let revealed = [];
    let flagged = [];
    let firstClick = true;

    function init() {
        // Initialize minefield module
        grid = [];
        mines = [];
        adjacentCounts = [];
        revealed = [];
        flagged = [];
        firstClick = true;
    }

    function generateField(width, height, mineCount) {
        if (GameState.gameStatus !== 'playing') return;

        MinefieldState.width = width;
        MinefieldState.height = height;
        MinefieldState.mineCount = mineCount;
        MinefieldState.revealedCells = 0;
        GameState.flagsRemaining = mineCount;

        // Initialize grids
        grid = [];
        mines = [];
        adjacentCounts = [];
        revealed = [];
        flagged = [];

        for (let y = 0; y < height; y++) {
            grid[y] = [];
            mines[y] = [];
            adjacentCounts[y] = [];
            revealed[y] = [];
            flagged[y] = [];
            for (let x = 0; x < width; x++) {
                grid[y][x] = 'empty';
                mines[y][x] = false;
                adjacentCounts[y][x] = 0;
                revealed[y][x] = false;
                flagged[y][x] = false;
            }
        }

        firstClick = true;
    }

    function placeMines(excludeX, excludeY, mineCount) {
        const positions = [];
        for (let y = 0; y < MinefieldState.height; y++) {
            for (let x = 0; x < MinefieldState.width; x++) {
                if (x !== excludeX || y !== excludeY) {
                    positions.push({x, y});
                }
            }
        }

        // Shuffle and place mines
        for (let i = 0; i < mineCount && positions.length > 0; i++) {
            const randomIndex = Math.floor(Math.random() * positions.length);
            const pos = positions.splice(randomIndex, 1)[0];
            mines[pos.y][pos.x] = true;
            grid[pos.y][pos.x] = 'mine';
        }

        // Calculate adjacent mine counts
        for (let y = 0; y < MinefieldState.height; y++) {
            for (let x = 0; x < MinefieldState.width; x++) {
                if (!mines[y][x]) {
                    adjacentCounts[y][x] = countAdjacentMines(x, y);
                }
            }
        }
    }

    function countAdjacentMines(x, y) {
        let count = 0;
        for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
                if (dx === 0 && dy === 0) continue;
                const nx = x + dx;
                const ny = y + dy;
                if (nx >= 0 && nx < MinefieldState.width && ny >= 0 && ny < MinefieldState.height) {
                    if (mines[ny][nx]) count++;
                }
            }
        }
        return count;
    }

    function revealCell(x, y) {
        if (GameState.gameStatus !== 'playing') return 'invalid';
        if (x < 0 || x >= MinefieldState.width || y < 0 || y >= MinefieldState.height) return 'invalid';
        if (revealed[y][x] || flagged[y][x]) return 'invalid';

        // Handle first click - place mines after first reveal
        if (firstClick) {
            placeMines(x, y, MinefieldState.mineCount);
            firstClick = false;
        }

        revealed[y][x] = true;
        MinefieldState.revealedCells++;

        // Emit cell revealed event
        EventBus.emit('CELL_REVEALED', {x, y, result: mines[y][x] ? 'mine' : adjacentCounts[y][x].toString()});

        if (mines[y][x]) {
            // Hit a mine - game over
            EventBus.emit('GAME_LOST', {time: GameState.gameTime});
            return 'mine';
        }

        // If cell has no adjacent mines, reveal adjacent cells
        if (adjacentCounts[y][x] === 0) {
            const queue = [{x, y}];
            const visited = new Set();
            visited.add(`${x},${y}`);

            while (queue.length > 0) {
                const current = queue.shift();
                
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        if (dx === 0 && dy === 0) continue;
                        const nx = current.x + dx;
                        const ny = current.y + dy;
                        const key = `${nx},${ny}`;
                        
                        if (nx >= 0 && nx < MinefieldState.width && 
                            ny >= 0 && ny < MinefieldState.height &&
                            !revealed[ny][nx] && !flagged[ny][nx] && 
                            !visited.has(key)) {
                            
                            revealed[ny][nx] = true;
                            MinefieldState.revealedCells++;
                            visited.add(key);
                            
                            EventBus.emit('CELL_REVEALED', {x: nx, y: ny, result: adjacentCounts[ny][nx].toString()});
                            
                            if (adjacentCounts[ny][nx] === 0) {
                                queue.push({x: nx, y: ny});
                            }
                        }
                    }
                }
            }
        }

        // Check win condition
        if (checkWinCondition()) {
            EventBus.emit('GAME_WON', {time: GameState.gameTime});
        }

        return adjacentCounts[y][x].toString();
    }

    function flagCell(x, y) {
        if (GameState.gameStatus !== 'playing') return;
        if (x < 0 || x >= MinefieldState.width || y < 0 || y >= MinefieldState.height) return;
        if (revealed[y][x]) return;

        flagged[y][x] = !flagged[y][x];
        GameState.flagsRemaining += flagged[y][x] ? -1 : 1;

        EventBus.emit('CELL_FLAGGED', {x, y, flagged: flagged[y][x]});
    }

    function getCellState(x, y) {
        if (x < 0 || x >= MinefieldState.width || y < 0 || y >= MinefieldState.height) {
            return 'invalid';
        }

        if (flagged[y][x]) return 'flagged';
        if (!revealed[y][x]) return 'hidden';
        if (mines[y][x]) return 'mine';
        return adjacentCounts[y][x].toString();
    }

    function checkWinCondition() {
        if (GameState.gameStatus !== 'playing') return false;
        
        const totalCells = MinefieldState.width * MinefieldState.height;
        const nonMineCells = totalCells - MinefieldState.mineCount;
        
        return MinefieldState.revealedCells === nonMineCells;
    }

    return {
        init,
        generateField,
        revealCell,
        flagCell,
        getCellState,
        checkWinCondition
    };
})();

const ui_manager = (function() {
    let canvas;
    let ctx;
    let cellGrid = [];
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        if (canvas) {
            ctx = canvas.getContext('2d');
            canvas.width = CANVAS_WIDTH;
            canvas.height = CANVAS_HEIGHT;
        }
        
        // Initialize cell grid for tracking visual states
        cellGrid = [];
        
        // Listen for cell events to update visual state
        EventBus.on('CELL_REVEALED', function(data) {
            const { x, y, result } = data;
            if (!cellGrid[y]) cellGrid[y] = [];
            cellGrid[y][x] = { revealed: true, result: result };
        });
        
        EventBus.on('CELL_FLAGGED', function(data) {
            const { x, y, flagged } = data;
            if (!cellGrid[y]) cellGrid[y] = [];
            if (!cellGrid[y][x]) cellGrid[y][x] = {};
            cellGrid[y][x].flagged = flagged;
        });
    }
    
    function render() {
        updateUI();
        if (!canvas || !ctx) return;
        
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        if (GameState.gameStatus === 'playing') {
            renderGame();
        }
    }
    
    function updateUI() {
        // Update timer display
        const timerEl = document.getElementById('timer');
        if (timerEl) {
            timerEl.textContent = `⏱ ${Math.floor(GameState.gameTime).toString().padStart(3, '0')}`;
        }
        
        // Update mine count
        const mineCountEl = document.getElementById('mine_count');
        if (mineCountEl) {
            mineCountEl.textContent = `💣 ${GameState.flagsRemaining}`;
        }
        
        // Update flag count
        const flagCountEl = document.getElementById('flag_count');
        if (flagCountEl) {
            const totalFlags = MinefieldState.mineCount - GameState.flagsRemaining;
            flagCountEl.textContent = `🚩 ${totalFlags}`;
        }
        
        // Update game over screen
        if (GameState.gameStatus === 'game_over') {
            const gameoverText = document.getElementById('gameover_text');
            const finalScore = document.getElementById('final_score');
            if (gameoverText) {
                gameoverText.textContent = GameState.gameWon ? '你赢了!' : '游戏结束';
            }
            if (finalScore) {
                finalScore.textContent = `最终时间: ${Math.floor(GameState.gameTime)}秒`;
            }
        }
    }
    
    function renderMenu() {
        // Menu is handled by HTML/CSS
    }
    
    function renderGame() {
        if (!canvas || !ctx) return;
        
        // Calculate minefield position (centered)
        const fieldWidth = MinefieldState.width * CELL_SIZE;
        const fieldHeight = MinefieldState.height * CELL_SIZE;
        const startX = (CANVAS_WIDTH - fieldWidth) / 2;
        const startY = 50;
        
        // Render minefield
        for (let y = 0; y < MinefieldState.height; y++) {
            for (let x = 0; x < MinefieldState.width; x++) {
                const cellX = startX + x * CELL_SIZE;
                const cellY = startY + y * CELL_SIZE;
                
                const cellState = cellGrid[y] && cellGrid[y][x] ? cellGrid[y][x] : {};
                
                // Cell background
                if (cellState.revealed) {
                    if (cellState.result === 'mine') {
                        ctx.fillStyle = '#FF0000';
                    } else {
                        ctx.fillStyle = '#FFFFFF';
                    }
                } else {
                    ctx.fillStyle = '#CCCCCC';
                }
                
                ctx.fillRect(cellX, cellY, CELL_SIZE - 1, CELL_SIZE - 1);
                
                // Cell border
                ctx.strokeStyle = '#999';
                ctx.lineWidth = 1;
                ctx.strokeRect(cellX, cellY, CELL_SIZE - 1, CELL_SIZE - 1);
                
                // Cell content
                ctx.fillStyle = '#333';
                ctx.font = '16px Arial';
                ctx.textAlign = 'center';
                
                if (cellState.flagged && !cellState.revealed) {
                    ctx.fillStyle = '#FF0000';
                    ctx.fillText('🚩', cellX + CELL_SIZE / 2, cellY + CELL_SIZE / 2 + 5);
                } else if (cellState.revealed) {
                    if (cellState.result === 'mine') {
                        ctx.fillStyle = '#000';
                        ctx.fillText('💣', cellX + CELL_SIZE / 2, cellY + CELL_SIZE / 2 + 5);
                    } else if (cellState.result !== 'safe' && cellState.result !== '0') {
                        const num = parseInt(cellState.result);
                        if (num > 0) {
                            const colors = ['', '#0000FF', '#008000', '#FF0000', '#800080', '#800000', '#008080', '#000000', '#808080'];
                            ctx.fillStyle = colors[num] || '#000';
                            ctx.fillText(cellState.result, cellX + CELL_SIZE / 2, cellY + CELL_SIZE / 2 + 5);
                        }
                    }
                }
            }
        }
    }
    
    function renderGameOver() {
        // Game over is handled by HTML/CSS
    }
    
    function renderLeaderboard() {
        // Leaderboard is handled by HTML/CSS
    }
    
    return {
        init,
        renderMenu,
        renderGame,
        renderGameOver,
        renderLeaderboard,
        render
    };
})();

const input_handler = (function() {
    let canvas;
    let inputQueue = [];
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        
        // Add canvas event listeners
        if (canvas) {
            canvas.addEventListener('click', onCanvasClick);
            canvas.addEventListener('contextmenu', onContextMenu);
        }
        
        // Add button event listeners
        setupButtonListeners();
    }
    
    function setupButtonListeners() {
        // Main menu buttons
        const btnPlay = document.getElementById('btn_play');
        const btnLeaderboard = document.getElementById('btn_leaderboard');
        
        if (btnPlay) {
            btnPlay.addEventListener('click', () => handleMenuClick('beginner'));
        }
        if (btnLeaderboard) {
            btnLeaderboard.addEventListener('click', () => handleMenuClick('leaderboard'));
        }
        
        // Game over buttons
        const btnRetry = document.getElementById('btn_retry');
        const btnMenu = document.getElementById('btn_menu');
        const btnLeaderboardGameover = document.getElementById('btn_leaderboard_gameover');
        
        if (btnRetry) {
            btnRetry.addEventListener('click', () => handleMenuClick('retry'));
        }
        if (btnMenu) {
            btnMenu.addEventListener('click', () => handleMenuClick('menu'));
        }
        if (btnLeaderboardGameover) {
            btnLeaderboardGameover.addEventListener('click', () => handleMenuClick('leaderboard'));
        }
        
        // Leaderboard buttons
        const btnClose = document.getElementById('btn_close');
        if (btnClose) {
            btnClose.addEventListener('click', () => handleMenuClick('close'));
        }
    }
    
    function onCanvasClick(event) {
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        const button = event.button; // 0 = left, 2 = right
        
        inputQueue.push({ type: 'click', x, y, button });
    }
    
    function onContextMenu(event) {
        event.preventDefault(); // Prevent right-click context menu
    }
    
    function processInput() {
        while (inputQueue.length > 0) {
            const input = inputQueue.shift();
            
            if (input.type === 'click') {
                handleClick(input.x, input.y, input.button);
            }
        }
    }
    
    function handleClick(x, y, button) {
        if (GameState.gameStatus === 'playing') {
            // Convert screen coordinates to grid coordinates
            const fieldWidth = MinefieldState.width * CELL_SIZE;
            const startX = (CANVAS_WIDTH - fieldWidth) / 2;
            const startY = 50;
            
            const gridX = Math.floor((x - startX) / CELL_SIZE);
            const gridY = Math.floor((y - startY) / CELL_SIZE);
            
            // Check if click is within minefield bounds
            if (gridX >= 0 && gridX < MinefieldState.width && gridY >= 0 && gridY < MinefieldState.height) {
                if (button === 0) { // Left click - reveal cell
                    minefield.revealCell(gridX, gridY);
                } else if (button === 2) { // Right click - flag cell
                    minefield.flagCell(gridX, gridY);
                }
            }
        }
    }
    
    function handleMenuClick(buttonId) {
        if (!buttonId) return;
        
        if (GameState.gameStatus === 'menu') {
            if (buttonId === 'beginner' || buttonId === 'intermediate' || buttonId === 'expert') {
                EventBus.emit('GAME_START', { difficulty: buttonId });
            } else if (buttonId === 'leaderboard') {
                EventBus.emit('SHOW_LEADERBOARD', {});
            }
        } else if (GameState.gameStatus === 'game_over') {
            if (buttonId === 'retry') {
                EventBus.emit('RETRY', {});
            } else if (buttonId === 'menu') {
                EventBus.emit('RETURN_MENU', {});
            } else if (buttonId === 'leaderboard') {
                EventBus.emit('SHOW_LEADERBOARD', {});
            }
        } else if (GameState.gameStatus === 'leaderboard') {
            if (buttonId === 'close') {
                EventBus.emit('CLOSE_LEADERBOARD', {});
            }
        }
    }
    
    return {
        init,
        handleClick,
        handleMenuClick,
        processInput
    };
})();

// Screen management
function showScreen(screenId) {
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.style.display = 'none';
    });
    
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.style.display = 'block';
    }
}

// State transition functions
function startGame() {
    showScreen('gameplay');
    // Generate field based on difficulty
    let width, height, mines;
    switch (GameState.difficulty) {
        case 'beginner':
            width = BEGINNER_WIDTH;
            height = BEGINNER_HEIGHT;
            mines = BEGINNER_MINES;
            break;
        case 'intermediate':
            width = INTERMEDIATE_WIDTH;
            height = INTERMEDIATE_HEIGHT;
            mines = INTERMEDIATE_MINES;
            break;
        case 'expert':
            width = EXPERT_WIDTH;
            height = EXPERT_HEIGHT;
            mines = EXPERT_MINES;
            break;
        default:
            width = BEGINNER_WIDTH;
            height = BEGINNER_HEIGHT;
            mines = BEGINNER_MINES;
    }
    minefield.generateField(width, height, mines);
}

function gameOver() {
    showScreen('game_over');
}

function retry() {
    showScreen('gameplay');
    // Generate field again
    let width, height, mines;
    switch (GameState.difficulty) {
        case 'beginner':
            width = BEGINNER_WIDTH;
            height = BEGINNER_HEIGHT;
            mines = BEGINNER_MINES;
            break;
        case 'intermediate':
            width = INTERMEDIATE_WIDTH;
            height = INTERMEDIATE_HEIGHT;
            mines = INTERMEDIATE_MINES;
            break;
        case 'expert':
            width = EXPERT_WIDTH;
            height = EXPERT_HEIGHT;
            mines = EXPERT_MINES;
            break;
        default:
            width = BEGINNER_WIDTH;
            height = BEGINNER_HEIGHT;
            mines = BEGINNER_MINES;
    }
    minefield.generateField(width, height, mines);
}

function returnToMenu() {
    showScreen('main_menu');
}

function showLeaderboard() {
    showScreen('leaderboard');
}

function closeLeaderboard() {
    showScreen('main_menu');
}

// Event listeners for state changes
EventBus.on('GAME_START', startGame);
EventBus.on('GAME_WON', gameOver);
EventBus.on('GAME_LOST', gameOver);
EventBus.on('RETRY', retry);
EventBus.on('RETURN_MENU', returnToMenu);
EventBus.on('SHOW_LEADERBOARD', showLeaderboard);
EventBus.on('CLOSE_LEADERBOARD', closeLeaderboard);

// Game loop
let lastTime = 0;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions in order
    input_handler.processInput();
    game_state.updateTimer();
    
    // Render functions in order
    ui_manager.render();
    
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    } else {
        // Continue loop for other states too
        requestAnimationFrame(gameLoop);
    }
}

// Initialize game
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules in order
    game_state.init();
    minefield.init();
    ui_manager.init();
    input_handler.init();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
});