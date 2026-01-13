import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Clock, Play, Eye, Search, Filter, ChevronDown, ChevronRight, GitCompare, Zap, Database, Check, X, Copy } from 'lucide-react'
import { RunScenarioResponse, CompareModelsResponse, RunDatasetResponse } from '../lib/api'
import { SingleRunResult, ComparisonResult } from '../components/ResultDisplay'

interface RunResult {
  filename: string
  path: string
  scenario_id: string
  timestamp: string
  metadata: Record<string, unknown>
}

type ResultTypeFilter = 'all' | 'single' | 'comparison' | 'dataset'

// Helper to detect if a result is a comparison based on filename
const isComparisonResult = (result: RunResult): boolean => {
  return result.scenario_id.endsWith('_comparison') || result.filename.includes('_comparison_')
}

// Helper to detect if a result is a dataset benchmark
const isDatasetResult = (result: RunResult): boolean => {
  return result.scenario_id.includes('_dataset_') || result.filename.includes('_dataset_')
}

// Get base scenario name without _comparison or _dataset_* suffix
const getBaseScenarioId = (scenarioId: string): string => {
  return scenarioId.replace(/_comparison$/, '').replace(/_dataset_.*$/, '')
}

// The stored result format - can be single run, comparison, or dataset benchmark
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
  // Dataset benchmark fields
  dataset_id?: string
  total_cases?: number
  passed_cases?: number
  failed_cases?: number
  pass_rate?: number
  avg_score?: number
  avg_percentage?: number
  by_expected?: Record<string, { passed: number; failed: number }>
  total_time_ms?: number
  case_results?: unknown[]
}

