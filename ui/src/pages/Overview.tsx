import { Cpu, HardDrive, ListOrdered, Zap, Thermometer, Box } from 'lucide-react'
import StatCard from '../components/StatCard'
import GPUCard from '../components/GPUCard'
import { useMegazord } from '../hooks/useMegazord'

export default function Overview() {
  const { stats, gpus, models, loading } = useMegazord()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="text-center text-gray-400 py-12">
        <p>Unable to connect to Megazord API</p>
        <p className="text-sm mt-2">Make sure the server is running on port 8420</p>
      </div>
    )
  }

  const loadedModels = models.filter(m => m.loaded)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Overview</h1>
          <p className="text-gray-400">Cluster Status Dashboard</p>
        </div>
        <div className={`
          flex items-center gap-2 px-4 py-2 rounded-lg
          ${stats.state === 'Execute' ? 'bg-success/20 text-success' : 'bg-yellow-500/20 text-yellow-500'}
        `}>
          <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
          {stats.state}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="GPUs"
          value={`${stats.gpu_ready}/${stats.gpu_count}`}
          icon={<Cpu size={24} />}
          subtitle="Ready / Total"
          color={stats.gpu_ready === stats.gpu_count ? 'success' : 'warning'}
        />
        <StatCard
          title="VRAM Available"
          value={`${(stats.vram_available_mb / 1024).toFixed(1)} GB`}
          icon={<HardDrive size={24} />}
          subtitle={`of ${(stats.vram_total_mb / 1024).toFixed(1)} GB`}
        />
        <StatCard
          title="Queue Depth"
          value={stats.queue_depth}
          icon={<ListOrdered size={24} />}
          subtitle={`${stats.active_requests} active`}
          color={stats.queue_depth > 80 ? 'warning' : 'default'}
        />
        <StatCard
          title="Throughput"
          value={`${stats.requests_per_sec.toFixed(1)}`}
          icon={<Zap size={24} />}
          subtitle="requests/sec"
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Max Temperature"
          value={`${stats.temp_max}°C`}
          icon={<Thermometer size={24} />}
          subtitle={`Avg: ${stats.temp_avg.toFixed(1)}°C`}
          color={stats.temp_max >= 83 ? 'error' : stats.temp_max >= 75 ? 'warning' : 'success'}
        />
        <StatCard
          title="Models Loaded"
          value={`${stats.model_loaded}/${stats.model_count}`}
          icon={<Box size={24} />}
        />
        <StatCard
          title="Total Requests"
          value={stats.total_requests.toLocaleString()}
          icon={<Zap size={24} />}
          subtitle={`${stats.completed_requests} completed, ${stats.failed_requests} failed`}
        />
      </div>

      {/* GPU Grid */}
      <div>
        <h2 className="text-xl font-semibold mb-4">GPU Array</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {gpus.map(gpu => (
            <GPUCard key={gpu.h} gpu={gpu} />
          ))}
          {gpus.length === 0 && (
            <div className="col-span-full text-center text-gray-400 py-8">
              No GPUs detected
            </div>
          )}
        </div>
      </div>

      {/* Loaded Models */}
      {loadedModels.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Loaded Models</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {loadedModels.map(model => (
              <div
                key={model.h}
                className="bg-surface rounded-xl p-4 border border-success/30"
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{model.name}</h3>
                  <span className="text-xs bg-success/20 text-success px-2 py-1 rounded">
                    Loaded
                  </span>
                </div>
                <p className="text-sm text-gray-400">
                  VRAM: {(model.vram / 1024).toFixed(1)} GB
                </p>
                <p className="text-sm text-gray-400">
                  GPUs: {model.on.join(', ')}
                </p>
                <p className="text-sm text-gray-400">
                  Active refs: {model.refs}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
