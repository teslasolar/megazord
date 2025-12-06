import GPUCard from '../components/GPUCard'
import { useMegazord } from '../hooks/useMegazord'

export default function GPUs() {
  const { gpus, stats, loading } = useMegazord()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">GPU Array</h1>
          <p className="text-gray-400">
            {stats?.gpu_ready || 0} of {stats?.gpu_count || 0} GPUs ready
          </p>
        </div>
        {stats && (
          <div className="text-right">
            <p className="text-sm text-gray-400">Total VRAM</p>
            <p className="text-xl font-semibold">
              {(stats.vram_available_mb / 1024).toFixed(1)} / {(stats.vram_total_mb / 1024).toFixed(1)} GB
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {gpus.map(gpu => (
          <GPUCard key={gpu.h} gpu={gpu} />
        ))}
      </div>

      {gpus.length === 0 && (
        <div className="text-center text-gray-400 py-12">
          <p>No GPUs detected</p>
          <p className="text-sm mt-2">Run `megazord init` to scan for GPUs</p>
        </div>
      )}
    </div>
  )
}
