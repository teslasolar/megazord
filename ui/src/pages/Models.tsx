import { Box, Upload, Download } from 'lucide-react'
import { useMegazord } from '../hooks/useMegazord'

export default function Models() {
  const { models, gpus, loadModel, unloadModel, loading } = useMegazord()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    )
  }

  const handleLoad = async (name: string) => {
    try {
      await loadModel(name)
    } catch (err) {
      console.error('Failed to load model:', err)
    }
  }

  const handleUnload = async (name: string) => {
    try {
      await unloadModel(name)
    } catch (err) {
      console.error('Failed to unload model:', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Models</h1>
          <p className="text-gray-400">
            {models.filter(m => m.loaded).length} of {models.length} models loaded
          </p>
        </div>
      </div>

      {models.length === 0 ? (
        <div className="text-center text-gray-400 py-12">
          <Box size={48} className="mx-auto mb-4 opacity-50" />
          <p>No models registered</p>
          <p className="text-sm mt-2">
            Run `megazord model add &lt;name&gt; &lt;vram&gt;` to register a model
          </p>
        </div>
      ) : (
        <div className="bg-surface rounded-xl border border-surface-light overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-surface-light bg-surface-light/50">
                <th className="text-left py-3 px-4 font-medium text-gray-400">Name</th>
                <th className="text-left py-3 px-4 font-medium text-gray-400">Hash</th>
                <th className="text-right py-3 px-4 font-medium text-gray-400">VRAM</th>
                <th className="text-center py-3 px-4 font-medium text-gray-400">Shard</th>
                <th className="text-left py-3 px-4 font-medium text-gray-400">GPUs</th>
                <th className="text-center py-3 px-4 font-medium text-gray-400">Refs</th>
                <th className="text-center py-3 px-4 font-medium text-gray-400">Status</th>
                <th className="text-right py-3 px-4 font-medium text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {models.map(model => (
                <tr
                  key={model.h}
                  className="border-b border-surface-light hover:bg-surface-light/30 transition-colors"
                >
                  <td className="py-3 px-4 font-medium">{model.name}</td>
                  <td className="py-3 px-4 font-mono text-sm text-gray-400">{model.h}</td>
                  <td className="py-3 px-4 text-right">{(model.vram / 1024).toFixed(1)} GB</td>
                  <td className="py-3 px-4 text-center">
                    {model.shard ? (
                      <span className="text-success">Yes</span>
                    ) : (
                      <span className="text-gray-500">No</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {model.on.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {model.on.map(h => {
                          const gpu = gpus.find(g => g.h === h)
                          return (
                            <span
                              key={h}
                              className="text-xs bg-accent/20 text-accent px-2 py-0.5 rounded"
                            >
                              {gpu ? `GPU:${gpu.idx}` : h}
                            </span>
                          )
                        })}
                      </div>
                    ) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {model.refs > 0 ? (
                      <span className="text-accent">{model.refs}</span>
                    ) : (
                      <span className="text-gray-500">0</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {model.loaded ? (
                      <span className="bg-success/20 text-success px-2 py-1 rounded text-sm">
                        Loaded
                      </span>
                    ) : (
                      <span className="bg-gray-500/20 text-gray-400 px-2 py-1 rounded text-sm">
                        Unloaded
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {model.loaded ? (
                      <button
                        onClick={() => handleUnload(model.name)}
                        disabled={model.refs > 0}
                        className={`
                          inline-flex items-center gap-1 px-3 py-1 rounded
                          transition-colors
                          ${model.refs > 0
                            ? 'bg-gray-500/20 text-gray-500 cursor-not-allowed'
                            : 'bg-warning/20 text-warning hover:bg-warning/30'
                          }
                        `}
                      >
                        <Download size={16} />
                        Unload
                      </button>
                    ) : (
                      <button
                        onClick={() => handleLoad(model.name)}
                        className="inline-flex items-center gap-1 px-3 py-1 rounded bg-success/20 text-success hover:bg-success/30 transition-colors"
                      >
                        <Upload size={16} />
                        Load
                      </button>
                    )}
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
