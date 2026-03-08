core.js
// Game state
let gameState = 'menu'; // menu, playing, paused, game_over
let score = 0;
let movesLeft = 30;
let targetScore = 5000;
let level = 1;

// Game grid
const GRID_SIZE = 8;
const CELL_SIZE = 60;
const COLORS = ['#FF6B9D', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'];
let grid = [];
let selectedCell = null;
let canvas, ctx;
let animating = false;

// Initialize game
function init() {
    canvas = document.getElementById('gameCanvas');
    if (canvas) {
        ctx = canvas.getContext('2d');
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
    }
    
    // Initialize leaderboard
    if (!localStorage.getItem('match3_scores')) {
        localStorage.setItem('match3_scores', JSON.stringify([9999, 7500, 5000, 2500, 1000]));
    }
    updateLeaderboard();
}

function resizeCanvas() {
    if (!canvas) return;
    
    const container = canvas.parentElement;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
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
        
        if (screenId === 'gameplay') {
            startGame();
        } else if (screenId === 'leaderboard') {
            targetScreen.style.display = 'flex';
        }
    }
}

function startGame() {
    gameState = 'playing';
    score = 0;
    movesLeft = 30;
    selectedCell = null;
    animating = false;
    
    // Initialize grid
    initializeGrid();
    
    // Update UI
    updateUI();
    
    // Start render loop
    render();
}

function restartGame() {
    showScreen('gameplay');
}

function initializeGrid() {
    grid = [];
    for (let row = 0; row < GRID_SIZE; row++) {
        grid[row] = [];
        for (let col = 0; col < GRID_SIZE; col++) {
            grid[row][col] = {
                color: COLORS[Math.floor(Math.random() * COLORS.length)],
                matched: false
            };
        }
    }
    
    // Ensure no initial matches
    removeInitialMatches();
}

function removeInitialMatches() {
    let hasMatches = true;
    while (hasMatches) {
        hasMatches = false;
        for (let row = 0; row < GRID_SIZE; row++) {
            for (let col = 0; col < GRID_SIZE; col++) {
                if (checkMatch(row, col)) {
                    grid[row][col].color = COLORS[Math.floor(Math.random() * COLORS.length)];
                    hasMatches = true;
                }
            }
        }
    }
}

function checkMatch(row, col) {
    const color = grid[row][col].color;
    
    // Check horizontal
    let horizontalCount = 1;
    // Check left
    for (let c = col - 1; c >= 0 && grid[row][c].color === color; c--) {
        horizontalCount++;
    }
    // Check right
    for (let c = col + 1; c < GRID_SIZE && grid[row][c].color === color; c++) {
        horizontalCount++;
    }
    
    // Check vertical
    let verticalCount = 1;
    // Check up
    for (let r = row - 1; r >= 0 && grid[r][col].color === color; r--) {
        verticalCount++;
    }
    // Check down
    for (let r = row + 1; r < GRID_SIZE && grid[r][col].color === color; r++) {
        verticalCount++;
    }
    
    return horizontalCount >= 3 || verticalCount >= 3;
}

function handleCanvasClick(event) {
    if (gameState !== 'playing' || animating || movesLeft <= 0) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const col = Math.floor(x / (canvas.width / GRID_SIZE));
    const row = Math.floor(y / (canvas.height / GRID_SIZE));
    
    if (row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE) {
        if (!selectedCell) {
            selectedCell = { row, col };
        } else {
            if (selectedCell.row === row && selectedCell.col === col) {
                selectedCell = null;
            } else if (isAdjacent(selectedCell, { row, col })) {
                attemptSwap(selectedCell, { row, col });
                selectedCell = null;
            } else {
                selectedCell = { row, col };
            }
        }
        render();
    }
}

function isAdjacent(cell1, cell2) {
    const rowDiff = Math.abs(cell1.row - cell2.row);
    const colDiff = Math.abs(cell1.col - cell2.col);
    return (rowDiff === 1 && colDiff === 0) || (rowDiff === 0 && colDiff === 1);
}

function attemptSwap(cell1, cell2) {
    // Swap cells
    const temp = grid[cell1.row][cell1.col];
    grid[cell1.row][cell1.col] = grid[cell2.row][cell2.col];
    grid[cell2.row][cell2.col] = temp;
    
    // Check if swap creates matches
    const hasMatches = findMatches();
    
    if (hasMatches.length > 0) {
        movesLeft--;
        processMatches();
    } else {
        // Swap back if no matches
        const temp = grid[cell1.row][cell1.col];
        grid[cell1.row][cell1.col] = grid[cell2.row][cell2.col];
        grid[cell2.row][cell2.col] = temp;
    }
    
    updateUI();
}

