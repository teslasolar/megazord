/**
 * Megazord SCADA/HMI Controller
 * Real-time updates and process visualization
 */

const SCADA = {
    config: {
        apiBase: '',
        updateInterval: 2000,
        wsEndpoint: '/ws'
    },

    state: {
        connected: false,
        gpus: [],
        models: [],
        stats: null,
        alarms: [],
        routerState: 'IDLE'
    },

    elements: {},

    // Initialize SCADA interface
    init() {
        this.cacheElements();
        this.startClock();
        this.fetchInitialData();
        this.startPolling();
        this.tryWebSocket();
    },

    // Cache DOM elements
    cacheElements() {
        this.elements = {
            time: document.getElementById('scada-time'),
            date: document.getElementById('scada-date'),
            statusDot: document.getElementById('status-dot'),
            statusText: document.getElementById('status-text'),
            alarmBanner: document.getElementById('alarm-banner'),
            alarmText: document.getElementById('alarm-text'),
            gpuArray: document.getElementById('gpu-array'),
            modelList: document.getElementById('model-list'),
            routerState: document.getElementById('router-state'),
            statGpus: document.getElementById('stat-gpus'),
            statModels: document.getElementById('stat-models'),
            statQueue: document.getElementById('stat-queue'),
            statReqs: document.getElementById('stat-reqs'),
            statVram: document.getElementById('stat-vram'),
            statTemp: document.getElementById('stat-temp'),
            statThroughput: document.getElementById('stat-throughput'),
            statUptime: document.getElementById('stat-uptime')
        };
    },

    // Update clock
    startClock() {
        const updateClock = () => {
            const now = new Date();
            if (this.elements.time) {
                this.elements.time.textContent = now.toLocaleTimeString('en-US', { hour12: false });
            }
            if (this.elements.date) {
                this.elements.date.textContent = now.toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric'
                });
            }
        };
        updateClock();
        setInterval(updateClock, 1000);
    },

    // Fetch initial data
    async fetchInitialData() {
        try {
            const [health, stats, gpus, models] = await Promise.all([
                this.fetchAPI('/health'),
                this.fetchAPI('/stats'),
                this.fetchAPI('/gpus'),
                this.fetchAPI('/models')
            ]);

            this.state.connected = true;
            this.state.stats = stats;
            this.state.gpus = gpus || [];
            this.state.models = models || [];
            this.state.routerState = stats?.state || 'IDLE';

            this.updateUI();
        } catch (e) {
            this.state.connected = false;
            this.updateConnectionStatus();
            this.showDemoData();
        }
    },

    // Fetch from API
    async fetchAPI(endpoint) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3000);

        try {
            const response = await fetch(this.config.apiBase + endpoint, {
                signal: controller.signal
            });
            clearTimeout(timeout);

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (e) {
            clearTimeout(timeout);
            throw e;
        }
    },

    // Start polling for updates
    startPolling() {
        setInterval(async () => {
            try {
                const stats = await this.fetchAPI('/stats');
                this.state.stats = stats;
                this.state.connected = true;
                this.state.routerState = stats?.state || 'IDLE';
                this.updateStats();
                this.updateConnectionStatus();
            } catch (e) {
                this.state.connected = false;
                this.updateConnectionStatus();
            }
        }, this.config.updateInterval);
    },

    // Try WebSocket connection
    tryWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${window.location.host}${this.config.wsEndpoint}`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                this.state.connected = true;
                this.updateConnectionStatus();
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'stats') {
                    this.state.stats = data.data;
                    this.state.gpus = data.data.gpus || this.state.gpus;
                    this.updateUI();
                }
            };

            ws.onclose = () => {
                console.log('WebSocket closed, falling back to polling');
            };
        } catch (e) {
            console.log('WebSocket not available');
        }
    },

    // Update all UI elements
    updateUI() {
        this.updateConnectionStatus();
        this.updateStats();
        this.updateGPUArray();
        this.updateModelList();
        this.updateRouterState();
        this.updateAlarms();
    },

    // Update connection status
    updateConnectionStatus() {
        const dot = this.elements.statusDot;
        const text = this.elements.statusText;

        if (!dot || !text) return;

        if (this.state.connected) {
            dot.className = 'dot online';
            text.textContent = 'ONLINE';
        } else {
            dot.className = 'dot offline';
            text.textContent = 'OFFLINE';
        }
    },

    // Update statistics display
    updateStats() {
        const s = this.state.stats;
        if (!s) return;

        this.updateElement('stat-gpus', s.gpu_count || 0);
        this.updateElement('stat-gpus-ready', s.gpu_ready || 0);
        this.updateElement('stat-models', s.model_count || 0);
        this.updateElement('stat-models-loaded', s.model_loaded || 0);
        this.updateElement('stat-queue', s.queue_depth || 0);
        this.updateElement('stat-active', s.active_requests || 0);
        this.updateElement('stat-total-reqs', s.total_requests || 0);
        this.updateElement('stat-completed', s.completed_requests || 0);
        this.updateElement('stat-vram-total', Math.round((s.vram_total_mb || 0) / 1024));
        this.updateElement('stat-vram-avail', Math.round((s.vram_available_mb || 0) / 1024));
        this.updateElement('stat-temp-max', Math.round(s.temp_max || 0));
        this.updateElement('stat-temp-avg', Math.round(s.temp_avg || 0));
        this.updateElement('stat-rps', (s.requests_per_sec || 0).toFixed(1));
        this.updateElement('stat-uptime', this.formatUptime(s.uptime_sec || 0));
    },

    updateElement(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    },

    // Update GPU array
    updateGPUArray() {
        const container = this.elements.gpuArray;
        if (!container) return;

        if (this.state.gpus.length === 0) {
            container.innerHTML = '<div class="no-data">No GPUs detected</div>';
            return;
        }

        container.innerHTML = this.state.gpus.map((gpu, i) => {
            const vramPct = gpu.vram_total ? ((gpu.vram_total - gpu.vram_avail) / gpu.vram_total * 100) : 0;
            const vramClass = vramPct > 90 ? 'critical' : vramPct > 75 ? 'warning' : '';
            const stateClass = (gpu.status || 'offline').toLowerCase();

            return `
                <div class="gpu-faceplate">
                    <div class="index">${gpu.idx ?? i}</div>
                    <div class="info">
                        <div class="name">${gpu.name || 'GPU ' + i}</div>
                        <div class="metrics">
                            <span>${gpu.temp || 0}°C</span>
                            <span>${Math.round((gpu.load || 0) * 100)}%</span>
                            <span>${Math.round((gpu.vram_avail || 0) / 1024)}GB</span>
                        </div>
                        <div class="vram-bar">
                            <div class="fill ${vramClass}" style="width: ${vramPct}%"></div>
                        </div>
                    </div>
                    <div class="state ${stateClass}">${gpu.status || 'OFF'}</div>
                </div>
            `;
        }).join('');
    },

    // Update model list
    updateModelList() {
        const container = this.elements.modelList;
        if (!container) return;

        if (this.state.models.length === 0) {
            container.innerHTML = '<div class="no-data">No models registered</div>';
            return;
        }

        container.innerHTML = this.state.models.map(model => {
            const loaded = model.on && model.on.length > 0;
            return `
                <div class="model-item">
                    <div class="status-dot" style="background: ${loaded ? 'var(--success)' : 'var(--text-muted)'}"></div>
                    <div class="name">${model.name || model.h}</div>
                    <div class="vram">${Math.round((model.vram || 0) / 1024)}GB</div>
                </div>
            `;
        }).join('');
    },

    // Update router state visualization
    updateRouterState() {
        const states = ['IDLE', 'STARTING', 'EXECUTE', 'HELD', 'STOPPING'];
        states.forEach(state => {
            const el = document.getElementById(`state-${state.toLowerCase()}`);
            if (el) {
                el.className = 'state-node' + (this.state.routerState === state ? ' active' : '');
            }
        });
    },

    // Update alarms
    updateAlarms() {
        const banner = this.elements.alarmBanner;
        const text = this.elements.alarmText;

        if (!banner) return;

        if (this.state.alarms.length > 0) {
            const alarm = this.state.alarms[0];
            banner.className = 'alarm-banner active' + (alarm.priority > 2 ? ' warning' : '');
            if (text) text.textContent = `${alarm.tag}: ${alarm.message}`;
        } else {
            banner.className = 'alarm-banner';
        }
    },

    // Show demo data when API is not available
    showDemoData() {
        this.state.gpus = [
            { idx: 0, name: 'RTX 4090', temp: 45, load: 0.12, vram_total: 24576, vram_avail: 22000, status: 'READY' },
            { idx: 1, name: 'RTX 4090', temp: 42, load: 0.08, vram_total: 24576, vram_avail: 24000, status: 'READY' },
            { idx: 2, name: 'RTX 3090', temp: 38, load: 0, vram_total: 24576, vram_avail: 24576, status: 'READY' },
            { idx: 3, name: 'RTX 3090', temp: 36, load: 0, vram_total: 24576, vram_avail: 24576, status: 'READY' }
        ];

        this.state.models = [
            { name: 'llama-3-70b', vram: 42000, on: ['gpu0', 'gpu1'] },
            { name: 'mistral-7b', vram: 8000, on: [] },
            { name: 'codellama-34b', vram: 20000, on: [] }
        ];

        this.state.stats = {
            gpu_count: 4, gpu_ready: 4,
            model_count: 3, model_loaded: 1,
            queue_depth: 0, active_requests: 0,
            total_requests: 0, completed_requests: 0,
            vram_total_mb: 98304, vram_available_mb: 95152,
            temp_max: 45, temp_avg: 40,
            requests_per_sec: 0, uptime_sec: 0
        };

        this.state.routerState = 'EXECUTE';
        this.updateUI();
    },

    // Format uptime
    formatUptime(seconds) {
        if (seconds < 60) return `${seconds}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
        return `${Math.floor(seconds / 86400)}d`;
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => SCADA.init());
