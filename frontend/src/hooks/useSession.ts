import { useState, useEffect, useCallback, useRef } from 'react'

export type SessionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'running'
  | 'awaiting_input'
  | 'completed'
  | 'error'

export interface ChatMessage {
  id: string
  role: 'user' | 'agent' | 'system' | 'tool'
  content: string
  timestamp: Date
  metadata?: Record<string, unknown>
}

export interface SessionConfig {
  moduleId: string
  agentId: string
  variables?: Record<string, unknown>
}

export interface GameState {
  cash?: number
  inventory?: Record<string, number>
  weather?: string
  time?: string
  day?: number
  turn?: number
  stats?: {
    customers_served?: number
    customers_lost?: number
    profit?: number
    reputation?: number
  }
  [key: string]: unknown
}

export interface EventResult {
  event: string
  message: string
  effects?: Record<string, unknown>
  warning?: string
}

interface WebSocketMessage {
  type: string
  session_id?: string
  event_type?: string
  payload?: Record<string, unknown>
  prompt?: string
  evaluation?: Record<string, unknown>
  message?: string
  event?: string
  result?: EventResult
}

export function useSession() {
  const [state, setState] = useState<SessionState>('disconnected')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [awaitingPrompt, setAwaitingPrompt] = useState<string | null>(null)
  const [evaluation, setEvaluation] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [gameState, setGameState] = useState<GameState | null>(null)
  const [lastEvent, setLastEvent] = useState<EventResult | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const messageIdRef = useRef(0)
  const mountedRef = useRef(true)

  const addMessage = useCallback((
    role: ChatMessage['role'],
    content: string,
    metadata?: Record<string, unknown>
  ) => {
    const message: ChatMessage = {
      id: `msg-${++messageIdRef.current}`,
      role,
      content,
      timestamp: new Date(),
      metadata,
    }
    setMessages(prev => [...prev, message])
    return message
  }, [])

  const connect = useCallback(() => {
    // Close any existing connection first
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setState('connecting')
    setError(null)

    // For port-forwarded dev environments, connect to backend directly on port 8000
    // In production, use the same host as the page
    const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = isLocalDev
      ? `${protocol}//${window.location.hostname}:8000/ws/session`
      : `${protocol}//${window.location.host}/ws/session`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (mountedRef.current) {
        setState('connected')
      }
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      const data: WebSocketMessage = JSON.parse(event.data)

      switch (data.type) {
        case 'started':
          setSessionId(data.session_id || null)
          setState('running')
          addMessage('system', 'Session started')
          break

        case 'event':
          handleEvent(data.event_type, data.payload)
          break

        case 'awaiting_input':
          setState('awaiting_input')
          setAwaitingPrompt(data.prompt || 'Enter your message:')
          break

        case 'completed':
          setState('completed')
          setEvaluation(data.evaluation || null)
          addMessage('system', 'Session completed')
          break

        case 'error':
          setState('error')
          setError(data.message || 'Unknown error')
          addMessage('system', `Error: ${data.message}`)
          break

        case 'event_injected':
          // Game event was injected (chaos event)
          if (data.result) {
            setLastEvent(data.result)
            addMessage('system', `🎲 ${data.result.message}`, { event: data.event, result: data.result })
          }
          break
      }
    }

    ws.onerror = () => {
      if (mountedRef.current) {
        setState('error')
        setError('WebSocket connection error')
      }
    }

    ws.onclose = () => {
      if (mountedRef.current && wsRef.current === ws) {
        setState('disconnected')
      }
    }
  }, [addMessage])

  const handleEvent = useCallback((eventType?: string, payload?: Record<string, unknown>) => {
    if (!eventType || !payload) return

    switch (eventType) {
      case 'user':
      case 'user_message':
        addMessage('user', payload.content as string, payload)
        break

      case 'agent':
      case 'agent_message':
        addMessage('agent', payload.content as string, payload)
        break

      case 'tool_call':
        addMessage('tool', `Tool: ${payload.tool || payload.tool_name}\nArgs: ${JSON.stringify(payload.args || payload.arguments, null, 2)}`, payload)
        break

      case 'tool_result':
        addMessage('tool', `Result: ${JSON.stringify(payload.result, null, 2)}`, payload)
        // Extract game state from check_status results
        const result = payload.result as { success?: boolean; data?: GameState }
        if (result?.success && result?.data) {
          const data = result.data
          // Update game state if this looks like a status check
          if (data.cash !== undefined || data.inventory !== undefined) {
            setGameState(data)
          }
        }
        break

      case 'step_started':
      case 'step_completed':
      case 'branch':
        // Optional: show step/branch progress
        break
    }
  }, [addMessage])

  const startSession = useCallback((config: SessionConfig) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      setError('Not connected to server')
      return
    }

    // Reset state
    setMessages([])
    setEvaluation(null)
    setAwaitingPrompt(null)
    messageIdRef.current = 0

    wsRef.current.send(JSON.stringify({
      type: 'start',
      module_id: config.moduleId,
      agent_id: config.agentId,
      variables: config.variables || {},
    }))
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      setError('Not connected to server')
      return
    }

    if (state !== 'awaiting_input') {
      return
    }

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content,
    }))

    setState('running')
    setAwaitingPrompt(null)
  }, [state])

  const injectEvent = useCallback((eventType: string, toolName: string = 'stand', args?: Record<string, unknown>) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      setError('Not connected to server')
      return
    }

    wsRef.current.send(JSON.stringify({
      type: 'inject_event',
      tool: toolName,
      event: eventType,
      args: args || {},
    }))
  }, [])

  const clearLastEvent = useCallback(() => {
    setLastEvent(null)
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setState('disconnected')
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [])

  return {
    state,
    sessionId,
    messages,
    awaitingPrompt,
    evaluation,
    error,
    gameState,
    lastEvent,
    connect,
    disconnect,
    startSession,
    sendMessage,
    injectEvent,
    clearLastEvent,
  }
}
