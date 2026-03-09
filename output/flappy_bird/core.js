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
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const GRAVITY = 0.6;
const FLAP_STRENGTH = -12;
const PIPE_SPEED = 3;
const PIPE_GAP = 200;
const BIRD_SIZE = 40;
const PIPE_WIDTH = 80;

// Shared GameState
const GameState = {
    gameStatus: 'start',
    score: 0,
    highScore: parseInt(localStorage.getItem('flappyBirdHighScore') || '0'),
    birdX: 200,
    birdY: 960,
    birdVelocityY: 0,
    pipes: [],
    previousScreen: 'start'
};

// Module: game_state
const GameStateModule = (function() {
    function init() {
        // Load high score from localStorage
        GameState.highScore = parseInt(localStorage.getItem('flappyBirdHighScore') || '0');
        
        // Listen for events from other modules
        EventBus.on('BIRD_COLLISION', handleBirdCollision);
        EventBus.on('BIRD_SCORED', handleBirdScored);
    }
    
    function startGame() {
        if (GameState.gameStatus === 'start') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            EventBus.emit('GAME_START', {});
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            
            // Update high score if current score is higher
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
                localStorage.setItem('flappyBirdHighScore', GameState.highScore.toString());
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
            EventBus.emit('SHOW_LEADERBOARD', {});
        }
    }
    
    function closeLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = GameState.previousScreen;
            EventBus.emit('CLOSE_LEADERBOARD', {});
        }
    }
    
    function retry() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            EventBus.emit('RETRY', {});
        }
    }
    
    function returnToMenu() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'start';
            EventBus.emit('RETURN_MENU', {});
        }
    }
    
    // Event handlers for incoming events
    function handleBirdCollision() {
        endGame();
    }
    
    function handleBirdScored(payload) {
        addScore(payload.points);
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

// Module: bird_physics
const BirdPhysics = (function() {
    function init() {
        // Initialize bird at starting position
        GameState.birdX = 200;
        GameState.birdY = 960;
        GameState.birdVelocityY = 0;
        
        // Listen for game events
        EventBus.on('GAME_START', reset);
        EventBus.on('RETRY', reset);
    }
    
    function flap() {
        if (GameState.gameStatus === 'playing') {
            GameState.birdVelocityY = FLAP_STRENGTH;
        }
    }
    
    function update() {
        if (GameState.gameStatus !== 'playing') {
            return;
        }
        
        // Apply gravity
        GameState.birdVelocityY += GRAVITY;
        
        // Update position
        GameState.birdY += GameState.birdVelocityY;
        
        // Check collision with ground
        if (GameState.birdY >= CANVAS_HEIGHT - 240) { // Ground level
            EventBus.emit('BIRD_COLLISION', {});
            return;
        }
        
        // Check collision with ceiling
        if (GameState.birdY <= 0) {
            EventBus.emit('BIRD_COLLISION', {});
            return;
        }
        
        // Check collision with pipes
        checkPipeCollisions();
    }
    
    function checkPipeCollisions() {
        const birdLeft = GameState.birdX - BIRD_SIZE / 2;
        const birdRight = GameState.birdX + BIRD_SIZE / 2;
        const birdTop = GameState.birdY - BIRD_SIZE / 2;
        const birdBottom = GameState.birdY + BIRD_SIZE / 2;
        
        for (let i = 0; i < GameState.pipes.length; i++) {
            const pipe = GameState.pipes[i];
            const pipeLeft = pipe.x;
            const pipeRight = pipe.x + PIPE_WIDTH;
            
            // Check if bird is horizontally aligned with pipe
            if (birdRight > pipeLeft && birdLeft < pipeRight) {
                // Check collision with top pipe
                if (birdTop < pipe.topHeight) {
                    EventBus.emit('BIRD_COLLISION', {});
                    return;
                }
                
                // Check collision with bottom pipe
                const bottomPipeTop = pipe.topHeight + PIPE_GAP;
                if (birdBottom > bottomPipeTop) {
                    EventBus.emit('BIRD_COLLISION', {});
                    return;
                }
            }
        }
    }
    
    function reset() {
        GameState.birdX = 200;
        GameState.birdY = 960;
        GameState.birdVelocityY = 0;
    }
    
    return {
        init,
        flap,
        update,
        reset
    };
})();

// Module: pipe_system
const PipeSystem = (function() {
    let pipes = [];
    let pipeSpawnTimer = 0;
    let pipeSpawnInterval = 180; // frames between pipe spawns
    let scoredPipes = new Set(); // track which pipes have been scored
    
    function init() {
        pipes = [];
        pipeSpawnTimer = 0;
        scoredPipes.clear();
        GameState.pipes = pipes;
        
        // Listen for game events
        EventBus.on('GAME_START', reset);
        EventBus.on('RETRY', reset);
    }
    
    function update() {
        if (GameState.gameStatus !== 'playing') {
            return;
        }
        
        // Move existing pipes
        for (let i = pipes.length - 1; i >= 0; i--) {
            const pipe = pipes[i];
            pipe.x -= PIPE_SPEED;
            
            // Remove pipes that have moved off screen
            if (pipe.x + PIPE_WIDTH < 0) {
                pipes.splice(i, 1);
                scoredPipes.delete(pipe.id);
            }
        }
        
        // Spawn new pipes
        pipeSpawnTimer++;
        if (pipeSpawnTimer >= pipeSpawnInterval) {
            spawnPipe();
            pipeSpawnTimer = 0;
        }
        
        // Check for scoring
        checkScoring();
        
        // Update shared state
        GameState.pipes = pipes;
    }
    
    function spawnPipe() {
        // Random gap position - keep gap away from top and bottom edges
        const minGapY = 100;
        const maxGapY = CANVAS_HEIGHT - 400 - PIPE_GAP;
        const gapY = Math.random() * (maxGapY - minGapY) + minGapY;
        
        const pipeId = Date.now() + Math.random(); // unique ID for scoring tracking
        
        const pipe = {
            id: pipeId,
            x: CANVAS_WIDTH,
            gapY: gapY,
            topHeight: gapY,
            bottomY: gapY + PIPE_GAP,
            bottomHeight: CANVAS_HEIGHT - (gapY + PIPE_GAP)
        };
        
        pipes.push(pipe);
    }
    
    function checkScoring() {
        const birdCenterX = GameState.birdX;
        
        for (const pipe of pipes) {
            // Check if bird has passed through pipe gap center
            if (!scoredPipes.has(pipe.id)) {
                const pipeCenterX = pipe.x + PIPE_WIDTH / 2;
                
                // Bird has passed the center of the pipe
                if (birdCenterX > pipeCenterX) {
                    // Mark this pipe as scored
                    scoredPipes.add(pipe.id);
                    
                    // Emit scoring event
                    EventBus.emit('BIRD_SCORED', { points: 1 });
                }
            }
        }
    }
    
    function reset() {
        pipes = [];
        pipeSpawnTimer = 0;
        scoredPipes.clear();
        GameState.pipes = pipes;
    }
    
    function getPipes() {
        return pipes;
    }
    
    return {
        init,
        update,
        reset,
        getPipes
    };
})();

// Module: ui_screens
const UIScreens = (function() {
    let canvas;
    let ctx;
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        if (canvas) {
            ctx = canvas.getContext('2d');
            
            // Set up input event listeners
            canvas.addEventListener('click', handleCanvasClick);
            canvas.addEventListener('touchstart', handleTouchStart);
            
            // Prevent default touch behaviors
            canvas.addEventListener('touchmove', function(e) { e.preventDefault(); });
            canvas.addEventListener('touchend', function(e) { e.preventDefault(); });
        }
    }
    
    function render() {
        if (!canvas || !ctx) return;
        
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        if (GameState.gameStatus === 'playing') {
            renderGameplayScreen();
        }
    }
    
    function renderGameplayScreen() {
        // Sky background
        ctx.fillStyle = '#70C5CE';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Ground
        ctx.fillStyle = '#DED895';
        ctx.fillRect(0, CANVAS_HEIGHT - 240, CANVAS_WIDTH, 240);
        
        // Render pipes
        ctx.fillStyle = '#228B22';
        GameState.pipes.forEach(pipe => {
            // Top pipe
            ctx.fillRect(pipe.x, 0, PIPE_WIDTH, pipe.topHeight);
            // Bottom pipe
            ctx.fillRect(pipe.x, pipe.topHeight + PIPE_GAP, PIPE_WIDTH, CANVAS_HEIGHT - pipe.topHeight - PIPE_GAP - 240);
        });
        
        // Render bird
        ctx.fillStyle = '#FFD700';
        ctx.fillRect(GameState.birdX - BIRD_SIZE / 2, GameState.birdY - BIRD_SIZE / 2, BIRD_SIZE, BIRD_SIZE);
        
        // Score display
        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 4;
        ctx.font = 'bold 96px Arial';
        ctx.textAlign = 'center';
        ctx.strokeText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
        ctx.fillText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
    }
    
    function handleCanvasClick(event) {
        const rect = canvas.getBoundingClientRect();
        const x = (event.clientX - rect.left) * (CANVAS_WIDTH / rect.width);
        const y = (event.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
        handleInput('click', x, y);
    }
    
    function handleTouchStart(event) {
        event.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const touch = event.touches[0];
        const x = (touch.clientX - rect.left) * (CANVAS_WIDTH / rect.width);
        const y = (touch.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
        handleInput('touch', x, y);
    }
    
    function handleInput(inputType, x, y) {
        if (GameState.gameStatus === 'playing') {
            // Tap anywhere to flap
            BirdPhysics.flap();
        }
    }
    
    return {
        init,
        render,
        handleInput
    };
})();

// Screen management
function showScreen(screenId) {
    // Hide all screens
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.style.display = 'none';
    });
    
    // Show target screen
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.style.display = 'block';
    }
    
    // Update UI elements based on game state
    updateUI();
}

