const API = '/api/exam';

let state = {
    sessionId: null,
    questions: [],
    currentIndex: 0,
    answers: {},
    startTime: null,
    timerInterval: null,
    timeLimit: 30 * 60,
};

function showView(id) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById(id).classList.remove('hidden');
}

async function startExam(e) {
    e.preventDefault();
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const type = document.getElementById('exam-type').value;

    if (!name || !email) return;

    const btn = e.target.querySelector('button');
    btn.disabled = true;
    btn.textContent = 'Loading...';

    try {
        const resp = await fetch(`${API}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidate_name: name,
                candidate_email: email,
                exam_type: type,
            }),
        });
        const data = await resp.json();
        state.sessionId = data.session_id;
        state.questions = data.questions;
        state.currentIndex = 0;
        state.answers = {};
        startTimer();
        showView('exam-view');
        renderQuestion();
    } catch (err) {
        alert('Failed to start exam. Please try again.');
        btn.disabled = false;
        btn.textContent = 'Start Assessment';
    }
}

function startTimer() {
    state.startTime = Date.now();
    const timerEl = document.getElementById('timer');
    timerEl.classList.remove('hidden');

    state.timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
        const remaining = Math.max(0, state.timeLimit - elapsed);
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

        timerEl.classList.remove('warning', 'danger');
        if (remaining <= 60) timerEl.classList.add('danger');
        else if (remaining <= 300) timerEl.classList.add('warning');

        if (remaining <= 0) {
            clearInterval(state.timerInterval);
            submitExam();
        }
    }, 1000);
}

function renderQuestion() {
    const q = state.questions[state.currentIndex];
    const total = state.questions.length;
    const idx = state.currentIndex;

    document.getElementById('progress-fill').style.width = `${((idx + 1) / total) * 100}%`;
    document.getElementById('question-count').textContent = `${idx + 1} / ${total}`;

    const dimNames = {
        jumping_thinking: 'Jumping Thinking',
        pdca_thinking: 'PDCA Thinking',
        ai_collaboration: 'AI Collaboration',
        critical_questioning: 'Critical Questioning',
    };
    const dims = q.type === 'mcq' ? [q.dimension] : (q.dimensions || []);
    document.getElementById('question-dimension').textContent = dims.map(d => dimNames[d] || d).join(' + ');

    document.getElementById('question-text').textContent = q.question;

    const optArea = document.getElementById('options-area');
    optArea.innerHTML = '';

    if (q.type === 'mcq') {
        q.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'option' + (state.answers[q.id] === opt.label ? ' selected' : '');
            btn.textContent = `${opt.label}) ${opt.text}`;
            btn.onclick = () => {
                state.answers[q.id] = opt.label;
                renderQuestion();
            };
            optArea.appendChild(btn);
        });
    } else {
        const textarea = document.createElement('textarea');
        textarea.className = 'scenario-input';
        textarea.placeholder = 'Write your response here (200-400 words recommended)...';
        textarea.value = state.answers[q.id] || '';
        textarea.oninput = (e) => {
            state.answers[q.id] = e.target.value;
            const words = e.target.value.trim().split(/\s+/).filter(w => w).length;
            document.getElementById('word-count').textContent = `${words} words`;
        };
        optArea.appendChild(textarea);

        const wc = document.createElement('div');
        wc.id = 'word-count';
        wc.className = 'word-count';
        const currentWords = (state.answers[q.id] || '').trim().split(/\s+/).filter(w => w).length;
        wc.textContent = `${currentWords} words`;
        optArea.appendChild(wc);
    }

    document.getElementById('btn-prev').classList.toggle('hidden', idx === 0);
    const nextBtn = document.getElementById('btn-next');
    if (idx === total - 1) {
        nextBtn.textContent = 'Submit';
        nextBtn.onclick = submitExam;
    } else {
        nextBtn.textContent = 'Next';
        nextBtn.onclick = nextQuestion;
    }
}

function nextQuestion() {
    if (state.currentIndex < state.questions.length - 1) {
        state.currentIndex++;
        renderQuestion();
    }
}

function prevQuestion() {
    if (state.currentIndex > 0) {
        state.currentIndex--;
        renderQuestion();
    }
}

async function submitExam() {
    clearInterval(state.timerInterval);
    document.getElementById('timer').classList.add('hidden');
    showView('loading-view');

    try {
        const resp = await fetch(`${API}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                answers: state.answers,
            }),
        });
        const result = await resp.json();
        renderResult(result);
    } catch (err) {
        alert('Failed to submit. Please try again.');
        showView('exam-view');
    }
}

function renderResult(result) {
    showView('result-view');

    const statusEl = document.getElementById('result-status');
    statusEl.textContent = result.passed ? 'PASSED' : 'NOT PASSED';
    statusEl.className = result.passed ? 'result-pass' : 'result-fail';

    document.getElementById('result-score').textContent = `${result.total_score} / 20 points`;

    const dimConfig = [
        { key: 'jumping_thinking', label: 'Jumping Thinking', cls: 'jt', max: 8 },
        { key: 'pdca_thinking', label: 'PDCA Thinking', cls: 'pdca', max: 8 },
        { key: 'ai_collaboration', label: 'AI Collaboration', cls: 'ai', max: 8 },
        { key: 'critical_questioning', label: 'Critical Questioning', cls: 'cq', max: 8 },
    ];

    const barsEl = document.getElementById('dimension-bars');
    barsEl.innerHTML = '';

    dimConfig.forEach(dim => {
        const score = (result.dimension_scores || {})[dim.key] || 0;
        const pct = Math.min(100, (score / dim.max) * 100);

        const row = document.createElement('div');
        row.className = 'dim-row';
        row.innerHTML = `
            <div class="dim-label">
                <span>${dim.label}</span>
                <span>${score.toFixed(1)}</span>
            </div>
            <div class="dim-bar">
                <div class="dim-fill ${dim.cls}" style="width: ${pct}%"></div>
            </div>
        `;
        barsEl.appendChild(row);
    });

    const feedbackEl = document.getElementById('feedback-text');
    feedbackEl.textContent = result.llm_feedback || 'No detailed feedback available.';
}

document.getElementById('start-form').addEventListener('submit', startExam);
document.getElementById('btn-prev').addEventListener('click', prevQuestion);
