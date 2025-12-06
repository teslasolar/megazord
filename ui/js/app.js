// State
let clientGPU = null;
let modelRegistry = null;
let demoMode = true;
let data = { gpus: [], models: [], queue: [], alarms: [], stats: {} };

// WebGPU Detection
async function detectClientGPU() {
    if (!navigator.gpu) return null;
    try {
        const adapter = await navigator.gpu.requestAdapter();
        if (!adapter) return null;
        const info = await adapter.requestAdapterInfo();
        const device = await adapter.requestDevice();
        const limits = device.limits;
        clientGPU = {
            h: H('client-0'), idx: 0,
            name: info.device || info.description || 'WebGPU Device',
            vendor: info.vendor || 'Unknown',
            state: ST.READY,
            vram_total: Math.round((limits.maxBufferSize || 256*1024*1024) / (1024*1024)),
            vram_used: 0, temp: null, pwr: null, pwr_cap: null, util: null, isClient: true
        };
        document.getElementById('client-gpu-banner').style.display = 'flex';
        document.getElementById('client-gpu-name').textContent = clientGPU.name;
        document.getElementById('client-gpu-vram').textContent = clientGPU.vram_total > 1024 ? `~${(clientGPU.vram_total/1024).toFixed(1)} GB` : `~${clientGPU.vram_total} MB`;
        document.getElementById('client-gpu-tag').textContent = makeTag(UDT.GPU.tag_prefix, 'CL', 'Info');
        return clientGPU;
    } catch (err) { console.error('WebGPU detection failed:', err); return null; }
}

// Load model registry
async function loadModelRegistry() {
    try {
        const response = await fetch('../models/registry.json');
        if (response.ok) { modelRegistry = await response.json(); return modelRegistry; }
    } catch (err) { console.log('Registry not available'); }
    return { version: '1.0.0', tag_prefix: 'GPUCluster_MDL', models: [
        { id: 'llama-3-70b', name: 'Llama 3 70B', vram_mb: 42000, shard: true },
        { id: 'mistral-7b', name: 'Mistral 7B', vram_mb: 8000, shard: false },
        { id: 'codellama-34b', name: 'Code Llama 34B', vram_mb: 20000, shard: true },
        { id: 'phi-3-mini', name: 'Phi-3 Mini', vram_mb: 4000, shard: false }
    ]};
}

// Data generation from UDT
function createGPUFromUDT(idx, overrides = {}) {
    const vramTotal = overrides.vram_total || (24000 + Math.floor(Math.random() * 3) * 24000);
    return { h: H(idx), idx, name: overrides.name || ['NVIDIA RTX 4090', 'NVIDIA RTX 4080', 'NVIDIA A100', 'NVIDIA RTX 3090'][idx % 4],
        state: overrides.state ?? [ST.READY, ST.BUSY, ST.READY, ST.BUSY][idx % 4],
        temp: overrides.temp ?? (45 + Math.floor(Math.random() * 30)),
        pwr: overrides.pwr ?? (150 + Math.floor(Math.random() * 200)), pwr_cap: overrides.pwr_cap ?? 450,
        vram_used: overrides.vram_used ?? Math.floor(Math.random() * vramTotal * 0.7), vram_total: vramTotal,
        util: overrides.util ?? Math.floor(Math.random() * 100), models: overrides.models ?? [],
        tag: makeTag(UDT.GPU.tag_prefix, idx, 'State') };
}
function createModelFromUDT(name, vram, shard = true) {
    return { h: M(name), name, vram, shard, on_gpus: [], req_cnt: Math.floor(Math.random() * 1000),
        tag: `${UDT.Model.tag_prefix}_${name.replace(/[^a-zA-Z0-9]/g, '_')}` };
}
function createRequestFromUDT(model_h, priority = 0) {
    return { h: R(model_h), model_h, state: priority === 0 ? RS.PROCESSING : RS.QUEUED, priority,
        queued_at: new Date(Date.now() - priority * 30000).toISOString(), tok_in: 0, tok_out: 0 };
}
function createAlarmFromUDT(source_tag, cls, message, active = true) {
    return { h: H(source_tag + Date.now()), tag: source_tag, class: cls, message,
        t_raised: new Date(Date.now() - Math.random() * 600000).toISOString(),
        t_ack: null, t_clear: active ? null : new Date().toISOString(), active };
}

