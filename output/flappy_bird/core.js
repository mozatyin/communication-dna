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

// Shared State
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
        GameState.highScore = parseInt(localStorage.getItem('flappyHighScore') || '0');
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
        }
    }
    
    function endGame() {
        if (GameState.gameStatus === 'playing') {
            GameState.gameStatus = 'game_over';
            if (GameState.score > GameState.highScore) {
                GameState.highScore = GameState.score;
                localStorage.setItem('flappyHighScore', GameState.highScore.toString());
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
            EventBus.emit('SHOW_LEADERBOARD');
        }
    }
    
    function closeLeaderboard() {
        if (GameState.gameStatus === 'leaderboard') {
            GameState.gameStatus = GameState.previousScreen;
            EventBus.emit('CLOSE_LEADERBOARD');
        }
    }
    
    function retry() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'playing';
            GameState.score = 0;
            EventBus.emit('RETRY');
        }
    }
    
    function returnToMenu() {
        if (GameState.gameStatus === 'game_over') {
            GameState.gameStatus = 'start';
            EventBus.emit('RETURN_MENU');
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
        if (GameState.birdY >= CANVAS_HEIGHT - 240 - BIRD_SIZE) {
            EventBus.emit('BIRD_COLLISION', {});
            return;
        }

        if (GameState.birdY <= 0) {
            EventBus.emit('BIRD_COLLISION', {});
            return;
        }

        for (let pipe of GameState.pipes) {
            if (checkBirdPipeCollision(pipe)) {
                EventBus.emit('BIRD_COLLISION', {});
                return;
            }
        }
    }

    function checkBirdPipeCollision(pipe) {
        const birdLeft = GameState.birdX;
        const birdRight = GameState.birdX + BIRD_SIZE;
        const birdTop = GameState.birdY;
        const birdBottom = GameState.birdY + BIRD_SIZE;

        const pipeLeft = pipe.x;
        const pipeRight = pipe.x + PIPE_WIDTH;
        const topPipeBottom = pipe.gapY;
        const bottomPipeTop = pipe.gapY + PIPE_GAP;

        if (birdRight > pipeLeft && birdLeft < pipeRight) {
            if (birdTop < topPipeBottom) {
                return true;
            }
            if (birdBottom > bottomPipeTop) {
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

// Module: pipe_system
const pipe_system = (function() {
    let lastPipeX = CANVAS_WIDTH;
    let pipeSpacing = 300;
    let scoredPipes = new Set();

    function init() {
        GameState.pipes = [];
        lastPipeX = CANVAS_WIDTH;
        scoredPipes.clear();
        
        EventBus.on('GAME_START', reset);
        EventBus.on('RETRY', reset);
    }

    function update() {
        if (GameState.gameStatus !== 'playing') return;

        for (let i = GameState.pipes.length - 1; i >= 0; i--) {
            GameState.pipes[i].x -= PIPE_SPEED;
            
            if (GameState.pipes[i].x + PIPE_WIDTH < 0) {
                const pipeId = GameState.pipes[i].id;
                scoredPipes.delete(pipeId);
                GameState.pipes.splice(i, 1);
            }
        }

        if (GameState.pipes.length === 0 || lastPipeX - GameState.pipes[GameState.pipes.length - 1].x >= pipeSpacing) {
            generatePipe();
        }

        checkScoring();
    }

    function generatePipe() {
        const gapY = Math.random() * (CANVAS_HEIGHT - PIPE_GAP - 400) + 200;
        const pipeId = Date.now() + Math.random();
        
        const newPipe = {
            id: pipeId,
            x: CANVAS_WIDTH,
            gapY: gapY,
            topHeight: gapY,
            bottomY: gapY + PIPE_GAP,
            bottomHeight: CANVAS_HEIGHT - (gapY + PIPE_GAP)
        };
        
        GameState.pipes.push(newPipe);
        lastPipeX = CANVAS_WIDTH;
    }

    function checkScoring() {
        for (let pipe of GameState.pipes) {
            if (!scoredPipes.has(pipe.id) && 
                GameState.birdX > pipe.x + PIPE_WIDTH/2) {
                
                scoredPipes.add(pipe.id);
                EventBus.emit('BIRD_SCORED', { points: 1 });
            }
        }
    }

    function reset() {
        GameState.pipes = [];
        lastPipeX = CANVAS_WIDTH;
        scoredPipes.clear();
    }

    function getPipes() {
        return GameState.pipes;
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
        if (canvas) {
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
    }
    
    function render() {
        if (!canvas || !ctx) return;
        
        ctx.fillStyle = '#70C5CE';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
        
        if (GameState.gameStatus === 'playing') {
            renderGameplayScreen();
        }
    }
    
    function renderGameplayScreen() {
        // Render pipes
        ctx.fillStyle = '#228B22';
        GameState.pipes.forEach(pipe => {
            ctx.fillRect(pipe.x, 0, PIPE_WIDTH, pipe.topHeight);
            ctx.fillRect(pipe.x, pipe.topHeight + PIPE_GAP, PIPE_WIDTH, CANVAS_HEIGHT - pipe.topHeight - PIPE_GAP - 240);
        });
        
        // Render bird
        renderBird(GameState.birdX, GameState.birdY, GameState.birdVelocityY);
        
        // Ground
        ctx.fillStyle = '#DEB887';
        ctx.fillRect(0, CANVAS_HEIGHT - 240, CANVAS_WIDTH, 240);
        
        // Score
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 96px Arial';
        ctx.textAlign = 'center';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 4;
        ctx.strokeText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
        ctx.fillText(GameState.score.toString(), CANVAS_WIDTH / 2, 150);
    }
    
    function renderBird(x, y, velocityY) {
        ctx.save();
        ctx.translate(x + BIRD_SIZE/2, y + BIRD_SIZE/2);
        
        let rotation = Math.max(-0.5, Math.min(0.5, velocityY * 0.05));
        ctx.rotate(rotation);
        
        ctx.fillStyle = '#FFFF00';
        ctx.beginPath();
        ctx.arc(0, 0, BIRD_SIZE / 2, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        ctx.fillStyle = '#000000';
        ctx.beginPath();
        ctx.arc(8, -5, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.fillStyle = '#FFA500';
        ctx.beginPath();
        ctx.moveTo(15, 0);
        ctx.lineTo(25, -3);
        ctx.lineTo(25, 3);
        ctx.closePath();
        ctx.fill();
        
        ctx.restore();
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
function showScreen(id) {
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.style.display = 'none';
    });
    
    const targetScreen = document.getElementById(id);
    if (targetScreen) {
        targetScreen.style.display = 'block';
    }
    
    // Update UI elements
    updateUI();
}

function updateUI() {
    const scoreValue = document.getElementById('score_value');
    const bestValue = document.getElementById('best_value');
    const highScoreDisplay = document.getElementById('high_score_display');
    const lastScoreDisplay = document.getElementById('last_score_display');
    
    if (scoreValue) scoreValue.textContent = GameState.score;
    if (bestValue) bestValue.textContent = GameState.highScore;
    if (highScoreDisplay) highScoreDisplay.textContent = GameState.highScore;
    if (lastScoreDisplay) lastScoreDisplay.textContent = GameState.score;
}

// State transition functions
function startGame() {
    game_state.startGame();
    showScreen('gameplay');
}

function gameOver() {
    showScreen('game_over');
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
    if (GameState.gameStatus === 'start') {
        showScreen('start_screen');
    } else if (GameState.gameStatus === 'game_over') {
        showScreen('game_over');
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
    
    // Check for game over transition
    if (GameState.gameStatus === 'game_over' && document.getElementById('gameplay').style.display === 'block') {
        gameOver();
    }
    
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    }
}

// Event listeners for state changes
EventBus.on('GAME_START', () => {
    requestAnimationFrame(gameLoop);
});

EventBus.on('RETRY', () => {
    requestAnimationFrame(gameLoop);
});

// Input handlers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modules
    game_state.init();
    bird_physics.init();
    pipe_system.init();
    ui_screens.init();
    
    // Set up button event listeners
    const btnPlay = document.getElementById('btn_play');
    const btnLeaderboard = document.getElementById('btn_leaderboard');
    const btnRestart = document.getElementById('btn_restart');
    const btnLeaderboardGo = document.getElementById('btn_leaderboard_go');
    const btnClose = document.getElementById('btn_close');
    
    if (btnPlay) btnPlay.addEventListener('click', startGame);
    if (btnLeaderboard) btnLeaderboard.addEventListener('click', showLeaderboard);
    if (btnRestart) btnRestart.addEventListener('click', retry);
    if (btnLeaderboardGo) btnLeaderboardGo.addEventListener('click', showLeaderboard);
    if (btnClose) btnClose.addEventListener('click', closeLeaderboard);
    
    // Keyboard input
    document.addEventListener('keydown', function(e) {
        if (e.code === 'Space' && GameState.gameStatus === 'playing') {
            e.preventDefault();
            bird_physics.flap();
        }
    });
    
    // Show initial screen
    showScreen('start_screen');
});