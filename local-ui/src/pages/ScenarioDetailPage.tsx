import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Play,
  Pencil,
  ArrowLeft,
  Wrench,
  Target,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  Server,
  Zap,
  CheckCircle,
  FileText,
  Variable,
  Scale,
} from 'lucide-react'
import {
  api,
  ScenarioDetail,
  ScenarioGoalInfo,
  ScenarioToolInfo,
} from '../lib/api'

interface StepSpec {
  id: string
  action: string
  params?: Record<string, unknown>
}

interface McpServerSpec {
  name: string
  url?: string
  command?: string
  args?: string[]
}

interface JudgeSpec {
  type: string
  model?: string
  rubric?: string
  pass_threshold?: number
  pattern?: string
}

export default function ScenarioDetailPage() {
  const { scenarioId } = useParams<{ scenarioId: string }>()
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null)
  const [goals, setGoals] = useState<ScenarioGoalInfo[]>([])
  const [tools, setTools] = useState<ScenarioToolInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Expandable sections
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['tools', 'evaluation', 'interaction'])
  )

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  useEffect(() => {
    if (!scenarioId) return

    setLoading(true)
    Promise.all([
      api.getScenario(scenarioId),
      api.getScenarioGoals(scenarioId).catch(() => []),
      api.getScenarioTools(scenarioId).catch(() => []),
    ])
      .then(([s, g, t]) => {
        setScenario(s)
        setGoals(g)
        setTools(t)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [scenarioId])

  if (loading) {
    return (
      <div className="p-8 page">
        <div className="text-slate-400">Loading scenario...</div>
      </div>
    )
  }

  if (error || !scenario) {
    return (
      <div className="p-8 page">
        <div className="text-red-400">Error: {error || 'Scenario not found'}</div>
        <Link to="/" className="text-orange-400 hover:underline mt-4 inline-block">
          &larr; Back to Dashboard
        </Link>
      </div>
    )
  }

  const content = scenario.content || {}
  const steps = (content.steps as StepSpec[]) || []
  const mcpServers = (content.mcp_servers as McpServerSpec[]) || []
  const inlineTools = (content.tools as Record<string, unknown>) || {}
  const toolsFrom = (content.tools_from as string[]) || []
  const judge = content.evaluation
    ? ((content.evaluation as Record<string, unknown>).judge as JudgeSpec)
    : null

  // Calculate max score from evaluation config
  const evalContent = content.evaluation as Record<string, unknown> | undefined
  const goalsContent = evalContent?.goals as Array<Record<string, unknown>> | undefined
  const maxScore = evalContent
    ? (evalContent.max_score as number) ||
      (goalsContent?.reduce((sum, g) => sum + ((g.points as number) || 0), 0) ?? 0)
    : null
  const variables = scenario.variables || []
  const isMultiTurn = steps.length > 0
  const category = (content.category as string) || null
  const tags = (content.tags as string[]) || []

  // Count tools - API returns all tools, inline tools are shown separately for display
  // Don't double-count: use API tools count OR inline count, not both
  const totalToolCount = tools.length > 0 ? tools.length : Object.keys(inlineTools).length

  return (
    <div className="p-8 page max-w-5xl">
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-slate-400 hover:text-slate-200 mb-6 text-sm"
      >
        <ArrowLeft size={16} />
        Back to Dashboard
      </Link>

      {/* Header */}
      <div className="panel-card p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-semibold text-slate-100 mb-2">
              {scenario.name}
            </h1>
            <p className="text-slate-400 mb-4">{scenario.description}</p>

            {/* Tags & Category */}
            <div className="flex flex-wrap gap-2">
              {category && (
                <span className="px-2 py-1 bg-purple-900/40 border border-purple-700/50 rounded text-xs text-purple-300">
                  {category}
                </span>
              )}
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-1 bg-slate-700/50 border border-slate-600/50 rounded text-xs text-slate-300"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 ml-4">
            <Link
              to={`/builder?scenario=${scenarioId}`}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm font-medium transition-colors"
            >
              <Pencil size={16} />
              Edit
            </Link>
            <Link
              to={`/run/${scenarioId}`}
              className="flex items-center gap-1.5 px-4 py-2 bg-orange-400 hover:bg-orange-300 text-slate-900 rounded-lg text-sm font-semibold transition-colors"
            >
              <Play size={16} />
              Run
            </Link>
          </div>
        </div>

        {/* Quick stats */}
        <div className="flex gap-6 mt-6 pt-4 border-t border-slate-700/60">
          <div className="flex items-center gap-2 text-sm">
            <MessageSquare size={16} className="text-slate-500" />
            <span className="text-slate-400">
              {isMultiTurn ? `Multi-turn (${steps.length} steps)` : 'Single-turn'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Wrench size={16} className="text-slate-500" />
            <span className="text-slate-400">
              {mcpServers.length > 0 && totalToolCount === 0
                ? `${mcpServers.length} MCP server${mcpServers.length !== 1 ? 's' : ''}`
                : `${totalToolCount} tool${totalToolCount !== 1 ? 's' : ''}${mcpServers.length > 0 ? ` + ${mcpServers.length} MCP` : ''}`}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Target size={16} className="text-slate-500" />
            <span className="text-slate-400">
              {goals.length} goal{goals.length !== 1 ? 's' : ''}
              {maxScore && ` (${maxScore} pt${maxScore !== 1 ? 's' : ''})`}
            </span>
          </div>
          {variables.length > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <Variable size={16} className="text-slate-500" />
              <span className="text-slate-400">{variables.length} variables</span>
            </div>
          )}
        </div>
      </div>

      {/* Tools Section */}
      <div className="panel-card mb-4">
        <button
          onClick={() => toggleSection('tools')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Wrench size={18} className="text-emerald-400" />
            <h2 className="font-semibold text-slate-100">
              Tools
              {mcpServers.length > 0 && totalToolCount === 0 ? (
                <span className="ml-2 text-sm font-normal text-slate-400">
                  ({mcpServers.length} MCP server{mcpServers.length > 1 ? 's' : ''})
                </span>
              ) : (
                <span className="ml-2 text-sm font-normal text-slate-400">
                  ({totalToolCount}{mcpServers.length > 0 ? ` + ${mcpServers.length} MCP` : ''})
                </span>
              )}
            </h2>
          </div>
          {expandedSections.has('tools') ? (
            <ChevronDown size={18} className="text-slate-500" />
          ) : (
            <ChevronRight size={18} className="text-slate-500" />
          )}
        </button>

        {expandedSections.has('tools') && (
          <div className="px-4 pb-4 space-y-4">
            {/* MCP Servers */}
            {mcpServers.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  MCP Servers
                </h3>
                {mcpServers.map((server) => (
                  <div
                    key={server.name}
                    className="p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg mb-2"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Server size={14} className="text-cyan-400" />
                      <span className="font-medium text-slate-200">{server.name}</span>
                      <span className="text-xs px-1.5 py-0.5 bg-cyan-900/40 text-cyan-300 rounded">
                        MCP
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mb-2">
                      {server.url ? (
                        <span className="font-mono">{server.url}</span>
                      ) : server.command ? (
                        <span className="font-mono">
                          {server.command} {server.args?.join(' ')}
                        </span>
                      ) : null}
                    </div>
                    {/* Show tools from this server */}
                    {tools.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {tools.map((tool) => (
                          <span
                            key={tool.name}
                            className="text-xs px-2 py-1 bg-emerald-900/30 border border-emerald-700/40 rounded text-emerald-300"
                            title={tool.description}
                          >
                            {tool.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Tool Libraries */}
            {toolsFrom.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Tool Libraries
                </h3>
                <div className="flex flex-wrap gap-2">
                  {toolsFrom.map((lib) => (
                    <span
                      key={lib}
                      className="px-3 py-1.5 bg-slate-800/50 border border-slate-700/60 rounded text-sm text-slate-300"
                    >
                      {lib}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Inline Tools (Mock) */}
            {Object.keys(inlineTools).length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Inline Tools (Mock)
                </h3>
                <div className="space-y-2">
                  {Object.entries(inlineTools).map(([name, config]) => {
                    const toolConfig = config as Record<string, unknown>
                    const actions = toolConfig.actions as Record<string, unknown> | undefined
                    const actionNames = actions ? Object.keys(actions) : []

                    return (
                      <div
                        key={name}
                        className="p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <Zap size={14} className="text-yellow-400" />
                          <span className="font-medium text-slate-200">{name}</span>
                          <span className="text-xs px-1.5 py-0.5 bg-yellow-900/40 text-yellow-300 rounded">
                            Mock
                          </span>
                        </div>
                        {typeof toolConfig.description === 'string' && toolConfig.description && (
                          <p className="text-xs text-slate-500 mb-2">
                            {toolConfig.description}
                          </p>
                        )}
                        {actionNames.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {actionNames.map((action) => (
                              <span
                                key={action}
                                className="text-xs px-2 py-1 bg-slate-700/50 rounded text-slate-400"
                              >
                                {action}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* No tools */}
            {mcpServers.length === 0 &&
              toolsFrom.length === 0 &&
              Object.keys(inlineTools).length === 0 && (
                <p className="text-slate-500 text-sm">No tools configured</p>
              )}
          </div>
        )}
      </div>

      {/* Evaluation Section */}
      <div className="panel-card mb-4">
        <button
          onClick={() => toggleSection('evaluation')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Target size={18} className="text-orange-400" />
            <h2 className="font-semibold text-slate-100">
              Evaluation
              {maxScore && (
                <span className="ml-2 text-sm font-normal text-slate-400">
                  ({maxScore} pts max)
                </span>
              )}
            </h2>
          </div>
          {expandedSections.has('evaluation') ? (
            <ChevronDown size={18} className="text-slate-500" />
          ) : (
            <ChevronRight size={18} className="text-slate-500" />
          )}
        </button>

        {expandedSections.has('evaluation') && (
          <div className="px-4 pb-4 space-y-4">
            {/* Goals */}
            {goals.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                  Goals
                </h3>
                <div className="space-y-2">
                  {goals.map((goal) => {
                    // Try to get detection type from content
                    const evalContent = content.evaluation as Record<string, unknown> | undefined
                    const goalsContent = evalContent?.goals as Array<Record<string, unknown>> | undefined
                    const goalContent = goalsContent?.find((g) => g.id === goal.id)
                    const detection = goalContent?.detection as Record<string, unknown> | undefined
                    const detectionType = detection?.type as string | undefined
                    const points = goalContent?.points as number | undefined

                    return (
                      <div
                        key={goal.id}
                        className="flex items-start gap-3 p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg"
                      >
                        <CheckCircle size={16} className="text-slate-600 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-slate-200">{goal.name}</span>
                            {goal.outcome && (
                              <span className="text-xs px-1.5 py-0.5 bg-blue-900/40 text-blue-300 rounded">
                                outcome
                              </span>
                            )}
                          </div>
                          {goal.description && (
                            <p className="text-xs text-slate-500">{goal.description}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {detectionType && (
                            <span className="text-xs px-2 py-1 bg-slate-700/50 rounded text-slate-400 font-mono">
                              {detectionType}
                            </span>
                          )}
                          {points !== undefined && (
                            <span className="text-sm font-semibold text-orange-400">
                              {points} pts
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Judge */}
            {judge && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                  Judge
                </h3>
                <div className="p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Scale size={14} className="text-purple-400" />
                    <span className="font-medium text-slate-200 capitalize">
                      {judge.type} Judge
                    </span>
                    {judge.model && (
                      <span className="text-xs px-1.5 py-0.5 bg-purple-900/40 text-purple-300 rounded">
                        {judge.model}
                      </span>
                    )}
                  </div>
                  {judge.pass_threshold !== undefined && (
                    <p className="text-xs text-slate-500 mb-2">
                      Pass threshold: {(judge.pass_threshold * 100).toFixed(0)}%
                    </p>
                  )}
                  {judge.rubric && (
                    <details className="text-xs">
                      <summary className="text-slate-400 cursor-pointer hover:text-slate-300">
                        View rubric
                      </summary>
                      <pre className="mt-2 p-2 bg-slate-900 rounded text-slate-400 overflow-auto max-h-48 whitespace-pre-wrap">
                        {judge.rubric}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            )}

            {/* No evaluation */}
            {goals.length === 0 && !judge && (
              <p className="text-slate-500 text-sm">No evaluation configured</p>
            )}
          </div>
        )}
      </div>

      {/* Interaction Section */}
      <div className="panel-card mb-4">
        <button
          onClick={() => toggleSection('interaction')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-blue-400" />
            <h2 className="font-semibold text-slate-100">
              Interaction
              <span className="ml-2 text-sm font-normal text-slate-400">
                ({isMultiTurn ? 'Multi-turn' : 'Single-turn'})
              </span>
            </h2>
          </div>
          {expandedSections.has('interaction') ? (
            <ChevronDown size={18} className="text-slate-500" />
          ) : (
            <ChevronRight size={18} className="text-slate-500" />
          )}
        </button>

        {expandedSections.has('interaction') && (
          <div className="px-4 pb-4 space-y-4">
            {/* System Prompt */}
            {typeof content.system_prompt === 'string' && content.system_prompt && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  System Prompt
                </h3>
                <pre className="p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg text-xs text-slate-300 overflow-auto max-h-48 whitespace-pre-wrap">
                  {content.system_prompt}
                </pre>
              </div>
            )}

            {/* Steps (Multi-turn) */}
            {isMultiTurn && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                  Steps
                </h3>
                <div className="space-y-2">
                  {steps.map((step, idx) => (
                    <div
                      key={step.id}
                      className="flex items-start gap-3 p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg"
                    >
                      <div className="w-6 h-6 rounded-full bg-blue-900/40 border border-blue-700/50 flex items-center justify-center text-xs text-blue-300 flex-shrink-0">
                        {idx + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-slate-200">{step.id}</span>
                          <span className="text-xs px-1.5 py-0.5 bg-slate-700/50 text-slate-400 rounded font-mono">
                            {step.action}
                          </span>
                        </div>
                        {typeof step.params?.content === 'string' && step.params.content && (
                          <p className="text-xs text-slate-500 line-clamp-2">
                            {step.params.content.substring(0, 100)}
                            {step.params.content.length > 100 && '...'}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Prompt (Single-turn) */}
            {!isMultiTurn && typeof content.prompt === 'string' && content.prompt && (
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Prompt
                </h3>
                <pre className="p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg text-xs text-slate-300 overflow-auto max-h-48 whitespace-pre-wrap">
                  {content.prompt}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Variables Section */}
      {variables.length > 0 && (
        <div className="panel-card mb-4">
          <button
            onClick={() => toggleSection('variables')}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Variable size={18} className="text-indigo-400" />
              <h2 className="font-semibold text-slate-100">
                Variables ({variables.length})
              </h2>
            </div>
            {expandedSections.has('variables') ? (
              <ChevronDown size={18} className="text-slate-500" />
            ) : (
              <ChevronRight size={18} className="text-slate-500" />
            )}
          </button>

          {expandedSections.has('variables') && (
            <div className="px-4 pb-4">
              <div className="grid gap-2">
                {variables.map((v) => (
                  <div
                    key={v.name}
                    className="flex items-center justify-between p-3 bg-slate-800/50 border border-slate-700/60 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <code className="text-sm font-mono text-indigo-300">{`{{${v.name}}}`}</code>
                      <span className="text-xs px-1.5 py-0.5 bg-slate-700/50 text-slate-400 rounded">
                        {v.type}
                      </span>
                      {v.required && (
                        <span className="text-xs px-1.5 py-0.5 bg-red-900/40 text-red-300 rounded">
                          required
                        </span>
                      )}
                    </div>
                    {v.default !== undefined && (
                      <span className="text-xs text-slate-500">
                        default: {JSON.stringify(v.default)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* File Info */}
      <div className="panel-card">
        <button
          onClick={() => toggleSection('file')}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-slate-500" />
            <h2 className="font-semibold text-slate-100">File</h2>
          </div>
          {expandedSections.has('file') ? (
            <ChevronDown size={18} className="text-slate-500" />
          ) : (
            <ChevronRight size={18} className="text-slate-500" />
          )}
        </button>

        {expandedSections.has('file') && (
          <div className="px-4 pb-4">
            <p className="text-xs text-slate-500 font-mono">{scenario.path}</p>
          </div>
        )}
      </div>
    </div>
  )
}