function generateDataFromUDT() {
    const gpuCount = clientGPU ? 3 : 4;
    const gpus = [];
    for (let i = 0; i < gpuCount; i++) gpus.push(createGPUFromUDT(i));
    if (clientGPU) gpus.unshift({ ...clientGPU, tag: makeTag(UDT.GPU.tag_prefix, 'CL', 'State'), state: ST.READY, models: [] });

    const registryModels = modelRegistry?.models || [];
    const modelDefs = registryModels.length > 0
        ? registryModels.map(m => ({ id: m.id, name: m.name || m.id, vram: m.vram_mb, shard: m.shard }))
        : [{ id: 'llama-3-70b', name: 'Llama 3 70B', vram: 42000, shard: true }, { id: 'mistral-7b', name: 'Mistral 7B', vram: 8000, shard: false },
           { id: 'codellama-34b', name: 'Code Llama 34B', vram: 20000, shard: true }, { id: 'phi-3-mini', name: 'Phi-3 Mini', vram: 4000, shard: false }];

    const models = modelDefs.slice(0, 3).map((m, i) => {
        const model = createModelFromUDT(m.id, m.vram, m.shard);
        model.display_name = m.name;
        if (i < gpus.length) { model.on_gpus = [gpus[i].h]; gpus[i].models = [model.h]; }
        return model;
    });
    const queue = modelDefs.slice(0, 4).map((m, i) => createRequestFromUDT(M(m.id), i));
    const alarms = [
        createAlarmFromUDT(makeTag(UDT.GPU.tag_prefix, 0, 'Temp'), 'MED', `Temperature approaching threshold (${gpus[0]?.temp || 78}°C)`, true),
        createAlarmFromUDT(`${UDT.Model.tag_prefix}_LDR_Active`, 'LOW', `Model ${models[0]?.name || 'llama-3-70b'} loaded successfully`, false)
    ];
    return { gpus, models, queue, alarms, stats: { gpu_count: gpus.length, model_count: models.length, queue_depth: queue.length,
        active_alarms: alarms.filter(a => a.active).length, uptime_sec: 3600 + Math.floor(Math.random() * 86400) }};
}

