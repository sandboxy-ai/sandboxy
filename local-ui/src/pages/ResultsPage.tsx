import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Clock, Play, Eye, Search, Filter, ChevronDown, ChevronRight, GitCompare, Zap } from 'lucide-react'
import { RunScenarioResponse, CompareModelsResponse } from '../lib/api'
import { SingleRunResult, ComparisonResult } from '../components/ResultDisplay'

interface RunResult {
  filename: string
  path: string
  scenario_id: string
  timestamp: string
  metadata: Record<string, unknown>
}

type ResultTypeFilter = 'all' | 'single' | 'comparison'

// Helper to detect if a result is a comparison based on filename
const isComparisonResult = (result: RunResult): boolean => {
  return result.scenario_id.endsWith('_comparison') || result.filename.includes('_comparison_')
}

// Get base scenario name without _comparison suffix
const getBaseScenarioId = (scenarioId: string): string => {
  return scenarioId.replace(/_comparison$/, '')
}

// The stored result format - can be either a single run or comparison
interface StoredResult {
  scenario_id: string
  timestamp?: string
  result?: Record<string, unknown>
  // Comparison fields might be at top level or nested in result
  ranking?: string[]
  winner?: string
  runs_per_model?: number
  stats?: Record<string, unknown>
  models?: string[]
  // Single run fields might be at top level or nested in result
  model?: string
  response?: string
  history?: unknown[]
  tool_calls?: unknown[]
  evaluation?: unknown
}

