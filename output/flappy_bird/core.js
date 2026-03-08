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

// Global constants
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const GRAVITY = 0.6;
const FLAP_STRENGTH = -12;
const PIPE_SPEED = 3;
const PIPE_GAP = 200;
const BIRD_SIZE = 40;
const PIPE_WIDTH = 80;

// Shared state
const GameState = {
    gameStatus: 'start',
    score: 0,
    highScore: 0,
    birdX: 200,
    birdY: 960,
    birdVelocityY: 0,
    pipes: [],
    previousScreen: 'start'
};

// Module: game_state
const game_state = (function() {
    function init() {
        GameState.gameStatus = 'start';
        GameState.score = 0;
        GameState.highScore = parseInt(localStorage.getItem('flappyBirdHighScore') || '0');
        GameState.birdX = 200;
        GameState.birdY = 960;
        GameState.birdVelocityY = 0;
        GameState.pipes = [];
        GameState.previousScreen = 'start';
        
        // Listen for collision events
        EventBus.on('BIRD_COLLISION', () => {
            if (GameState.gameStatus === 'playing') {
                endGame();
            }
        });
        
        EventBus.on('BIRD_SCORED', (payload) => {
            if (GameState.gameStatus === 'playing') {
                addScore(payload.points);
            }
        });
    }
    
    function startGame() {
        if (GameState.gameStatus === 'start') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            EventBus.emit('GAME_START');
            showScreen('gameplay');
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
                localStorage.setItem('flappyBirdHighScore', GameState.highScore.toString());
            }
            
            // Update game over screen with current scores
            document.getElementById('score_value').textContent = GameState.score;
            document.getElementById('best_value').textContent = GameState.highScore;
            
            showScreen('game_over');
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
            document.getElementById('score_list').textContent = 'Best Score: ' + GameState.highScore;
            EventBus.emit('SHOW_LEADERBOARD');
            showScreen('leaderboard');
        }
    }
    
    function closeLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = GameState.previousScreen;
            EventBus.emit('CLOSE_LEADERBOARD');
            showScreen(GameState.previousScreen === 'start' ? 'start_screen' : 'game_over');
        }
    }
    
    function retry() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            EventBus.emit('RETRY');
            showScreen('gameplay');
        }
    }
    
    function returnToMenu() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'start';
            EventBus.emit('RETURN_MENU');
            showScreen('start_screen');
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

// Module: bird_physics
const bird_physics = (function() {
    function init() {
        GameState.birdX = 200;
        GameState.birdY = 960;
        GameState.birdVelocityY = 0;
        
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
        
        GameState.birdVelocityY += GRAVITY;
        GameState.birdY += GameState.birdVelocityY;
        
        checkCollisions();
    }
    
    function reset() {
        GameState.birdX = 200;
        GameState.birdY = 960;
        GameState.birdVelocityY = 0;
    }
    
    function checkCollisions() {
        const birdLeft = GameState.birdX - BIRD_SIZE / 2;
        const birdRight = GameState.birdX + BIRD_SIZE / 2;
        const birdTop = GameState.birdY - BIRD_SIZE / 2;
        const birdBottom = GameState.birdY + BIRD_SIZE / 2;
        
        if (birdBottom >= CANVAS_HEIGHT - 200) {
            EventBus.emit('BIRD_COLLISION', {});
            return;
        }
        
        if (birdTop <= 0) {
            EventBus.emit('BIRD_COLLISION', {});
            return;
        }
        
        for (let pipe of GameState.pipes) {
            const pipeLeft = pipe.x;
            const pipeRight = pipe.x + PIPE_WIDTH;
            
            if (birdLeft < pipeRight && birdRight > pipeLeft && 
                birdTop < pipe.topHeight) {
                EventBus.emit('BIRD_COLLISION', {});
                return;
            }
            
            const bottomPipeTop = pipe.topHeight + PIPE_GAP;
            if (birdLeft < pipeRight && birdRight > pipeLeft && 
                birdBottom > bottomPipeTop) {
                EventBus.emit('BIRD_COLLISION', {});
                return;
            }
        }
    }
    
    return {
        init,
        flap,
        update,
        reset
    };
})();

