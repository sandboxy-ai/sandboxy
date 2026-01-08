import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Send,
  Loader2,
  Trophy,
  Target,
  Clock,
  Zap,
  CheckCircle2,
  Circle,
  Play,
  RotateCcw,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import ShareButton from '../components/ShareButton'
import { useSession, ChatMessage } from '../hooks/useSession'
import {
  api,
  ArenaModel,
  ChallengeSummary,
  ChallengeDetail,
  ChallengeGoal,
  ChallengeCompleteResponse,
} from '../lib/api'

type PageState = 'select' | 'pregame' | 'playing' | 'results'

export default function ChallengePage() {
  const { challengeId } = useParams<{ challengeId: string }>()
  const navigate = useNavigate()

  // Page state
  const [pageState, setPageState] = useState<PageState>('select')
  const [challenges, setChallenges] = useState<ChallengeSummary[]>([])
  const [selectedChallenge, setSelectedChallenge] = useState<ChallengeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Game state
  const [goals, setGoals] = useState<ChallengeGoal[]>([])
  const [maxTurns, setMaxTurns] = useState(8)
  const [turnsUsed, setTurnsUsed] = useState(0)
  const [results, setResults] = useState<ChallengeCompleteResponse | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>('anthropic/claude-3.5-haiku')
  const [models, setModels] = useState<ArenaModel[]>([])

  // Chat state
  const [inputValue, setInputValue] = useState('')
  const {
    state: sessionState,
    dbSessionId,
    messages,
    awaitingPrompt,
    error: sessionError,
    connect,
    startSession,
    sendMessage,
  } = useSession()

  // Define loading functions with useCallback for stable references
  const loadChallenges = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.getChallenges()
      setChallenges(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load challenges')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadModels = useCallback(async () => {
    try {
      const data = await api.getArenaModels()
      setModels(data.models)
    } catch (err) {
      console.error('Failed to load models:', err)
    }
  }, [])

  const loadChallenge = useCallback(async (id: string) => {
    try {
      setLoading(true)
      const data = await api.getChallenge(id)
      setSelectedChallenge(data)
      setGoals(data.goals)
      setMaxTurns(data.max_turns)
      setPageState('pregame')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load challenge')
    } finally {
      setLoading(false)
    }
  }, [])

  // Load challenges and models on mount
  useEffect(() => {
    loadChallenges()
    loadModels()
  }, [loadChallenges, loadModels])

  // Handle route parameter
  useEffect(() => {
    if (challengeId && challenges.length > 0) {
      loadChallenge(challengeId)
    }
  }, [challengeId, challenges, loadChallenge])

  // Connect to WebSocket when playing
  useEffect(() => {
    if (pageState === 'playing' && selectedChallenge) {
      connect()
    }
  }, [pageState, selectedChallenge, connect])

  // Start session when WebSocket is connected
  useEffect(() => {
    if (sessionState === 'connected' && pageState === 'playing' && selectedChallenge) {
      startSession({
        moduleId: `challenge:${selectedChallenge.id}`,
        agentId: selectedModel,  // Pass model ID directly
        variables: {},
      })
    }
  }, [sessionState, pageState, selectedChallenge, selectedModel, startSession])

  // Count turns from messages
  useEffect(() => {
    const userMessages = messages.filter((m) => m.role === 'user')
    setTurnsUsed(userMessages.length)
  }, [messages])

  const handleSelectChallenge = (challenge: ChallengeSummary) => {
    navigate(`/challenge/${challenge.id}`)
  }

  const handleStartChallenge = async () => {
    if (!selectedChallenge) return

    setPageState('playing')
    // WebSocket session will be started after connect() in useEffect
  }

  const handleCompleteChallenge = useCallback(async () => {
    if (!selectedChallenge || !dbSessionId) return

    try {
      setLoading(true)
      const response = await api.completeChallenge(selectedChallenge.id, dbSessionId)
      setResults(response)
      setPageState('results')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete challenge')
    } finally {
      setLoading(false)
    }
  }, [selectedChallenge, dbSessionId])

  // Auto-complete when max turns reached or session completed
  useEffect(() => {
    if (
      pageState === 'playing' &&
      dbSessionId &&
      (turnsUsed >= maxTurns || sessionState === 'completed')
    ) {
      handleCompleteChallenge()
    }
  }, [turnsUsed, maxTurns, sessionState, pageState, dbSessionId, handleCompleteChallenge])

  const handleSend = () => {
    if (!inputValue.trim() || sessionState !== 'awaiting_input') return
    if (turnsUsed >= maxTurns) {
      handleCompleteChallenge()
      return
    }
    sendMessage(inputValue.trim())
    setInputValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handlePlayAgain = () => {
    setResults(null)
    setTurnsUsed(0)
    setPageState('pregame')
  }

  const handleBackToSelect = () => {
    setSelectedChallenge(null)
    setResults(null)
    setTurnsUsed(0)
    setPageState('select')
    navigate('/challenge')
  }

  if (loading && pageState === 'select') {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={32} />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-dark-card border-b border-dark-border p-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={pageState === 'select' ? () => navigate('/') : handleBackToSelect}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-semibold text-white">
              {pageState === 'select'
                ? 'Challenges'
                : selectedChallenge?.name || 'Challenge'}
            </h1>
            {pageState === 'playing' && (
              <div className="flex items-center gap-4 text-sm text-gray-400">
                <span className="flex items-center gap-1">
                  <Clock size={14} />
                  Turn {turnsUsed} of {maxTurns}
                </span>
              </div>
            )}
          </div>
          {pageState === 'playing' && (
            <TurnIndicator current={turnsUsed} max={maxTurns} />
          )}
        </div>
      </header>

      {/* Challenge Select */}
      {pageState === 'select' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Play Against AI</h2>
              <p className="text-gray-400">
                Compete in interactive challenges. Use your wits to achieve goals against
                AI defenders.
              </p>
            </div>

            {error && (
              <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4 mb-6">
                <p className="text-red-400">{error}</p>
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              {challenges.map((challenge) => (
                <ChallengeCard
                  key={challenge.id}
                  challenge={challenge}
                  onClick={() => handleSelectChallenge(challenge)}
                />
              ))}
            </div>

            {challenges.length === 0 && !loading && (
              <div className="text-center py-12">
                <p className="text-gray-500">No challenges available yet.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Pre-game */}
      {pageState === 'pregame' && selectedChallenge && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto">
            <div className="bg-dark-card border border-dark-border rounded-xl p-8">
              {/* Challenge Info */}
              <div className="text-center mb-8">
                <div className="flex justify-center gap-2 mb-4">
                  <DifficultyBadge difficulty={selectedChallenge.difficulty} />
                  <span className="px-2 py-1 bg-dark-border rounded text-xs text-gray-400">
                    {selectedChallenge.category}
                  </span>
                </div>
                <h2 className="text-2xl font-bold text-white mb-4">
                  {selectedChallenge.name}
                </h2>
                <p className="text-gray-400 whitespace-pre-line">
                  {selectedChallenge.description}
                </p>
              </div>

              {/* Rules */}
              <div className="flex justify-center gap-8 mb-8 text-sm">
                <div className="flex items-center gap-2 text-gray-400">
                  <Clock size={16} />
                  <span>{selectedChallenge.max_turns} turns max</span>
                </div>
                {selectedChallenge.time_limit_seconds && (
                  <div className="flex items-center gap-2 text-gray-400">
                    <Zap size={16} />
                    <span>{Math.floor(selectedChallenge.time_limit_seconds / 60)}m time limit</span>
                  </div>
                )}
              </div>

              {/* Model Selection */}
              <div className="mb-8">
                <label className="block text-sm text-gray-400 mb-2">
                  AI Opponent
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2 text-white focus:outline-none focus:border-accent"
                >
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {models.find(m => m.id === selectedModel)?.context_length?.toLocaleString()} token context
                </p>
              </div>

              {/* Goals */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Target size={18} />
                  Goals
                </h3>
                <div className="space-y-3">
                  {goals.map((goal) => (
                    <div
                      key={goal.id}
                      className="flex items-start gap-3 bg-dark-bg rounded-lg p-3"
                    >
                      <Circle size={16} className="text-gray-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-white font-medium">{goal.name}</span>
                          <span className="text-accent text-sm">+{goal.points} pts</span>
                        </div>
                        <p className="text-sm text-gray-500">{goal.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Start Button */}
              <button
                onClick={handleStartChallenge}
                disabled={loading}
                className="w-full bg-accent hover:bg-accent-hover disabled:opacity-50 text-white font-semibold py-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                aria-label="Start Challenge"
              >
                {loading ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <>
                    <Play size={20} />
                    Start Challenge
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Playing */}
      {pageState === 'playing' && selectedChallenge && (
        <div className="flex-1 flex overflow-hidden">
          {/* Chat area */}
          <div className="flex-1 flex flex-col min-w-0">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}

              {sessionState === 'running' && (
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="animate-spin" size={16} />
                  <span>AI is responding...</span>
                </div>
              )}
            </div>

            {/* Input area */}
            <div className="bg-dark-card border-t border-dark-border p-4">
              {awaitingPrompt && (
                <p className="text-sm text-accent mb-2">{awaitingPrompt}</p>
              )}

              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={sessionState !== 'awaiting_input' || turnsUsed >= maxTurns}
                  placeholder={
                    turnsUsed >= maxTurns
                      ? 'No turns remaining'
                      : sessionState === 'awaiting_input'
                      ? 'Type your message...'
                      : 'Waiting...'
                  }
                  className="flex-1 bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent disabled:opacity-50"
                />
                <button
                  onClick={handleSend}
                  disabled={
                    sessionState !== 'awaiting_input' ||
                    !inputValue.trim() ||
                    turnsUsed >= maxTurns
                  }
                  className="bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 rounded-lg transition-colors"
                  aria-label="Send"
                >
                  <Send size={20} />
                </button>
              </div>

              {sessionError && (
                <p className="text-sm text-red-400 mt-2">{sessionError}</p>
              )}

              {turnsUsed >= maxTurns - 1 && turnsUsed < maxTurns && (
                <p className="text-sm text-yellow-400 mt-2">Final turn! Make it count!</p>
              )}
            </div>
          </div>

          {/* Goals sidebar */}
          <div className="w-72 border-l border-dark-border bg-dark-bg p-4 overflow-y-auto">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <Target size={16} />
              Goals
            </h3>
            <div className="space-y-3">
              {goals.map((goal) => (
                <GoalItem key={goal.id} goal={goal} />
              ))}
            </div>

            <div className="mt-6 pt-4 border-t border-dark-border">
              <div className="text-sm text-gray-400">
                <div className="flex justify-between mb-2">
                  <span>Turns remaining</span>
                  <span className="text-white">{maxTurns - turnsUsed}</span>
                </div>
                <div className="flex justify-between">
                  <span>Turn bonus potential</span>
                  <span className="text-accent">+{(maxTurns - turnsUsed) * 3} pts</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleCompleteChallenge}
              className="w-full mt-6 bg-dark-card hover:bg-dark-hover border border-dark-border text-gray-300 hover:text-white py-2 rounded-lg transition-colors text-sm"
              aria-label="End Challenge Early"
            >
              End Challenge Early
            </button>
          </div>
        </div>
      )}

      {/* Results */}
      {pageState === 'results' && results && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto">
            <div className="bg-dark-card border border-dark-border rounded-xl p-8 text-center">
              {/* Score */}
              <div className="mb-8">
                <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-accent/20 mb-4">
                  <Trophy size={40} className="text-accent" />
                </div>
                <h2 className="text-3xl font-bold text-white mb-2">
                  {results.score.toFixed(0)} pts
                </h2>
                <p className="text-gray-400">
                  out of {results.max_score.toFixed(0)} possible
                </p>
                <div className="w-full bg-dark-border rounded-full h-3 mt-4">
                  <div
                    className="bg-accent h-3 rounded-full transition-all"
                    style={{
                      width: `${(results.score / results.max_score) * 100}%`,
                    }}
                  />
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mb-8">
                <div className="bg-dark-bg rounded-lg p-4">
                  <div className="text-2xl font-bold text-white">
                    {results.goals_completed}/{results.goals_total}
                  </div>
                  <div className="text-sm text-gray-400">Goals Achieved</div>
                </div>
                <div className="bg-dark-bg rounded-lg p-4">
                  <div className="text-2xl font-bold text-white">
                    {results.turns_used}/{results.max_turns}
                  </div>
                  <div className="text-sm text-gray-400">Turns Used</div>
                </div>
                <div className="bg-dark-bg rounded-lg p-4">
                  <div className="text-2xl font-bold text-accent">
                    +{results.turn_bonus.toFixed(0)}
                  </div>
                  <div className="text-sm text-gray-400">Turn Bonus</div>
                </div>
              </div>

              {/* Goal breakdown */}
              <div className="text-left mb-8">
                <h3 className="text-lg font-semibold text-white mb-4">Goal Breakdown</h3>
                <div className="space-y-2">
                  {results.goals.map((goal) => (
                    <div
                      key={goal.id}
                      className={`flex items-center justify-between p-3 rounded-lg ${
                        goal.achieved ? 'bg-green-900/20' : 'bg-dark-bg'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {goal.achieved ? (
                          <CheckCircle2 size={18} className="text-green-400" />
                        ) : (
                          <Circle size={18} className="text-gray-500" />
                        )}
                        <span
                          className={goal.achieved ? 'text-white' : 'text-gray-500'}
                        >
                          {goal.name}
                        </span>
                      </div>
                      <span
                        className={
                          goal.achieved ? 'text-green-400' : 'text-gray-500'
                        }
                      >
                        {goal.achieved
                          ? `+${goal.points_earned.toFixed(0)} pts`
                          : '0 pts'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Share */}
              <div className="flex justify-center mb-6">
                <ShareButton
                  sessionId={results.session_id}
                  score={results.score / results.max_score}
                  moduleName={results.challenge_name}
                />
              </div>

              {/* Actions */}
              <div className="flex gap-4">
                <button
                  onClick={handlePlayAgain}
                  className="flex-1 bg-accent hover:bg-accent-hover text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
                  aria-label="Play Again"
                >
                  <RotateCcw size={18} />
                  Play Again
                </button>
                <button
                  onClick={handleBackToSelect}
                  className="flex-1 bg-dark-bg hover:bg-dark-hover border border-dark-border text-white py-3 rounded-lg transition-colors"
                  aria-label="More Challenges"
                >
                  More Challenges
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Components
// =============================================================================

function ChallengeCard({
  challenge,
  onClick,
}: {
  challenge: ChallengeSummary
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="text-left bg-dark-card border border-dark-border rounded-xl p-6 hover:border-accent/50 hover:bg-dark-hover transition-all group"
    >
      <div className="flex items-start justify-between mb-3">
        <DifficultyBadge difficulty={challenge.difficulty} />
        <span className="text-xs text-gray-500">{challenge.max_turns} turns</span>
      </div>
      <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-accent transition-colors">
        {challenge.name}
      </h3>
      <p className="text-sm text-gray-400 line-clamp-2 mb-4">{challenge.description}</p>
      <div className="flex flex-wrap gap-2">
        {challenge.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 bg-dark-border rounded text-xs text-gray-400"
          >
            {tag}
          </span>
        ))}
      </div>
    </button>
  )
}

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    easy: { bg: 'bg-green-900/30', text: 'text-green-400' },
    medium: { bg: 'bg-yellow-900/30', text: 'text-yellow-400' },
    hard: { bg: 'bg-red-900/30', text: 'text-red-400' },
  }
  const { bg, text } = config[difficulty] || config.medium

  return (
    <span className={`px-2 py-1 ${bg} rounded text-xs ${text} capitalize`}>
      {difficulty}
    </span>
  )
}

function TurnIndicator({ current, max }: { current: number; max: number }) {
  const remaining = max - current
  const percentage = (current / max) * 100

  return (
    <div className="flex items-center gap-3">
      <div className="w-32 bg-dark-border rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${
            remaining <= 2 ? 'bg-red-500' : remaining <= 4 ? 'bg-yellow-500' : 'bg-accent'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={`text-sm font-medium ${remaining <= 2 ? 'text-red-400' : 'text-gray-400'}`}>
        {remaining} left
      </span>
    </div>
  )
}

function GoalItem({ goal }: { goal: ChallengeGoal }) {
  const achieved = goal.achieved

  return (
    <div
      className={`flex items-start gap-2 p-2 rounded ${
        achieved ? 'bg-green-900/20' : 'bg-dark-card'
      }`}
    >
      {achieved ? (
        <CheckCircle2 size={16} className="text-green-400 mt-0.5 flex-shrink-0" />
      ) : (
        <Circle size={16} className="text-gray-500 mt-0.5 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span
            className={`text-sm ${achieved ? 'text-green-400' : 'text-gray-300'} truncate`}
          >
            {goal.name}
          </span>
          <span className={`text-xs ml-2 ${achieved ? 'text-green-400' : 'text-gray-500'}`}>
            {goal.points}
          </span>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const roleConfig: Record<string, { align: string; bg: string; label: string }> = {
    user: { align: 'justify-end', bg: 'bg-accent', label: 'You' },
    agent: { align: 'justify-start', bg: 'bg-dark-hover', label: 'Support Agent' },
    system: { align: 'justify-center', bg: 'bg-dark-border', label: 'System' },
  }

  const config = roleConfig[message.role] || roleConfig.system

  if (message.role === 'system') {
    return (
      <div className="flex justify-center">
        <span className="text-xs px-3 py-1 rounded-full text-gray-500 bg-dark-card">
          {message.content}
        </span>
      </div>
    )
  }

  const renderContent = () => {
    if (message.role === 'agent') {
      return (
        <div className="prose prose-invert max-w-none prose-p:my-2 prose-p:leading-relaxed prose-p:text-gray-100">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      )
    }
    return <div className="text-white whitespace-pre-wrap">{message.content}</div>
  }

  return (
    <div className={`flex ${config.align} animate-slide-in`}>
      <div className={`max-w-[80%] ${config.bg} rounded-xl px-4 py-3`}>
        <div className="text-xs text-gray-400 mb-1">{config.label}</div>
        {renderContent()}
      </div>
    </div>
  )
}