export default function ResultsPage() {
  const [results, setResults] = useState<RunResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedResult, setSelectedResult] = useState<StoredResult | null>(null)
  const [viewingFile, setViewingFile] = useState<string | null>(null)
  const [showJson, setShowJson] = useState(false)

  // Filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<ResultTypeFilter>('all')
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())

  const toggleGroup = (scenarioId: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev)
      if (next.has(scenarioId)) {
        next.delete(scenarioId)
      } else {
        next.add(scenarioId)
      }
      return next
    })
  }

  // Filter and group results
  const { filteredResults, groupedResults, scenarioOrder } = useMemo(() => {
    // First filter by search and type
    let filtered = results.filter(result => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (!result.scenario_id.toLowerCase().includes(query)) {
          return false
        }
      }

      // Type filter
      if (typeFilter !== 'all') {
        const isComparison = isComparisonResult(result)
        if (typeFilter === 'comparison' && !isComparison) return false
        if (typeFilter === 'single' && isComparison) return false
      }

      return true
    })

    // Sort by timestamp (newest first)
    filtered = filtered.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )

    // Group by base scenario ID
    const grouped: Record<string, RunResult[]> = {}
    const order: string[] = []

    for (const result of filtered) {
      const baseId = getBaseScenarioId(result.scenario_id)
      if (!grouped[baseId]) {
        grouped[baseId] = []
        order.push(baseId)
      }
      grouped[baseId].push(result)
    }

    return { filteredResults: filtered, groupedResults: grouped, scenarioOrder: order }
  }, [results, searchQuery, typeFilter])

  useEffect(() => {
    fetch('/api/v1/local/runs')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch results')
        return res.json()
      })
      .then(setResults)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const viewResult = async (filename: string) => {
    try {
      const res = await fetch(`/api/v1/local/runs/${encodeURIComponent(filename)}`)
      if (!res.ok) throw new Error('Failed to fetch result')
      const data = await res.json()
      setSelectedResult(data)
      setViewingFile(filename)
      setShowJson(false)
    } catch (e) {
      console.error('Error fetching result:', e)
    }
  }

  // Helper to detect result type and extract data
  const getResultType = (data: StoredResult | null): 'single' | 'comparison' | 'unknown' => {
    if (!data) return 'unknown'

    // Check if it's a comparison (has ranking)
    const ranking = data.ranking || (data.result as Record<string, unknown>)?.ranking
    if (ranking) return 'comparison'

    // Check if it's a single run (has model or response)
    const model = data.model || (data.result as Record<string, unknown>)?.model
    const response = data.response || (data.result as Record<string, unknown>)?.response
    if (model || response !== undefined) return 'single'

    return 'unknown'
  }

  // Convert stored result to SingleRunResult format
  const toSingleRunResult = (data: StoredResult): RunScenarioResponse => {
    // Data might be at top level or nested in result
    const inner = (data.result as Record<string, unknown>) || data
    return {
      id: (inner.id as string) || '',
      scenario_id: (inner.scenario_id as string) || data.scenario_id || '',
      model: (inner.model as string) || '',
      response: (inner.response as string) || '',
      history: (inner.history as RunScenarioResponse['history']) || [],
      tool_calls: (inner.tool_calls as RunScenarioResponse['tool_calls']) || [],
      final_state: (inner.final_state as Record<string, unknown>) || {},
      evaluation: (inner.evaluation as RunScenarioResponse['evaluation']) || null,
      latency_ms: (inner.latency_ms as number) || 0,
      input_tokens: (inner.input_tokens as number) || 0,
      output_tokens: (inner.output_tokens as number) || 0,
      cost_usd: (inner.cost_usd as number | null) || null,
      error: (inner.error as string | null) || null,
    }
  }

  // Convert stored result to ComparisonResult format
  const toComparisonResult = (data: StoredResult): CompareModelsResponse => {
    // Data might be at top level or nested in result
    const inner = (data.result as Record<string, unknown>) || data
    return {
      scenario_id: (inner.scenario_id as string) || data.scenario_id || '',
      scenario_name: (inner.scenario_name as string) || data.scenario_id || '',
      models: (inner.models as string[]) || [],
      runs_per_model: (inner.runs_per_model as number) || 1,
      stats: (inner.stats as CompareModelsResponse['stats']) || {},
      ranking: (inner.ranking as string[]) || [],
      winner: (inner.winner as string | null) || null,
      results: (inner.results as CompareModelsResponse['results']) || [],
    }
  }

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

  const resultType = getResultType(selectedResult)

  return (
    <div className="p-8 page">
      <h1 className="text-2xl font-semibold text-slate-100 mb-6">Run Results</h1>

      {results.length === 0 ? (
        <div className="panel-card p-6 text-center">
          <FileText size={48} className="mx-auto text-slate-600 mb-4" />
          <p className="text-slate-400 mb-2">No run results found</p>
          <p className="text-slate-500 text-sm mb-4">
            Run a scenario to see results here.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-orange-300 hover:text-orange-200"
          >
            <Play size={16} />
            Go to Dashboard
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Results List - narrower on large screens */}
          <div className="lg:col-span-1 space-y-4">
            {/* Filter Bar */}
            <div className="space-y-3">
              {/* Search Input */}
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search scenarios..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-400/50"
                />
              </div>

              {/* Type Filter Tabs */}
              <div className="flex gap-1 p-1 bg-slate-900/60 rounded-lg border border-slate-700/50">
                <button
                  onClick={() => setTypeFilter('all')}
                  className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    typeFilter === 'all'
                      ? 'bg-slate-700/80 text-slate-100'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All ({results.length})
                </button>
                <button
                  onClick={() => setTypeFilter('single')}
                  className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                    typeFilter === 'single'
                      ? 'bg-slate-700/80 text-slate-100'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Zap size={12} />
                  Single
                </button>
                <button
                  onClick={() => setTypeFilter('comparison')}
                  className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                    typeFilter === 'comparison'
                      ? 'bg-slate-700/80 text-slate-100'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <GitCompare size={12} />
                  Compare
                </button>
              </div>
            </div>

            {/* Results Count */}
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-400">
                {filteredResults.length} result{filteredResults.length !== 1 ? 's' : ''} in {scenarioOrder.length} scenario{scenarioOrder.length !== 1 ? 's' : ''}
              </h2>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="text-xs text-slate-500 hover:text-slate-300"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Grouped Results */}
            <div className="space-y-2 max-h-[70vh] overflow-y-auto pr-2">
              {scenarioOrder.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <Filter size={24} className="mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No results match your filters</p>
                </div>
              ) : (
                scenarioOrder.map((scenarioId) => {
                  const scenarioResults = groupedResults[scenarioId]
                  const isCollapsed = collapsedGroups.has(scenarioId)

                  return (
                    <div key={scenarioId} className="panel-card overflow-hidden">
                      {/* Scenario Group Header */}
                      <button
                        onClick={() => toggleGroup(scenarioId)}
                        className="w-full flex items-center justify-between p-3 hover:bg-slate-800/40 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          {isCollapsed ? (
                            <ChevronRight size={16} className="text-slate-500" />
                          ) : (
                            <ChevronDown size={16} className="text-slate-500" />
                          )}
                          <span className="font-medium text-slate-200 text-sm">{scenarioId}</span>
                        </div>
                        <span className="text-xs text-slate-500 bg-slate-800/60 px-2 py-0.5 rounded">
                          {scenarioResults.length}
                        </span>
                      </button>

                      {/* Scenario Results */}
                      {!isCollapsed && (
                        <div className="border-t border-slate-800/50">
                          {scenarioResults.map((result) => {
                            const isComparison = isComparisonResult(result)

                            return (
                              <div
                                key={result.filename}
                                className={`flex items-center justify-between p-3 cursor-pointer transition-colors border-l-2 ${
                                  viewingFile === result.filename
                                    ? 'bg-slate-800/60 border-l-orange-400'
                                    : 'hover:bg-slate-800/40 border-l-transparent'
                                }`}
                                onClick={() => viewResult(result.filename)}
                              >
                                <div className="flex items-center gap-2 min-w-0">
                                  {isComparison ? (
                                    <GitCompare size={14} className="text-purple-400 flex-shrink-0" />
                                  ) : (
                                    <Zap size={14} className="text-blue-400 flex-shrink-0" />
                                  )}
                                  <div className="min-w-0">
                                    <p className="text-xs text-slate-400 flex items-center gap-1">
                                      <Clock size={10} />
                                      {new Date(result.timestamp).toLocaleString()}
                                    </p>
                                  </div>
                                </div>
                                <Link
                                  to={`/run/${getBaseScenarioId(result.scenario_id)}`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="p-1.5 text-slate-500 hover:text-orange-300 hover:bg-slate-700/60 rounded flex-shrink-0"
                                  title="Run again"
                                >
                                  <Play size={12} />
                                </Link>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>

          {/* Result Detail - wider on large screens */}
          <div className="lg:col-span-2">
            {selectedResult ? (
              <div className="space-y-4">
                {/* Header */}
                <div className="panel-card p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="font-semibold text-slate-100">
                        {selectedResult.scenario_id}
                      </h2>
                      {resultType === 'single' && toSingleRunResult(selectedResult).model && (
                        <p className="text-sm text-slate-400 mt-1">
                          Model: {toSingleRunResult(selectedResult).model}
                        </p>
                      )}
                      {resultType === 'comparison' && (
                        <p className="text-sm text-slate-400 mt-1">
                          Model Comparison
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowJson(!showJson)}
                        className="text-xs text-slate-400 hover:text-slate-100 px-2 py-1 border border-slate-700/70 rounded"
                      >
                        {showJson ? 'View Details' : 'View JSON'}
                      </button>
                      <Link
                        to={`/run/${selectedResult.scenario_id.replace(/_comparison$/, '')}`}
                        className="flex items-center gap-1 bg-orange-400 hover:bg-orange-300 text-slate-900 px-3 py-1 rounded text-sm font-semibold"
                      >
                        <Play size={14} />
                        Run Again
                      </Link>
                    </div>
                  </div>
                </div>

                {/* Content */}
                {showJson ? (
                  <div className="panel-card p-4">
                    <pre className="text-xs text-slate-300 bg-slate-950/70 p-3 rounded overflow-auto max-h-[70vh]">
                      {JSON.stringify(selectedResult, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <>
                    {resultType === 'single' && (
                      <SingleRunResult result={toSingleRunResult(selectedResult)} />
                    )}
                    {resultType === 'comparison' && (
                      <ComparisonResult comparison={toComparisonResult(selectedResult)} />
                    )}
                    {resultType === 'unknown' && (
                      <div className="panel-card p-6 text-center">
                        <p className="text-slate-500">
                          Could not parse result format. Click "View JSON" to see raw data.
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>
            ) : (
              <div className="panel-card p-8 text-center">
                <Eye size={32} className="mx-auto text-slate-600 mb-3" />
                <p className="text-slate-400">Select a result to view details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
