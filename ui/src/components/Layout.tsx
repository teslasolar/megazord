import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  Activity,
  Cpu,
  Box,
  ListOrdered,
  AlertTriangle,
  Wifi,
  WifiOff
} from 'lucide-react'
import { useMegazord } from '../hooks/useMegazord'

const navItems = [
  { path: '/', icon: Activity, label: 'Overview' },
  { path: '/gpus', icon: Cpu, label: 'GPUs' },
  { path: '/models', icon: Box, label: 'Models' },
  { path: '/queue', icon: ListOrdered, label: 'Queue' },
  { path: '/alarms', icon: AlertTriangle, label: 'Alarms' },
]

export default function Layout() {
  const location = useLocation()
  const { connected, stats, alarms } = useMegazord()

  const activeAlarms = alarms.filter(a => a.active).length

  return (
    <div className="min-h-screen bg-dark flex">
      {/* Sidebar */}
      <aside className="w-64 bg-surface border-r border-surface-light flex flex-col">
        <div className="p-4 border-b border-surface-light">
          <h1 className="text-xl font-bold text-accent">
            Megazord
          </h1>
          <p className="text-sm text-gray-500">
            LLM Cluster Dashboard
          </p>
        </div>

        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path
              const Icon = item.icon
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`
                      flex items-center gap-3 px-4 py-2 rounded-lg
                      transition-colors
                      ${isActive
                        ? 'bg-accent/20 text-accent'
                        : 'text-gray-400 hover:bg-surface-light hover:text-white'
                      }
                    `}
                  >
                    <Icon size={20} />
                    <span>{item.label}</span>
                    {item.path === '/alarms' && activeAlarms > 0 && (
                      <span className="ml-auto bg-error text-white text-xs px-2 py-0.5 rounded-full">
                        {activeAlarms}
                      </span>
                    )}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Connection Status */}
        <div className="p-4 border-t border-surface-light">
          <div className="flex items-center gap-2 text-sm">
            {connected ? (
              <>
                <Wifi size={16} className="text-success" />
                <span className="text-success">Connected</span>
              </>
            ) : (
              <>
                <WifiOff size={16} className="text-error" />
                <span className="text-error">Disconnected</span>
              </>
            )}
          </div>
          {stats && (
            <p className="text-xs text-gray-500 mt-1">
              Uptime: {formatUptime(stats.uptime_sec)}
            </p>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}
