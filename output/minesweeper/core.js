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

// Module code (concatenated exactly as provided)
const GameState_module = (function() {
    let timerInterval = null;
    let lastUpdateTime = Date.now();

    function init() {
        GameState.gameStatus = 'menu';
        GameState.gameTime = 0;
        GameState.difficulty = 'beginner';
        GameState.gameWon = false;
        GameState.flagsRemaining = 10;

        // Set up event listeners for game state transitions
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
        if (GameState.gameStatus !== 'menu' && GameState.gameStatus !== 'game_over' && GameState.gameStatus !== 'leaderboard') return;

        GameState.difficulty = difficulty;
        GameState.gameStatus = 'playing';
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
                GameState.flagsRemaining = BEGINNER_MINES;
        }

        // Start timer
        lastUpdateTime = Date.now();
        if (timerInterval) {
            clearInterval(timerInterval);
        }
        timerInterval = setInterval(() => {
            if (GameState.gameStatus === 'playing') {
                GameState.gameTime++;
                updateUI();
            }
        }, 1000);
    }

    function endGame(won) {
        if (GameState.gameStatus !== 'playing') return;

        GameState.gameStatus = 'game_over';
        GameState.gameWon = won;

        // Stop timer
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }

        // Save high score if won
        if (won) {
            saveHighScore(GameState.gameTime, GameState.difficulty);
        }
    }

    function updateTimer() {
        if (GameState.gameStatus !== 'playing') return;
        
        const currentTime = Date.now();
        const deltaTime = currentTime - lastUpdateTime;
        
        // Update timer more frequently for smoother display
        if (deltaTime >= 100) { // Update every 100ms for smoother UI
            lastUpdateTime = currentTime;
        }
    }

    function setState(newState) {
        GameState.gameStatus = newState;
    }

    // Event handlers
    function handleGameStart(event) {
        const difficulty = event.difficulty;
        startGame(difficulty);
        showScreen('gameplay');
        // Generate minefield after showing screen
        setTimeout(() => {
            minefield.generateField(
                difficulty === 'beginner' ? BEGINNER_WIDTH : 
                difficulty === 'intermediate' ? INTERMEDIATE_WIDTH : EXPERT_WIDTH,
                difficulty === 'beginner' ? BEGINNER_HEIGHT : 
                difficulty === 'intermediate' ? INTERMEDIATE_HEIGHT : EXPERT_HEIGHT,
                difficulty === 'beginner' ? BEGINNER_MINES : 
                difficulty === 'intermediate' ? INTERMEDIATE_MINES : EXPERT_MINES
            );
        }, 100);
    }

    function handleGameWon(event) {
        endGame(true);
        showScreen('game_over');
        updateGameOverScreen();
    }

    function handleGameLost(event) {
        endGame(false);
        showScreen('game_over');
        updateGameOverScreen();
    }

    function handleRetry(event) {
        if (GameState.gameStatus === 'game_over') {
            startGame(GameState.difficulty);
            showScreen('gameplay');
            setTimeout(() => {
                minefield.generateField(
                    GameState.difficulty === 'beginner' ? BEGINNER_WIDTH : 
                    GameState.difficulty === 'intermediate' ? INTERMEDIATE_WIDTH : EXPERT_WIDTH,
                    GameState.difficulty === 'beginner' ? BEGINNER_HEIGHT : 
                    GameState.difficulty === 'intermediate' ? INTERMEDIATE_HEIGHT : EXPERT_HEIGHT,
                    GameState.difficulty === 'beginner' ? BEGINNER_MINES : 
                    GameState.difficulty === 'intermediate' ? INTERMEDIATE_MINES : EXPERT_MINES
                );
            }, 100);
        }
    }

    function handleReturnMenu(event) {
        if (GameState.gameStatus === 'game_over') {
            setState('menu');
            showScreen('main_menu');
        }
    }

    function handleShowLeaderboard(event) {
        if (GameState.gameStatus === 'game_over' || GameState.gameStatus === 'menu') {
            setState('leaderboard');
            showScreen('leaderboard');
            updateLeaderboard();
        }
    }

    function handleCloseLeaderboard(event) {
        if (GameState.gameStatus === 'leaderboard') {
            setState('menu');
            showScreen('main_menu');
        }
    }

    function handlePlayAgain(event) {
        if (GameState.gameStatus === 'leaderboard') {
            const difficulty = event.difficulty;
            startGame(difficulty);
            showScreen('gameplay');
            setTimeout(() => {
                minefield.generateField(
                    difficulty === 'beginner' ? BEGINNER_WIDTH : 
                    difficulty === 'intermediate' ? INTERMEDIATE_WIDTH : EXPERT_WIDTH,
                    difficulty === 'beginner' ? BEGINNER_HEIGHT : 
                    difficulty === 'intermediate' ? INTERMEDIATE_HEIGHT : EXPERT_HEIGHT,
                    difficulty === 'beginner' ? BEGINNER_MINES : 
                    difficulty === 'intermediate' ? INTERMEDIATE_MINES : EXPERT_MINES
                );
            }, 100);
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
    let revealed = [];
    let flagged = [];
    let firstClick = true;

    function init() {
        // Initialize empty arrays
        grid = [];
        mines = [];
        revealed = [];
        flagged = [];
        firstClick = true;
    }

    function generateField(width, height, mineCount) {
        if (GameState.gameStatus !== 'playing') return;

        // Update MinefieldState
        MinefieldState.width = width;
        MinefieldState.height = height;
        MinefieldState.mineCount = mineCount;
        MinefieldState.revealedCells = 0;
        GameState.flagsRemaining = mineCount;

        // Initialize grid arrays
        grid = [];
        mines = [];
        revealed = [];
        flagged = [];

        for (let y = 0; y < height; y++) {
            grid[y] = [];
            mines[y] = [];
            revealed[y] = [];
            flagged[y] = [];
            for (let x = 0; x < width; x++) {
                grid[y][x] = 0; // adjacency count
                mines[y][x] = false;
                revealed[y][x] = false;
                flagged[y][x] = false;
            }
        }

        firstClick = true;
        updateUI();
    }

    function placeMines(width, height, mineCount, firstX, firstY) {
        let placedMines = 0;
        
        while (placedMines < mineCount) {
            const x = Math.floor(Math.random() * width);
            const y = Math.floor(Math.random() * height);
            
            // Don't place mine on first click or if already has mine
            if ((x === firstX && y === firstY) || mines[y][x]) {
                continue;
            }
            
            mines[y][x] = true;
            placedMines++;
        }

        // Calculate adjacency numbers
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                if (!mines[y][x]) {
                    grid[y][x] = countAdjacentMines(x, y);
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
                if (nx >= 0 && nx < MinefieldState.width && 
                    ny >= 0 && ny < MinefieldState.height && 
                    mines[ny][nx]) {
                    count++;
                }
            }
        }
        return count;
    }

    function revealCell(x, y) {
        if (GameState.gameStatus !== 'playing') return '';
        if (x < 0 || x >= MinefieldState.width || y < 0 || y >= MinefieldState.height) return '';
        if (revealed[y][x] || flagged[y][x]) return '';

        // Handle first click - place mines after first reveal
        if (firstClick) {
            placeMines(MinefieldState.width, MinefieldState.height, MinefieldState.mineCount, x, y);
            firstClick = false;
        }

        revealed[y][x] = true;
        MinefieldState.revealedCells++;

        if (mines[y][x]) {
            // Hit a mine - game over
            EventBus.emit('GAME_LOST', { time: GameState.gameTime });
            EventBus.emit('CELL_REVEALED', { x: x, y: y, result: 'mine' });
            return 'mine';
        }

        const adjacentMines = grid[y][x];
        let result;

        if (adjacentMines === 0) {
            // Empty cell - reveal adjacent cells using BFS
            result = 'safe';
            const queue = [[x, y]];
            const processed = new Set();
            processed.add(`${x},${y}`);

            while (queue.length > 0) {
                const [cx, cy] = queue.shift();
                
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        if (dx === 0 && dy === 0) continue;
                        const nx = cx + dx;
                        const ny = cy + dy;
                        const key = `${nx},${ny}`;
                        
                        if (nx >= 0 && nx < MinefieldState.width && 
                            ny >= 0 && ny < MinefieldState.height && 
                            !revealed[ny][nx] && !flagged[ny][nx] && 
                            !processed.has(key)) {
                            
                            revealed[ny][nx] = true;
                            MinefieldState.revealedCells++;
                            processed.add(key);
                            
                            EventBus.emit('CELL_REVEALED', {
                                x: nx, y: ny, result: grid[ny][nx] === 0 ? 'safe' : grid[ny][nx].toString()
                            });
                            
                            // If this cell is also empty, add to queue for further expansion
                            if (grid[ny][nx] === 0) {
                                queue.push([nx, ny]);
                            }
                        }
                    }
                }
            }
        } else {
            // Cell with number
            result = adjacentMines.toString();
        }

        EventBus.emit('CELL_REVEALED', { x: x, y: y, result: result });

        // Check win condition
        if (checkWinCondition()) {
            EventBus.emit('GAME_WON', { time: GameState.gameTime });
        }

        return result;
    }

    function flagCell(x, y) {
        if (GameState.gameStatus !== 'playing') return;
        if (x < 0 || x >= MinefieldState.width || y < 0 || y >= MinefieldState.height) return;
        if (revealed[y][x]) return;

        const wasFlagged = flagged[y][x];
        flagged[y][x] = !flagged[y][x];
        
        if (flagged[y][x]) {
            GameState.flagsRemaining--;
        } else {
            GameState.flagsRemaining++;
        }

        EventBus.emit('CELL_FLAGGED', { x: x, y: y, flagged: flagged[y][x] });
        updateUI();
    }

    function getCellState(x, y) {
        if (x < 0 || x >= MinefieldState.width || y < 0 || y >= MinefieldState.height) {
            return 'invalid';
        }
        
        if (flagged[y][x]) {
            return 'flagged';
        }
        
        if (!revealed[y][x]) {
            return 'hidden';
        }
        
        if (mines[y][x]) {
            return 'mine';
        }
        
        const adjacentMines = grid[y][x];
        if (adjacentMines === 0) {
            return 'empty';
        }
        
        return adjacentMines.toString();
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
        if (!canvas) return;
        
        ctx = canvas.getContext('2d');
        
        // Set canvas size based on screen size
        const maxSize = Math.min(window.innerWidth * 0.9, window.innerHeight * 0.5);
        canvas.width = maxSize;
        canvas.height = maxSize;
        canvas.style.width = maxSize + 'px';
        canvas.style.height = maxSize + 'px';
        
        // Initialize cell grid for tracking visual state
        cellGrid = [];
        
        // Listen for cell events to update visual state
        EventBus.on('CELL_REVEALED', function(event) {
            const { x, y, result } = event;
            if (!cellGrid[y]) cellGrid[y] = [];
            cellGrid[y][x] = { revealed: true, result: result };
        });
        
        EventBus.on('CELL_FLAGGED', function(event) {
            const { x, y, flagged } = event;
            if (!cellGrid[y]) cellGrid[y] = [];
            if (!cellGrid[y][x]) cellGrid[y][x] = {};
            cellGrid[y][x].flagged = flagged;
        });
    }
    
    function renderGame() {
        if (GameState.gameStatus !== 'playing' || !canvas || !ctx) return;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Calculate cell size based on canvas and grid dimensions
        const cellSize = Math.min(
            canvas.width / MinefieldState.width,
            canvas.height / MinefieldState.height
        );
        
        const fieldWidth = MinefieldState.width * cellSize;
        const fieldHeight = MinefieldState.height * cellSize;
        const startX = (canvas.width - fieldWidth) / 2;
        const startY = (canvas.height - fieldHeight) / 2;
        
        for (let row = 0; row < MinefieldState.height; row++) {
            for (let col = 0; col < MinefieldState.width; col++) {
                const x = startX + col * cellSize;
                const y = startY + row * cellSize;
                
                const cellState = (cellGrid[row] && cellGrid[row][col]) || {};
                
                if (cellState.revealed) {
                    // Revealed cell
                    ctx.fillStyle = '#fff';
                    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
                    
                    if (cellState.result === 'mine') {
                        // Mine
                        ctx.fillStyle = '#f44336';
                        ctx.fillRect(x + 2, y + 2, cellSize - 4, cellSize - 4);
                        ctx.fillStyle = '#000';
                        ctx.font = Math.floor(cellSize * 0.6) + 'px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText('💣', x + cellSize / 2, y + cellSize / 2 + cellSize * 0.2);
                    } else if (cellState.result !== 'safe' && cellState.result !== '0') {
                        // Number
                        const num = parseInt(cellState.result);
                        const colors = ['', '#1976D2', '#388E3C', '#D32F2F', '#7B1FA2', '#F57C00', '#C2185B', '#000', '#424242'];
                        ctx.fillStyle = colors[num] || '#000';
                        ctx.font = 'bold ' + Math.floor(cellSize * 0.6) + 'px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(cellState.result, x + cellSize / 2, y + cellSize / 2 + cellSize * 0.2);
                    }
                } else {
                    // Unrevealed cell
                    ctx.fillStyle = '#bbb';
                    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
                    
                    // Highlight effect
                    ctx.fillStyle = '#ddd';
                    ctx.fillRect(x + 1, y + 1, cellSize - 3, 2);
                    ctx.fillRect(x + 1, y + 1, 2, cellSize - 3);
                    
                    if (cellState.flagged) {
                        // Flag
                        ctx.fillStyle = '#f44336';
                        ctx.font = 'bold ' + Math.floor(cellSize * 0.6) + 'px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText('🚩', x + cellSize / 2, y + cellSize / 2 + cellSize * 0.2);
                    }
                }
                
                // Cell border
                ctx.strokeStyle = '#999';
                ctx.lineWidth = 1;
                ctx.strokeRect(x, y, cellSize - 1, cellSize - 1);
            }
        }
    }
    
    function render() {
        if (GameState.gameStatus === 'playing') {
            renderGame();
        }
    }
    
    return {
        init,
        render
    };
})();