export default function ResultsPage() {
  const [results, setResults] = useState<RunResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedResult, setSelectedResult] = useState<StoredResult | null>(null)
  const [viewingFile, setViewingFile] = useState<string | null>(null)
  const [showJson, setShowJson] = useState(false)
  const [copied, setCopied] = useState(false)

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
        const isDataset = isDatasetResult(result)
        if (typeFilter === 'comparison' && !isComparison) return false
        if (typeFilter === 'dataset' && !isDataset) return false
        if (typeFilter === 'single' && (isComparison || isDataset)) return false
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

  const copyJson = async () => {
    if (!selectedResult) return
    try {
      await navigator.clipboard.writeText(JSON.stringify(selectedResult, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  // Helper to detect result type and extract data
  const getResultType = (data: StoredResult | null): 'single' | 'comparison' | 'dataset' | 'unknown' => {
    if (!data) return 'unknown'

    // Check if it's a dataset benchmark (has case_results)
    const caseResults = data.case_results || (data.result as Record<string, unknown>)?.case_results
    const datasetId = data.dataset_id || (data.result as Record<string, unknown>)?.dataset_id
    if (caseResults || datasetId) return 'dataset'

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

  // Convert stored result to DatasetResult format
  const toDatasetResult = (data: StoredResult): RunDatasetResponse => {
    // Data might be at top level or nested in result
    const inner = (data.result as Record<string, unknown>) || data
    return {
      scenario_id: (inner.scenario_id as string) || data.scenario_id || '',
      model: (inner.model as string) || '',
      dataset_id: (inner.dataset_id as string) || '',
      total_cases: (inner.total_cases as number) || 0,
      passed_cases: (inner.passed_cases as number) || 0,
      failed_cases: (inner.failed_cases as number) || 0,
      pass_rate: (inner.pass_rate as number) || 0,
      avg_score: (inner.avg_score as number) || 0,
      avg_percentage: (inner.avg_percentage as number) || 0,
      by_expected: (inner.by_expected as Record<string, { passed: number; failed: number }>) || {},
      total_time_ms: (inner.total_time_ms as number) || 0,
      case_results: (inner.case_results as RunDatasetResponse['case_results']) || [],
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
              <div className="flex flex-wrap gap-1 p-1 bg-slate-900/60 rounded-lg border border-slate-700/50">
                <button
                  onClick={() => setTypeFilter('all')}
                  className={`flex-1 min-w-0 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    typeFilter === 'all'
                      ? 'bg-slate-700/80 text-slate-100'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setTypeFilter('single')}
                  className={`flex-1 min-w-0 px-2 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
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
                  className={`flex-1 min-w-0 px-2 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                    typeFilter === 'comparison'
                      ? 'bg-slate-700/80 text-slate-100'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <GitCompare size={12} />
                  Compare
                </button>
                <button
                  onClick={() => setTypeFilter('dataset')}
                  className={`flex-1 min-w-0 px-2 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                    typeFilter === 'dataset'
                      ? 'bg-blue-600/80 text-slate-100'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Database size={12} />
                  Dataset
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
                            const isDataset = isDatasetResult(result)

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
                                  {isDataset ? (
                                    <Database size={14} className="text-blue-400 flex-shrink-0" />
                                  ) : isComparison ? (
                                    <GitCompare size={14} className="text-purple-400 flex-shrink-0" />
                                  ) : (
                                    <Zap size={14} className="text-orange-400 flex-shrink-0" />
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
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <h2 className="font-semibold text-slate-100 truncate">
                        {getBaseScenarioId(selectedResult.scenario_id)}
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
                      {resultType === 'dataset' && (
                        <p className="text-sm text-slate-400 mt-1">
                          Dataset: {toDatasetResult(selectedResult).dataset_id} | Model: {toDatasetResult(selectedResult).model}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={copyJson}
                        className={`flex items-center gap-1 text-xs px-2 py-1 border rounded whitespace-nowrap transition-colors ${
                          copied
                            ? 'text-emerald-400 border-emerald-500/50 bg-emerald-500/10'
                            : 'text-slate-400 hover:text-slate-100 border-slate-700/70'
                        }`}
                      >
                        <Copy size={12} />
                        {copied ? 'Copied!' : 'Copy JSON'}
                      </button>
                      <button
                        onClick={() => setShowJson(!showJson)}
                        className="text-xs text-slate-400 hover:text-slate-100 px-2 py-1 border border-slate-700/70 rounded whitespace-nowrap"
                      >
                        {showJson ? 'View Details' : 'View JSON'}
                      </button>
                      <Link
                        to={`/run/${getBaseScenarioId(selectedResult.scenario_id)}`}
                        className="flex items-center gap-1 bg-orange-400 hover:bg-orange-300 text-slate-900 px-3 py-1 rounded text-sm font-semibold whitespace-nowrap"
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
                    {resultType === 'dataset' && (
                      <DatasetBenchmarkResult result={toDatasetResult(selectedResult)} />
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

// Dataset benchmark result display component
function DatasetBenchmarkResult({ result }: { result: RunDatasetResponse }) {
  const [expandedCases, setExpandedCases] = useState<Set<string>>(new Set())

  const toggleCase = (id: string) => {
    const newExpanded = new Set(expandedCases)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedCases(newExpanded)
  }

  const passedCount = result.passed_cases
  const totalCount = result.total_cases
  const passRate = result.pass_rate

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Database className="w-4 h-4" />
            Cases Passed
          </div>
          <div className={`text-2xl font-bold ${passRate >= 0.9 ? 'text-emerald-300' : passRate >= 0.7 ? 'text-amber-300' : 'text-red-400'}`}>
            {passedCount}/{totalCount}
          </div>
          <div className="text-xs text-slate-500">
            {(passRate * 100).toFixed(1)}% pass rate
          </div>
        </div>

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Check className="w-4 h-4" />
            Avg Score
          </div>
          <div className="text-2xl font-bold text-slate-100">
            {result.avg_percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500">
            {result.avg_score.toFixed(1)} points
          </div>
        </div>

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Clock className="w-4 h-4" />
            Total Time
          </div>
          <div className="text-2xl font-bold text-slate-100">
            {(result.total_time_ms / 1000).toFixed(1)}s
          </div>
          <div className="text-xs text-slate-500">
            {Math.round(result.total_time_ms / Math.max(totalCount, 1))}ms/case
          </div>
        </div>

        <div className="panel-card p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <X className="w-4 h-4" />
            Failed
          </div>
          <div className="text-2xl font-bold text-red-400">
            {result.failed_cases}
          </div>
          <div className="text-xs text-slate-500">
            {totalCount - passedCount} case{totalCount - passedCount !== 1 ? 's' : ''} failed
          </div>
        </div>
      </div>

      {/* By Expected Outcome */}
      {Object.keys(result.by_expected).length > 0 && (
        <div className="panel-card p-6">
          <h3 className="font-semibold text-slate-100 mb-4">By Expected Outcome</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(result.by_expected).map(([outcome, counts]) => {
              const total = counts.passed + counts.failed
              const rate = total > 0 ? counts.passed / total : 0
              return (
                <div key={outcome} className="panel-subtle p-3 rounded-lg">
                  <div className="font-medium text-slate-200">{outcome}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className={`text-lg font-semibold ${rate >= 0.9 ? 'text-emerald-300' : rate >= 0.7 ? 'text-amber-300' : 'text-red-400'}`}>
                      {counts.passed}/{total}
                    </div>
                    <span className="text-xs text-slate-500">
                      ({(rate * 100).toFixed(0)}%)
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Case Results */}
      <div className="panel-card p-6">
        <h3 className="font-semibold text-slate-100 mb-4">
          Case Results ({result.failed_cases} failed, {result.passed_cases} passed)
        </h3>
        <div className="space-y-2 max-h-[50vh] overflow-y-auto">
          {result.case_results.map((c) => (
            <div
              key={c.case_id}
              className={`panel-subtle rounded-lg overflow-hidden ${
                !c.passed ? 'border border-red-500/30' : ''
              }`}
            >
              <button
                onClick={() => toggleCase(c.case_id)}
                className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-slate-700/50 transition-colors"
              >
                {c.passed ? (
                  <Check size={16} className="text-emerald-400 flex-shrink-0" />
                ) : (
                  <X size={16} className="text-red-400 flex-shrink-0" />
                )}
                <span className="font-medium text-slate-200">{c.case_id}</span>
                {c.expected && c.expected.length > 0 && (
                  <span className="text-sm text-slate-400">
                    expected: {c.expected.join(' or ')}
                  </span>
                )}
                <span className="ml-auto text-sm text-slate-400 flex-shrink-0">
                  {c.percentage.toFixed(0)}% | {c.latency_ms}ms
                </span>
                {expandedCases.has(c.case_id) ? (
                  <ChevronDown size={14} className="text-slate-500 flex-shrink-0" />
                ) : (
                  <ChevronRight size={14} className="text-slate-500 flex-shrink-0" />
                )}
              </button>

              {expandedCases.has(c.case_id) && (
                <div className="px-4 pb-3 pt-1 border-t border-slate-700">
                  {c.failure_reason && (
                    <div className="text-red-400 text-sm mb-2 p-2 bg-red-950/30 rounded">
                      {c.failure_reason}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-slate-500">Expected:</span>{' '}
                      <span className="text-slate-200">
                        {c.expected && c.expected.length > 0 ? c.expected.join(' or ') : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Actual:</span>{' '}
                      <span className="text-slate-200">{c.actual_outcome || 'None'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Score:</span>{' '}
                      <span className="text-slate-200">{c.goal_score}/{c.max_score}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Latency:</span>{' '}
                      <span className="text-slate-200">{c.latency_ms}ms</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
