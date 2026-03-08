core.js
// Game state
let gameState = 'menu'; // menu, playing, game_over
let score = 0;
let timer = 0;
let gameTimer = null;
let mineCount = 10;
let flagCount = 0;

// Grid settings
const GRID_SIZE = 10;
const CELL_SIZE = 40;
let grid = [];
let revealed = [];
let flagged = [];
let mines = [];

// Canvas and context
let canvas;
let ctx;

// Initialize game
function init() {
    canvas = document.getElementById('game_canvas');
    if (canvas) {
        ctx = canvas.getContext('2d');
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        canvas.addEventListener('click', handleCanvasClick);
        canvas.addEventListener('contextmenu', handleRightClick);
    }
    
    // Initialize leaderboard
    loadLeaderboard();
}

function resizeCanvas() {
    if (!canvas) return;
    
    const container = canvas.parentElement;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * 0.926;
    canvas.height = rect.height * 0.521;
    
    if (gameState === 'playing') {
        render();
    }
}

function showScreen(screenId) {
    // Hide all screens
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => screen.style.display = 'none');
    
    // Show target screen
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.style.display = 'block';
    }
    
    // Handle screen-specific logic
    if (screenId === 'gameplay') {
        startGame();
    } else if (screenId === 'main_menu') {
        gameState = 'menu';
        if (gameTimer) {
            clearInterval(gameTimer);
            gameTimer = null;
        }
    }
}

function startGame() {
    gameState = 'playing';
    score = 0;
    timer = 0;
    flagCount = 0;
    
    // Initialize grid
    initializeGrid();
    placeMines();
    calculateNumbers();
    
    // Update UI
    updateScore();
    updateTimer();
    updateMineCount();
    updateFlagCount();
    
    // Start timer
    if (gameTimer) clearInterval(gameTimer);
    gameTimer = setInterval(() => {
        timer++;
        updateTimer();
    }, 1000);
    
    // Render game
    render();
}

function restartGame() {
    showScreen('gameplay');
}

function initializeGrid() {
    grid = [];
    revealed = [];
    flagged = [];
    mines = [];
    
    for (let row = 0; row < GRID_SIZE; row++) {
        grid[row] = [];
        revealed[row] = [];
        flagged[row] = [];
        for (let col = 0; col < GRID_SIZE; col++) {
            grid[row][col] = 0;
            revealed[row][col] = false;
            flagged[row][col] = false;
        }
    }
}

function placeMines() {
    let minesPlaced = 0;
    while (minesPlaced < mineCount) {
        const row = Math.floor(Math.random() * GRID_SIZE);
        const col = Math.floor(Math.random() * GRID_SIZE);
        
        if (grid[row][col] !== -1) {
            grid[row][col] = -1;
            mines.push({row, col});
            minesPlaced++;
        }
    }
}

function calculateNumbers() {
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            if (grid[row][col] !== -1) {
                let count = 0;
                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        const newRow = row + dr;
                        const newCol = col + dc;
                        if (newRow >= 0 && newRow < GRID_SIZE && 
                            newCol >= 0 && newCol < GRID_SIZE && 
                            grid[newRow][newCol] === -1) {
                            count++;
                        }
                    }
                }
                grid[row][col] = count;
            }
        }
    }
}

function handleCanvasClick(event) {
    if (gameState !== 'playing') return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const cellWidth = canvas.width / GRID_SIZE;
    const cellHeight = canvas.height / GRID_SIZE;
    
    const col = Math.floor(x / cellWidth);
    const row = Math.floor(y / cellHeight);
    
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
    
    const cellWidth = canvas.width / GRID_SIZE;
    const cellHeight = canvas.height / GRID_SIZE;
    
    const col = Math.floor(x / cellWidth);
    const row = Math.floor(y / cellHeight);
    
    if (row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE) {
        toggleFlag(row, col);
    }
}

function revealCell(row, col) {
    if (revealed[row][col] || flagged[row][col]) return;
    
    revealed[row][col] = true;
    
    if (grid[row][col] === -1) {
        // Hit a mine - game over
        gameOver(false);
        return;
    }
    
    // Add score for revealing cell
    score += 10;
    updateScore();
    
    // If cell is empty, reveal adjacent cells
    if (grid[row][col] === 0) {
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
    checkWinCondition();
    render();
}

function toggleFlag(row, col) {
    if (revealed[row][col]) return;
    
    flagged[row][col] = !flagged[row][col];
    flagCount += flagged[row][col] ? 1 : -1;
    updateFlagCount();
    render();
}

function checkWinCondition() {
    let revealedCount = 0;
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            if (revealed[row][col]) revealedCount++;
        }
    }
    
    if (revealedCount === GRID_SIZE * GRID_SIZE - mineCount) {
        gameOver(true);
    }
}

