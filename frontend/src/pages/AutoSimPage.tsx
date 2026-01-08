import { useState, useEffect, useMemo } from 'react'
import {
  Play,
  Trophy,
  Clock,
  DollarSign,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  Zap,
  X,
  Users,
  Shuffle,
  MessageSquare,
  Bot,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useArenaModels } from '../hooks/useArena'
import {
  api,
  AutoSimScenario,
  AutoSimScenarioDetail,
  AutoSimRunDetail,
  AutoSimModelResult,
  ArenaModel,
} from '../lib/api'

// Popular models for quick selection
const POPULAR_MODELS = [
  'openai/gpt-4o',
  'anthropic/claude-3.5-sonnet',
  'google/gemini-2.0-flash-exp:free',
  'deepseek/deepseek-chat',
  'x-ai/grok-3',
]

function ModelSelector({
  models,
  selectedModels,
  onToggle,
  disabled,
}: {
  models: ArenaModel[]
  selectedModels: string[]
  onToggle: (modelId: string) => void
  disabled?: boolean
}) {
  const [showAll, setShowAll] = useState(false)
  const [search, setSearch] = useState('')

  const groupedModels = useMemo(() => {
    const filtered = models.filter(m =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.id.toLowerCase().includes(search.toLowerCase())
    )
    const groups: Record<string, ArenaModel[]> = {}
    for (const model of filtered) {
      if (!groups[model.provider]) groups[model.provider] = []
      groups[model.provider].push(model)
    }
    return groups
  }, [models, search])

  const popularModels = useMemo(() => {
    if (showAll || search) return []
    return models.filter(m => POPULAR_MODELS.includes(m.id))
  }, [models, showAll, search])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search models..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-dark-bg border border-dark-border rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-accent"
          disabled={disabled}
        />
        <button
          onClick={() => setShowAll(!showAll)}
          className="text-sm text-gray-400 hover:text-white transition-colors"
          disabled={disabled}
        >
          {showAll ? 'Show Popular' : 'Show All'}
        </button>
      </div>

      <div className="text-sm text-gray-400">
        {selectedModels.length} model{selectedModels.length !== 1 ? 's' : ''} selected
        {selectedModels.length > 5 && (
          <span className="text-yellow-400 ml-2">(max 5 for auto-sim)</span>
        )}
      </div>

      {popularModels.length > 0 && !search && (
        <div className="space-y-2">
          <div className="text-xs text-gray-500 uppercase tracking-wider">Popular</div>
          <div className="flex flex-wrap gap-2">
            {popularModels.map(model => (
              <button
                key={model.id}
                onClick={() => onToggle(model.id)}
                disabled={disabled || (selectedModels.length >= 5 && !selectedModels.includes(model.id))}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  selectedModels.includes(model.id)
                    ? 'bg-accent text-white'
                    : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {model.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {(showAll || search) && (
        <div className="space-y-4 max-h-64 overflow-y-auto">
          {Object.entries(groupedModels).map(([provider, providerModels]) => (
            <div key={provider}>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-2 capitalize">
                {provider}
              </div>
              <div className="flex flex-wrap gap-2">
                {providerModels.map(model => (
                  <button
                    key={model.id}
                    onClick={() => onToggle(model.id)}
                    disabled={disabled || (selectedModels.length >= 5 && !selectedModels.includes(model.id))}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      selectedModels.includes(model.id)
                        ? 'bg-accent text-white'
                        : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {model.name}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ScenarioCard({
  scenario,
  selected,
  onClick,
}: {
  scenario: AutoSimScenario
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all ${
        selected
          ? 'bg-accent/10 border-accent'
          : 'bg-dark-card border-dark-border hover:border-accent/50'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="font-semibold text-white mb-1">{scenario.name}</h3>
          <p className="text-sm text-gray-400 line-clamp-2">{scenario.description}</p>
        </div>
        {selected && <CheckCircle size={20} className="text-accent flex-shrink-0" />}
      </div>
    </button>
  )
}

function TranscriptViewer({ transcript }: { transcript: Array<{ role: string; content: string }> }) {
  const [expanded, setExpanded] = useState(false)
  const displayMessages = expanded ? transcript : transcript.slice(0, 4)

  return (
    <div className="space-y-2">
      {displayMessages.map((msg, idx) => (
        <div
          key={idx}
          className={`p-3 rounded-lg ${
            msg.role === 'customer'
              ? 'bg-blue-900/20 border-l-2 border-blue-500'
              : msg.role === 'agent'
              ? 'bg-green-900/20 border-l-2 border-green-500'
              : 'bg-dark-bg border-l-2 border-gray-500'
          }`}
        >
          <div className="text-xs text-gray-500 uppercase mb-1">{msg.role}</div>
          <div className="text-sm text-gray-300 prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        </div>
      ))}
      {transcript.length > 4 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp size={14} />
              Show less
            </>
          ) : (
            <>
              <ChevronDown size={14} />
              Show all {transcript.length} messages
            </>
          )}
        </button>
      )}
    </div>
  )
}

function ResultCard({
  result,
  isWinner,
  rank,
}: {
  result: AutoSimModelResult
  isWinner: boolean
  rank: number
}) {
  const [showTranscript, setShowTranscript] = useState(false)
  const modelName = result.model_id.split('/').pop() || result.model_id

  return (
    <div
      className={`bg-dark-card border rounded-xl overflow-hidden ${
        isWinner ? 'border-yellow-500/50 ring-1 ring-yellow-500/20' : 'border-dark-border'
      }`}
    >
      {/* Header */}
      <div className="p-4 border-b border-dark-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold ${
                isWinner
                  ? 'bg-yellow-500/20 text-yellow-400'
                  : 'bg-dark-bg text-gray-400'
              }`}
            >
              #{rank}
            </div>
            <div>
              <h4 className="font-semibold text-white">{modelName}</h4>
              <p className="text-xs text-gray-500">{result.model_id}</p>
            </div>
            {isWinner && <Trophy size={18} className="text-yellow-400" />}
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1 text-gray-400">
              <Clock size={14} />
              <span>{result.latency_ms}ms</span>
            </div>
            {result.cost_usd !== null && (
              <div className="flex items-center gap-1 text-gray-400">
                <DollarSign size={14} />
                <span>${result.cost_usd.toFixed(4)}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Score */}
      {result.score && (
        <div className="px-4 py-3 bg-dark-bg/50 border-b border-dark-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-300">
              Score: <span className="font-bold text-white">{result.score.total_score.toFixed(1)}</span>
              <span className="text-gray-500">/{result.score.max_score}</span>
              <span className="ml-2 text-accent">({result.score.percentage.toFixed(0)}%)</span>
            </span>
          </div>
          <p className="text-xs text-gray-400">{result.score.summary}</p>

          {/* Check breakdown */}
          <div className="mt-3 space-y-1">
            {result.score.checks.slice(0, 3).map((check, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs">
                {check.passed ? (
                  <CheckCircle size={12} className="text-green-400" />
                ) : (
                  <XCircle size={12} className="text-red-400" />
                )}
                <span className="text-gray-400">{check.name}</span>
                <span className="text-gray-500">({check.points}/{check.max_points})</span>
              </div>
            ))}
            {result.score.checks.length > 3 && (
              <span className="text-xs text-gray-500">
                +{result.score.checks.length - 3} more checks
              </span>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {result.error && (
        <div className="px-4 py-3 bg-red-500/10 border-b border-red-500/30">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle size={14} />
            <span className="text-sm">{result.error}</span>
          </div>
        </div>
      )}

      {/* Transcript toggle */}
      <div className="p-4">
        <button
          onClick={() => setShowTranscript(!showTranscript)}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <MessageSquare size={14} />
          {showTranscript ? 'Hide' : 'Show'} Conversation
          {showTranscript ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showTranscript && result.transcript && (
          <div className="mt-4">
            <TranscriptViewer transcript={result.transcript} />
          </div>
        )}
      </div>
    </div>
  )
}

function AutoSimResults({ runDetail }: { runDetail: AutoSimRunDetail }) {
  if (!runDetail.results || !runDetail.comparison) {
    return (
      <div className="text-center py-12 text-gray-500">
        No results available
      </div>
    )
  }

  const rankings = runDetail.comparison.rankings

  return (
    <div className="space-y-6">
      {/* Summary header */}
      <div className="bg-gradient-to-r from-accent/10 to-purple-500/10 border border-accent/20 rounded-xl p-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">
              {runDetail.winner ? (
                <>
                  <Trophy className="inline mr-2 text-yellow-400" size={24} />
                  Winner: {runDetail.winner.split('/').pop()}
                </>
              ) : (
                'Results'
              )}
            </h2>
            <p className="text-gray-400">
              Compared {Object.keys(runDetail.results).length} models
            </p>
          </div>
          {runDetail.comparison.key_differences.length > 0 && (
            <div className="text-sm text-gray-400 max-w-md">
              {runDetail.comparison.key_differences[0]}
            </div>
          )}
        </div>
      </div>

      {/* Ranking bar */}
      {rankings.length > 1 && (
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Ranking by Score</h3>
          <div className="flex flex-wrap gap-2">
            {rankings.map((r, index) => (
              <div
                key={r.model_id}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                  index === 0
                    ? 'bg-yellow-500/20 text-yellow-400'
                    : 'bg-dark-bg text-gray-400'
                }`}
              >
                <span className="font-bold">#{index + 1}</span>
                <span>{r.model_id.split('/').pop()}</span>
                <span className="text-xs opacity-75">{r.percentage.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Individual results */}
      <div className="grid gap-4 md:grid-cols-2">
        {rankings.map((r, index) => {
          const result = runDetail.results![r.model_id]
          return (
            <ResultCard
              key={r.model_id}
              result={result}
              isWinner={r.model_id === runDetail.winner}
              rank={index + 1}
            />
          )
        })}
      </div>
    </div>
  )
}

export default function AutoSimPage() {
  const { models, loading: modelsLoading } = useArenaModels()

  const [scenarios, setScenarios] = useState<AutoSimScenario[]>([])
  const [scenariosLoading, setScenariosLoading] = useState(true)
  const [selectedScenario, setSelectedScenario] = useState<AutoSimScenario | null>(null)
  const [scenarioDetail, setScenarioDetail] = useState<AutoSimScenarioDetail | null>(null)

  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [selectedPersonality, setSelectedPersonality] = useState<string>('')
  const [eventsMode, setEventsMode] = useState<string>('random')
  const [turns, setTurns] = useState<number>(5)

  const [runId, setRunId] = useState<string | null>(null)
  const [runDetail, setRunDetail] = useState<AutoSimRunDetail | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load scenarios
  useEffect(() => {
    async function loadScenarios() {
      try {
        const data = await api.getAutoSimScenarios()
        setScenarios(data)
      } catch (err) {
        console.error('Failed to load scenarios:', err)
      } finally {
        setScenariosLoading(false)
      }
    }
    loadScenarios()
  }, [])

  // Load scenario detail when selected
  useEffect(() => {
    if (!selectedScenario) {
      setScenarioDetail(null)
      return
    }

    async function loadDetail() {
      try {
        const data = await api.getAutoSimScenario(selectedScenario!.id)
        setScenarioDetail(data)
        // Set defaults
        if (data.defaults.counterparty?.personality) {
          setSelectedPersonality(data.defaults.counterparty.personality)
        }
        if (data.defaults.events?.mode) {
          setEventsMode(data.defaults.events.mode)
        }
        if (data.defaults.turns) {
          setTurns(data.defaults.turns)
        }
      } catch (err) {
        console.error('Failed to load scenario detail:', err)
      }
    }
    loadDetail()
  }, [selectedScenario])

  // Poll for run results
  useEffect(() => {
    if (!runId || runDetail?.status === 'completed' || runDetail?.status === 'error') {
      return
    }

    const interval = setInterval(async () => {
      try {
        const data = await api.getAutoSimRun(runId)
        setRunDetail(data)
        if (data.status !== 'running') {
          setRunning(false)
        }
      } catch (err) {
        console.error('Failed to poll run:', err)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [runId, runDetail?.status])

  const handleToggleModel = (modelId: string) => {
    setSelectedModels(prev =>
      prev.includes(modelId)
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId]
    )
  }

  const handleRun = async () => {
    if (!selectedScenario || selectedModels.length === 0) return

    setRunning(true)
    setError(null)
    setRunDetail(null)

    try {
      const response = await api.startAutoSimRun({
        scenario: selectedScenario.id,
        models: selectedModels,
        turns,
        counterparty_personality: selectedPersonality || undefined,
        events_mode: eventsMode,
      })
      setRunId(response.run_id)
      setRunDetail({ run_id: response.run_id, status: 'running' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start run')
      setRunning(false)
    }
  }

  const handleReset = () => {
    setRunId(null)
    setRunDetail(null)
    setRunning(false)
    setError(null)
  }

  const canRun =
    selectedScenario !== null &&
    selectedModels.length > 0 &&
    selectedModels.length <= 5

  // Show results if we have them
  if (runDetail && runDetail.status !== 'running') {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <button
          onClick={handleReset}
          className="mb-6 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          aria-label="New Run"
        >
          <X size={16} />
          New Run
        </button>
        <AutoSimResults runDetail={runDetail} />
      </div>
    )
  }

  // Show running state
  if (running || runDetail?.status === 'running') {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <div className="flex flex-col items-center justify-center py-24">
          <div className="relative mb-8">
            <Bot size={64} className="text-accent animate-pulse" />
            <div className="absolute -right-2 -bottom-2">
              <Loader2 size={24} className="animate-spin text-accent" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Running Simulation</h2>
          <p className="text-gray-400 mb-4">
            Testing {selectedModels.length} models on {selectedScenario?.name}
          </p>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Clock size={14} />
            <span>This may take a few minutes...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
            <Bot size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Auto-Sim</h1>
            <p className="text-gray-400">Hands-free simulations to compare AI models</p>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left: Scenario & Config */}
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Users size={20} />
            Scenario
          </h2>

          {scenariosLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-accent" size={24} />
            </div>
          ) : scenarios.length === 0 ? (
            <div className="bg-dark-card border border-dark-border rounded-xl p-6 text-center">
              <AlertCircle className="mx-auto text-yellow-400 mb-3" size={32} />
              <p className="text-gray-400">No scenarios available</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
              {scenarios.map(scenario => (
                <ScenarioCard
                  key={scenario.id}
                  scenario={scenario}
                  selected={selectedScenario?.id === scenario.id}
                  onClick={() => setSelectedScenario(scenario)}
                />
              ))}
            </div>
          )}

          {/* Config options */}
          {scenarioDetail && (
            <div className="bg-dark-card border border-dark-border rounded-xl p-4 space-y-4">
              <h3 className="text-sm font-medium text-gray-400">Configuration</h3>

              {/* Personality */}
              {scenarioDetail.personalities.length > 0 && (
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
                    Counterparty
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {scenarioDetail.personalities.map(p => (
                      <button
                        key={p.id}
                        onClick={() => setSelectedPersonality(p.id)}
                        disabled={running}
                        title={p.style}
                        className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                          selectedPersonality === p.id
                            ? 'bg-accent text-white'
                            : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
                        } disabled:opacity-50`}
                      >
                        {p.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Events */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
                  <Shuffle size={12} className="inline mr-1" />
                  Events
                </label>
                <div className="flex gap-2">
                  {['random', 'none'].map(mode => (
                    <button
                      key={mode}
                      onClick={() => setEventsMode(mode)}
                      disabled={running}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-all capitalize ${
                        eventsMode === mode
                          ? 'bg-accent text-white'
                          : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
                      } disabled:opacity-50`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              {/* Turns */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
                  Turns: {turns}
                </label>
                <input
                  type="range"
                  min={3}
                  max={10}
                  value={turns}
                  onChange={(e) => setTurns(Number(e.target.value))}
                  disabled={running}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>

        {/* Right: Model Selection */}
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Zap size={20} />
            Models to Compare
          </h2>

          {modelsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-accent" size={24} />
            </div>
          ) : models.length === 0 ? (
            <div className="bg-dark-card border border-dark-border rounded-xl p-6 text-center">
              <AlertCircle className="mx-auto text-yellow-400 mb-3" size={32} />
              <h3 className="font-semibold text-white mb-2">No API Key Configured</h3>
              <p className="text-sm text-gray-400">
                Set <code className="bg-dark-bg px-1.5 py-0.5 rounded text-accent">OPENROUTER_API_KEY</code> to access models.
              </p>
            </div>
          ) : (
            <ModelSelector
              models={models}
              selectedModels={selectedModels}
              onToggle={handleToggleModel}
              disabled={running}
            />
          )}
        </div>
      </div>

      {/* Run button */}
      <div className="mt-8 flex items-center justify-center">
        <button
          onClick={handleRun}
          disabled={!canRun || running}
          className="flex items-center gap-3 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 text-white font-semibold px-8 py-4 rounded-xl transition-all shadow-lg shadow-green-500/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          aria-label="Run Simulation"
        >
          {running ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              Running...
            </>
          ) : (
            <>
              <Play size={20} />
              Run Simulation
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-center">
          {error}
        </div>
      )}

      <p className="text-center text-sm text-gray-500 mt-4">
        Select a scenario and 1-5 models to compare how they handle the situation
      </p>
    </div>
  )
}