const input_handler = (function() {
    let canvas;
    let inputQueue = [];
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        
        // Set up canvas event listeners
        if (canvas) {
            canvas.addEventListener('click', onCanvasClick);
            canvas.addEventListener('contextmenu', onContextMenu);
            canvas.addEventListener('touchstart', onTouchStart);
            canvas.addEventListener('touchend', onTouchEnd);
        }
        
        // Set up button click listeners
        document.addEventListener('click', onDocumentClick);
        
        // Set up keyboard listeners
        document.addEventListener('keydown', onKeyDown);
    }
    
    let touchStartTime = 0;
    let touchStartPos = { x: 0, y: 0 };
    
    function onTouchStart(event) {
        event.preventDefault();
        touchStartTime = Date.now();
        const touch = event.touches[0];
        const rect = canvas.getBoundingClientRect();
        touchStartPos.x = touch.clientX - rect.left;
        touchStartPos.y = touch.clientY - rect.top;
    }
    
    function onTouchEnd(event) {
        event.preventDefault();
        const touchDuration = Date.now() - touchStartTime;
        const isLongPress = touchDuration > 500;
        
        inputQueue.push({ 
            type: 'click', 
            x: touchStartPos.x, 
            y: touchStartPos.y, 
            button: isLongPress ? 2 : 0 
        });
    }
    
    function onCanvasClick(event) {
        event.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        const button = event.button;
        
        inputQueue.push({ type: 'click', x, y, button });
    }
    
    function onContextMenu(event) {
        event.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        inputQueue.push({ type: 'click', x, y, button: 2 });
    }
    
    function onKeyDown(event) {
        if (GameState.gameStatus === 'menu' || GameState.gameStatus === 'game_over' || GameState.gameStatus === 'leaderboard') {
            switch(event.key) {
                case 'Enter':
                    inputQueue.push({ type: 'menu', buttonId: 'confirm' });
                    break;
                case 'Escape':
                    inputQueue.push({ type: 'menu', buttonId: 'back' });
                    break;
            }
        }
    }
    
    function onDocumentClick(event) {
        if (event.target.classList.contains('menu-button')) {
            const buttonId = event.target.id || event.target.dataset.action;
            inputQueue.push({ type: 'menu', buttonId });
        }
    }
    
    function processInput() {
        while (inputQueue.length > 0) {
            const input = inputQueue.shift();
            
            if (input.type === 'click') {
                handleClick(input.x, input.y, input.button);
            } else if (input.type === 'menu') {
                handleMenuClick(input.buttonId);
            }
        }
    }
    
    function handleClick(x, y, button) {
        if (GameState.gameStatus === 'playing' && canvas) {
            // Calculate cell size and grid position
            const cellSize = Math.min(
                canvas.width / MinefieldState.width,
                canvas.height / MinefieldState.height
            );
            
            const fieldWidth = MinefieldState.width * cellSize;
            const fieldHeight = MinefieldState.height * cellSize;
            const startX = (canvas.width - fieldWidth) / 2;
            const startY = (canvas.height - fieldHeight) / 2;
            
            if (x >= startX && y >= startY && 
                x < startX + fieldWidth && y < startY + fieldHeight) {
                
                const gridX = Math.floor((x - startX) / cellSize);
                const gridY = Math.floor((y - startY) / cellSize);
                
                if (gridX >= 0 && gridX < MinefieldState.width && 
                    gridY >= 0 && gridY < MinefieldState.height) {
                    
                    if (button === 0) { // Left click - reveal cell
                        minefield.revealCell(gridX, gridY);
                    } else if (button === 2) { // Right click - flag cell
                        minefield.flagCell(gridX, gridY);
                    }
                }
            }
        }
    }
    
    function handleMenuClick(buttonId) {
        switch(buttonId) {
            case 'beginner':
                EventBus.emit('GAME_START', { difficulty: 'beginner' });
                break;
            case 'intermediate':
                EventBus.emit('GAME_START', { difficulty: 'intermediate' });
                break;
            case 'expert':
                EventBus.emit('GAME_START', { difficulty: 'expert' });
                break;
            case 'leaderboard':
                EventBus.emit('SHOW_LEADERBOARD', {});
                break;
            case 'retry':
                EventBus.emit('RETRY', {});
                break;
            case 'menu':
                EventBus.emit('RETURN_MENU', {});
                break;
            case 'close':
                EventBus.emit('CLOSE_LEADERBOARD', {});
                break;
        }
    }
    
    return {
        init,
        handleClick,
        handleMenuClick,
        processInput
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
        targetScreen.style.display = 'flex';
    }
}

