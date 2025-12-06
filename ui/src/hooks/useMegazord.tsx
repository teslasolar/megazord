import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

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
}

const MegazordContext = createContext<MegazordContextValue | null>(null)

const API_BASE = '/api'

export function MegazordProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<MegazordState>({
    connected: false,
    stats: null,
    gpus: [],
    models: [],
    queue: [],
    alarms: [],
    loading: true,
    error: null,
  })

  const fetchData = async () => {
    try {
      const [statsRes, gpusRes, modelsRes, queueRes, alarmsRes] = await Promise.all([
        fetch(`${API_BASE}/stats`),
        fetch(`${API_BASE}/gpus`),
        fetch(`${API_BASE}/models`),
        fetch(`${API_BASE}/queue`),
        fetch(`${API_BASE}/alarms`),
      ])

      const stats = await statsRes.json()
      const gpus = await gpusRes.json()
      const models = await modelsRes.json()
      const queue = await queueRes.json()
      const alarms = await alarmsRes.json()

      setState(prev => ({
        ...prev,
        connected: true,
        stats,
        gpus,
        models,
        queue,
        alarms,
        loading: false,
        error: null,
      }))
    } catch (err) {
      setState(prev => ({
        ...prev,
        connected: false,
        loading: false,
        error: err instanceof Error ? err.message : 'Connection failed',
      }))
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 2000)
    return () => clearInterval(interval)
  }, [])

  // WebSocket for real-time updates
  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws`)

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
      setState(prev => ({ ...prev, connected: false }))
    }

    return () => ws.close()
  }, [])

  const loadModel = async (name: string) => {
    await fetch(`${API_BASE}/model/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    await fetchData()
  }

  const unloadModel = async (name: string) => {
    await fetch(`${API_BASE}/model/unload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    await fetchData()
  }

  const ackAlarm = async (hash: string) => {
    await fetch(`${API_BASE}/alarms/${hash}/ack`, { method: 'POST' })
    await fetchData()
  }

  const clearAlarm = async (hash: string) => {
    await fetch(`${API_BASE}/alarms/${hash}/clear`, { method: 'POST' })
    await fetchData()
  }

  return (
    <MegazordContext.Provider
      value={{
        ...state,
        refresh: fetchData,
        loadModel,
        unloadModel,
        ackAlarm,
        clearAlarm,
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
