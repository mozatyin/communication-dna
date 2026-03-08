core.js
// Game state
let gameState = 'menu'; // menu, playing, game_over
let score = 0;
let timer = 0;
let gameStartTime = 0;
let timerInterval = null;

// Minesweeper grid
const GRID_SIZE = 10;
const MINE_COUNT = 10;
let grid = [];
let revealedCells = 0;
let flaggedCells = 0;
let gameWon = false;

// Canvas and rendering
let canvas;
let ctx;
let cellSize;
let gridOffsetX;
let gridOffsetY;

// Touch/click handling
let isRightClick = false;
let touchStartTime = 0;

// Initialize game
function init() {
    canvas = document.getElementById('game_canvas');
    ctx = canvas.getContext('2d');
    
    // Set canvas size
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    // Calculate cell size and grid offset
    cellSize = Math.min(canvas.width, canvas.height) / GRID_SIZE;
    gridOffsetX = (canvas.width - cellSize * GRID_SIZE) / 2;
    gridOffsetY = (canvas.height - cellSize * GRID_SIZE) / 2;
    
    // Add event listeners
    canvas.addEventListener('click', handleClick);
    canvas.addEventListener('contextmenu', handleRightClick);
    canvas.addEventListener('touchstart', handleTouchStart);
    canvas.addEventListener('touchend', handleTouchEnd);
    
    // Initialize leaderboard
    initLeaderboard();
}

// Screen management
function showScreen(screenId) {
    // Hide all screens
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => screen.style.display = 'none');
    
    // Show target screen
    document.getElementById(screenId).style.display = 'block';
    
    if (screenId === 'gameplay') {
        startGame();
    }
    
    gameState = screenId === 'gameplay' ? 'playing' : 'menu';
}

function hideLeaderboard() {
    document.getElementById('leaderboard').style.display = 'none';
    document.getElementById('main_menu').style.display = 'block';
}

// Game initialization
function startGame() {
    gameState = 'playing';
    score = 0;
    timer = 0;
    revealedCells = 0;
    flaggedCells = 0;
    gameWon = false;
    gameStartTime = Date.now();
    
    // Initialize grid
    initGrid();
    placeMines();
    calculateNumbers();
    
    // Update UI
    updateScore();
    updateMineCount();
    updateFlagCount();
    
    // Start timer
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(updateTimer, 1000);
    
    // Start render loop
    render();
}

function restartGame() {
    showScreen('gameplay');
}

// Grid management
function initGrid() {
    grid = [];
    for (let row = 0; row < GRID_SIZE; row++) {
        grid[row] = [];
        for (let col = 0; col < GRID_SIZE; col++) {
            grid[row][col] = {
                isMine: false,
                isRevealed: false,
                isFlagged: false,
                neighborMines: 0
            };
        }
    }
}

function placeMines() {
    let minesPlaced = 0;
    while (minesPlaced < MINE_COUNT) {
        const row = Math.floor(Math.random() * GRID_SIZE);
        const col = Math.floor(Math.random() * GRID_SIZE);
        
        if (!grid[row][col].isMine) {
            grid[row][col].isMine = true;
            minesPlaced++;
        }
    }
}

function calculateNumbers() {
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            if (!grid[row][col].isMine) {
                let count = 0;
                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        const newRow = row + dr;
                        const newCol = col + dc;
                        if (newRow >= 0 && newRow < GRID_SIZE && 
                            newCol >= 0 && newCol < GRID_SIZE &&
                            grid[newRow][newCol].isMine) {
                            count++;
                        }
                    }
                }
                grid[row][col].neighborMines = count;
            }
        }
    }
}

// Input handling
function handleClick(event) {
    if (gameState !== 'playing') return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const col = Math.floor((x - gridOffsetX) / cellSize);
    const row = Math.floor((y - gridOffsetY) / cellSize);
    
    if (row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE) {
        revealCell(row, col);
    }
}

function handleRightClick(event) {
    event.preventDefault();
    if (gameState !== 'playing') return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const col = Math.floor((x - gridOffsetX) / cellSize);
    const row = Math.floor((y - gridOffsetY) / cellSize);
    
    if (row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE) {
        toggleFlag(row, col);
    }
}

function handleTouchStart(event) {
    touchStartTime = Date.now();
}

function handleTouchEnd(event) {
    event.preventDefault();
    if (gameState !== 'playing') return;
    
    const touchDuration = Date.now() - touchStartTime;
    const rect = canvas.getBoundingClientRect();
    const touch = event.changedTouches[0];
    const x = touch.clientX - rect.left;
    const y = touch.clientY - rect.top;
    
    const col = Math.floor((x - gridOffsetX) / cellSize);
    const row = Math.floor((y - gridOffsetY) / cellSize);
    
    if (row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE) {
        if (touchDuration > 500) {
            // Long press = flag
            toggleFlag(row, col);
        } else {
            // Short press = reveal
            revealCell(row, col);
        }
    }
}