// Game loop
let lastTime = 0;
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions in order
    input_handler.processInput();
    GameState_module.updateTimer();
    
    // Render functions in order
    ui_manager.render();
    
    requestAnimationFrame(gameLoop);
}

// High score management
function saveHighScore(time, difficulty) {
    const leaderboard = getLeaderboardData();
    const entry = {
        time: time,
        date: new Date().toLocaleDateString()
    };
    
    if (!leaderboard[difficulty]) {
        leaderboard[difficulty] = [];
    }
    
    leaderboard[difficulty].push(entry);
    leaderboard[difficulty].sort((a, b) => a.time - b.time);
    leaderboard[difficulty] = leaderboard[difficulty].slice(0, 10); // Keep top 10
    
    localStorage.setItem('minesweeper_leaderboard', JSON.stringify(leaderboard));
}

function getLeaderboardData() {
    const stored = localStorage.getItem('minesweeper_leaderboard');
    if (!stored) {
        return { beginner: [], intermediate: [], expert: [] };
    }
    return JSON.parse(stored);
}

function updateLeaderboard() {
    const leaderboard = getLeaderboardData();
    const scoreList = document.getElementById('score_list');
    if (scoreList) {
        const entries = leaderboard[GameState.difficulty] || [];
        let html = '';
        
        for (let i = 0; i < 5; i++) {
            if (i < entries.length) {
                const entry = entries[i];
                html += `<div class="score-entry">${i + 1}. ${entry.time}秒 - ${entry.date}</div>`;
            } else {
                html += `<div class="score-entry">${i + 1}. 暂无记录</div>`;
            }
        }
        
        scoreList.innerHTML = html;
    }
}