function findMatches() {
    const matches = [];
    
    // Reset matched flags
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            grid[row][col].matched = false;
        }
    }
    
    // Find horizontal matches
    for (let row = 0; row < GRID_SIZE; row++) {
        let count = 1;
        let currentColor = grid[row][0].color;
        
        for (let col = 1; col < GRID_SIZE; col++) {
            if (grid[row][col].color === currentColor) {
                count++;
            } else {
                if (count >= 3) {
                    for (let c = col - count; c < col; c++) {
                        grid[row][c].matched = true;
                        matches.push({ row, col: c });
                    }
                }
                count = 1;
                currentColor = grid[row][col].color;
            }
        }
        
        if (count >= 3) {
            for (let c = GRID_SIZE - count; c < GRID_SIZE; c++) {
                grid[row][c].matched = true;
                matches.push({ row, col: c });
            }
        }
    }
    
    // Find vertical matches
    for (let col = 0; col < GRID_SIZE; col++) {
        let count = 1;
        let currentColor = grid[0][col].color;
        
        for (let row = 1; row < GRID_SIZE; row++) {
            if (grid[row][col].color === currentColor) {
                count++;
            } else {
                if (count >= 3) {
                    for (let r = row - count; r < row; r++) {
                        grid[r][col].matched = true;
                        matches.push({ row: r, col });
                    }
                }
                count = 1;
                currentColor = grid[row][col].color;
            }
        }
        
        if (count >= 3) {
            for (let r = GRID_SIZE - count; r < GRID_SIZE; r++) {
                grid[r][col].matched = true;
                matches.push({ row: r, col });
            }
        }
    }
    
    return matches;
}

function processMatches() {
    animating = true;
    
    setTimeout(() => {
        const matches = findMatches();
        
        if (matches.length > 0) {
            // Add score
            score += matches.length * 100;
            
            // Remove matched cells
            for (let row = 0; row < GRID_SIZE; row++) {
                for (let col = 0; col < GRID_SIZE; col++) {
                    if (grid[row][col].matched) {
                        grid[row][col] = null;
                    }
                }
            }
            
            // Drop cells down
            dropCells();
            
            // Fill empty spaces
            fillEmptySpaces();
            
            // Check for new matches
            setTimeout(() => {
                const newMatches = findMatches();
                if (newMatches.length > 0) {
                    processMatches();
                } else {
                    animating = false;
                    checkGameOver();
                }
            }, 300);
        } else {
            animating = false;
            checkGameOver();
        }
        
        updateUI();
        render();
    }, 200);
}

function dropCells() {
    for (let col = 0; col < GRID_SIZE; col++) {
        let writePos = GRID_SIZE - 1;
        
        for (let row = GRID_SIZE - 1; row >= 0; row--) {
            if (grid[row][col] !== null) {
                if (row !== writePos) {
                    grid[writePos][col] = grid[row][col];
                    grid[row][col] = null;
                }
                writePos--;
            }
        }
    }
}

function fillEmptySpaces() {
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            if (grid[row][col] === null) {
                grid[row][col] = {
                    color: COLORS[Math.floor(Math.random() * COLORS.length)],
                    matched: false
                };
            }
        }
    }
}

function checkGameOver() {
    if (movesLeft <= 0) {
        gameState = 'game_over';
        updateFinalScore();
        updateLeaderboard();
        showScreen('game_over');
    } else if (score >= targetScore) {
        // Level complete - could add level progression here
        level++;
        targetScore += 2000;
        movesLeft += 10;
        updateUI();
    }
}

function updateUI() {
    document.getElementById('score_display').textContent = `得分: ${score}`;
    document.getElementById('moves_left').textContent = `步数: ${movesLeft}`;
    document.getElementById('target').textContent = `目标: ${targetScore}`;
    document.getElementById('level_label').textContent = `第 ${level} 关`;
}

function updateFinalScore() {
    document.getElementById('final_score').textContent = `得分: ${score}`;
    
    // Update leaderboard
    const scores = JSON.parse(localStorage.getItem('match3_scores') || '[0,0,0,0,0]');
    scores.push(score);
    scores.sort((a, b) => b - a);
    scores.splice(5); // Keep only top 5
    localStorage.setItem('match3_scores', JSON.stringify(scores));
}

function updateLeaderboard() {
    const scores = JSON.parse(localStorage.getItem('match3_scores') || '[9999,7500,5000,2500,1000]');
    const scoreList = document.getElementById('score_list');
    if (scoreList) {
        scoreList.innerHTML = scores.map((score, index) => `${index + 1}. ${score}`).join('<br>');
    }
}

function render() {
    if (!ctx || !canvas) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (gameState !== 'playing') return;
    
    const cellWidth = canvas.width / GRID_SIZE;
    const cellHeight = canvas.height / GRID_SIZE;
    
    // Draw grid
    for (let row = 0; row < GRID_SIZE; row++) {
        for (let col = 0; col < GRID_SIZE; col++) {
            const x = col * cellWidth;
            const y = row * cellHeight;
            
            if (grid[row][col]) {
                // Draw cell background
                ctx.fillStyle = grid[row][col].matched ? '#FFD700' : grid[row][col].color;
                ctx.fillRect(x + 2, y + 2, cellWidth - 4, cellHeight - 4);
                
                // Draw cell border
                ctx.strokeStyle = '#FFFFFF';
                ctx.lineWidth = 2;
                ctx.strokeRect(x + 2, y + 2, cellWidth - 4, cellHeight - 4);
                
                // Highlight selected cell
                if (selectedCell && selectedCell.row === row && selectedCell.col === col) {
                    ctx.strokeStyle = '#FFD700';
                    ctx.lineWidth = 4;
                    ctx.strokeRect(x, y, cellWidth, cellHeight);
                }
            }
        }
    }
}

// Initialize when page loads
window.addEventListener('load', init);