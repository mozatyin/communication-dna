core.js
// Game state
let gameState = 'menu'; // menu, playing, game_over
let grid = [];
let score = 0;
let bestScore = 0;
let canvas, ctx;
let animationId;

// Game constants
const GRID_SIZE = 4;
const CELL_SIZE = 230;
const CELL_GAP = 20;
const GRID_PADDING = 25;

// Tile colors
const TILE_COLORS = {
    2: '#EEE4DA',
    4: '#EDE0C8',
    8: '#F2B179',
    16: '#F59563',
    32: '#F67C5F',
    64: '#F65E3B',
    128: '#EDCF72',
    256: '#EDCC61',
    512: '#EDC850',
    1024: '#EDC53F',
    2048: '#EDC22E'
};

const TEXT_COLORS = {
    2: '#776E65',
    4: '#776E65',
    8: '#F9F6F2',
    16: '#F9F6F2',
    32: '#F9F6F2',
    64: '#F9F6F2',
    128: '#F9F6F2',
    256: '#F9F6F2',
    512: '#F9F6F2',
    1024: '#F9F6F2',
    2048: '#F9F6F2'
};

// Initialize game
function init() {
    canvas = document.getElementById('game_canvas');
    ctx = canvas.getContext('2d');
    
    // Load best score from localStorage
    bestScore = parseInt(localStorage.getItem('2048_best_score') || '0');
    updateBestScore();
    
    // Initialize empty grid
    initGrid();
    
    // Setup input handlers
    setupInputHandlers();
    
    // Start render loop
    render();
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
        gameState = 'playing';
        startNewGame();
    } else if (screenId === 'main_menu') {
        gameState = 'menu';
    } else if (screenId === 'game_over') {
        gameState = 'game_over';
        updateFinalScore();
    }
}

function initGrid() {
    grid = [];
    for (let i = 0; i < GRID_SIZE; i++) {
        grid[i] = [];
        for (let j = 0; j < GRID_SIZE; j++) {
            grid[i][j] = 0;
        }
    }
}

function startNewGame() {
    initGrid();
    score = 0;
    updateScore();
    addRandomTile();
    addRandomTile();
    gameState = 'playing';
    render();
}

function addRandomTile() {
    const emptyCells = [];
    for (let i = 0; i < GRID_SIZE; i++) {
        for (let j = 0; j < GRID_SIZE; j++) {
            if (grid[i][j] === 0) {
                emptyCells.push({row: i, col: j});
            }
        }
    }
    
    if (emptyCells.length > 0) {
        const randomCell = emptyCells[Math.floor(Math.random() * emptyCells.length)];
        grid[randomCell.row][randomCell.col] = Math.random() < 0.9 ? 2 : 4;
    }
}

function setupInputHandlers() {
    let startX, startY;
    
    // Touch events
    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        const touch = e.touches[0];
        startX = touch.clientX;
        startY = touch.clientY;
    });
    
    canvas.addEventListener('touchend', (e) => {
        e.preventDefault();
        if (gameState !== 'playing') return;
        
        const touch = e.changedTouches[0];
        const endX = touch.clientX;
        const endY = touch.clientY;
        
        const deltaX = endX - startX;
        const deltaY = endY - startY;
        const minSwipeDistance = 50;
        
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            if (Math.abs(deltaX) > minSwipeDistance) {
                if (deltaX > 0) {
                    move('right');
                } else {
                    move('left');
                }
            }
        } else {
            if (Math.abs(deltaY) > minSwipeDistance) {
                if (deltaY > 0) {
                    move('down');
                } else {
                    move('up');
                }
            }
        }
    });
    
    // Keyboard events
    document.addEventListener('keydown', (e) => {
        if (gameState !== 'playing') return;
        
        switch(e.key) {
            case 'ArrowUp':
                e.preventDefault();
                move('up');
                break;
            case 'ArrowDown':
                e.preventDefault();
                move('down');
                break;
            case 'ArrowLeft':
                e.preventDefault();
                move('left');
                break;
            case 'ArrowRight':
                e.preventDefault();
                move('right');
                break;
        }
    });
}

function move(direction) {
    const previousGrid = JSON.parse(JSON.stringify(grid));
    let moved = false;
    
    switch(direction) {
        case 'left':
            moved = moveLeft();
            break;
        case 'right':
            moved = moveRight();
            break;
        case 'up':
            moved = moveUp();
            break;
        case 'down':
            moved = moveDown();
            break;
    }
    
    if (moved) {
        addRandomTile();
        updateScore();
        
        if (checkWin()) {
            // Player reached 2048
            setTimeout(() => {
                alert('恭喜！你达到了2048！');
            }, 100);
        } else if (checkGameOver()) {
            setTimeout(() => {
                showScreen('game_over');
            }, 100);
        }
    }
    
    render();
}

function moveLeft() {
    let moved = false;
    for (let i = 0; i < GRID_SIZE; i++) {
        const row = grid[i].filter(val => val !== 0);
        for (let j = 0; j < row.length - 1; j++) {
            if (row[j] === row[j + 1]) {
                row[j] *= 2;
                score += row[j];
                row.splice(j + 1, 1);
            }
        }
        while (row.length < GRID_SIZE) {
            row.push(0);
        }
        
        for (let j = 0; j < GRID_SIZE; j++) {
            if (grid[i][j] !== row[j]) {
                moved = true;
            }
            grid[i][j] = row[j];
        }
    }
    return moved;
}