function updateUI() {
    // Update score displays
    const scoreValue = document.getElementById('score_value');
    const bestValue = document.getElementById('best_value');
    
    if (scoreValue) scoreValue.textContent = GameState.score;
    if (bestValue) bestValue.textContent = GameState.highScore;
    
    // Update leaderboard
    const scoreList = document.getElementById('score_list');
    if (scoreList) {
        const scores = getTopScores();
        const listItems = scoreList.children;
        for (let i = 0; i < Math.min(5, listItems.length); i++) {
            listItems[i].textContent = `${i + 1}. ${scores[i] || 0}`;
        }
    }
}

function getTopScores() {
    // Simple implementation - just return high score and some decreasing values
    const scores = [GameState.highScore];
    for (let i = 1; i < 5; i++) {
        scores.push(Math.max(0, GameState.highScore - i * 10));
    }
    return scores;
}

// State transition functions
function startGame() {
    GameStateModule.startGame();
    showScreen('gameplay');
}

function gameOver() {
    showScreen('game_over');
}

function retry() {
    GameStateModule.retry();
    showScreen('gameplay');
}

function returnToMenu() {
    GameStateModule.returnToMenu();
    showScreen('start_screen');
}

function showLeaderboard() {
    GameStateModule.showLeaderboard();
    showScreen('leaderboard');
}

