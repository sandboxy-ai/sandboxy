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

interface WebSocketMessage {
  type: string
  session_id?: string
  event_type?: string
  payload?: Record<string, unknown>
  prompt?: string
  evaluation?: Record<string, unknown>
  message?: string
}

export function useSession() {
  const [state, setState] = useState<SessionState>('disconnected')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [awaitingPrompt, setAwaitingPrompt] = useState<string | null>(null)
  const [evaluation, setEvaluation] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const messageIdRef = useRef(0)

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
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setState('connecting')
    setError(null)

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/session`)
    wsRef.current = ws

    ws.onopen = () => {
      setState('connected')
    }

    ws.onmessage = (event) => {
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
      }
    }

    ws.onerror = () => {
      setState('error')
      setError('WebSocket connection error')
    }

    ws.onclose = () => {
      if (state !== 'completed' && state !== 'error') {
        setState('disconnected')
      }
      wsRef.current = null
    }
  }, [addMessage, state])

  const handleEvent = useCallback((eventType?: string, payload?: Record<string, unknown>) => {
    if (!eventType || !payload) return

    switch (eventType) {
      case 'user_message':
        addMessage('user', payload.content as string, payload)
        break

      case 'agent_message':
        addMessage('agent', payload.content as string, payload)
        break

      case 'tool_call':
        addMessage('tool', `Tool: ${payload.tool_name}\nArgs: ${JSON.stringify(payload.arguments, null, 2)}`, payload)
        break

      case 'tool_result':
        addMessage('tool', `Result: ${JSON.stringify(payload.result, null, 2)}`, payload)
        break

      case 'step_started':
        // Optional: show step progress
        break

      case 'step_completed':
        // Optional: show step completion
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

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setState('disconnected')
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  return {
    state,
    sessionId,
    messages,
    awaitingPrompt,
    evaluation,
    error,
    connect,
    disconnect,
    startSession,
    sendMessage,
  }
}