function gameOver(won) {
    gameState = 'game_over';
    
    if (gameTimer) {
        clearInterval(gameTimer);
        gameTimer = null;
    }
    
    if (won) {
        score += 1000; // Bonus for winning
        document.getElementById('gameover_text').textContent = '恭喜获胜!';
    } else {
        document.getElementById('gameover_text').textContent = '游戏结束';
        // Reveal all mines
        for (let mine of mines) {
            revealed[mine.row][mine.col] = true;
        }
        render();
    }
    
    // Update final score
    document.getElementById('final_score').textContent = `得分: ${score}`;
    
    // Save to leaderboard
    saveScore(score);
    
    // Show game over screen after a delay
    setTimeout(() => {
        showScreen('game_over');
    }, 1500);
}

function render() {
    if (!ctx || !canvas) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const cellWidth = canvas.width / GRID_SIZE;
    const cellHeight = canvas.height / GRID_SIZE;
    
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            const x = col * cellWidth;
            const y = row * cellHeight;
            
            // Draw cell background
            if (revealed[row][col]) {
                if (grid[row][col] === -1) {
                    ctx.fillStyle = '#F44336'; // Mine - red
                } else {
                    ctx.fillStyle = '#E0E0E0'; // Revealed - light gray
                }
            } else {
                ctx.fillStyle = '#BDBDBD'; // Hidden - gray
            }
            
            ctx.fillRect(x, y, cellWidth, cellHeight);
            
            // Draw cell border
            ctx.strokeStyle = '#757575';
            ctx.lineWidth = 1;
            ctx.strokeRect(x, y, cellWidth, cellHeight);
            
            // Draw cell content
            ctx.fillStyle = '#333333';
            ctx.font = `${Math.min(cellWidth, cellHeight) * 0.6}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            const centerX = x + cellWidth / 2;
            const centerY = y + cellHeight / 2;
            
            if (flagged[row][col]) {
                ctx.fillStyle = '#F44336';
                ctx.fillText('🚩', centerX, centerY);
            } else if (revealed[row][col]) {
                if (grid[row][col] === -1) {
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillText('💣', centerX, centerY);
                } else if (grid[row][col] > 0) {
                    // Color numbers based on count
                    const colors = ['', '#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#D32F2F', '#00796B', '#5D4037', '#424242'];
                    ctx.fillStyle = colors[grid[row][col]] || '#333333';
                    ctx.fillText(grid[row][col].toString(), centerX, centerY);
                }
            }
        }
    }
}

function updateScore() {
    document.getElementById('score_display').textContent = `得分: ${score}`;
}

function updateTimer() {
    const minutes = Math.floor(timer / 60);
    const seconds = timer % 60;
    const timeStr = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('timer').textContent = `⏱ ${timeStr}`;
}

function updateMineCount() {
    document.getElementById('mine_count').textContent = `💣 ${mineCount}`;
}

function updateFlagCount() {
    document.getElementById('flag_count').textContent = `🚩 ${flagCount}`;
}

function saveScore(newScore) {
    let scores = JSON.parse(localStorage.getItem('minesweeper_scores') || '[]');
    scores.push(newScore);
    scores.sort((a, b) => b - a);
    scores = scores.slice(0, 5); // Keep top 5
    localStorage.setItem('minesweeper_scores', JSON.stringify(scores));
    updateLeaderboard(scores);
}

function loadLeaderboard() {
    const scores = JSON.parse(localStorage.getItem('minesweeper_scores') || '[9999, 7500, 5000, 2500, 1000]');
    updateLeaderboard(scores);
}

function updateLeaderboard(scores) {
    const scoreList = document.getElementById('score_list');
    let html = '';
    for (let i = 0; i < Math.min(5, scores.length); i++) {
        html += `${i + 1}. ${scores[i]}<br>`;
    }
    scoreList.innerHTML = html;
}

// Initialize when page loads
window.addEventListener('load', init);