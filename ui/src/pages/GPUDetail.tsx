import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Thermometer, HardDrive, Zap, Activity } from 'lucide-react'
import { useMegazord } from '../hooks/useMegazord'

export default function GPUDetail() {
  const { hash } = useParams<{ hash: string }>()
  const { gpus, loading } = useMegazord()

  const gpu = gpus.find(g => g.h === hash)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    )
  }

  if (!gpu) {
    return (
      <div className="text-center text-gray-400 py-12">
        <p>GPU not found</p>
        <Link to="/gpus" className="text-accent hover:underline mt-2 inline-block">
          Back to GPU list
        </Link>
      </div>
    )
  }

  const tempColor = gpu.temp >= 83 ? 'text-error' :
                    gpu.temp >= 75 ? 'text-warning' :
                    'text-success'

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          to="/gpus"
          className="p-2 hover:bg-surface-light rounded-lg transition-colors"
        >
          <ArrowLeft size={24} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">{gpu.name}</h1>
          <p className="text-gray-400">GPU:{gpu.idx} • {gpu.h}</p>
        </div>
        <span className={`
          ml-auto px-4 py-2 rounded-lg font-medium
          ${gpu.ok ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}
        `}>
          {gpu.status_label}
        </span>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface rounded-xl p-6 border border-surface-light">
          <div className="flex items-center gap-3 mb-4">
            <Thermometer className={tempColor} size={24} />
            <span className="text-gray-400">Temperature</span>
          </div>
          <p className={`text-4xl font-bold ${tempColor}`}>{gpu.temp}°C</p>
          <div className="mt-4 bg-surface-light rounded-full h-3 overflow-hidden">
            <div
              className="temp-gradient h-full transition-all"
              style={{ width: `${Math.min(gpu.temp, 100)}%` }}
            />
          </div>
        </div>

        <div className="bg-surface rounded-xl p-6 border border-surface-light">
          <div className="flex items-center gap-3 mb-4">
            <HardDrive className="text-accent" size={24} />
            <span className="text-gray-400">VRAM</span>
          </div>
          <p className="text-4xl font-bold text-accent">
            {(gpu.vram_avail / 1024).toFixed(1)} GB
          </p>
          <p className="text-sm text-gray-400 mt-1">
            of {(gpu.vram_total / 1024).toFixed(1)} GB
          </p>
          <div className="mt-4 bg-surface-light rounded-full h-3 overflow-hidden">
            <div
              className="bg-accent h-full transition-all"
              style={{ width: `${gpu.vram_pct}%` }}
            />
          </div>
        </div>

        <div className="bg-surface rounded-xl p-6 border border-surface-light">
          <div className="flex items-center gap-3 mb-4">
            <Zap className="text-yellow-400" size={24} />
            <span className="text-gray-400">Speed</span>
          </div>
          <p className="text-4xl font-bold text-yellow-400">
            {gpu.speed.toFixed(1)}
          </p>
          <p className="text-sm text-gray-400 mt-1">tokens/sec</p>
        </div>

        <div className="bg-surface rounded-xl p-6 border border-surface-light">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="text-purple-400" size={24} />
            <span className="text-gray-400">Load</span>
          </div>
          <p className="text-4xl font-bold text-purple-400">
            {(gpu.load * 100).toFixed(0)}%
          </p>
          <div className="mt-4 bg-surface-light rounded-full h-3 overflow-hidden">
            <div
              className="bg-purple-400 h-full transition-all"
              style={{ width: `${gpu.load * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Details Table */}
      <div className="bg-surface rounded-xl p-6 border border-surface-light">
        <h2 className="text-xl font-semibold mb-4">Details</h2>
        <table className="w-full">
          <tbody>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">Hash</td>
              <td className="py-3 font-mono">{gpu.h}</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">Index</td>
              <td className="py-3">{gpu.idx}</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">Name</td>
              <td className="py-3">{gpu.name}</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">VRAM Total</td>
              <td className="py-3">{gpu.vram_total.toLocaleString()} MB</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">VRAM Available</td>
              <td className="py-3">{gpu.vram_avail.toLocaleString()} MB</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">VRAM Used</td>
              <td className="py-3">{(gpu.vram_total - gpu.vram_avail).toLocaleString()} MB ({gpu.vram_pct.toFixed(1)}%)</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">Temperature</td>
              <td className={`py-3 ${tempColor}`}>{gpu.temp}°C</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">Load</td>
              <td className="py-3">{(gpu.load * 100).toFixed(1)}%</td>
            </tr>
            <tr className="border-b border-surface-light">
              <td className="py-3 text-gray-400">Speed</td>
              <td className="py-3">{gpu.speed.toFixed(2)} tok/s</td>
            </tr>
            <tr>
              <td className="py-3 text-gray-400">Status</td>
              <td className="py-3">
                <span className={`
                  px-2 py-1 rounded text-sm
                  ${gpu.ok ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}
                `}>
                  {gpu.status_label}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
