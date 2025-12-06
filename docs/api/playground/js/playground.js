const endpoints = {
    health: { method: 'GET', path: '/health', description: 'System health check', body: null },
    stats: { method: 'GET', path: '/stats', description: 'Detailed statistics', body: null },
    gpus: { method: 'GET', path: '/gpus', description: 'List all GPUs', body: null },
    'gpu-detail': { method: 'GET', path: '/gpus/{hash}', description: 'Get GPU by hash', params: [{ name: 'hash', placeholder: 'abc12345' }], body: null },
    models: { method: 'GET', path: '/models', description: 'List all models', body: null },
    'model-add': { method: 'POST', path: '/model/add', description: 'Register a new model', body: { name: 'llama-70b', vram: 48000, shard: true, context_len: 8192 } },
    'model-load': { method: 'POST', path: '/model/load', description: 'Load model to GPU(s)', body: { name: 'llama-70b' } },
    'model-unload': { method: 'POST', path: '/model/unload', description: 'Unload model', body: { name: 'llama-70b' } },
    queue: { method: 'GET', path: '/queue', description: 'View request queue', body: null },
    alarms: { method: 'GET', path: '/alarms', description: 'Active alarms', body: null },
    completions: { method: 'POST', path: '/v1/completions', description: 'OpenAI-compatible text completion', body: { model: 'llama-70b', prompt: 'Hello, world!', max_tokens: 100, temperature: 0.7 } },
    chat: { method: 'POST', path: '/v1/chat/completions', description: 'OpenAI-compatible chat completion', body: { model: 'llama-70b', messages: [{ role: 'user', content: 'Hello!' }], max_tokens: 100 } },
    websocket: { method: 'WS', path: '/ws', description: 'Real-time WebSocket updates', body: null }
};
let currentEndpoint = 'health';
let ws = null;

function selectEndpoint(id) {
    currentEndpoint = id;
    const ep = endpoints[id];
    document.querySelectorAll('.endpoint').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-endpoint="${id}"]`).classList.add('active');
    document.getElementById('endpointTitle').textContent = `${ep.method} ${ep.path}`;
    let formHtml = `<p style="color: var(--text-dim); margin-bottom: 1rem;">${ep.description}</p>`;
    if (ep.params) {
        ep.params.forEach(p => {
            formHtml += `<div class="form-group"><label>${p.name}</label><input type="text" id="param_${p.name}" placeholder="${p.placeholder}"></div>`;
        });
    }
    if (ep.body) {
        formHtml += `<div class="form-group"><label>Request Body (JSON)</label><textarea id="requestBody">${JSON.stringify(ep.body, null, 2)}</textarea></div>`;
    }
    document.getElementById('requestForm').innerHTML = formHtml;
    const btn = document.getElementById('sendBtn');
    btn.textContent = ep.method === 'WS' ? (ws ? 'Disconnect' : 'Connect') : 'Send Request';
}

async function sendRequest() {
    const ep = endpoints[currentEndpoint];
    const baseUrl = document.getElementById('baseUrl').value;
    if (ep.method === 'WS') { toggleWebSocket(baseUrl); return; }
    let path = ep.path;
    if (ep.params) { ep.params.forEach(p => { path = path.replace(`{${p.name}}`, document.getElementById(`param_${p.name}`).value); }); }
    const url = baseUrl + path;
    const statusBadge = document.getElementById('statusBadge');
    const responseBody = document.getElementById('responseBody');
    statusBadge.textContent = 'Loading...';
    statusBadge.className = 'status pending';
    const start = performance.now();
    try {
        const options = { method: ep.method, headers: { 'Content-Type': 'application/json' } };
        if (ep.body) { options.body = document.getElementById('requestBody').value; }
        const response = await fetch(url, options);
        const data = await response.json();
        const latency = Math.round(performance.now() - start);
        statusBadge.textContent = response.status;
        statusBadge.className = `status ${response.ok ? 'success' : 'error'}`;
        document.getElementById('latency').textContent = `${latency}ms`;
        responseBody.innerHTML = syntaxHighlight(JSON.stringify(data, null, 2));
    } catch (err) {
        statusBadge.textContent = 'Error';
        statusBadge.className = 'status error';
        responseBody.textContent = err.message;
    }
}

function toggleWebSocket(baseUrl) {
    const btn = document.getElementById('sendBtn');
    const responseBody = document.getElementById('responseBody');
    const statusBadge = document.getElementById('statusBadge');
    if (ws) { ws.close(); ws = null; btn.textContent = 'Connect'; statusBadge.textContent = 'Disconnected'; statusBadge.className = 'status'; return; }
    const wsUrl = baseUrl.replace('http', 'ws') + '/ws';
    ws = new WebSocket(wsUrl);
    ws.onopen = () => { btn.textContent = 'Disconnect'; statusBadge.textContent = 'Connected'; statusBadge.className = 'status success'; };
    ws.onmessage = (event) => { responseBody.innerHTML = syntaxHighlight(JSON.stringify(JSON.parse(event.data), null, 2)); };
    ws.onerror = () => { statusBadge.textContent = 'Error'; statusBadge.className = 'status error'; };
    ws.onclose = () => { ws = null; btn.textContent = 'Connect'; statusBadge.textContent = 'Disconnected'; statusBadge.className = 'status'; };
}

function syntaxHighlight(json) {
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, match => {
        let cls = 'json-number';
        if (/^"/.test(match)) { cls = /:$/.test(match) ? 'json-key' : 'json-string'; }
        else if (/true|false/.test(match)) { cls = 'json-boolean'; }
        else if (/null/.test(match)) { cls = 'json-null'; }
        return `<span class="${cls}">${match}</span>`;
    });
}

document.querySelectorAll('.endpoint').forEach(el => { el.addEventListener('click', () => selectEndpoint(el.dataset.endpoint)); });
document.querySelectorAll('.tab').forEach(tab => { tab.addEventListener('click', () => { document.querySelectorAll('.tab').forEach(t => t.classList.remove('active')); tab.classList.add('active'); }); });
selectEndpoint('health');
