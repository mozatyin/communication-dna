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

// Global Constants
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const GRAVITY = 0.6;
const FLAP_STRENGTH = -12;
const PIPE_SPEED = 3;
const PIPE_GAP = 200;
const BIRD_SIZE = 40;
const GROUND_HEIGHT = 100;

// Shared State
const GameState = {
    gameStatus: 'start',
    score: 0,
    highScore: 0,
    birdX: 200,
    birdY: 960,
    birdVelocity: 0,
    pipes: [],
    previousScreen: 'start'
};

// Module Code
const game_state = (function() {
    let eventBus = window.eventBus || { emit: function() {}, on: function() {} };

    function init() {
        if (!window.GameState) {
            window.GameState = {
                gameStatus: 'start',
                score: 0,
                highScore: 0,
                birdX: 200,
                birdY: 960,
                birdVelocity: 0,
                pipes: [],
                previousScreen: 'start'
            };
        }

        // Listen for events that trigger state changes
        eventBus.on('BIRD_COLLISION', function() {
            if (GameState.gameStatus === 'playing') {
                endGame();
            }
        });

        eventBus.on('BIRD_SCORED', function(data) {
            if (GameState.gameStatus === 'playing') {
                addScore(data.points);
            }
        });
    }

    function startGame() {
        if (GameState.gameStatus === 'start') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            eventBus.emit('GAME_START', {});
        }
    }

    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
            }
        }
    }

    function addScore(points) {
        if (GameState.gameStatus === 'playing') {
            GameState.score += points;
        }
    }

    function showLeaderboard() {
        if (GameState.gameStatus === 'start' || GameState.gameStatus === 'game_over') {
            GameState.previousScreen = GameState.gameStatus;
            GameState.gameStatus = 'leaderboard';
            eventBus.emit('SHOW_LEADERBOARD', {});
        }
    }

    function closeLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = GameState.previousScreen;
            eventBus.emit('CLOSE_LEADERBOARD', {});
        }
    }

    function retry() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            eventBus.emit('RETRY', {});
        }
    }

    function returnToMenu() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'start';
            eventBus.emit('RETURN_MENU', {});
        }
    }

    return {
        init,
        startGame,
        endGame,
        addScore,
        showLeaderboard,
        closeLeaderboard,
        retry,
        returnToMenu
    };
})();

const bird_physics = (function() {
    let eventListeners = [];

    function addEventListener(eventName, callback) {
        if (!eventListeners[eventName]) {
            eventListeners[eventName] = [];
        }
        eventListeners[eventName].push(callback);
    }

    function emitEvent(eventName, payload = {}) {
        if (eventListeners[eventName]) {
            eventListeners[eventName].forEach(callback => callback(payload));
        }
        // Also emit through global EventBus
        EventBus.emit(eventName, payload);
    }

    function init() {
        GameState.birdX = 200;
        GameState.birdY = 960;
        GameState.birdVelocity = 0;

        EventBus.on('GAME_START', reset);
        EventBus.on('RETRY', reset);
    }

    function flap() {
        if (GameState.gameStatus === 'playing') {
            GameState.birdVelocity = FLAP_STRENGTH;
        }
    }

    function update() {
        if (GameState.gameStatus !== 'playing') {
            return;
        }

        // Apply gravity
        GameState.birdVelocity += GRAVITY;
        
        // Update position
        GameState.birdY += GameState.birdVelocity;

        // Check collisions
        checkCollisions();
    }

    function reset() {
        GameState.birdX = 200;
        GameState.birdY = 960;
        GameState.birdVelocity = 0;
    }

    function checkCollisions() {
        // Check ground collision
        if (GameState.birdY >= CANVAS_HEIGHT - GROUND_HEIGHT) {
            emitEvent('BIRD_COLLISION');
            return;
        }

        // Check ceiling collision
        if (GameState.birdY <= 0) {
            emitEvent('BIRD_COLLISION');
            return;
        }

        // Check pipe collisions
        for (let pipe of GameState.pipes) {
            if (checkBirdPipeCollision(pipe)) {
                emitEvent('BIRD_COLLISION');
                return;
            }
        }
    }

    function checkBirdPipeCollision(pipe) {
        const birdLeft = GameState.birdX - BIRD_SIZE / 2;
        const birdRight = GameState.birdX + BIRD_SIZE / 2;
        const birdTop = GameState.birdY - BIRD_SIZE / 2;
        const birdBottom = GameState.birdY + BIRD_SIZE / 2;

        const pipeLeft = pipe.x;
        const pipeRight = pipe.x + 80; // PIPE_WIDTH
        const topHeight = pipe.gapCenter - PIPE_GAP / 2;

        // Check if bird is horizontally aligned with pipe
        if (birdRight > pipeLeft && birdLeft < pipeRight) {
            // Check collision with top pipe
            if (birdTop < topHeight) {
                return true;
            }
            // Check collision with bottom pipe
            if (birdBottom > topHeight + PIPE_GAP) {
                return true;
            }
        }

        return false;
    }

    return {
        init,
        flap,
        update,
        reset
    };
})();