// Game logic
function revealCell(row, col) {
    const cell = grid[row][col];
    
    if (cell.isRevealed || cell.isFlagged) return;
    
    cell.isRevealed = true;
    revealedCells++;
    
    if (cell.isMine) {
        // Game over
        gameOver(false);
        return;
    }
    
    // Add score for revealed cell
    score += 10;
    updateScore();
    
    // If cell has no neighboring mines, reveal neighbors
    if (cell.neighborMines === 0) {
        for (let dr = -1; dr <= 1; dr++) {
            for (let dc = -1; dc <= 1; dc++) {
                const newRow = row + dr;
                const newCol = col + dc;
                if (newRow >= 0 && newRow < GRID_SIZE && 
                    newCol >= 0 && newCol < GRID_SIZE) {
                    revealCell(newRow, newCol);
                }
            }
        }
    }
    
    // Check win condition
    if (revealedCells === GRID_SIZE * GRID_SIZE - MINE_COUNT) {
        gameOver(true);
    }
    
    render();
}

function toggleFlag(row, col) {
    const cell = grid[row][col];
    
    if (cell.isRevealed) return;
    
    if (cell.isFlagged) {
        cell.isFlagged = false;
        flaggedCells--;
    } else {
        cell.isFlagged = true;
        flaggedCells++;
    }
    
    updateFlagCount();
    render();
}

function gameOver(won) {
    gameState = 'game_over';
    gameWon = won;
    
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    
    // Reveal all mines
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            if (grid[row][col].isMine) {
                grid[row][col].isRevealed = true;
            }
        }
    }
    
    // Calculate final score
    if (won) {
        score += 1000; // Bonus for winning
        score += Math.max(0, 300 - timer) * 10; // Time bonus
    }
    
    // Update leaderboard
    updateLeaderboard(score);
    
    // Show game over screen
    document.getElementById('final_score').textContent = `得分: ${score}`;
    document.getElementById('gameover_text').textContent = won ? '恭喜获胜!' : '游戏结束';
    
    render();
    
    setTimeout(() => {
        showScreen('game_over');
    }, 1000);
}

// UI updates
function updateScore() {
    document.getElementById('score_display').textContent = `得分: ${score}`;
}

function updateMineCount() {
    const remaining = MINE_COUNT - flaggedCells;
    document.getElementById('mine_count').textContent = `💣 ${remaining}`;
}

function updateFlagCount() {
    document.getElementById('flag_count').textContent = `🚩 ${flaggedCells}`;
}

function updateTimer() {
    if (gameState === 'playing') {
        timer = Math.floor((Date.now() - gameStartTime) / 1000);
        document.getElementById('timer').textContent = `⏱ ${timer.toString().padStart(3, '0')}`;
    }
}

// Rendering
function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            const cell = grid[row][col];
            const x = gridOffsetX + col * cellSize;
            const y = gridOffsetY + row * cellSize;
            
            // Draw cell background
            if (cell.isRevealed) {
                if (cell.isMine) {
                    ctx.fillStyle = '#F44336';
                } else {
                    ctx.fillStyle = '#E0E0E0';
                }
            } else {
                ctx.fillStyle = '#BDBDBD';
            }
            
            ctx.fillRect(x, y, cellSize, cellSize);
            
            // Draw cell border
            ctx.strokeStyle = '#757575';
            ctx.lineWidth = 1;
            ctx.strokeRect(x, y, cellSize, cellSize);
            
            // Draw cell content
            ctx.fillStyle = '#333333';
            ctx.font = `${cellSize * 0.6}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            const centerX = x + cellSize / 2;
            const centerY = y + cellSize / 2;
            
            if (cell.isFlagged && !cell.isRevealed) {
                ctx.fillStyle = '#F44336';
                ctx.fillText('🚩', centerX, centerY);
            } else if (cell.isRevealed) {
                if (cell.isMine) {
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillText('💣', centerX, centerY);
                } else if (cell.neighborMines > 0) {
                    // Color numbers based on count
                    const colors = ['', '#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#D32F2F', '#00796B', '#5D4037', '#424242'];
                    ctx.fillStyle = colors[cell.neighborMines] || '#333333';
                    ctx.fillText(cell.neighborMines.toString(), centerX, centerY);
                }
            }
        }
    }
}

// Leaderboard management
function initLeaderboard() {
    const savedScores = localStorage.getItem('minesweeper_scores');
    if (!savedScores) {
        localStorage.setItem('minesweeper_scores', JSON.stringify([9999, 7500, 5000, 2500, 1000]));
    }
}

function updateLeaderboard(newScore) {
    const savedScores = JSON.parse(localStorage.getItem('minesweeper_scores') || '[9999, 7500, 5000, 2500, 1000]');
    savedScores.push(newScore);
    savedScores.sort((a, b) => b - a);
    savedScores.splice(5); // Keep only top 5
    
    localStorage.setItem('minesweeper_scores', JSON.stringify(savedScores));
    
    // Update display
    const scoreList = savedScores.map((score, index) => `${index + 1}. ${score}`).join('<br>');
    document.getElementById('score_list').innerHTML = scoreList;
}

// Initialize game when page loads
window.addEventListener('load', init);