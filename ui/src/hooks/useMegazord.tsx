import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'

// Types matching the Python UDTs
interface GPU {
  h: string
  idx: number
  name: string
  vram_total: number
  vram_avail: number
  vram_pct: number
  speed: number
  temp: number
  load: number
  status: number
  status_label: string
  ok: boolean
}

interface Model {
  h: string
  name: string
  vram: number
  shard: boolean
  on: string[]
  refs: number
  loaded: boolean
}

interface Request {
  h: string
  model_h: string
  gpu_h: string
  tok_in: number
  tok_out: number
  status: number
  status_label: string
  t_start: number
  priority: number
  latency_ms: number
}

interface Alarm {
  h: string
  tag: string
  priority: number
  message: string
  t_raised: number
  t_ack: number
  active: boolean
  acknowledged: boolean
  value: number
}

interface Stats {
  state: string
  uptime_sec: number
  gpu_count: number
  gpu_ready: number
  model_count: number
  model_loaded: number
  queue_depth: number
  active_requests: number
  total_requests: number
  completed_requests: number
  failed_requests: number
  requests_per_sec: number
  total_tokens_in: number
  total_tokens_out: number
  vram_total_mb: number
  vram_available_mb: number
  temp_max: number
  temp_avg: number
}

interface MegazordState {
  connected: boolean
  demoMode: boolean
  stats: Stats | null
  gpus: GPU[]
  models: Model[]
  queue: Request[]
  alarms: Alarm[]
  loading: boolean
  error: string | null
}

interface MegazordContextValue extends MegazordState {
  refresh: () => Promise<void>
  loadModel: (name: string) => Promise<void>
  unloadModel: (name: string) => Promise<void>
  ackAlarm: (hash: string) => Promise<void>
  clearAlarm: (hash: string) => Promise<void>
  toggleDemoMode: () => void
}

const MegazordContext = createContext<MegazordContextValue | null>(null)

// Demo data generator
function generateDemoData(): { gpus: GPU[], models: Model[], stats: Stats, queue: Request[], alarms: Alarm[] } {
  const gpuNames = ['NVIDIA RTX 4090', 'NVIDIA RTX 4080', 'NVIDIA A100 80GB', 'NVIDIA RTX 3090'];
  const statusLabels = ['Offline', 'Starting', 'Ready', 'Busy', 'Throttle', 'Error'];

  const gpus: GPU[] = Array.from({ length: 4 }, (_, i) => ({
    h: `demo${i}${Math.random().toString(36).slice(2, 6)}`,
    idx: i,
    name: gpuNames[i % gpuNames.length],
    vram_total: [24576, 16384, 81920, 24576][i % 4],
    vram_avail: Math.floor([24576, 16384, 81920, 24576][i % 4] * (0.3 + Math.random() * 0.5)),
    vram_pct: 30 + Math.random() * 50,
    speed: 80 + Math.random() * 120,
    temp: 45 + Math.floor(Math.random() * 35),
    load: Math.random() * 0.8,
    status: Math.random() > 0.2 ? 2 : 3,
    status_label: statusLabels[Math.random() > 0.2 ? 2 : 3],
    ok: Math.random() > 0.1,
  }));

  const models: Model[] = [
    { h: 'mdl001', name: 'llama-70b', vram: 48000, shard: true, on: [gpus[0].h, gpus[1].h], refs: 2, loaded: true },
    { h: 'mdl002', name: 'mistral-7b', vram: 8000, shard: false, on: [gpus[2].h], refs: 1, loaded: true },
    { h: 'mdl003', name: 'codellama-34b', vram: 24000, shard: true, on: [], refs: 0, loaded: false },
  ];

  const vramTotal = gpus.reduce((sum, g) => sum + g.vram_total, 0);
  const vramAvail = gpus.reduce((sum, g) => sum + g.vram_avail, 0);
  const temps = gpus.map(g => g.temp);

  const stats: Stats = {
    state: 'Execute',
    uptime_sec: Math.floor(Math.random() * 86400) + 3600,
    gpu_count: gpus.length,
    gpu_ready: gpus.filter(g => g.ok).length,
    model_count: models.length,
    model_loaded: models.filter(m => m.loaded).length,
    queue_depth: Math.floor(Math.random() * 15),
    active_requests: Math.floor(Math.random() * 8),
    total_requests: Math.floor(Math.random() * 50000) + 1000,
    completed_requests: Math.floor(Math.random() * 48000) + 900,
    failed_requests: Math.floor(Math.random() * 500) + 10,
    requests_per_sec: Math.random() * 15 + 1,
    total_tokens_in: Math.floor(Math.random() * 5000000) + 100000,
    total_tokens_out: Math.floor(Math.random() * 10000000) + 500000,
    vram_total_mb: vramTotal,
    vram_available_mb: vramAvail,
    temp_max: Math.max(...temps),
    temp_avg: temps.reduce((a, b) => a + b, 0) / temps.length,
  };

  const queue: Request[] = Array.from({ length: Math.floor(Math.random() * 5) }, (_, i) => ({
    h: `req${i}${Math.random().toString(36).slice(2, 6)}`,
    model_h: models[Math.floor(Math.random() * models.length)].h,
    gpu_h: gpus[Math.floor(Math.random() * gpus.length)].h,
    tok_in: Math.floor(Math.random() * 500) + 50,
    tok_out: Math.floor(Math.random() * 1000),
    status: Math.floor(Math.random() * 3),
    status_label: ['Queued', 'Running', 'Done'][Math.floor(Math.random() * 3)],
    t_start: Math.floor(Date.now() / 1000) - Math.floor(Math.random() * 300),
    priority: Math.floor(Math.random() * 3),
    latency_ms: Math.floor(Math.random() * 2000) + 100,
  }));

  const alarms: Alarm[] = Math.random() > 0.5 ? [{
    h: `alm${Math.random().toString(36).slice(2, 8)}`,
    tag: 'GPU0_Temp_Warn',
    priority: 3,
    message: `GPU 0 temperature warning: ${gpus[0].temp}°C`,
    t_raised: Math.floor(Date.now() / 1000) - 300,
    t_ack: 0,
    active: true,
    acknowledged: false,
    value: gpus[0].temp,
  }] : [];

  return { gpus, models, stats, queue, alarms };
}