const pipe_system = (function() {
    let pipeSpawnTimer = 0;
    const PIPE_SPAWN_INTERVAL = 120; // frames between pipe spawns
    const PIPE_WIDTH = 80;
    
    function init() {
        GameState.pipes = [];
        pipeSpawnTimer = 0;
    }
    
    function update() {
        if (GameState.gameStatus !== 'playing') return;
        
        // Move existing pipes
        for (let i = GameState.pipes.length - 1; i >= 0; i--) {
            const pipe = GameState.pipes[i];
            pipe.x -= PIPE_SPEED;
            
            // Remove pipes that have moved off screen
            if (pipe.x + PIPE_WIDTH < 0) {
                GameState.pipes.splice(i, 1);
            }
        }
        
        // Spawn new pipes
        pipeSpawnTimer++;
        if (pipeSpawnTimer >= PIPE_SPAWN_INTERVAL) {
            spawnPipe();
            pipeSpawnTimer = 0;
        }
        
        // Check for scoring
        checkScoring();
    }
    
    function spawnPipe() {
        // Random gap position - center of gap can be between 300 and 1620 (leaving room for gap)
        const minGapCenter = PIPE_GAP / 2 + 100;
        const maxGapCenter = CANVAS_HEIGHT - GROUND_HEIGHT - PIPE_GAP / 2 - 100;
        const gapCenter = Math.random() * (maxGapCenter - minGapCenter) + minGapCenter;
        
        const pipe = {
            x: CANVAS_WIDTH,
            gapCenter: gapCenter,
            scored: false,
            width: PIPE_WIDTH
        };
        
        GameState.pipes.push(pipe);
    }
    
    function checkScoring() {
        for (const pipe of GameState.pipes) {
            // Check if bird has passed through pipe gap center and hasn't been scored yet
            if (!pipe.scored && GameState.birdX > pipe.x + PIPE_WIDTH / 2 && GameState.birdX < pipe.x + PIPE_WIDTH) {
                // Bird is passing through pipe gap center
                pipe.scored = true;
                
                // Emit scoring event
                EventBus.emit('BIRD_SCORED', { points: 1 });
            }
        }
    }
    
    function reset() {
        GameState.pipes = [];
        pipeSpawnTimer = 0;
    }
    
    function getPipes() {
        return GameState.pipes;
    }
    
    // Listen for game events
    EventBus.on('GAME_START', reset);
    EventBus.on('RETRY', reset);
    
    return {
        init,
        update,
        reset,
        getPipes
    };
})();

