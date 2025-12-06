import { AlertTriangle, Bell, Check, X } from 'lucide-react'
import { useMegazord } from '../hooks/useMegazord'

const priorityClasses: Record<number, { bg: string; text: string; label: string }> = {
  1: { bg: 'bg-error/20', text: 'text-error', label: 'Critical' },
  2: { bg: 'bg-orange-500/20', text: 'text-orange-400', label: 'High' },
  3: { bg: 'bg-warning/20', text: 'text-warning', label: 'Medium' },
  4: { bg: 'bg-info/20', text: 'text-info', label: 'Low' },
}

export default function Alarms() {
  const { alarms, ackAlarm, clearAlarm, loading } = useMegazord()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    )
  }

  const activeAlarms = alarms.filter(a => a.active)
  const acknowledgedAlarms = alarms.filter(a => a.acknowledged && a.active)

  const handleAck = async (hash: string) => {
    try {
      await ackAlarm(hash)
    } catch (err) {
      console.error('Failed to acknowledge alarm:', err)
    }
  }

  const handleClear = async (hash: string) => {
    try {
      await clearAlarm(hash)
    } catch (err) {
      console.error('Failed to clear alarm:', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Alarms</h1>
          <p className="text-gray-400">
            {activeAlarms.length} active, {acknowledgedAlarms.length} acknowledged
          </p>
        </div>
        {activeAlarms.length > 0 && (
          <div className="flex items-center gap-2 text-error animate-pulse">
            <Bell size={20} />
            <span>Active Alarms</span>
          </div>
        )}
      </div>

      {alarms.length === 0 ? (
        <div className="text-center text-gray-400 py-12">
          <AlertTriangle size={48} className="mx-auto mb-4 opacity-50" />
          <p>No alarms</p>
          <p className="text-sm mt-2">System is operating normally</p>
        </div>
      ) : (
        <div className="space-y-4">
          {alarms.map(alarm => {
            const priority = priorityClasses[alarm.priority] || priorityClasses[3]
            return (
              <div
                key={alarm.h}
                className={`
                  bg-surface rounded-xl p-4 border-l-4
                  ${alarm.active
                    ? priority.text.replace('text-', 'border-')
                    : 'border-gray-600 opacity-60'
                  }
                `}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${priority.bg}`}>
                      <AlertTriangle size={20} className={priority.text} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${priority.text}`}>
                          {priority.label}
                        </span>
                        <span className="text-gray-400">•</span>
                        <span className="text-sm text-gray-400">{alarm.tag}</span>
                      </div>
                      <p className="font-medium mt-1">{alarm.message}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                        <span>Raised: {formatTime(alarm.t_raised)}</span>
                        {alarm.acknowledged && (
                          <span className="text-success">
                            Acknowledged: {formatTime(alarm.t_ack)}
                          </span>
                        )}
                        {alarm.value !== 0 && (
                          <span>Value: {alarm.value}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {alarm.active && (
                    <div className="flex gap-2">
                      {!alarm.acknowledged && (
                        <button
                          onClick={() => handleAck(alarm.h)}
                          className="flex items-center gap-1 px-3 py-1 rounded bg-accent/20 text-accent hover:bg-accent/30 transition-colors"
                        >
                          <Check size={16} />
                          ACK
                        </button>
                      )}
                      <button
                        onClick={() => handleClear(alarm.h)}
                        className="flex items-center gap-1 px-3 py-1 rounded bg-success/20 text-success hover:bg-success/30 transition-colors"
                      >
                        <X size={16} />
                        Clear
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function formatTime(timestamp: number): string {
  if (!timestamp) return '-'
  return new Date(timestamp * 1000).toLocaleString()
}