function updateUI() {
    // Update mine count
    const mineCountEl = document.getElementById('mine_count');
    if (mineCountEl) {
        mineCountEl.textContent = `💣 ${GameState.flagsRemaining}`;
    }
    
    // Update timer
    const timerEl = document.getElementById('timer');
    if (timerEl) {
        timerEl.textContent = `⏱ ${String(GameState.gameTime).padStart(3, '0')}`;
    }
    
    // Update flag count
    const flagCountEl = document.getElementById('flag_count');
    if (flagCountEl) {
        const flagsUsed = MinefieldState.mineCount - GameState.flagsRemaining;
        flagCountEl.textContent = `🚩 ${flagsUsed}`;
    }
}

function updateGameOverScreen() {
    const gameoverText = document.getElementById('gameover_text');
    const finalScore = document.getElementById('final_score');
    
    if (gameoverText) {
        gameoverText.textContent = GameState.gameWon ? '恭喜获胜!' : '游戏失败';
    }
    
    if (finalScore) {
        finalScore.textContent = `用时: ${GameState.gameTime}秒`;
    }
}

// State transition functions
function startGame() {
    GameState.gameStatus = 'playing';
    EventBus.emit('GAME_START', { difficulty: 'beginner' });
    showScreen('gameplay');
}

function gameOver() {
    GameState.gameStatus = 'game_over';
    showScreen('game_over');
}

function retry() {
    EventBus.emit('RETRY', {});
}

function returnToMenu() {
    GameState.gameStatus = 'menu';
    EventBus.emit('RETURN_MENU', {});
    showScreen('main_menu');
}

// Initialize modules in order
function initGame() {
    GameState_module.init();
    minefield.init();
    ui_manager.init();
    input_handler.init();
    
    // Show initial screen
    showScreen('main_menu');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

// Start the game when page loads
window.addEventListener('load', initGame);