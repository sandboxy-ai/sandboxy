import { Link } from 'react-router-dom'
import { Play, AlertTriangle, Shield, Bot } from 'lucide-react'
import { useModules } from '../hooks/useModules'

const categoryIcons: Record<string, React.ReactNode> = {
  'social-engineering': <AlertTriangle className="text-accent" size={24} />,
  'security': <Shield className="text-accent" size={24} />,
  'default': <Bot className="text-accent" size={24} />,
}

export default function HomePage() {
  const { modules, loading, error } = useModules()

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Scenarios</h1>
          <p className="text-gray-400">
            Select a scenario to test your social engineering skills against AI agents
          </p>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4 mb-6">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Module grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {modules.map((module) => (
              <Link
                key={module.id}
                to={`/session/${module.slug}`}
                className="group bg-dark-card border border-dark-border rounded-xl p-6 hover:border-accent transition-colors"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-dark-bg rounded-lg flex items-center justify-center">
                    {categoryIcons[module.category || 'default'] || categoryIcons['default']}
                  </div>
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <Play className="text-accent" size={20} />
                  </div>
                </div>

                <h3 className="text-lg font-semibold text-white mb-2">
                  {module.name}
                </h3>
                <p className="text-gray-400 text-sm line-clamp-2">
                  {module.description || 'No description available'}
                </p>

                {module.category && (
                  <div className="mt-4">
                    <span className="text-xs bg-dark-bg text-gray-400 px-2 py-1 rounded">
                      {module.category}
                    </span>
                  </div>
                )}
              </Link>
            ))}

            {/* Empty state */}
            {modules.length === 0 && (
              <div className="col-span-full text-center py-12">
                <Bot className="mx-auto text-gray-600 mb-4" size={48} />
                <h3 className="text-lg font-semibold text-white mb-2">
                  No scenarios yet
                </h3>
                <p className="text-gray-400 mb-4">
                  Create your first scenario using the builder
                </p>
                <Link
                  to="/builder"
                  className="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded-lg transition-colors"
                >
                  <Wrench size={16} />
                  Open Builder
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Wrench(props: { size: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={props.size}
      height={props.size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  )
}