function moveRight() {
    let moved = false;
    for (let i = 0; i < GRID_SIZE; i++) {
        const row = grid[i].filter(val => val !== 0);
        for (let j = row.length - 1; j > 0; j--) {
            if (row[j] === row[j - 1]) {
                row[j] *= 2;
                score += row[j];
                row.splice(j - 1, 1);
                j--;
            }
        }
        while (row.length < GRID_SIZE) {
            row.unshift(0);
        }
        
        for (let j = 0; j < GRID_SIZE; j++) {
            if (grid[i][j] !== row[j]) {
                moved = true;
            }
            grid[i][j] = row[j];
        }
    }
    return moved;
}

function moveUp() {
    let moved = false;
    for (let j = 0; j < GRID_SIZE; j++) {
        const column = [];
        for (let i = 0; i < GRID_SIZE; i++) {
            if (grid[i][j] !== 0) {
                column.push(grid[i][j]);
            }
        }
        
        for (let i = 0; i < column.length - 1; i++) {
            if (column[i] === column[i + 1]) {
                column[i] *= 2;
                score += column[i];
                column.splice(i + 1, 1);
            }
        }
        
        while (column.length < GRID_SIZE) {
            column.push(0);
        }
        
        for (let i = 0; i < GRID_SIZE; i++) {
            if (grid[i][j] !== column[i]) {
                moved = true;
            }
            grid[i][j] = column[i];
        }
    }
    return moved;
}

function moveDown() {
    let moved = false;
    for (let j = 0; j < GRID_SIZE; j++) {
        const column = [];
        for (let i = 0; i < GRID_SIZE; i++) {
            if (grid[i][j] !== 0) {
                column.push(grid[i][j]);
            }
        }
        
        for (let i = column.length - 1; i > 0; i--) {
            if (column[i] === column[i - 1]) {
                column[i] *= 2;
                score += column[i];
                column.splice(i - 1, 1);
                i--;
            }
        }
        
        while (column.length < GRID_SIZE) {
            column.unshift(0);
        }
        
        for (let i = 0; i < GRID_SIZE; i++) {
            if (grid[i][j] !== column[i]) {
                moved = true;
            }
            grid[i][j] = column[i];
        }
    }
    return moved;
}

function checkWin() {
    for (let i = 0; i < GRID_SIZE; i++) {
        for (let j = 0; j < GRID_SIZE; j++) {
            if (grid[i][j] === 2048) {
                return true;
            }
        }
    }
    return false;
}

function checkGameOver() {
    // Check for empty cells
    for (let i = 0; i < GRID_SIZE; i++) {
        for (let j = 0; j < GRID_SIZE; j++) {
            if (grid[i][j] === 0) {
                return false;
            }
        }
    }
    
    // Check for possible merges
    for (let i = 0; i < GRID_SIZE; i++) {
        for (let j = 0; j < GRID_SIZE; j++) {
            const current = grid[i][j];
            if ((i < GRID_SIZE - 1 && grid[i + 1][j] === current) ||
                (j < GRID_SIZE - 1 && grid[i][j + 1] === current)) {
                return false;
            }
        }
    }
    
    return true;
}

function updateScore() {
    document.getElementById('score_value').textContent = score;
    if (score > bestScore) {
        bestScore = score;
        localStorage.setItem('2048_best_score', bestScore.toString());
        updateBestScore();
    }
}

function updateBestScore() {
    document.getElementById('best_value').textContent = bestScore;
}

function updateFinalScore() {
    document.getElementById('final_score').textContent = `得分: ${score}`;
}

function render() {
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid background
    for (let i = 0; i < GRID_SIZE; i++) {
        for (let j = 0; j < GRID_SIZE; j++) {
            const x = GRID_PADDING + j * (CELL_SIZE + CELL_GAP);
            const y = GRID_PADDING + i * (CELL_SIZE + CELL_GAP);
            
            ctx.fillStyle = '#CDC1B4';
            ctx.fillRect(x, y, CELL_SIZE, CELL_SIZE);
        }
    }
    
    // Draw tiles
    for (let i = 0; i < GRID_SIZE; i++) {
        for (let j = 0; j < GRID_SIZE; j++) {
            const value = grid[i][j];
            if (value !== 0) {
                const x = GRID_PADDING + j * (CELL_SIZE + CELL_GAP);
                const y = GRID_PADDING + i * (CELL_SIZE + CELL_GAP);
                
                // Draw tile background
                ctx.fillStyle = TILE_COLORS[value] || '#3C3A32';
                ctx.fillRect(x, y, CELL_SIZE, CELL_SIZE);
                
                // Draw tile text
                ctx.fillStyle = TEXT_COLORS[value] || '#F9F6F2';
                ctx.font = value < 100 ? 'bold 80px Arial' : 
                          value < 1000 ? 'bold 70px Arial' : 'bold 60px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(value.toString(), x + CELL_SIZE / 2, y + CELL_SIZE / 2);
            }
        }
    }
    
    if (gameState === 'playing') {
        requestAnimationFrame(render);
    }
}

function retryGame() {
    showScreen('gameplay');
}

// Initialize game when page loads
window.addEventListener('load', init);