const ui_screens = (function() {
    let canvas;
    let ctx;
    
    function init() {
        canvas = document.getElementById('gameCanvas') || document.createElement('canvas');
        canvas.width = CANVAS_WIDTH;
        canvas.height = CANVAS_HEIGHT;
        if (!document.getElementById('gameCanvas')) {
            canvas.id = 'gameCanvas';
            document.body.appendChild(canvas);
        }
        ctx = canvas.getContext('2d');
        
        // Set up canvas styling
        canvas.style.display = 'block';
        canvas.style.margin = '0 auto';
        canvas.style.border = '1px solid #000';
        canvas.style.backgroundColor = '#70c5ce';
    }
    
    function render() {
        // Clear canvas
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Render sky background
        ctx.fillStyle = '#70c5ce';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        switch (GameState.gameStatus) {
            case 'start':
                renderStartScreen();
                break;
            case 'playing':
                renderGameplayScreen();
                break;
            case 'game_over':
                renderGameOverScreen();
                break;
            case 'leaderboard':
                renderLeaderboardScreen();
                break;
        }
        
        // Update UI elements
        updateUIElements();
    }
    
    function updateUIElements() {
        // Update score displays
        const currentScoreEl = document.getElementById('current-score');
        const highScoreEl = document.getElementById('high-score');
        const leaderboardScoreEl = document.getElementById('leaderboard-score');
        const lastScoreEl = document.getElementById('last-score');
        
        if (currentScoreEl) currentScoreEl.textContent = GameState.score;
        if (highScoreEl) highScoreEl.textContent = GameState.highScore;
        if (leaderboardScoreEl) leaderboardScoreEl.textContent = GameState.highScore;
        if (lastScoreEl) lastScoreEl.textContent = GameState.score;
    }
    
    function renderStartScreen() {
        // Title logo
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 80px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Flappy Bird', CANVAS_WIDTH / 2, 400);
        
        // Bird preview
        renderBird(CANVAS_WIDTH / 2, 600);
        
        // Play button
        ctx.fillStyle = '#4CAF50';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 800, 300, 80);
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 40px Arial';
        ctx.fillText('PLAY', CANVAS_WIDTH / 2, 850);
        
        // Score button
        ctx.fillStyle = '#2196F3';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 920, 300, 80);
        ctx.fillStyle = '#fff';
        ctx.fillText('SCORES', CANVAS_WIDTH / 2, 970);
        
        // Instructions
        ctx.fillStyle = '#333';
        ctx.font = '30px Arial';
        ctx.fillText('Tap to flap!', CANVAS_WIDTH / 2, 1200);
    }
    
    function renderGameplayScreen() {
        // Render pipes
        ctx.fillStyle = '#4CAF50';
        for (let pipe of GameState.pipes) {
            const topHeight = pipe.gapCenter - PIPE_GAP / 2;
            // Top pipe
            ctx.fillRect(pipe.x, 0, pipe.width, topHeight);
            // Bottom pipe
            ctx.fillRect(pipe.x, topHeight + PIPE_GAP, pipe.width, CANVAS_HEIGHT - topHeight - PIPE_GAP - GROUND_HEIGHT);
        }
        
        // Render ground
        ctx.fillStyle = '#8B4513';
        ctx.fillRect(0, CANVAS_HEIGHT - GROUND_HEIGHT, CANVAS_WIDTH, GROUND_HEIGHT);
        
        // Render bird
        renderBird(GameState.birdX, GameState.birdY);
        
        // Render score
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 60px Arial';
        ctx.textAlign = 'center';
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 3;
        ctx.strokeText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
        ctx.fillText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
    }
    
    function renderGameOverScreen() {
        // Render game elements first
        renderGameplayScreen();
        
        // Semi-transparent overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Game Over text
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 80px Arial';
        ctx.textAlign = 'center';
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 3;
        ctx.strokeText('GAME OVER', CANVAS_WIDTH / 2, 400);
        ctx.fillText('GAME OVER', CANVAS_WIDTH / 2, 400);
        
        // Score panel
        ctx.fillStyle = '#fff';
        ctx.fillRect(CANVAS_WIDTH / 2 - 200, 500, 400, 200);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeRect(CANVAS_WIDTH / 2 - 200, 500, 400, 200);
        
        // Score text
        ctx.fillStyle = '#333';
        ctx.font = 'bold 40px Arial';
        ctx.fillText('Score: ' + GameState.score, CANVAS_WIDTH / 2, 580);
        ctx.fillText('Best: ' + GameState.highScore, CANVAS_WIDTH / 2, 640);
        
        // Medal (simple circle)
        if (GameState.score > 0) {
            ctx.fillStyle = GameState.score >= GameState.highScore ? '#FFD700' : '#C0C0C0';
            ctx.beginPath();
            ctx.arc(CANVAS_WIDTH / 2 - 120, 600, 30, 0, Math.PI * 2);
            ctx.fill();
        }
        
        // Retry button
        ctx.fillStyle = '#4CAF50';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 800, 300, 80);
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 40px Arial';
        ctx.fillText('RETRY', CANVAS_WIDTH / 2, 850);
        
        // Menu button
        ctx.fillStyle = '#FF5722';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 920, 300, 80);
        ctx.fillStyle = '#fff';
        ctx.fillText('MENU', CANVAS_WIDTH / 2, 970);
        
        // Scores button
        ctx.fillStyle = '#2196F3';
        ctx.fillRect(CANVAS_WIDTH / 2 - 150, 1040, 300, 80);
        ctx.fillStyle = '#fff';
        ctx.fillText('SCORES', CANVAS_WIDTH / 2, 1090);
    }
    
    function renderLeaderboardScreen() {
        // Semi-transparent overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Leaderboard panel
        ctx.fillStyle = '#fff';
        ctx.fillRect(CANVAS_WIDTH / 2 - 300, 300, 600, 800);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 3;
        ctx.strokeRect(CANVAS_WIDTH / 2 - 300, 300, 600, 800);
        
        // Title
        ctx.fillStyle = '#333';
        ctx.font = 'bold 60px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('LEADERBOARD', CANVAS_WIDTH / 2, 380);
        
        // High score display
        ctx.font = 'bold 50px Arial';
        ctx.fillText('Best Score', CANVAS_WIDTH / 2, 500);
        ctx.font = 'bold 80px Arial';
        ctx.fillStyle = '#FFD700';
        ctx.fillText(GameState.highScore.toString(), CANVAS_WIDTH / 2, 600);
        
        // Current score
        ctx.fillStyle = '#333';
        ctx.font = 'bold 40px Arial';
        ctx.fillText('Last Score: ' + GameState.score, CANVAS_WIDTH / 2, 700);
        
        // OK button
        ctx.fillStyle = '#4CAF50';
        ctx.fillRect(CANVAS_WIDTH / 2 - 100, 900, 200, 80);
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 40px Arial';
        ctx.fillText('OK', CANVAS_WIDTH / 2, 950);
    }
    
    function renderBird(x, y) {
        // Simple bird representation
        ctx.fillStyle = '#FFD700';
        ctx.beginPath();
        ctx.arc(x, y, BIRD_SIZE / 2, 0, Math.PI * 2);
        ctx.fill();
        
        // Bird outline
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Eye
        ctx.fillStyle = '#000';
        ctx.beginPath();
        ctx.arc(x + 8, y - 5, 4, 0, Math.PI * 2);
        ctx.fill();
        
        // Beak
        ctx.fillStyle = '#FF8C00';
        ctx.beginPath();
        ctx.moveTo(x + BIRD_SIZE / 2, y);
        ctx.lineTo(x + BIRD_SIZE / 2 + 10, y - 3);
        ctx.lineTo(x + BIRD_SIZE / 2 + 10, y + 3);
        ctx.closePath();
        ctx.fill();
    }
    
    function handleInput(inputType, x, y) {
        if (inputType === 'tap' || inputType === 'click') {
            switch (GameState.gameStatus) {
                case 'start':
                    // Check Play button
                    if (x >= CANVAS_WIDTH / 2 - 150 && x <= CANVAS_WIDTH / 2 + 150 &&
                        y >= 800 && y <= 880) {
                        game_state.startGame();
                    }
                    // Check Scores button
                    else if (x >= CANVAS_WIDTH / 2 - 150 && x <= CANVAS_WIDTH / 2 + 150 &&
                             y >= 920 && y <= 1000) {
                        game_state.showLeaderboard();
                    }
                    break;
                    
                case 'playing':
                    // Any tap makes bird flap
                    bird_physics.flap();
                    break;
                    
                case 'game_over':
                    // Check Retry button
                    if (x >= CANVAS_WIDTH / 2 - 150 && x <= CANVAS_WIDTH / 2 + 150 &&
                        y >= 800 && y <= 880) {
                        game_state.retry();
                    }
                    // Check Menu button
                    else if (x >= CANVAS_WIDTH / 2 - 150 && x <= CANVAS_WIDTH / 2 + 150 &&
                             y >= 920 && y <= 1000) {
                        game_state.returnToMenu();
                    }
                    // Check Scores button
                    else if (x >= CANVAS_WIDTH / 2 - 150 && x <= CANVAS_WIDTH / 2 + 150 &&
                             y >= 1040 && y <= 1120) {
                        game_state.showLeaderboard();
                    }
                    break;
                    
                case 'leaderboard':
                    // Check OK button
                    if (x >= CANVAS_WIDTH / 2 - 100 && x <= CANVAS_WIDTH / 2 + 100 &&
                        y >= 900 && y <= 980) {
                        game_state.closeLeaderboard();
                    }
                    break;
            }
        }
    }
    
    return {
        init,
        render,
        handleInput
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

// Game loop
let lastTime = 0;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update functions in order
    bird_physics.update();
    pipe_system.update();
    
    // Render functions in order
    ui_screens.render();
    
    // Show appropriate screen
    switch (GameState.gameStatus) {
        case 'start':
            showScreen('start_screen');
            break;
        case 'playing':
            showScreen('gameplay');
            break;
        case 'game_over':
            showScreen('gameplay'); // Keep gameplay visible with overlay
            break;
        case 'leaderboard':
            showScreen('leaderboard');
            break;
    }
    
    requestAnimationFrame(gameLoop);
}

