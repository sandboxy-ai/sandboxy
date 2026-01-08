import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Clock, User, Bot, Loader2, AlertCircle, Play } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { api, SessionExport } from '../lib/api'

interface ChatMessage {
  role: 'user' | 'agent' | 'system' | 'tool'
  content: string
  timestamp?: string
}

export default function ReplayPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [session, setSession] = useState<SessionExport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const loadSession = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await api.exportSession(sessionId)
        setSession(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session')
      } finally {
        setLoading(false)
      }
    }

    loadSession()
  }, [sessionId])

  // Convert events to chat messages
  const messages: ChatMessage[] = session?.events
    ?.filter(e => ['user', 'user_message', 'agent', 'agent_message', 'system_message', 'tool_call', 'tool_result'].includes(e.type))
    ?.map(e => {
      // Determine role
      let role: ChatMessage['role'] = 'system'
      if (e.type === 'user' || e.type === 'user_message') {
        role = 'user'
      } else if (e.type === 'agent' || e.type === 'agent_message') {
        role = 'agent'
      } else if (e.type === 'tool_call' || e.type === 'tool_result') {
        role = 'tool'
      }

      // Extract content based on event type
      let content: string
      if (e.type === 'tool_call') {
        const tool = e.payload?.tool || e.payload?.tool_name || 'unknown'
        const action = e.payload?.action || ''
        const args = e.payload?.args || e.payload?.arguments || {}
        content = `**${tool}.${action}**\n\`\`\`json\n${JSON.stringify(args, null, 2)}\n\`\`\``
      } else if (e.type === 'tool_result') {
        const tool = e.payload?.tool || ''
        const action = e.payload?.action || ''
        const result = e.payload?.result as { success?: boolean; data?: unknown; error?: string } | undefined
        const status = result?.success ? '✓' : '✗'
        const data = result?.success ? result?.data : result?.error
        content = `**${tool}.${action}** ${status}\n\`\`\`json\n${JSON.stringify(data, null, 2)}\n\`\`\``
      } else {
        // User and agent messages - content is in payload.content
        content = (e.payload?.content as string) || ''
      }

      return {
        role,
        content,
        timestamp: e.timestamp || undefined,
      }
    })
    ?.filter(m => m.content) || []  // Filter out empty messages

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-400">
          <Loader2 className="animate-spin" size={24} />
          <span>Loading session replay...</span>
        </div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertCircle size={48} className="text-red-400 mx-auto mb-4" />
          <h2 className="text-xl text-white mb-2">Session Not Found</h2>
          <p className="text-gray-400 mb-6">{error || 'This session may have expired or been deleted.'}</p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover rounded-lg text-white transition-colors"
          >
            <ArrowLeft size={16} />
            Back to Home
          </Link>
        </div>
      </div>
    )
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-dark-card border-b border-dark-border flex-shrink-0">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(-1)}
                className="text-gray-400 hover:text-white transition-colors"
                aria-label="Session Replay"
              >
                <ArrowLeft size={20} />
              </button>
              <div>
                <h1 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Play size={18} className="text-accent" />
                  Session Replay
                </h1>
                <p className="text-sm text-gray-400">
                  {session.module_name || session.module_id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <div className="flex items-center gap-1.5">
                <Clock size={14} />
                <span>{formatDuration(session.duration_seconds)}</span>
              </div>
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                session.state === 'completed' ? 'bg-green-900/30 text-green-400' :
                session.state === 'error' ? 'bg-red-900/30 text-red-400' :
                'bg-gray-700 text-gray-300'
              }`}>
                {session.state}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Debug: Show event types summary */}
        {session?.events && session.events.length > 0 && (
          <div className="mb-4 p-3 bg-dark-card rounded-lg border border-dark-border text-xs">
            <span className="text-gray-500">Events ({session.events.length}): </span>
            <span className="text-gray-400">
              {Object.entries(
                session.events.reduce((acc, e) => {
                  acc[e.type] = (acc[e.type] || 0) + 1
                  return acc
                }, {} as Record<string, number>)
              ).map(([type, count]) => `${type}(${count})`).join(', ')}
            </span>
          </div>
        )}

        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No messages in this session
            </div>
          ) : (
            messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))
          )}
        </div>

        {/* Session Info */}
        <div className="mt-8 p-4 bg-dark-card rounded-lg border border-dark-border">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Session Details</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Session ID:</span>
              <span className="ml-2 text-gray-300 font-mono text-xs">{session.session_id}</span>
            </div>
            <div>
              <span className="text-gray-500">Agent:</span>
              <span className="ml-2 text-gray-300">{session.agent_id}</span>
            </div>
            <div>
              <span className="text-gray-500">Created:</span>
              <span className="ml-2 text-gray-300">{new Date(session.created_at).toLocaleString()}</span>
            </div>
            {session.completed_at && (
              <div>
                <span className="text-gray-500">Completed:</span>
                <span className="ml-2 text-gray-300">{new Date(session.completed_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
        </div>
      </main>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const config = {
    user: { align: 'justify-end', bg: 'bg-accent', icon: User, label: 'You' },
    agent: { align: 'justify-start', bg: 'bg-dark-hover', icon: Bot, label: 'Agent' },
    system: { align: 'justify-center', bg: 'bg-dark-border', icon: null, label: 'System' },
    tool: { align: 'justify-start', bg: 'bg-purple-900/30', icon: null, label: 'Tool' },
  }[message.role] || { align: 'justify-start', bg: 'bg-dark-card', icon: null, label: 'Unknown' }

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
        <div className="prose prose-invert max-w-none
          prose-p:my-3 prose-p:leading-relaxed prose-p:text-gray-100
          prose-headings:font-bold prose-headings:text-white prose-headings:border-b prose-headings:border-dark-border prose-headings:pb-2
          prose-h1:text-2xl prose-h1:mt-6 prose-h1:mb-4
          prose-h2:text-xl prose-h2:mt-5 prose-h2:mb-3
          prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2
          prose-h4:text-base prose-h4:mt-3 prose-h4:mb-2 prose-h4:border-none
          prose-ul:my-3 prose-ol:my-3 prose-li:my-1 prose-li:text-gray-200
          prose-code:bg-dark-card prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-accent prose-code:font-mono prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
          prose-pre:bg-dark-card prose-pre:border prose-pre:border-dark-border prose-pre:rounded-lg prose-pre:my-4 prose-pre:p-4
          prose-blockquote:border-l-4 prose-blockquote:border-accent prose-blockquote:bg-dark-card/50 prose-blockquote:pl-4 prose-blockquote:py-2 prose-blockquote:my-4 prose-blockquote:text-gray-300 prose-blockquote:italic
          prose-strong:text-white prose-strong:font-semibold
          prose-em:text-gray-200
          prose-a:text-accent prose-a:no-underline hover:prose-a:underline
          prose-hr:border-dark-border prose-hr:my-6"
        >
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
