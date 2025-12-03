import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Loader2 } from 'lucide-react'
import { useModule, useAgents } from '../hooks/useModules'
import { useSession, ChatMessage } from '../hooks/useSession'

export default function SessionPage() {
  const { moduleSlug } = useParams<{ moduleSlug: string }>()
  const navigate = useNavigate()
  const { module, loading: moduleLoading, error: moduleError } = useModule(moduleSlug)
  const { agents, loading: agentsLoading } = useAgents()
  const {
    state,
    messages,
    awaitingPrompt,
    evaluation,
    error: sessionError,
    connect,
    startSession,
    sendMessage,
  } = useSession()

  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [inputValue, setInputValue] = useState('')

  // Connect to WebSocket on mount
  useEffect(() => {
    connect()
  }, [connect])

  // Set default agent when agents load
  useEffect(() => {
    if (agents.length > 0 && !selectedAgent) {
      setSelectedAgent(agents[0].id)
    }
  }, [agents, selectedAgent])

  const handleStart = () => {
    if (!module || !selectedAgent) return
    startSession({
      moduleId: module.id,
      agentId: selectedAgent,
      variables: {},
    })
  }

  const handleSend = () => {
    if (!inputValue.trim() || state !== 'awaiting_input') return
    sendMessage(inputValue.trim())
    setInputValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (moduleLoading || agentsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={32} />
      </div>
    )
  }

  if (moduleError || !module) {
    return (
      <div className="p-8">
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-400">{moduleError || 'Module not found'}</p>
        </div>
      </div>
    )
  }

  const isIdle = state === 'disconnected' || state === 'connecting' || state === 'connected'
  const canSend = state === 'awaiting_input'

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="bg-dark-card border-b border-dark-border p-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-semibold text-white">{module.name}</h1>
            <p className="text-sm text-gray-400">{module.description}</p>
          </div>
          <SessionStatus state={state} />
        </div>
      </header>

      {/* Pre-session setup */}
      {isIdle && (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="bg-dark-card border border-dark-border rounded-xl p-8 max-w-md w-full">
            <h2 className="text-xl font-semibold text-white mb-4">Configure Session</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Target Agent
                </label>
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2 text-white focus:outline-none focus:border-accent"
                >
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name} ({agent.provider})
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleStart}
                disabled={state === 'connecting' || !selectedAgent}
                className="w-full bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-colors"
              >
                {state === 'connecting' ? 'Connecting...' : 'Start Session'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chat area */}
      {!isIdle && (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {state === 'running' && (
              <div className="flex items-center gap-2 text-gray-400">
                <Loader2 className="animate-spin" size={16} />
                <span>Processing...</span>
              </div>
            )}

            {evaluation && (
              <EvaluationCard evaluation={evaluation} />
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
                disabled={!canSend}
                placeholder={canSend ? "Type your message..." : "Waiting..."}
                className="flex-1 bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={!canSend || !inputValue.trim()}
                className="bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 rounded-lg transition-colors"
              >
                <Send size={20} />
              </button>
            </div>

            {sessionError && (
              <p className="text-sm text-red-400 mt-2">{sessionError}</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function SessionStatus({ state }: { state: string }) {
  const statusConfig: Record<string, { color: string; text: string }> = {
    disconnected: { color: 'bg-gray-500', text: 'Disconnected' },
    connecting: { color: 'bg-yellow-500', text: 'Connecting' },
    connected: { color: 'bg-green-500', text: 'Ready' },
    running: { color: 'bg-blue-500', text: 'Running' },
    awaiting_input: { color: 'bg-accent animate-pulse', text: 'Your Turn' },
    completed: { color: 'bg-green-500', text: 'Completed' },
    error: { color: 'bg-red-500', text: 'Error' },
  }

  const config = statusConfig[state] || statusConfig.disconnected

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${config.color}`} />
      <span className="text-sm text-gray-400">{config.text}</span>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const roleConfig: Record<string, { align: string; bg: string; label: string }> = {
    user: { align: 'justify-end', bg: 'bg-accent', label: 'You' },
    agent: { align: 'justify-start', bg: 'bg-dark-hover', label: 'Agent' },
    system: { align: 'justify-center', bg: 'bg-dark-border', label: 'System' },
    tool: { align: 'justify-start', bg: 'bg-purple-900/30', label: 'Tool' },
  }

  const config = roleConfig[message.role] || roleConfig.system

  if (message.role === 'system') {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-gray-500 bg-dark-card px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    )
  }

  return (
    <div className={`flex ${config.align} animate-slide-in`}>
      <div className={`max-w-[80%] ${config.bg} rounded-xl px-4 py-3`}>
        <div className="text-xs text-gray-400 mb-1">{config.label}</div>
        <div className="text-white whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  )
}

function EvaluationCard({ evaluation }: { evaluation: Record<string, unknown> }) {
  const score = evaluation.score as number | undefined
  const checks = evaluation.checks as Array<{ name: string; passed: boolean }> | undefined

  return (
    <div className="bg-dark-card border border-dark-border rounded-xl p-4 mt-4">
      <h3 className="text-lg font-semibold text-white mb-3">Evaluation Results</h3>

      {score !== undefined && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-gray-400">Score</span>
            <span className="text-xl font-bold text-accent">{Math.round(score * 100)}%</span>
          </div>
          <div className="w-full bg-dark-bg rounded-full h-2">
            <div
              className="bg-accent rounded-full h-2 transition-all"
              style={{ width: `${score * 100}%` }}
            />
          </div>
        </div>
      )}

      {checks && checks.length > 0 && (
        <div className="space-y-2">
          {checks.map((check, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className={check.passed ? 'text-green-400' : 'text-red-400'}>
                {check.passed ? '✓' : '✗'}
              </span>
              <span className="text-gray-300">{check.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
