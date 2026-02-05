import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Play, FileCode, Wrench, Server, Plus, RefreshCw, Trash2, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { api, ProviderSummary, AddProviderRequest } from '../lib/api'

interface LocalFile {
  id: string
  name: string
  description: string
  type: string | null
  path: string
  relative_path: string
}

interface LocalStatus {
  mode: string
  root_dir: string
  scenarios: LocalFile[]
  tools: LocalFile[]
  agents: LocalFile[]
}

export default function DashboardPage() {
  const [status, setStatus] = useState<LocalStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Provider state
  const [providers, setProviders] = useState<ProviderSummary[]>([])
  const [providersLoading, setProvidersLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})

  // Add provider form state
  const [newProvider, setNewProvider] = useState<AddProviderRequest>({
    name: '',
    type: 'ollama',
    base_url: 'http://localhost:11434/v1',
  })
  const [addError, setAddError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const fetchProviders = async () => {
    try {
      const data = await api.listProviders()
      setProviders(data)
    } catch {
      // Providers endpoint may not be available
      setProviders([])
    } finally {
      setProvidersLoading(false)
    }
  }

  const handleAddProvider = async (e: React.FormEvent) => {
    e.preventDefault()
    setAddError(null)
    setAdding(true)

    try {
      await api.addProvider(newProvider)
      await fetchProviders()
      setShowAddForm(false)
      setNewProvider({ name: '', type: 'ollama', base_url: 'http://localhost:11434/v1' })
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to add provider')
    } finally {
      setAdding(false)
    }
  }

  const handleTestProvider = async (name: string) => {
    setTestingProvider(name)
    try {
      const result = await api.testProvider(name)
      setTestResults((prev) => ({
        ...prev,
        [name]: {
          success: result.success,
          message: result.success
            ? `Connected! Found ${result.models_found.length} models (${result.latency_ms}ms)`
            : result.error || 'Connection failed',
        },
      }))
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [name]: { success: false, message: err instanceof Error ? err.message : 'Test failed' },
      }))
    } finally {
      setTestingProvider(null)
    }
  }

  const handleDeleteProvider = async (name: string) => {
    if (!confirm(`Delete provider "${name}"?`)) return
    try {
      await api.deleteProvider(name)
      await fetchProviders()
      setTestResults((prev) => {
        const updated = { ...prev }
        delete updated[name]
        return updated
      })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete provider')
    }
  }

  const getDefaultUrl = (type: string) => {
    switch (type) {
      case 'ollama':
        return 'http://localhost:11434/v1'
      case 'lmstudio':
        return 'http://localhost:1234/v1'
      case 'vllm':
        return 'http://localhost:8000/v1'
      default:
        return 'http://localhost:8000/v1'
    }
  }

  useEffect(() => {
    fetch('/api/v1/local/status')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch status')
        return res.json()
      })
      .then(setStatus)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))

    fetchProviders()
  }, [])

  if (loading) {
    return (
      <div className="p-8 page">
        <div className="text-slate-400">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 page">
        <div className="text-red-400">Error: {error}</div>
      </div>
    )
  }

  if (!status) return null

  return (
    <div className="p-8 page">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-100 mb-2">Dashboard</h1>
        <p className="text-slate-400">
          Root: <code className="panel-subtle px-2 py-1 rounded">{status.root_dir}</code>
        </p>
      </div>

      {/* Scenarios */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <FileCode size={20} />
            Scenarios ({status.scenarios.length})
          </h2>
          <Link
            to="/builder"
            className="flex items-center gap-1 px-3 py-1.5 bg-orange-400 hover:bg-orange-300 text-slate-900 rounded-lg text-sm font-semibold"
          >
            <Plus size={16} />
            Create Scenario
          </Link>
        </div>
        {status.scenarios.length === 0 ? (
          <p className="text-slate-400">No scenarios found in scenarios/</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {status.scenarios.map((scenario) => (
              <div
                key={scenario.id}
                className="panel-card p-4"
              >
                <h3 className="font-medium text-slate-100 mb-1">{scenario.name}</h3>
                <p className="text-sm text-slate-400 mb-3 line-clamp-2">
                  {scenario.description || 'No description'}
                </p>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-500">{scenario.relative_path}</span>
                  <Link
                    to={`/run/${scenario.id}`}
                    className="flex items-center gap-1 px-3 py-1 bg-orange-400 text-slate-900 rounded hover:bg-orange-300 transition-colors text-sm font-medium"
                  >
                    <Play size={14} />
                    Run
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Tools */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <Wrench size={20} />
            Tools ({status.tools.length})
          </h2>
          <Link
            to="/tool-builder"
            className="flex items-center gap-1 px-3 py-1.5 bg-emerald-400 hover:bg-emerald-300 text-slate-900 rounded-lg text-sm font-semibold"
          >
            <Plus size={16} />
            Create Tool
          </Link>
        </div>
        {status.tools.length === 0 ? (
          <p className="text-slate-400">No tools found in tools/</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {status.tools.map((tool) => (
              <span
                key={tool.id}
                className="px-3 py-1 panel-subtle rounded-full text-sm text-slate-200 border border-slate-700/60"
              >
                {tool.name}
              </span>
            ))}
          </div>
        )}
      </section>

      {/* Providers */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <Server size={20} />
            Local Providers ({providers.length})
          </h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-1 px-3 py-1.5 bg-purple-500 hover:bg-purple-400 text-white rounded-lg text-sm font-semibold"
          >
            <Plus size={16} />
            Add Provider
          </button>
        </div>

        {/* Add Provider Form */}
        {showAddForm && (
          <div className="panel-card p-4 mb-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">Add Local Provider</h3>
            <form onSubmit={handleAddProvider} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Name</label>
                  <input
                    type="text"
                    value={newProvider.name}
                    onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
                    placeholder="ollama-local"
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-slate-100 placeholder-slate-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Type</label>
                  <select
                    value={newProvider.type}
                    onChange={(e) => {
                      const type = e.target.value as AddProviderRequest['type']
                      setNewProvider({ ...newProvider, type, base_url: getDefaultUrl(type) })
                    }}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-slate-100"
                  >
                    <option value="ollama">Ollama</option>
                    <option value="lmstudio">LM Studio</option>
                    <option value="vllm">vLLM</option>
                    <option value="openai-compatible">OpenAI Compatible</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Base URL</label>
                <input
                  type="url"
                  value={newProvider.base_url}
                  onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
                  placeholder="http://localhost:11434/v1"
                  className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-slate-100 placeholder-slate-500"
                  required
                />
              </div>
              {addError && <p className="text-red-400 text-xs">{addError}</p>}
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-3 py-1.5 text-slate-400 hover:text-slate-200 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={adding}
                  className="px-3 py-1.5 bg-purple-500 hover:bg-purple-400 text-white rounded text-sm font-medium disabled:opacity-50"
                >
                  {adding ? 'Adding...' : 'Add Provider'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Provider List */}
        {providersLoading ? (
          <p className="text-slate-400">Loading providers...</p>
        ) : providers.length === 0 ? (
          <div className="text-slate-400">
            <p className="mb-2">No local providers configured.</p>
            <p className="text-sm">
              Add a provider to use local models like Ollama, LM Studio, or vLLM.
            </p>
          </div>
        ) : (
          <div className="grid gap-3">
            {providers.map((provider) => (
              <div
                key={provider.name}
                className="panel-card p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  {/* Status indicator */}
                  {provider.status === 'connected' ? (
                    <CheckCircle size={18} className="text-green-400" />
                  ) : provider.status === 'error' ? (
                    <XCircle size={18} className="text-red-400" />
                  ) : (
                    <AlertCircle size={18} className="text-slate-500" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-100">{provider.name}</span>
                      <span className="text-xs px-1.5 py-0.5 bg-slate-700 rounded text-slate-300">
                        {provider.type}
                      </span>
                      {provider.enabled && (
                        <span className="text-xs px-1.5 py-0.5 bg-green-900/50 text-green-400 rounded">
                          enabled
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {provider.base_url}
                    </div>
                    {/* Model list */}
                    {provider.models?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {provider.models.map((model) => (
                          <span
                            key={model}
                            className="text-xs px-2 py-0.5 bg-emerald-900/40 border border-emerald-700/50 rounded text-emerald-300"
                          >
                            {model}
                          </span>
                        ))}
                      </div>
                    )}
                    {(provider.models?.length === 0 || !provider.models) && provider.status === 'connected' && (
                      <div className="text-xs text-slate-500 mt-1">No models available</div>
                    )}
                    {testResults[provider.name] && (
                      <div
                        className={`text-xs mt-1 ${
                          testResults[provider.name].success ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {testResults[provider.name].message}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTestProvider(provider.name)}
                    disabled={testingProvider === provider.name}
                    className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded disabled:opacity-50"
                    title="Test connection"
                  >
                    <RefreshCw
                      size={16}
                      className={testingProvider === provider.name ? 'animate-spin' : ''}
                    />
                  </button>
                  <button
                    onClick={() => handleDeleteProvider(provider.name)}
                    className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded"
                    title="Delete provider"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
