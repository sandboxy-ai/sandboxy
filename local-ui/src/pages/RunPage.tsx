import { useState, useEffect } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft, Play, Loader2, XCircle, Edit, Settings, Database, Check, X } from 'lucide-react'
import { api, ScenarioDetail, ModelInfo, VariableInfo, DatasetInfo, RunDatasetResponse, LocalFileInfo } from '../lib/api'
import { useScenarioRun } from '../hooks/useScenarioRun'
import { SingleRunResult, ComparisonResult } from '../components/ResultDisplay'
import { ModelSelector, MultiModelSelector } from '../components/ModelSelector'

type RunMode = 'single' | 'compare' | 'dataset'

export default function RunPage() {
  const { scenarioId } = useParams<{ scenarioId: string }>()
  const [searchParams] = useSearchParams()
  const datasetIdFromUrl = searchParams.get('dataset')
  const parallelFromUrl = parseInt(searchParams.get('parallel') || '5')

  const [scenarios, setScenarios] = useState<LocalFileInfo[]>([])
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null)
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(scenarioId || '')
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [runMode, setRunMode] = useState<RunMode>(datasetIdFromUrl ? 'dataset' : 'single')
  const [runsPerModel, setRunsPerModel] = useState(1)
  const [variables, setVariables] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Dataset state
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const [selectedDataset, setSelectedDataset] = useState<string>(datasetIdFromUrl || '')
  const [datasetResult, setDatasetResult] = useState<RunDatasetResponse | null>(null)
  const [datasetRunning, setDatasetRunning] = useState(false)
  const [parallel, setParallel] = useState(parallelFromUrl)

  const { state, result, comparison, error: runError, runScenario, compareModels } = useScenarioRun()

  useEffect(() => {
    const load = async () => {
      try {
        const [scenarioList, modelData, datasetList] = await Promise.all([
          api.listScenarios(),
          api.listModels(),
          api.listDatasets(),
        ])
        setScenarios(scenarioList)
        setModels(modelData)
        setDatasets(datasetList)

        if (modelData.length > 0) {
          setSelectedModel(modelData[0].id)
        }

        // Load specific scenario if ID provided
        if (scenarioId) {
          setSelectedScenarioId(scenarioId)
          const scenarioData = await api.getScenario(scenarioId)
          setScenario(scenarioData)

          // Initialize variables with defaults
          const initialVars: Record<string, unknown> = {}
          for (const v of scenarioData.variables || []) {
            initialVars[v.name] = v.default ?? ''
          }
          setVariables(initialVars)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [scenarioId])

  // Load scenario when selection changes
  useEffect(() => {
    if (selectedScenarioId && selectedScenarioId !== scenarioId) {
      api.getScenario(selectedScenarioId)
        .then((data) => {
          setScenario(data)
          const initialVars: Record<string, unknown> = {}
          for (const v of data.variables || []) {
            initialVars[v.name] = v.default ?? ''
          }
          setVariables(initialVars)
        })
        .catch((err) => setError(err.message))
    }
  }, [selectedScenarioId, scenarioId])

  const handleRun = async () => {
    const sid = selectedScenarioId || scenarioId
    if (!sid) return

    if (runMode === 'dataset') {
      if (!selectedDataset || !selectedModel) return
      setDatasetRunning(true)
      setDatasetResult(null)
      try {
        const result = await api.runDataset({
          scenario_id: sid,
          dataset_id: selectedDataset,
          model: selectedModel,
          parallel,
        })
        setDatasetResult(result)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Dataset run failed')
      } finally {
        setDatasetRunning(false)
      }
    } else if (runMode === 'single') {
      if (!selectedModel) return
      await runScenario(sid, selectedModel, variables)
    } else {
      if (selectedModels.length === 0) return
      await compareModels(sid, selectedModels, runsPerModel, variables)
    }
  }

  const updateVariable = (name: string, value: unknown) => {
    setVariables(prev => ({ ...prev, [name]: value }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-orange-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 page">
        <div className="panel-solid p-4 text-red-400 border border-red-700/60">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl mx-auto page">
      <Link
        to="/"
        className="flex items-center gap-2 text-slate-400 hover:text-slate-100 mb-6"
      >
        <ArrowLeft size={20} />
        Back to Dashboard
      </Link>

      {/* Scenario Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-100 mb-2">
          {scenario?.name || scenarioId}
        </h1>
        {scenario?.description && (
          <p className="text-slate-400">{scenario.description}</p>
        )}
      </div>

      {/* Run Configuration */}
      <div className="panel-card p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100">Run Configuration</h2>
          <Link
            to="/builder"
            className="flex items-center gap-2 text-slate-400 hover:text-slate-100 text-sm"
          >
            <Edit size={16} />
            Edit Scenario
          </Link>
        </div>

        {/* Scenario Selector (when no scenarioId in URL) */}
        {!scenarioId && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-400 mb-2">Scenario</label>
            <select
              value={selectedScenarioId}
              onChange={(e) => setSelectedScenarioId(e.target.value)}
              disabled={state === 'running' || datasetRunning}
              className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
            >
              <option value="">Select a scenario...</option>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* Mode Toggle */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-400 mb-2">Mode</label>
          <div className="flex gap-2">
            <button
              onClick={() => setRunMode('single')}
              disabled={state === 'running' || datasetRunning}
              className={`px-4 py-2 rounded-lg transition-colors ${
                runMode === 'single'
                  ? 'bg-orange-400 text-slate-900'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              Single Model
            </button>
            <button
              onClick={() => setRunMode('compare')}
              disabled={state === 'running' || datasetRunning}
              className={`px-4 py-2 rounded-lg transition-colors ${
                runMode === 'compare'
                  ? 'bg-orange-400 text-slate-900'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              Compare Models
            </button>
            <button
              onClick={() => setRunMode('dataset')}
              disabled={state === 'running' || datasetRunning || datasets.length === 0}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                runMode === 'dataset'
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              <Database size={16} />
              Dataset Benchmark
            </button>
          </div>
        </div>

        {runMode === 'single' ? (
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Model
            </label>
            <ModelSelector
              models={models}
              value={selectedModel}
              onChange={setSelectedModel}
              disabled={state === 'running'}
            />
          </div>
        ) : runMode === 'compare' ? (
          <div className="space-y-4 mb-6">
            {/* Model Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Models to Compare
              </label>
              <MultiModelSelector
                models={models}
                selected={selectedModels}
                onChange={setSelectedModels}
                disabled={state === 'running'}
              />
            </div>

            {/* Runs per Model */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Runs per Model
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={runsPerModel}
                onChange={(e) => setRunsPerModel(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))}
                disabled={state === 'running'}
                className="w-32 panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
              />
              <p className="mt-1 text-xs text-slate-500">More runs = more statistical significance</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4 mb-6">
            {/* Dataset Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Dataset
              </label>
              <select
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                disabled={datasetRunning}
                className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">Select a dataset...</option>
                {datasets.map((ds) => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name} ({ds.case_count} cases)
                  </option>
                ))}
              </select>
              {datasets.length === 0 && (
                <p className="mt-1 text-xs text-slate-500">
                  No datasets found. <Link to="/datasets" className="text-blue-400 hover:underline">Create one</Link>
                </p>
              )}
            </div>

            {/* Model Selection for Dataset */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Model
              </label>
              <ModelSelector
                models={models}
                value={selectedModel}
                onChange={setSelectedModel}
                disabled={datasetRunning}
              />
            </div>

            {/* Parallel runs */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Parallel Runs
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={parallel}
                  onChange={(e) => setParallel(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                  disabled={datasetRunning}
                  className="w-20 panel-subtle px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <span className="text-sm text-slate-500">concurrent cases</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">Higher = faster, but may hit rate limits</p>
            </div>
          </div>
        )}

        {/* Variables Section */}
        {scenario && scenario.variables && scenario.variables.length > 0 && (
          <div className="mb-6 p-4 panel-subtle">
            <div className="flex items-center gap-2 mb-4">
              <Settings size={18} className="text-slate-400" />
              <h3 className="font-medium text-slate-100">Variables</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {scenario.variables.map((variable) => (
                <VariableInput
                  key={variable.name}
                  variable={variable}
                  value={variables[variable.name]}
                  onChange={(value) => updateVariable(variable.name, value)}
                  disabled={state === 'running'}
                />
              ))}
            </div>
          </div>
        )}

        <button
          onClick={handleRun}
          disabled={
            state === 'running' || datasetRunning ||
            !selectedScenarioId ||
            (runMode === 'single' ? !selectedModel :
             runMode === 'compare' ? selectedModels.length === 0 :
             !selectedDataset || !selectedModel)
          }
          className={`flex items-center gap-2 ${
            runMode === 'dataset' ? 'bg-blue-500 hover:bg-blue-400' : 'bg-orange-400 hover:bg-orange-300'
          } disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed text-slate-900 px-6 py-2 rounded-lg transition-colors font-semibold`}
        >
          {state === 'running' || datasetRunning ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running...
            </>
          ) : (
            <>
              {runMode === 'dataset' ? <Database className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {runMode === 'single' ? 'Run Scenario' :
               runMode === 'compare' ? `Compare ${selectedModels.length} Models` :
               `Run ${datasets.find(d => d.id === selectedDataset)?.case_count || 0} Cases`}
            </>
          )}
        </button>
      </div>

      {/* Error Display */}
      {runError && (
        <div className="panel-solid border border-red-700/60 p-4 mb-6 text-red-400">
          <div className="flex items-center gap-2">
            <XCircle className="w-5 h-5" />
            <span>{runError}</span>
          </div>
        </div>
      )}

      {/* Results */}
      {result && <SingleRunResult result={result} />}
      {comparison && <ComparisonResult comparison={comparison} />}
      {datasetResult && <DatasetResultView result={datasetResult} />}
    </div>
  )
}

function DatasetResultView({ result }: { result: RunDatasetResponse }) {
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

  return (
    <div className="panel-card p-6">
      <h2 className="text-xl font-semibold text-slate-100 mb-4 flex items-center gap-2">
        <Database size={20} />
        Dataset Benchmark Results
      </h2>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="panel-subtle p-4 rounded-lg">
          <div className="text-2xl font-bold text-slate-100">
            {result.passed_cases}/{result.total_cases}
          </div>
          <div className="text-sm text-slate-400">Cases Passed</div>
        </div>
        <div className="panel-subtle p-4 rounded-lg">
          <div className={`text-2xl font-bold ${result.pass_rate >= 0.9 ? 'text-green-400' : result.pass_rate >= 0.7 ? 'text-yellow-400' : 'text-red-400'}`}>
            {(result.pass_rate * 100).toFixed(1)}%
          </div>
          <div className="text-sm text-slate-400">Pass Rate</div>
        </div>
        <div className="panel-subtle p-4 rounded-lg">
          <div className="text-2xl font-bold text-slate-100">
            {result.avg_percentage.toFixed(1)}%
          </div>
          <div className="text-sm text-slate-400">Avg Score</div>
        </div>
        <div className="panel-subtle p-4 rounded-lg">
          <div className="text-2xl font-bold text-slate-100">
            {(result.total_time_ms / 1000).toFixed(1)}s
          </div>
          <div className="text-sm text-slate-400">Total Time</div>
        </div>
      </div>

      {/* By Expected Outcome */}
      {Object.keys(result.by_expected).length > 0 && (
        <div className="mb-6">
          <h3 className="font-medium text-slate-300 mb-3">By Expected Outcome</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {Object.entries(result.by_expected).map(([outcome, counts]) => {
              const total = counts.passed + counts.failed
              const rate = total > 0 ? counts.passed / total : 0
              return (
                <div key={outcome} className="panel-subtle p-3 rounded">
                  <div className="font-medium text-slate-200">{outcome}</div>
                  <div className="text-sm text-slate-400">
                    {counts.passed}/{total} ({(rate * 100).toFixed(0)}%)
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Case Results */}
      <div>
        <h3 className="font-medium text-slate-300 mb-3">
          Case Results ({result.failed_cases} failed)
        </h3>
        <div className="space-y-2 max-h-[40vh] overflow-y-auto">
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
                  <Check size={16} className="text-green-400" />
                ) : (
                  <X size={16} className="text-red-400" />
                )}
                <span className="font-medium text-slate-200">{c.case_id}</span>
                {c.expected && (
                  <span className="text-sm text-slate-400">
                    expected: {c.expected}
                  </span>
                )}
                <span className="ml-auto text-sm text-slate-400">
                  {c.percentage.toFixed(0)}% | {c.latency_ms}ms
                </span>
              </button>

              {expandedCases.has(c.case_id) && (
                <div className="px-4 pb-3 pt-1 border-t border-slate-700">
                  {c.failure_reason && (
                    <div className="text-red-400 text-sm mb-2">
                      {c.failure_reason}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-slate-400">Expected:</span>{' '}
                      <span className="text-slate-200">{c.expected || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Actual:</span>{' '}
                      <span className="text-slate-200">{c.actual_outcome || 'None'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Score:</span>{' '}
                      <span className="text-slate-200">{c.goal_score}/{c.max_score}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Latency:</span>{' '}
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

function VariableInput({
  variable,
  value,
  onChange,
  disabled,
}: {
  variable: VariableInfo
  value: unknown
  onChange: (value: unknown) => void
  disabled: boolean
}) {
  const inputClass = "w-full panel-subtle px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 disabled:opacity-50"

  return (
    <div>
      <label className="block text-sm font-medium text-slate-400 mb-1">
        {variable.label}
        {variable.required && <span className="text-red-400 ml-1">*</span>}
      </label>

      {variable.type === 'select' && variable.options.length > 0 ? (
        <select
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={inputClass}
        >
          <option value="">Select...</option>
          {variable.options.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ) : variable.type === 'boolean' ? (
        <select
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value === 'true')}
          disabled={disabled}
          className={inputClass}
        >
          <option value="">Select...</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      ) : variable.type === 'number' ? (
        <input
          type="number"
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : '')}
          disabled={disabled}
          placeholder={variable.default !== null ? `Default: ${variable.default}` : ''}
          className={inputClass}
        />
      ) : (
        <input
          type="text"
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={variable.default !== null ? `Default: ${variable.default}` : ''}
          className={inputClass}
        />
      )}
    </div>
  )
}