function closeLeaderboard() {
    GameStateModule.closeLeaderboard();
    if (GameState.previousScreen === 'start') {
        showScreen('start_screen');
    } else {
        showScreen('game_over');
    }
}

// Game loop
let lastTime = 0;
let gameLoopRunning = false;

function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update modules in order
    BirdPhysics.update();
    PipeSystem.update();
    
    // Render
    UIScreens.render();
    
    // Check for state changes
    if (GameState.gameStatus === 'game_over' && document.getElementById('gameplay').style.display === 'block') {
        gameOver();
    }
    
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    } else {
        gameLoopRunning = false;
    }
}

function startGameLoop() {
    if (!gameLoopRunning) {
        gameLoopRunning = true;
        lastTime = performance.now();
        requestAnimationFrame(gameLoop);
    }
}

// Input handlers
document.addEventListener('keydown', function(event) {
    if (event.code === 'Space' && GameState.gameStatus === 'playing') {
        event.preventDefault();
        BirdPhysics.flap();
    }
});

// Button event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Start screen buttons
    document.getElementById('btn_play').addEventListener('click', function() {
        startGame();
        startGameLoop();
    });
    
    document.getElementById('btn_leaderboard').addEventListener('click', showLeaderboard);
    
    // Game over screen buttons
    document.getElementById('btn_restart').addEventListener('click', function() {
        retry();
        startGameLoop();
    });
    
    document.getElementById('btn_leaderboard_go').addEventListener('click', showLeaderboard);
    
    // Leaderboard screen button
    document.getElementById('btn_close').addEventListener('click', closeLeaderboard);
    
    // Touch support for buttons
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function(e) {
            e.preventDefault();
            this.click();
        });
    });
    
    // Initialize modules
    GameStateModule.init();
    BirdPhysics.init();
    PipeSystem.init();
    UIScreens.init();
    
    // Show initial screen
    showScreen('start_screen');
});