// Render helpers
const getProgressClass = (p) => p < 50 ? 'low' : p < 80 ? 'medium' : 'high';
const formatUptime = (s) => { const d = Math.floor(s/86400), h = Math.floor((s%86400)/3600), m = Math.floor((s%3600)/60); return d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`; };

function renderGpuCard(gpu) {
    const tempPct = gpu.temp !== null ? (gpu.temp / 90) * 100 : 0;
    const vramPct = (gpu.vram_used / gpu.vram_total) * 100;
    const stateName = ST_NAMES[gpu.state] || 'UNKNOWN';
    return `<div class="gpu-card" ${gpu.isClient ? 'style="border-color: var(--accent);"' : ''}>
        <div class="gpu-header"><span class="gpu-name">${gpu.isClient ? '🎮 ' : ''}${gpu.name}</span><span class="gpu-state ${stateName.toLowerCase()}">${stateName}</span></div>
        <div class="gpu-tag">${gpu.tag || makeTag(UDT.GPU.tag_prefix, gpu.idx, 'State')}</div>
        <div class="gpu-stats">
            <div class="gpu-stat"><span class="gpu-stat-label">Temperature</span><span class="gpu-stat-value">${gpu.temp !== null ? gpu.temp + '°C' : 'N/A'}</span>${gpu.temp !== null ? `<div class="progress-bar"><div class="progress-fill ${getProgressClass(tempPct)}" style="width:${tempPct}%"></div></div>` : ''}</div>
            <div class="gpu-stat"><span class="gpu-stat-label">VRAM</span><span class="gpu-stat-value">${(gpu.vram_used/1000).toFixed(1)}/${(gpu.vram_total/1000).toFixed(0)} GB</span><div class="progress-bar"><div class="progress-fill ${getProgressClass(vramPct)}" style="width:${vramPct}%"></div></div></div>
            <div class="gpu-stat"><span class="gpu-stat-label">Power</span><span class="gpu-stat-value">${gpu.pwr !== null ? `${gpu.pwr}W / ${gpu.pwr_cap}W` : 'N/A'}</span></div>
            <div class="gpu-stat"><span class="gpu-stat-label">Utilization</span><span class="gpu-stat-value">${gpu.util !== null ? gpu.util + '%' : 'N/A'}</span></div>
        </div></div>`;
}

function renderSchemas() {
    document.getElementById('schemas-container').innerHTML = Object.entries(UDT).map(([key, udt]) => `
        <div class="stat-card" style="margin-bottom: 1rem;"><h3 style="color: var(--accent); margin-bottom: 0.5rem;">${udt.name}</h3>
        <div class="gpu-tag">${udt.tag_prefix}_*</div>
        <div class="udt-schema"><pre>${Object.entries(udt.fields).map(([f, d]) => `${f.padEnd(12)} : ${d.type.padEnd(16)} // ${d.desc}${d.unit ? ' [' + d.unit + ']' : ''}`).join('\n')}</pre></div></div>`).join('');
}

function render() {
    document.getElementById('stat-gpus').textContent = data.stats.gpu_count;
    document.getElementById('stat-models').textContent = data.stats.model_count;
    document.getElementById('stat-queue').textContent = data.stats.queue_depth;
    document.getElementById('stat-alarms').textContent = data.stats.active_alarms;
    document.getElementById('uptime').textContent = 'Uptime: ' + formatUptime(data.stats.uptime_sec || 0);
    const badge = document.getElementById('alarm-badge');
    badge.style.display = data.stats.active_alarms > 0 ? 'block' : 'none';
    badge.textContent = data.stats.active_alarms;
    const gpuHtml = data.gpus.map(renderGpuCard).join('');
    document.getElementById('gpu-grid').innerHTML = gpuHtml;
    document.getElementById('gpu-detail-grid').innerHTML = gpuHtml;
    document.getElementById('models-body').innerHTML = data.models.map(m => `<tr><td>${m.display_name || m.name}</td><td class="model-hash">${m.h}</td><td>${(m.vram/1000).toFixed(1)} GB</td><td>${m.on_gpus.length}</td><td>${m.req_cnt.toLocaleString()}</td></tr>`).join('');
    document.getElementById('queue-body').innerHTML = data.queue.map(r => `<tr><td class="model-hash">${r.h}</td><td>${r.model_h}</td><td><span class="gpu-state ${RS_NAMES[r.state]?.toLowerCase() || 'queued'}">${RS_NAMES[r.state] || 'QUEUED'}</span></td><td>${r.priority}</td><td>${new Date(r.queued_at).toLocaleTimeString()}</td></tr>`).join('');
    document.getElementById('alarms-body').innerHTML = data.alarms.map(a => `<tr><td><span class="gpu-state ${a.class === 'CRIT' ? 'error' : a.class === 'HIGH' || a.class === 'MED' ? 'throttle' : 'ready'}">${a.class}</span></td><td class="model-hash" style="font-size: 0.75rem;">${a.tag}</td><td>${a.message}</td><td>${new Date(a.t_raised).toLocaleTimeString()}</td><td>${a.active ? '🔴 Active' : '✅ Cleared'}</td></tr>`).join('');
    renderSchemas();
}

function updateDemoUI() {
    const btn = document.getElementById('demo-toggle');
    const icon = document.getElementById('toggle-icon');
    const hint = document.getElementById('demo-hint');
    btn.classList.toggle('active', demoMode);
    icon.textContent = demoMode ? 'ON' : 'OFF';
    hint.style.display = demoMode ? 'block' : 'none';
}

// Init
async function init() {
    modelRegistry = await loadModelRegistry();
    await detectClientGPU();
    data = generateDataFromUDT();
    render();
    document.querySelectorAll('nav a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            document.querySelectorAll('nav a').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('view-' + view).classList.add('active');
        });
    });
    document.getElementById('demo-toggle').addEventListener('click', () => { demoMode = !demoMode; updateDemoUI(); if (demoMode) { data = generateDataFromUDT(); render(); }});
    setInterval(() => { if (demoMode) { data.gpus.forEach(g => { if (g.temp !== null) g.temp = Math.max(40, Math.min(85, g.temp + (Math.random() - 0.5) * 5)); if (g.util !== null) g.util = Math.max(0, Math.min(100, g.util + (Math.random() - 0.5) * 20)); g.vram_used = Math.max(0, Math.min(g.vram_total, g.vram_used + (Math.random() - 0.5) * 1000)); }); data.stats.uptime_sec += 5; render(); }}, 5000);
}
init();