// Detect API base URL
function getApiBase(): string {
  // Check if we're on GitHub Pages or local
  if (window.location.hostname.includes('github.io')) {
    return 'http://localhost:8420'; // Point to local server for GitHub Pages
  }
  // Local development - proxy through Vite
  return '/api';
}

export function MegazordProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<MegazordState>({
    connected: false,
    demoMode: false,
    stats: null,
    gpus: [],
    models: [],
    queue: [],
    alarms: [],
    loading: true,
    error: null,
  })

  const API_BASE = getApiBase();

  const fetchData = useCallback(async () => {
    if (state.demoMode) {
      // Generate fresh demo data
      const demo = generateDemoData();
      setState(prev => ({
        ...prev,
        connected: false,
        demoMode: true,
        stats: demo.stats,
        gpus: demo.gpus,
        models: demo.models,
        queue: demo.queue,
        alarms: demo.alarms,
        loading: false,
        error: null,
      }));
      return;
    }

    try {
      const [statsRes, gpusRes, modelsRes, queueRes, alarmsRes] = await Promise.all([
        fetch(`${API_BASE}/stats`),
        fetch(`${API_BASE}/gpus`),
        fetch(`${API_BASE}/models`),
        fetch(`${API_BASE}/queue`),
        fetch(`${API_BASE}/alarms`),
      ])

      if (!statsRes.ok) throw new Error('API not available');

      const stats = await statsRes.json()
      const gpus = await gpusRes.json()
      const models = await modelsRes.json()
      const queue = await queueRes.json()
      const alarms = await alarmsRes.json()

      setState(prev => ({
        ...prev,
        connected: true,
        demoMode: false,
        stats,
        gpus,
        models,
        queue,
        alarms,
        loading: false,
        error: null,
      }))
    } catch (err) {
      // Fall back to demo mode on connection failure
      const demo = generateDemoData();
      setState(prev => ({
        ...prev,
        connected: false,
        demoMode: true,
        stats: demo.stats,
        gpus: demo.gpus,
        models: demo.models,
        queue: demo.queue,
        alarms: demo.alarms,
        loading: false,
        error: 'API not available - showing demo data',
      }))
    }
  }, [API_BASE, state.demoMode]);

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, state.demoMode ? 3000 : 2000)
    return () => clearInterval(interval)
  }, [fetchData, state.demoMode])

  // WebSocket for real-time updates (only when connected)
  useEffect(() => {
    if (state.demoMode) return;

    try {
      const wsUrl = API_BASE.replace('http', 'ws').replace('/api', '') + '/ws';
      const ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'stats') {
          setState(prev => ({
            ...prev,
            stats: data.data,
            gpus: data.data.gpus || prev.gpus,
            connected: true,
          }))
        }
      }

      ws.onerror = () => {
        // Silent fail - will use polling instead
      }

      return () => ws.close()
    } catch {
      // WebSocket not available
    }
  }, [API_BASE, state.demoMode])

  const loadModel = async (name: string) => {
    if (state.demoMode) {
      // Simulate in demo mode
      setState(prev => ({
        ...prev,
        models: prev.models.map(m =>
          m.name === name ? { ...m, loaded: true, on: [prev.gpus[0]?.h || ''] } : m
        ),
      }));
      return;
    }
    await fetch(`${API_BASE}/model/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    await fetchData()
  }

  const unloadModel = async (name: string) => {
    if (state.demoMode) {
      setState(prev => ({
        ...prev,
        models: prev.models.map(m =>
          m.name === name ? { ...m, loaded: false, on: [], refs: 0 } : m
        ),
      }));
      return;
    }
    await fetch(`${API_BASE}/model/unload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    await fetchData()
  }

  const ackAlarm = async (hash: string) => {
    if (state.demoMode) {
      setState(prev => ({
        ...prev,
        alarms: prev.alarms.map(a =>
          a.h === hash ? { ...a, acknowledged: true, t_ack: Math.floor(Date.now() / 1000) } : a
        ),
      }));
      return;
    }
    await fetch(`${API_BASE}/alarms/${hash}/ack`, { method: 'POST' })
    await fetchData()
  }

  const clearAlarm = async (hash: string) => {
    if (state.demoMode) {
      setState(prev => ({
        ...prev,
        alarms: prev.alarms.filter(a => a.h !== hash),
      }));
      return;
    }
    await fetch(`${API_BASE}/alarms/${hash}/clear`, { method: 'POST' })
    await fetchData()
  }

  const toggleDemoMode = () => {
    setState(prev => ({ ...prev, demoMode: !prev.demoMode, loading: true }));
  };

  return (
    <MegazordContext.Provider
      value={{
        ...state,
        refresh: fetchData,
        loadModel,
        unloadModel,
        ackAlarm,
        clearAlarm,
        toggleDemoMode,
      }}
    >
      {children}
    </MegazordContext.Provider>
  )
}

export function useMegazord() {
  const context = useContext(MegazordContext)
  if (!context) {
    throw new Error('useMegazord must be used within a MegazordProvider')
  }
  return context
}

export type { GPU, Model, Request, Alarm, Stats }
