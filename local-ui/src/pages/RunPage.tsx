import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Play, Loader2, XCircle, Edit, Settings } from 'lucide-react'
import { api, ScenarioDetail, ModelInfo, VariableInfo } from '../lib/api'
import { useScenarioRun } from '../hooks/useScenarioRun'
import { SingleRunResult, ComparisonResult } from '../components/ResultDisplay'
import { ModelSelector, MultiModelSelector } from '../components/ModelSelector'

type RunMode = 'single' | 'compare'

export default function RunPage() {
  const { scenarioId } = useParams<{ scenarioId: string }>()
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [runMode, setRunMode] = useState<RunMode>('single')
  const [runsPerModel, setRunsPerModel] = useState(1)
  const [variables, setVariables] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { state, result, comparison, error: runError, runScenario, compareModels } = useScenarioRun()

  useEffect(() => {
    const load = async () => {
      if (!scenarioId) return
      try {
        const [scenarioData, modelData] = await Promise.all([
          api.getScenario(scenarioId),
          api.listModels(),
        ])
        setScenario(scenarioData)
        setModels(modelData)
        if (modelData.length > 0) {
          setSelectedModel(modelData[0].id)
        }

        // Initialize variables with defaults
        const initialVars: Record<string, unknown> = {}
        for (const v of scenarioData.variables || []) {
          initialVars[v.name] = v.default ?? ''
        }
        setVariables(initialVars)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load scenario')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [scenarioId])

  const handleRun = async () => {
    if (!scenarioId) return

    if (runMode === 'single') {
      if (!selectedModel) return
      await runScenario(scenarioId, selectedModel, variables)
    } else {
      if (selectedModels.length === 0) return
      await compareModels(scenarioId, selectedModels, runsPerModel, variables)
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

        {/* Mode Toggle */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-400 mb-2">Mode</label>
          <div className="flex gap-2">
            <button
              onClick={() => setRunMode('single')}
              disabled={state === 'running'}
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
              disabled={state === 'running'}
              className={`px-4 py-2 rounded-lg transition-colors ${
                runMode === 'compare'
                  ? 'bg-orange-400 text-slate-900'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              Compare Models
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
        ) : (
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
          disabled={state === 'running' || (runMode === 'single' ? !selectedModel : selectedModels.length === 0)}
          className="flex items-center gap-2 bg-orange-400 hover:bg-orange-300 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed text-slate-900 px-6 py-2 rounded-lg transition-colors font-semibold"
        >
          {state === 'running' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              {runMode === 'single' ? 'Run Scenario' : `Compare ${selectedModels.length} Models`}
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
