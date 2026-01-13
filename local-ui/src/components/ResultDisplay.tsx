import { useState } from 'react'
import { CheckCircle, XCircle, Trophy, Clock, Zap, DollarSign, Hash, MessageSquare, ChevronDown, ChevronRight, Eye, X, AlertCircle } from 'lucide-react'
import { RunScenarioResponse, CompareModelsResponse } from '../lib/api'

export function formatCost(cost: number | null | undefined): string {
  if (cost === null || cost === undefined) return '-'
  if (cost < 0.0001) return '<$0.0001'
  if (cost < 0.01) return `$${cost.toFixed(4)}`
  return `$${cost.toFixed(3)}`
}

export function SingleRunResult({ result }: { result: RunScenarioResponse }) {
  const [showHistory, setShowHistory] = useState(false)

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {result.evaluation && (
          <div className="panel-card p-4 col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 text-slate-400 mb-2">
              <Trophy className="w-4 h-4" />
              Score
            </div>
            <div className="text-2xl font-bold text-slate-100">
              {result.evaluation.percentage.toFixed(0)}%
            </div>
            <div className="text-xs text-slate-500">
              {result.evaluation.total_score.toFixed(0)} / {result.evaluation.max_score.toFixed(0)} pts
            </div>
          </div>
        )}

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Clock className="w-4 h-4" />
            Latency
          </div>
          <div className="text-2xl font-bold text-slate-100">{((result.latency_ms || 0) / 1000).toFixed(1)}s</div>
        </div>

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <MessageSquare className="w-4 h-4" />
            Messages
          </div>
          <div className="text-2xl font-bold text-slate-100">{result.history?.length || 0}</div>
        </div>

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Zap className="w-4 h-4" />
            Tool Calls
          </div>
          <div className="text-2xl font-bold text-slate-100">{result.tool_calls?.length || 0}</div>
        </div>

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Hash className="w-4 h-4" />
            Tokens
          </div>
          <div className="text-2xl font-bold text-slate-100">
            {((result.input_tokens || 0) + (result.output_tokens || 0)).toLocaleString()}
          </div>
          <div className="text-xs text-slate-500">
            {(result.input_tokens || 0).toLocaleString()} in / {(result.output_tokens || 0).toLocaleString()} out
          </div>
        </div>

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <DollarSign className="w-4 h-4" />
            Cost
          </div>
          <div className="text-2xl font-bold text-emerald-300">{formatCost(result.cost_usd)}</div>
        </div>
      </div>

      {/* Goals */}
      {result.evaluation && result.evaluation.goals && result.evaluation.goals.length > 0 && (
        <div className="panel-card p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Goals</h3>
          <div className="space-y-3">
            {result.evaluation.goals.map((goal) => (
              <div
                key={goal.id}
                className={`flex items-center justify-between p-3 rounded-lg border ${
                  goal.achieved ? 'bg-emerald-500/10 border-emerald-400/40' : 'bg-slate-950/40 border-slate-800/70'
                }`}
              >
                <div className="flex items-center gap-3">
                  {goal.achieved ? (
                    <CheckCircle className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-500" />
                  )}
                  <div>
                    <div className="font-medium text-slate-100">{goal.name || goal.id}</div>
                    {goal.reason && (
                      <div className="text-sm text-slate-400">{goal.reason}</div>
                    )}
                  </div>
                </div>
                <div className={`font-bold ${goal.achieved ? 'text-emerald-300' : 'text-slate-500'}`}>
                  {goal.achieved ? `+${goal.points}` : '0'} pts
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Judge Result */}
      {result.evaluation?.judge && (
        <div className="panel-card p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Judge Evaluation</h3>
          <div className="flex items-center gap-4 mb-4">
            <div className={`text-3xl font-bold ${result.evaluation.judge.passed ? 'text-emerald-300' : 'text-red-400'}`}>
              {(result.evaluation.judge.score * 100).toFixed(0)}%
            </div>
            <div className={`px-3 py-1 rounded-full text-sm ${
              result.evaluation.judge.passed ? 'bg-emerald-500/15 text-emerald-300' : 'bg-red-900/50 text-red-400'
            }`}>
              {result.evaluation.judge.passed ? 'Passed' : 'Failed'}
            </div>
          </div>
          <p className="text-slate-400">{result.evaluation.judge.reasoning}</p>
        </div>
      )}

      {/* Response */}
      {result.response && (
        <div className="panel-card p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Response</h3>
          <div className="panel-subtle rounded-lg p-4 whitespace-pre-wrap text-slate-200">
            {result.response || '(No response)'}
          </div>
        </div>
      )}

      {/* History Toggle */}
      {result.history && result.history.length > 0 && (
        <div className="panel-card">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="w-full p-4 text-left flex items-center justify-between hover:bg-slate-800/60 transition-colors rounded-lg"
          >
            <span className="font-semibold text-slate-100">Conversation History ({result.history.length} messages)</span>
            <span className="text-slate-400">{showHistory ? 'Hide' : 'Show'}</span>
          </button>

          {showHistory && (
            <div className="px-6 pb-6 space-y-4">
              {result.history.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${
                    msg.role === 'user' ? 'bg-orange-500/10 border border-orange-400/40' :
                    msg.role === 'assistant' ? 'panel-subtle' :
                    msg.role === 'tool' ? 'bg-amber-500/10 border border-amber-400/40' :
                    'panel-subtle'
                  }`}
                >
                  <div className="text-xs font-medium text-slate-500 mb-1 uppercase">
                    {msg.role}
                  </div>
                  <div className="text-slate-200 whitespace-pre-wrap text-sm">
                    {msg.content || '(empty)'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tool Calls */}
      {result.tool_calls && result.tool_calls.length > 0 && (
        <div className="panel-card p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Tool Calls ({result.tool_calls.length})</h3>
          <div className="space-y-3">
            {result.tool_calls.map((call, idx) => (
              <ToolCallDetail key={idx} call={call} />
            ))}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {result.error && (
        <div className="panel-card p-4 border-l-4 border-l-red-500 bg-red-950/30">
          <div className="flex items-center gap-2 text-red-400 mb-1">
            <AlertCircle className="w-4 h-4" />
            <span className="font-medium">Error</span>
          </div>
          <p className="text-sm text-red-300">{result.error}</p>
        </div>
      )}
    </div>
  )
}

// Helper to format JSON strings nicely
function formatJsonValue(value: unknown): string {
  if (typeof value === 'string') {
    // Try to parse and re-format if it's a JSON string
    try {
      const parsed = JSON.parse(value)
      return JSON.stringify(parsed, null, 2)
    } catch {
      // Not valid JSON, return as-is
      return value
    }
  }
  return JSON.stringify(value, null, 2)
}

// Component for displaying tool call details with expandable result/error
function ToolCallDetail({ call }: { call: { tool: string; action: string; args: Record<string, unknown>; result?: unknown; success: boolean; error?: string | null } }) {
  const [expanded, setExpanded] = useState(false)
  const hasResult = call.result !== undefined && call.result !== null
  const hasError = call.error !== undefined && call.error !== null

  return (
    <div className={`panel-subtle rounded-lg overflow-hidden ${!call.success ? 'border border-red-500/30' : ''}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 text-left flex items-center justify-between hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
          <code className="text-orange-300">{call.tool}.{call.action}()</code>
        </div>
        <span className={`text-sm ${call.success ? 'text-emerald-300' : 'text-red-400'}`}>
          {call.success ? '✓ Success' : '✗ Failed'}
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Arguments */}
          <div>
            <div className="text-xs font-medium text-slate-500 mb-1">Arguments</div>
            <pre className="text-xs text-slate-400 overflow-auto bg-slate-950/50 rounded p-2">
              {formatJsonValue(call.args)}
            </pre>
          </div>

          {/* Result */}
          {hasResult && (
            <div>
              <div className="text-xs font-medium text-emerald-400 mb-1">Result</div>
              <pre className="text-xs text-slate-400 overflow-auto bg-emerald-950/30 rounded p-2 max-h-48">
                {formatJsonValue(call.result)}
              </pre>
            </div>
          )}

          {/* Error */}
          {hasError && (
            <div>
              <div className="text-xs font-medium text-red-400 mb-1">Error</div>
              <pre className="text-xs text-red-300 overflow-auto bg-red-950/30 rounded p-2">
                {call.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface ModelAnalysis {
  modelId: string
  score: number
  cost: number
  latency: number
  efficiency: number // score per dollar
  badges: string[]
}

function analyzeModels(comparison: CompareModelsResponse): ModelAnalysis[] {
  const ranking = comparison.ranking || []
  const analyses: ModelAnalysis[] = []

  // Calculate efficiency for each model
  for (const modelId of ranking) {
    const stats = comparison.stats?.[modelId]
    if (!stats) continue

    const score = stats.avg_score || 0
    const cost = stats.avg_cost_usd || 0
    const latency = stats.avg_latency_ms || 0
    // Efficiency: score points per $0.01 spent (avoid division by zero)
    const efficiency = cost > 0 ? score / (cost * 100) : score > 0 ? Infinity : 0

    analyses.push({ modelId, score, cost, latency, efficiency, badges: [] })
  }

  if (analyses.length === 0) return analyses

  // Find best in each category
  const bestQuality = analyses.reduce((a, b) => a.score > b.score ? a : b)
  const bestValue = analyses.reduce((a, b) => a.efficiency > b.efficiency ? a : b)
  const qualifyingForFastest = analyses.filter(a => a.score >= bestQuality.score * 0.7) // 70% of best score
  const fastest = qualifyingForFastest.length > 0
    ? qualifyingForFastest.reduce((a, b) => a.latency < b.latency ? a : b)
    : null

  // Assign badges
  for (const analysis of analyses) {
    if (analysis.modelId === bestQuality.modelId) {
      analysis.badges.push('quality')
    }
    if (analysis.modelId === bestValue.modelId && bestValue.cost > 0) {
      analysis.badges.push('value')
    }
    if (fastest && analysis.modelId === fastest.modelId) {
      analysis.badges.push('fast')
    }
  }

  return analyses
}

function Badge({ type }: { type: string }) {
  switch (type) {
    case 'quality':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
          <Trophy className="w-3 h-3" /> Best Quality
        </span>
      )
    case 'value':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          <DollarSign className="w-3 h-3" /> Best Value
        </span>
      )
    case 'fast':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30">
          <Zap className="w-3 h-3" /> Fastest
        </span>
      )
    default:
      return null
  }
}

// Modal component for viewing run details
function RunDetailModal({ run, onClose }: { run: RunScenarioResponse; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={onClose}>
      <div
        className="bg-slate-900 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Run Details</h2>
            <p className="text-sm text-slate-400">{run.model}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="overflow-auto p-4">
          <SingleRunResult result={run} />
        </div>
      </div>
    </div>
  )
}

export function ComparisonResult({ comparison }: { comparison: CompareModelsResponse }) {
  const [expandedModel, setExpandedModel] = useState<string | null>(null)
  const [selectedRun, setSelectedRun] = useState<RunScenarioResponse | null>(null)

  const ranking = comparison.ranking || []
  const analyses = analyzeModels(comparison)
  const analysisMap = new Map(analyses.map(a => [a.modelId, a]))

  // Group results by model
  const resultsByModel = new Map<string, RunScenarioResponse[]>()
  if (comparison.results) {
    for (const result of comparison.results) {
      const existing = resultsByModel.get(result.model) || []
      existing.push(result as RunScenarioResponse)
      resultsByModel.set(result.model, existing)
    }
  }

  const hasResults = comparison.results && comparison.results.length > 0

  return (
    <>
      {/* Modal for viewing run details */}
      {selectedRun && (
        <RunDetailModal run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
    <div className="space-y-6">
      {/* Recommendations Summary */}
      {analyses.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {analyses.find(a => a.badges.includes('quality')) && (
            <div className="panel-card p-4 border-l-4 border-l-amber-400">
              <div className="flex items-center gap-2 text-amber-300 mb-1">
                <Trophy className="w-4 h-4" />
                <span className="text-sm font-medium">Best Quality</span>
              </div>
              <div className="text-lg font-semibold text-slate-100">
                {analyses.find(a => a.badges.includes('quality'))?.modelId.split('/')[1] || analyses.find(a => a.badges.includes('quality'))?.modelId}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Highest score: {analyses.find(a => a.badges.includes('quality'))?.score.toFixed(1)} pts
              </div>
            </div>
          )}
          {analyses.find(a => a.badges.includes('value')) && (
            <div className="panel-card p-4 border-l-4 border-l-emerald-400">
              <div className="flex items-center gap-2 text-emerald-300 mb-1">
                <DollarSign className="w-4 h-4" />
                <span className="text-sm font-medium">Best Value</span>
              </div>
              <div className="text-lg font-semibold text-slate-100">
                {analyses.find(a => a.badges.includes('value'))?.modelId.split('/')[1] || analyses.find(a => a.badges.includes('value'))?.modelId}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {(() => {
                  const bestValue = analyses.find(a => a.badges.includes('value'))
                  const bestQuality = analyses.find(a => a.badges.includes('quality'))
                  if (!bestValue || !bestQuality) return ''
                  if (bestValue.cost === 0) return 'Free!'
                  if (bestValue.modelId === bestQuality.modelId) return 'Also the best quality!'
                  const qualityPct = Math.round((bestValue.score / bestQuality.score) * 100)
                  const costPct = bestQuality.cost > 0
                    ? Math.round((bestValue.cost / bestQuality.cost) * 100)
                    : 0
                  if (costPct === 0) return `${qualityPct}% quality, nearly free`
                  return `${qualityPct}% quality at ${costPct}% cost`
                })()}
              </div>
            </div>
          )}
          {analyses.find(a => a.badges.includes('fast')) && (
            <div className="panel-card p-4 border-l-4 border-l-blue-400">
              <div className="flex items-center gap-2 text-blue-300 mb-1">
                <Zap className="w-4 h-4" />
                <span className="text-sm font-medium">Fastest</span>
              </div>
              <div className="text-lg font-semibold text-slate-100">
                {analyses.find(a => a.badges.includes('fast'))?.modelId.split('/')[1] || analyses.find(a => a.badges.includes('fast'))?.modelId}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {((analyses.find(a => a.badges.includes('fast'))?.latency || 0) / 1000).toFixed(1)}s avg latency
              </div>
            </div>
          )}
        </div>
      )}

      {/* Stats Table */}
      <div className="panel-card overflow-hidden">
        <div className="p-4 border-b border-slate-800/70">
          <h3 className="text-lg font-semibold text-slate-100">Model Comparison</h3>
          <p className="text-sm text-slate-400">
            {comparison.runs_per_model} run(s) per model
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-950/70">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Rank</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Model</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-400">Score</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-400">Judge</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-400">Latency</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-400">Tokens</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-400">Cost</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((modelId, idx) => {
                const stats = comparison.stats?.[modelId]
                const analysis = analysisMap.get(modelId)
                const modelRuns = resultsByModel.get(modelId) || []
                const isExpanded = expandedModel === modelId
                if (!stats) return null

                return (
                  <>
                    <tr
                      key={modelId}
                      className={`border-t border-slate-800/70 hover:bg-slate-900/40 ${hasResults ? 'cursor-pointer' : ''}`}
                      onClick={() => hasResults && setExpandedModel(isExpanded ? null : modelId)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {hasResults && (
                            isExpanded
                              ? <ChevronDown className="w-4 h-4 text-slate-500" />
                              : <ChevronRight className="w-4 h-4 text-slate-500" />
                          )}
                          <span className={`font-bold ${idx === 0 ? 'text-amber-300' : 'text-slate-400'}`}>
                            #{idx + 1}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-slate-100 font-medium">{modelId}</div>
                        {analysis && analysis.badges.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {analysis.badges.map(badge => <Badge key={badge} type={badge} />)}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-100 font-semibold">{stats.avg_score?.toFixed(1) || '0'}</td>
                      <td className="px-4 py-3 text-right text-slate-400">
                        {stats.avg_judge_score != null ? `${(stats.avg_judge_score * 100).toFixed(0)}%` : '-'}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-400">{((stats.avg_latency_ms || 0) / 1000).toFixed(1)}s</td>
                      <td className="px-4 py-3 text-right text-slate-400">
                        {((stats.total_input_tokens || 0) + (stats.total_output_tokens || 0)).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right text-emerald-300 font-medium">{formatCost(stats.avg_cost_usd)}</td>
                    </tr>

                    {/* Expanded runs for this model */}
                    {isExpanded && modelRuns.length > 0 && (
                      <tr key={`${modelId}-runs`}>
                        <td colSpan={7} className="px-4 py-2 bg-slate-950/50">
                          <div className="ml-8 space-y-2">
                            <div className="text-sm font-medium text-slate-400 mb-2">
                              Individual Runs ({modelRuns.length})
                            </div>
                            {modelRuns.map((run, runIdx) => (
                              <div
                                key={runIdx}
                                className="flex items-center justify-between p-3 rounded-lg bg-slate-900/50 border border-slate-800/50 hover:bg-slate-800/50 cursor-pointer"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setSelectedRun(run)
                                }}
                              >
                                <div className="flex items-center gap-3">
                                  <span className="text-slate-500 text-sm">Run {runIdx + 1}</span>
                                  <span className="text-slate-100 font-medium">
                                    {run.evaluation?.percentage?.toFixed(0) || 0}%
                                  </span>
                                  {run.evaluation?.judge && (
                                    <span className={`text-sm ${run.evaluation.judge.passed ? 'text-emerald-300' : 'text-red-400'}`}>
                                      {run.evaluation.judge.passed ? '✓ Passed' : '✗ Failed'}
                                    </span>
                                  )}
                                  {run.error && (
                                    <span className="text-sm text-red-400 flex items-center gap-1">
                                      <AlertCircle className="w-3 h-3" /> Error
                                    </span>
                                  )}
                                </div>
                                <button
                                  className="flex items-center gap-1 text-sm text-orange-300 hover:text-orange-200"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setSelectedRun(run)
                                  }}
                                >
                                  <Eye className="w-4 h-4" />
                                  View Details
                                </button>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Goal Achievement Rates */}
      {comparison.stats && Object.values(comparison.stats).some(s => s.goal_rates && Object.keys(s.goal_rates).length > 0) && (
        <div className="panel-card p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Goal Achievement Rates</h3>

          {/* Collect all goal IDs */}
          {(() => {
            const allGoals = new Set<string>()
            Object.values(comparison.stats).forEach(s => {
              if (s.goal_rates) {
                Object.keys(s.goal_rates).forEach(g => allGoals.add(g))
              }
            })

            return (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-950/70">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Model</th>
                      {Array.from(allGoals).map(goal => (
                        <th key={goal} className="px-4 py-3 text-right text-sm font-medium text-slate-400">
                          {goal}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ranking.map(modelId => {
                      const stats = comparison.stats?.[modelId]
                      if (!stats) return null

                      return (
                        <tr key={modelId} className="border-t border-slate-800/70">
                          <td className="px-4 py-3 text-slate-100 font-medium">{modelId}</td>
                          {Array.from(allGoals).map(goal => {
                            const rate = stats.goal_rates?.[goal] ?? 0
                            return (
                              <td key={goal} className="px-4 py-3 text-right">
                                <span className={rate >= 100 ? 'text-emerald-300' : rate >= 50 ? 'text-amber-300' : 'text-red-400'}>
                                  {rate.toFixed(0)}%
                                </span>
                              </td>
                            )
                          })}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )
          })()}
        </div>
      )}
    </div>
    </>
  )
}