// State transition functions
function startGame() {
    game_state.startGame();
    showScreen('gameplay');
}

function gameOver() {
    game_state.endGame();
    showScreen('gameplay');
}

function retry() {
    game_state.retry();
    showScreen('gameplay');
}

function returnToMenu() {
    game_state.returnToMenu();
    showScreen('start_screen');
}

function showLeaderboard() {
    game_state.showLeaderboard();
    showScreen('leaderboard');
}

function closeLeaderboard() {
    game_state.closeLeaderboard();
    if (GameState.previousScreen === 'start') {
        showScreen('start_screen');
    } else {
        showScreen('gameplay');
    }
}

// Input handlers
function setupInputHandlers() {
    // Canvas click/touch handlers
    const canvas = document.getElementById('gameCanvas');
    
    function getCanvasCoordinates(event) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = CANVAS_WIDTH / rect.width;
        const scaleY = CANVAS_HEIGHT / rect.height;
        
        let clientX, clientY;
        if (event.touches && event.touches[0]) {
            clientX = event.touches[0].clientX;
            clientY = event.touches[0].clientY;
        } else {
            clientX = event.clientX;
            clientY = event.clientY;
        }
        
        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY
        };
    }
    
    canvas.addEventListener('click', function(event) {
        const coords = getCanvasCoordinates(event);
        ui_screens.handleInput('click', coords.x, coords.y);
    });
    
    canvas.addEventListener('touchstart', function(event) {
        event.preventDefault();
        const coords = getCanvasCoordinates(event);
        ui_screens.handleInput('tap', coords.x, coords.y);
    });
    
    // Button handlers
    document.getElementById('btn_play').addEventListener('click', startGame);
    document.getElementById('btn_leaderboard').addEventListener('click', showLeaderboard);
    document.getElementById('btn_retry').addEventListener('click', retry);
    document.getElementById('btn_menu').addEventListener('click', returnToMenu);
    document.getElementById('btn_scores').addEventListener('click', showLeaderboard);
    document.getElementById('btn_ok').addEventListener('click', closeLeaderboard);
    
    // Keyboard handler for spacebar
    document.addEventListener('keydown', function(event) {
        if (event.code === 'Space') {
            event.preventDefault();
            if (GameState.gameStatus === 'playing') {
                bird_physics.flap();
            }
        }
    });
}

// Initialize game
function initGame() {
    // Initialize modules in order
    game_state.init();
    bird_physics.init();
    pipe_system.init();
    ui_screens.init();
    
    // Setup input handlers
    setupInputHandlers();
    
    // Show initial screen
    showScreen('start_screen');
    
    // Start game loop
    requestAnimationFrame(gameLoop);
}

// Start the game when page loads
document.addEventListener('DOMContentLoaded', initGame);