// Module: pipe_system
const pipe_system = (function() {
    let pipes = [];
    let pipeSpawnTimer = 0;
    const PIPE_SPAWN_INTERVAL = 120;
    
    function init() {
        pipes = [];
        pipeSpawnTimer = 0;
        GameState.pipes = pipes;
        
        EventBus.on('GAME_START', reset);
        EventBus.on('RETRY', reset);
    }
    
    function update() {
        if (GameState.gameStatus !== 'playing') return;
        
        for (let i = pipes.length - 1; i >= 0; i--) {
            pipes[i].x -= PIPE_SPEED;
            
            if (pipes[i].x + PIPE_WIDTH < 0) {
                pipes.splice(i, 1);
            }
        }
        
        pipeSpawnTimer++;
        if (pipeSpawnTimer >= PIPE_SPAWN_INTERVAL) {
            spawnPipe();
            pipeSpawnTimer = 0;
        }
        
        checkScoring();
        GameState.pipes = pipes;
    }
    
    function spawnPipe() {
        const minGapY = 150;
        const maxGapY = CANVAS_HEIGHT - 350;
        const gapCenterY = minGapY + Math.random() * (maxGapY - minGapY);
        
        const pipe = {
            x: CANVAS_WIDTH,
            gapCenterY: gapCenterY,
            topHeight: gapCenterY - PIPE_GAP / 2,
            bottomY: gapCenterY + PIPE_GAP / 2,
            bottomHeight: CANVAS_HEIGHT - (gapCenterY + PIPE_GAP / 2),
            width: PIPE_WIDTH,
            scored: false
        };
        
        pipes.push(pipe);
    }
    
    function checkScoring() {
        const birdX = GameState.birdX;
        
        for (let pipe of pipes) {
            if (!pipe.scored && 
                birdX > pipe.x + pipe.width / 2 && 
                birdX - BIRD_SIZE / 2 < pipe.x + pipe.width) {
                
                pipe.scored = true;
                EventBus.emit('BIRD_SCORED', { points: 1 });
            }
        }
    }
    
    function reset() {
        pipes = [];
        pipeSpawnTimer = 0;
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
const ui_screens = (function() {
    let canvas;
    let ctx;
    
    function init() {
        canvas = document.getElementById('gameCanvas');
        ctx = canvas.getContext('2d');
        
        canvas.addEventListener('click', function(e) {
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (CANVAS_WIDTH / rect.width);
            const y = (e.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
            handleInput('click', x, y);
        });
        
        canvas.addEventListener('touchstart', function(e) {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const touch = e.touches[0];
            const x = (touch.clientX - rect.left) * (CANVAS_WIDTH / rect.width);
            const y = (touch.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
            handleInput('tap', x, y);
        });
    }
    
    function render() {
        if (GameState.gameStatus !== 'playing') return;
        
        ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Sky background
        ctx.fillStyle = '#70C5CE';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        // Draw pipes
        ctx.fillStyle = '#228B22';
        for (let pipe of GameState.pipes) {
            ctx.fillRect(pipe.x, 0, PIPE_WIDTH, pipe.topHeight);
            ctx.fillRect(pipe.x, pipe.topHeight + PIPE_GAP, PIPE_WIDTH, CANVAS_HEIGHT - pipe.topHeight - PIPE_GAP - 200);
        }
        
        // Ground
        ctx.fillStyle = '#DED895';
        ctx.fillRect(0, CANVAS_HEIGHT - 200, CANVAS_WIDTH, 200);
        
        // Bird
        ctx.fillStyle = '#FFD700';
        ctx.fillRect(GameState.birdX - BIRD_SIZE / 2, GameState.birdY - BIRD_SIZE / 2, BIRD_SIZE, BIRD_SIZE);
        
        // Score
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 96px Arial';
        ctx.textAlign = 'center';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 4;
        ctx.strokeText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
        ctx.fillText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
    }
    
    function handleInput(inputType, x, y) {
        if (GameState.gameStatus === 'playing') {
            bird_physics.flap();
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
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.style.display = 'none';
    });
    
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.style.display = 'block';
    }
}

// Game loop
let lastTime = 0;
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    
    // Update modules
    bird_physics.update();
    pipe_system.update();
    
    // Render
    ui_screens.render();
    
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    }
}

// Input handlers
document.addEventListener('keydown', function(e) {
    if (e.code === 'Space' && GameState.gameStatus === 'playing') {
        e.preventDefault();
        bird_physics.flap();
    }
});

// Initialize game
function initGame() {
    // Initialize modules in order
    game_state.init();
    bird_physics.init();
    pipe_system.init();
    ui_screens.init();
    
    // Set up button event listeners
    document.getElementById('btn_play').addEventListener('click', () => {
        game_state.startGame();
        requestAnimationFrame(gameLoop);
    });
    
    document.getElementById('btn_leaderboard').addEventListener('click', () => {
        game_state.showLeaderboard();
    });
    
    document.getElementById('btn_restart').addEventListener('click', () => {
        game_state.retry();
        requestAnimationFrame(gameLoop);
    });
    
    document.getElementById('btn_leaderboard_go').addEventListener('click', () => {
        game_state.showLeaderboard();
    });
    
    document.getElementById('btn_close').addEventListener('click', () => {
        game_state.closeLeaderboard();
    });
    
    // Show initial screen
    showScreen('start_screen');
}

// Start the game when page loads
window.addEventListener('load', initGame);