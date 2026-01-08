import { useState, useMemo } from 'react'
import {
  Swords,
  Play,
  Trophy,
  Clock,
  DollarSign,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  AlertCircle,
  Loader2,
  MessageSquare,
  Zap,
  Filter,
  X,
  Scale,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useArenaPrompts, useArenaModels, useArenaCategories, useArenaRun, useArenaJudges } from '../hooks/useArena'
import type { ArenaPrompt, ArenaModel, ArenaRunResponse, JudgeTemplate } from '../lib/api'
import BlitzTab from '../components/BlitzTab'

type TabType = 'benchmark' | 'blitz'

// Popular models to show by default
const POPULAR_MODELS = [
  'openai/gpt-4o',
  'anthropic/claude-3.5-sonnet',
  'google/gemini-2.0-flash-exp:free',
  'deepseek/deepseek-chat',
  'x-ai/grok-3',
  'meta-llama/llama-3.3-70b-instruct',
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

  // Group models by provider
  const groupedModels = useMemo(() => {
    const filtered = models.filter(m =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.id.toLowerCase().includes(search.toLowerCase())
    )

    const groups: Record<string, ArenaModel[]> = {}
    for (const model of filtered) {
      if (!groups[model.provider]) {
        groups[model.provider] = []
      }
      groups[model.provider].push(model)
    }
    return groups
  }, [models, search])

  // Show popular models first if not searching and not showing all
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

      {/* Selected count */}
      <div className="text-sm text-gray-400">
        {selectedModels.length} model{selectedModels.length !== 1 ? 's' : ''} selected
        {selectedModels.length > 10 && (
          <span className="text-red-400 ml-2">(max 10)</span>
        )}
      </div>

      {/* Popular models (quick select) */}
      {popularModels.length > 0 && !search && (
        <div className="space-y-2">
          <div className="text-xs text-gray-500 uppercase tracking-wider">Popular</div>
          <div className="flex flex-wrap gap-2">
            {popularModels.map(model => (
              <button
                key={model.id}
                onClick={() => onToggle(model.id)}
                disabled={disabled || (selectedModels.length >= 10 && !selectedModels.includes(model.id))}
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

      {/* All models grouped by provider */}
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
                    disabled={disabled || (selectedModels.length >= 10 && !selectedModels.includes(model.id))}
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

function PromptCard({
  prompt,
  selected,
  onClick,
}: {
  prompt: ArenaPrompt
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
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-white truncate">{prompt.title}</h3>
            {prompt.is_featured && (
              <Sparkles size={14} className="text-yellow-400 flex-shrink-0" />
            )}
          </div>
          <p className="text-sm text-gray-400 line-clamp-2">{prompt.text}</p>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="text-xs px-2 py-0.5 bg-dark-bg rounded-full text-gray-500 capitalize">
              {prompt.category}
            </span>
            {prompt.judge_template_id && (
              <span className="text-xs px-2 py-0.5 bg-purple-500/20 rounded-full text-purple-400 flex items-center gap-1">
                <Scale size={10} />
                {prompt.judge_template_id}
              </span>
            )}
            {prompt.tags?.slice(0, 2).map(tag => (
              <span key={tag} className="text-xs text-gray-600">
                #{tag}
              </span>
            ))}
          </div>
        </div>
        {selected && (
          <CheckCircle size={20} className="text-accent flex-shrink-0" />
        )}
      </div>
    </button>
  )
}

function JudgeSelector({
  judges,
  selectedJudge,
  onSelect,
  disabled,
}: {
  judges: JudgeTemplate[]
  selectedJudge: JudgeTemplate | null
  onSelect: (judge: JudgeTemplate | null) => void
  disabled?: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  // Group judges by type
  const llmJudges = judges.filter(j => j.judge_type === 'llm')
  const otherJudges = judges.filter(j => j.judge_type !== 'llm')

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Scale size={16} />
          <span>Judge</span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-gray-500 hover:text-white transition-colors"
          disabled={disabled}
        >
          {expanded ? 'Hide options' : 'Show all'}
        </button>
      </div>

      {/* Quick select popular judges */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onSelect(null)}
          disabled={disabled}
          className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
            !selectedJudge
              ? 'bg-accent text-white'
              : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
          } disabled:opacity-50`}
        >
          Default
        </button>
        {llmJudges.slice(0, 4).map(judge => (
          <button
            key={judge.id}
            onClick={() => onSelect(judge)}
            disabled={disabled}
            title={judge.description || undefined}
            className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
              selectedJudge?.id === judge.id
                ? 'bg-accent text-white'
                : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
            } disabled:opacity-50`}
          >
            {judge.name}
          </button>
        ))}
      </div>

      {/* Expanded view with all judges */}
      {expanded && (
        <div className="space-y-3 p-3 bg-dark-bg rounded-lg">
          {llmJudges.length > 4 && (
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">LLM Judges</div>
              <div className="flex flex-wrap gap-2">
                {llmJudges.slice(4).map(judge => (
                  <button
                    key={judge.id}
                    onClick={() => onSelect(judge)}
                    disabled={disabled}
                    title={judge.description || undefined}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      selectedJudge?.id === judge.id
                        ? 'bg-accent text-white'
                        : 'border border-dark-border text-gray-300 hover:border-accent/50'
                    } disabled:opacity-50`}
                  >
                    {judge.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {otherJudges.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Other Judges</div>
              <div className="flex flex-wrap gap-2">
                {otherJudges.map(judge => (
                  <button
                    key={judge.id}
                    onClick={() => onSelect(judge)}
                    disabled={disabled}
                    title={judge.description || undefined}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      selectedJudge?.id === judge.id
                        ? 'bg-accent text-white'
                        : 'border border-dark-border text-gray-300 hover:border-accent/50'
                    } disabled:opacity-50`}
                  >
                    {judge.name}
                    <span className="ml-1 text-xs opacity-60">({judge.judge_type})</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Selected judge description */}
      {selectedJudge && selectedJudge.description && (
        <p className="text-xs text-gray-500 line-clamp-2">
          {selectedJudge.description}
        </p>
      )}
    </div>
  )
}

function ResultCard({
  modelId,
  result,
  judgment,
  isWinner,
  rank,
}: {
  modelId: string
  result: ArenaRunResponse['results'][string]
  judgment: ArenaRunResponse['judgments'][string] | undefined
  isWinner: boolean
  rank: number
}) {
  const [expanded, setExpanded] = useState(false)

  const modelName = modelId.split('/').pop() || modelId

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
              <p className="text-xs text-gray-500">{modelId}</p>
            </div>
            {isWinner && (
              <Trophy size={18} className="text-yellow-400" />
            )}
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
      {judgment && (
        <div className="px-4 py-3 bg-dark-bg/50 border-b border-dark-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {judgment.passed ? (
                <CheckCircle size={16} className="text-green-400" />
              ) : (
                <XCircle size={16} className="text-red-400" />
              )}
              <span className="text-sm text-gray-300">
                Score: <span className="font-semibold text-white">{(judgment.score * 100).toFixed(0)}%</span>
              </span>
              <span className="text-xs text-gray-500 capitalize">
                ({judgment.judge_type} judge)
              </span>
            </div>
          </div>
          {judgment.reasoning && (
            <p className="text-xs text-gray-400 mt-2 line-clamp-2">
              {judgment.reasoning}
            </p>
          )}
        </div>
      )}

      {/* Response */}
      <div className="p-4">
        {result.error ? (
          <div className="flex items-start gap-2 text-red-400">
            <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
            <span className="text-sm">{result.error}</span>
          </div>
        ) : (
          <>
            <div
              className={`text-gray-300 ${
                expanded ? '' : 'line-clamp-4'
              } prose prose-invert prose-sm max-w-none
                prose-p:my-2 prose-p:leading-relaxed prose-p:text-gray-200
                prose-headings:font-bold prose-headings:text-white
                prose-h1:text-xl prose-h1:mt-4 prose-h1:mb-3 prose-h1:border-b prose-h1:border-dark-border prose-h1:pb-2
                prose-h2:text-lg prose-h2:mt-4 prose-h2:mb-2 prose-h2:border-b prose-h2:border-dark-border prose-h2:pb-1
                prose-h3:text-base prose-h3:mt-3 prose-h3:mb-2
                prose-h4:text-sm prose-h4:mt-2 prose-h4:mb-1
                prose-ul:my-2 prose-ol:my-2 prose-li:my-1 prose-li:text-gray-200
                prose-code:bg-dark-card prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-accent prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
                prose-pre:bg-dark-card prose-pre:border prose-pre:border-dark-border prose-pre:rounded-lg prose-pre:my-3 prose-pre:p-3
                prose-blockquote:border-l-4 prose-blockquote:border-accent prose-blockquote:bg-dark-card/50 prose-blockquote:pl-3 prose-blockquote:py-1 prose-blockquote:my-3 prose-blockquote:text-gray-300 prose-blockquote:italic
                prose-strong:text-white prose-strong:font-semibold
                prose-em:text-gray-200
                prose-a:text-accent prose-a:no-underline hover:prose-a:underline`}
            >
              <ReactMarkdown>{result.response}</ReactMarkdown>
            </div>
            {result.response.length > 300 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover mt-2 transition-colors"
              >
                {expanded ? (
                  <>
                    <ChevronUp size={14} />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronDown size={14} />
                    Show more
                  </>
                )}
              </button>
            )}
          </>
        )}
      </div>

      {/* Token stats */}
      <div className="px-4 pb-4 flex gap-4 text-xs text-gray-500">
        <span>In: {result.input_tokens} tokens</span>
        <span>Out: {result.output_tokens} tokens</span>
      </div>
    </div>
  )
}

function ArenaResults({ result }: { result: ArenaRunResponse }) {
  return (
    <div className="space-y-6">
      {/* Summary header */}
      <div className="bg-gradient-to-r from-accent/10 to-purple-500/10 border border-accent/20 rounded-xl p-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">
              {result.winner ? (
                <>
                  <Trophy className="inline mr-2 text-yellow-400" size={24} />
                  Winner: {result.winner.split('/').pop()}
                </>
              ) : (
                'Results'
              )}
            </h2>
            <p className="text-gray-400">
              Tested {result.models.length} models
            </p>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{result.total_latency_ms}ms</div>
              <div className="text-gray-500">Total Time</div>
            </div>
            {result.total_cost_usd !== null && (
              <div className="text-center">
                <div className="text-2xl font-bold text-white">${result.total_cost_usd.toFixed(4)}</div>
                <div className="text-gray-500">Total Cost</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Ranking */}
      {result.ranking.length > 1 && (
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Ranking</h3>
          <div className="flex flex-wrap gap-2">
            {result.ranking.map(([modelId, score], index) => (
              <div
                key={modelId}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                  index === 0
                    ? 'bg-yellow-500/20 text-yellow-400'
                    : 'bg-dark-bg text-gray-400'
                }`}
              >
                <span className="font-bold">#{index + 1}</span>
                <span>{modelId.split('/').pop()}</span>
                <span className="text-xs opacity-75">{(score * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Individual results */}
      <div className="grid gap-4 md:grid-cols-2">
        {result.ranking.map(([modelId], index) => (
          <ResultCard
            key={modelId}
            modelId={modelId}
            result={result.results[modelId]}
            judgment={result.judgments[modelId]}
            isWinner={modelId === result.winner}
            rank={index + 1}
          />
        ))}
      </div>
    </div>
  )
}

export default function ArenaPage() {
  const { prompts, loading: promptsLoading } = useArenaPrompts()
  const { models, loading: modelsLoading } = useArenaModels()
  const { categories } = useArenaCategories()
  const { judges } = useArenaJudges()
  const { result, loading: runLoading, error: runError, runArena, reset } = useArenaRun()

  const [activeTab, setActiveTab] = useState<TabType>('benchmark')
  const [selectedPrompt, setSelectedPrompt] = useState<ArenaPrompt | null>(null)
  const [customPrompt, setCustomPrompt] = useState('')
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [selectedJudge, setSelectedJudge] = useState<JudgeTemplate | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [useCustomPrompt, setUseCustomPrompt] = useState(false)

  // Filter prompts by category
  const filteredPrompts = useMemo(() => {
    if (!categoryFilter) return prompts
    return prompts.filter(p => p.category === categoryFilter)
  }, [prompts, categoryFilter])

  const handleToggleModel = (modelId: string) => {
    setSelectedModels(prev =>
      prev.includes(modelId)
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId]
    )
  }

  const handleRun = async () => {
    if (selectedModels.length === 0) return
    if (!useCustomPrompt && !selectedPrompt) return
    if (useCustomPrompt && !customPrompt.trim()) return

    await runArena({
      prompt_id: useCustomPrompt ? undefined : selectedPrompt?.id,
      prompt_text: useCustomPrompt ? customPrompt : undefined,
      models: selectedModels,
      // Pass judge template for custom prompts
      judge_template_id: useCustomPrompt && selectedJudge ? selectedJudge.id : undefined,
    })
  }

  const canRun =
    selectedModels.length > 0 &&
    selectedModels.length <= 10 &&
    (useCustomPrompt ? customPrompt.trim().length > 0 : selectedPrompt !== null)

  // Show results if we have them (only for benchmark tab)
  if (result && activeTab === 'benchmark') {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <button
          onClick={reset}
          className="mb-6 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          aria-label="New Run"
        >
          <X size={16} />
          New Run
        </button>
        <ArenaResults result={result} />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-gradient-to-br from-accent to-purple-500 rounded-xl flex items-center justify-center">
            <Swords size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Arena</h1>
            <p className="text-gray-400">Test prompts against multiple AI models</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 p-1 bg-dark-card border border-dark-border rounded-xl w-fit">
          <button
            onClick={() => setActiveTab('benchmark')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'benchmark'
                ? 'bg-accent text-white'
                : 'text-gray-400 hover:text-white hover:bg-dark-bg'
            }`}
            aria-label="Benchmark"
          >
            <Swords size={16} />
            Benchmark
          </button>
          <button
            onClick={() => setActiveTab('blitz')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'blitz'
                ? 'bg-gradient-to-r from-yellow-500 to-orange-500 text-white'
                : 'text-gray-400 hover:text-white hover:bg-dark-bg'
            }`}
            aria-label="Blitz"
          >
            <Zap size={16} />
            Blitz
          </button>
        </div>
      </div>

      {/* Blitz Tab */}
      {activeTab === 'blitz' && (
        <div className="bg-dark-card border border-dark-border rounded-xl -mx-2">
          <BlitzTab models={models} modelsLoading={modelsLoading} />
        </div>
      )}

      {/* Benchmark Tab */}
      {activeTab === 'benchmark' && (
        <>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left: Prompt Selection */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <MessageSquare size={20} />
              Prompt
            </h2>
            <button
              onClick={() => setUseCustomPrompt(!useCustomPrompt)}
              className={`text-sm px-3 py-1 rounded-lg transition-colors ${
                useCustomPrompt
                  ? 'bg-accent text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              aria-label="Prompt"
            >
              {useCustomPrompt ? 'Use Template' : 'Custom Prompt'}
            </button>
          </div>

          {useCustomPrompt ? (
            <div className="space-y-4">
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Enter your prompt here..."
                rows={6}
                className="w-full bg-dark-card border border-dark-border rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent resize-none"
                disabled={runLoading}
              />

              {/* Judge selection for custom prompts */}
              {judges.length > 0 && (
                <div className="bg-dark-card border border-dark-border rounded-xl p-4">
                  <JudgeSelector
                    judges={judges}
                    selectedJudge={selectedJudge}
                    onSelect={setSelectedJudge}
                    disabled={runLoading}
                  />
                </div>
              )}

              <p className="text-xs text-gray-500">
                Your prompt will be sent to all selected models simultaneously.
              </p>
            </div>
          ) : (
            <>
              {/* Category filter */}
              <div className="flex items-center gap-2 flex-wrap">
                <Filter size={16} className="text-gray-500" />
                <button
                  onClick={() => setCategoryFilter(null)}
                  className={`text-sm px-3 py-1 rounded-lg transition-colors ${
                    !categoryFilter
                      ? 'bg-accent text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                  aria-label="All"
                >
                  All
                </button>
                {categories.map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => setCategoryFilter(cat.id)}
                    className={`text-sm px-3 py-1 rounded-lg transition-colors ${
                      categoryFilter === cat.id
                        ? 'bg-accent text-white'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>

              {/* Prompt list */}
              {promptsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="animate-spin text-accent" size={24} />
                </div>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                  {filteredPrompts.map(prompt => (
                    <PromptCard
                      key={prompt.id}
                      prompt={prompt}
                      selected={selectedPrompt?.id === prompt.id}
                      onClick={() => setSelectedPrompt(prompt)}
                    />
                  ))}
                  {filteredPrompts.length === 0 && (
                    <p className="text-gray-500 text-center py-8">
                      No prompts available
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Right: Model Selection */}
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Zap size={20} />
            Models
          </h2>

          {modelsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-accent" size={24} />
            </div>
          ) : models.length === 0 ? (
            <div className="bg-dark-card border border-dark-border rounded-xl p-6 text-center">
              <AlertCircle className="mx-auto text-yellow-400 mb-3" size={32} />
              <h3 className="font-semibold text-white mb-2">No API Key Configured</h3>
              <p className="text-sm text-gray-400 mb-4">
                Set <code className="bg-dark-bg px-1.5 py-0.5 rounded text-accent">OPENROUTER_API_KEY</code> to access 400+ models including GPT-4, Claude, Gemini, and Llama.
              </p>
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-accent hover:text-accent-hover transition-colors"
              >
                Get an OpenRouter API key
                <span className="text-xs">-&gt;</span>
              </a>
            </div>
          ) : (
            <ModelSelector
              models={models}
              selectedModels={selectedModels}
              onToggle={handleToggleModel}
              disabled={runLoading}
            />
          )}
        </div>
      </div>

      {/* Run button */}
      <div className="mt-8 flex items-center justify-center">
        <button
          onClick={handleRun}
          disabled={!canRun || runLoading}
          className="flex items-center gap-3 bg-gradient-to-r from-accent to-purple-500 hover:from-accent-hover hover:to-purple-400 text-white font-semibold px-8 py-4 rounded-xl transition-all shadow-lg shadow-accent/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          aria-label="Run Simulation"
        >
          {runLoading ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              Running...
            </>
          ) : (
            <>
              <Play size={20} />
              Run Arena
            </>
          )}
        </button>
      </div>

      {/* Error display */}
      {runError && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-center">
          {runError}
        </div>
      )}

      {/* Help text */}
      <p className="text-center text-sm text-gray-500 mt-4">
        Select a prompt and 1-10 models, then click Run to compare responses
      </p>
      </>
      )}
    </div>
  )
}
