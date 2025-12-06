import { Link } from 'react-router-dom'
import { Thermometer, HardDrive, Zap } from 'lucide-react'
import type { GPU } from '../hooks/useMegazord'

interface GPUCardProps {
  gpu: GPU
}

const statusColors: Record<number, string> = {
  0: 'bg-gray-500', // OFF
  1: 'bg-yellow-500', // STARTING
  2: 'bg-green-500', // READY
  3: 'bg-cyan-500', // BUSY
  4: 'bg-yellow-500', // THROTTLE
  5: 'bg-red-500', // ERROR
}

export default function GPUCard({ gpu }: GPUCardProps) {
  const tempColor = gpu.temp >= 83 ? 'text-error' :
                    gpu.temp >= 75 ? 'text-warning' :
                    'text-success'

  const vramPct = ((gpu.vram_total - gpu.vram_avail) / gpu.vram_total) * 100

  return (
    <Link
      to={`/gpus/${gpu.h}`}
      className={`
        block bg-surface rounded-xl p-4 border-2
        transition-all hover:scale-[1.02] hover:border-accent/50
        ${gpu.ok ? 'border-success/30' : 'border-warning/30'}
        ${gpu.status === 3 ? 'gpu-active text-cyan-400' : 'border-surface-light'}
      `}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-sm text-gray-400">GPU:{gpu.idx}</span>
          <span className={`
            ml-2 inline-block w-2 h-2 rounded-full
            ${statusColors[gpu.status] || 'bg-gray-500'}
          `} />
        </div>
        <span className="text-xs bg-surface-light px-2 py-1 rounded">
          {gpu.status_label}
        </span>
      </div>

      <h3 className="font-semibold mb-3 truncate">{gpu.name}</h3>

      {/* Temperature Bar */}
      <div className="flex items-center gap-2 mb-2">
        <Thermometer size={16} className={tempColor} />
        <div className="flex-1 bg-surface-light rounded-full h-2 overflow-hidden">
          <div
            className="temp-gradient h-full transition-all"
            style={{ width: `${Math.min(gpu.temp, 100)}%` }}
          />
        </div>
        <span className={`text-sm ${tempColor}`}>{gpu.temp}°C</span>
      </div>

      {/* VRAM Bar */}
      <div className="flex items-center gap-2 mb-2">
        <HardDrive size={16} className="text-gray-400" />
        <div className="flex-1 bg-surface-light rounded-full h-2 overflow-hidden">
          <div
            className="bg-accent h-full transition-all"
            style={{ width: `${vramPct}%` }}
          />
        </div>
        <span className="text-sm text-gray-400">
          {(gpu.vram_avail / 1024).toFixed(1)}GB
        </span>
      </div>

      {/* Speed */}
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <Zap size={16} />
        <span>{gpu.speed.toFixed(1)} tok/s</span>
        <span className="ml-auto">Load: {(gpu.load * 100).toFixed(0)}%</span>
      </div>
    </Link>
  )
}
