import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Play, FileCode, Wrench, Bot, Plus } from 'lucide-react'

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

  useEffect(() => {
    fetch('/api/v1/local/status')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch status')
        return res.json()
      })
      .then(setStatus)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
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

      {/* Agents */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
          <Bot size={20} />
          Agents ({status.agents.length})
        </h2>
        {status.agents.length === 0 ? (
          <p className="text-slate-400">No agents found in agents/</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {status.agents.map((agent) => (
              <span
                key={agent.id}
                className="px-3 py-1 panel-subtle rounded-full text-sm text-slate-200 border border-slate-700/60"
              >
                {agent.name}
              </span>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
