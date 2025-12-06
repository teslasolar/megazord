import { ListOrdered, Clock } from 'lucide-react'
import { useMegazord } from '../hooks/useMegazord'

const statusColors: Record<number, string> = {
  0: 'bg-gray-500/20 text-gray-400',      // QUEUED
  1: 'bg-cyan-500/20 text-cyan-400',       // RUNNING
  2: 'bg-success/20 text-success',         // DONE
  3: 'bg-error/20 text-error',             // ERROR
}

const priorityLabels: Record<number, { label: string; class: string }> = {
  0: { label: 'Low', class: 'text-gray-400' },
  1: { label: 'Normal', class: 'text-white' },
  2: { label: 'High', class: 'text-warning' },
}

export default function Queue() {
  const { queue, stats, loading } = useMegazord()

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
          <h1 className="text-2xl font-bold">Request Queue</h1>
          <p className="text-gray-400">
            {stats?.queue_depth || 0} pending, {stats?.active_requests || 0} active
          </p>
        </div>
        {stats && (
          <div className="flex gap-4 text-sm">
            <div className="text-center">
              <p className="text-gray-400">Total</p>
              <p className="text-xl font-semibold">{stats.total_requests.toLocaleString()}</p>
            </div>
            <div className="text-center">
              <p className="text-gray-400">Completed</p>
              <p className="text-xl font-semibold text-success">{stats.completed_requests.toLocaleString()}</p>
            </div>
            <div className="text-center">
              <p className="text-gray-400">Failed</p>
              <p className="text-xl font-semibold text-error">{stats.failed_requests.toLocaleString()}</p>
            </div>
          </div>
        )}
      </div>

      {queue.length === 0 ? (
        <div className="text-center text-gray-400 py-12">
          <ListOrdered size={48} className="mx-auto mb-4 opacity-50" />
          <p>No requests in queue</p>
          <p className="text-sm mt-2">Requests will appear here when submitted</p>
        </div>
      ) : (
        <div className="bg-surface rounded-xl border border-surface-light overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-surface-light bg-surface-light/50">
                <th className="text-left py-3 px-4 font-medium text-gray-400">ID</th>
                <th className="text-left py-3 px-4 font-medium text-gray-400">Model</th>
                <th className="text-left py-3 px-4 font-medium text-gray-400">GPU</th>
                <th className="text-right py-3 px-4 font-medium text-gray-400">Tokens In</th>
                <th className="text-right py-3 px-4 font-medium text-gray-400">Tokens Out</th>
                <th className="text-center py-3 px-4 font-medium text-gray-400">Priority</th>
                <th className="text-right py-3 px-4 font-medium text-gray-400">Latency</th>
                <th className="text-center py-3 px-4 font-medium text-gray-400">Status</th>
              </tr>
            </thead>
            <tbody>
              {queue.map(req => (
                <tr
                  key={req.h}
                  className="border-b border-surface-light hover:bg-surface-light/30 transition-colors"
                >
                  <td className="py-3 px-4 font-mono text-sm">{req.h}</td>
                  <td className="py-3 px-4 font-mono text-sm text-gray-400">{req.model_h}</td>
                  <td className="py-3 px-4 font-mono text-sm text-gray-400">
                    {req.gpu_h || '-'}
                  </td>
                  <td className="py-3 px-4 text-right">{req.tok_in.toLocaleString()}</td>
                  <td className="py-3 px-4 text-right">{req.tok_out.toLocaleString()}</td>
                  <td className="py-3 px-4 text-center">
                    <span className={priorityLabels[req.priority]?.class || ''}>
                      {priorityLabels[req.priority]?.label || req.priority}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="inline-flex items-center gap-1 text-gray-400">
                      <Clock size={14} />
                      {formatLatency(req.latency_ms)}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className={`px-2 py-1 rounded text-sm ${statusColors[req.status] || ''}`}>
                      {req.status_label}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}
