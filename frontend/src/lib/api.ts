const API_BASE = '/api/v1'

export interface ModuleVariable {
  name: string
  type: 'slider' | 'select' | 'text' | 'number' | 'boolean'
  label?: string
  description?: string
  default?: string | number | boolean
  min?: number
  max?: number
  step?: number
  options?: Array<{ value: string; label: string }>
}

export interface ModuleTool {
  name: string
  type: string
  description?: string
  config?: Record<string, unknown>
}

export interface ModuleEnvironment {
  sandbox_type?: string
  tools?: ModuleTool[]
  initial_state?: Record<string, unknown>
}

export interface ModuleMetadata {
  category?: string
  tags?: string[]
}

// UI Configuration from YAML
export interface ContextFieldConfig {
  key: string           // Path to value in state (e.g., "inventory.cups_ready")
  label: string         // Display label
  format: 'text' | 'number' | 'currency' | 'progress'
  icon?: string         // Emoji or icon
  max?: number          // For progress bars
  warn_below?: number   // Show warning if value below this
  warn_above?: number   // Show warning if value above this
}

export interface EventConfig {
  id: string
  label: string
  icon?: string
  description?: string
}

export interface EventsConfig {
  tool: string          // Which tool handles trigger_event
  categories: Record<string, EventConfig[]>
}

export interface ModuleUI {
  context?: ContextFieldConfig[]
  events?: EventsConfig
}

export interface Module {
  id: string
  slug: string
  name: string
  description: string | null
  icon: string | null
  category: string | null
  yaml_content: string
  created_at: string
  updated_at: string
  // Parsed from YAML
  variables?: ModuleVariable[]
  environment?: ModuleEnvironment
  metadata?: ModuleMetadata
  ui?: ModuleUI
}

export interface Agent {
  id: string
  name: string
  provider: string
  model: string
  description: string | null
}

export interface Session {
  id: string
  module_id: string
  agent_id: string
  variables: Record<string, unknown>
  state: 'idle' | 'running' | 'awaiting_user' | 'awaiting_agent' | 'paused' | 'completed' | 'error'
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface SessionEvent {
  id: number
  session_id: string
  sequence: number
  event_type: string
  payload: Record<string, unknown>
  created_at: string
}

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Modules
  async getModules(): Promise<Module[]> {
    const response = await this.request<{ modules: Module[]; count: number }>('/modules')
    return response.modules
  }

  async getModule(slug: string): Promise<Module> {
    return this.request<Module>(`/modules/${slug}`)
  }

  async createModule(data: {
    slug: string
    name: string
    description?: string
    yaml_content: string
  }): Promise<Module> {
    return this.request<Module>('/modules', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateModule(
    slug: string,
    data: Partial<{
      name: string
      description: string
      yaml_content: string
    }>
  ): Promise<Module> {
    return this.request<Module>(`/modules/${slug}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteModule(slug: string): Promise<void> {
    await this.request(`/modules/${slug}`, { method: 'DELETE' })
  }

  // Agents
  async getAgents(): Promise<Agent[]> {
    const response = await this.request<{ agents: Agent[]; count: number }>('/agents')
    return response.agents
  }

  // Sessions
  async getSessions(limit = 50): Promise<Session[]> {
    return this.request<Session[]>(`/sessions?limit=${limit}`)
  }

  async getSession(id: string): Promise<Session> {
    return this.request<Session>(`/sessions/${id}`)
  }

  async getSessionEvents(sessionId: string): Promise<SessionEvent[]> {
    return this.request<SessionEvent[]>(`/sessions/${sessionId}/events`)
  }

  async exportSession(sessionId: string): Promise<SessionExport> {
    return this.request<SessionExport>(`/sessions/${sessionId}/export`)
  }

  async getShareableResult(sessionId: string): Promise<ShareableResult> {
    return this.request<ShareableResult>(`/sessions/${sessionId}/share`)
  }
}

export interface SessionExport {
  session_id: string
  module_id: string
  module_name: string | null
  agent_id: string
  variables: Record<string, unknown> | null
  state: string
  created_at: string
  completed_at: string | null
  duration_seconds: number | null
  events: Array<{
    sequence: number
    type: string
    payload: Record<string, unknown>
    timestamp: string | null
  }>
  evaluation: {
    score: number | null
    checks: Record<string, unknown> | null
  } | null
  summary: {
    total_events: number
    user_messages: number
    agent_messages: number
    tool_calls: number
    final_score: number | null
  }
}

export interface ShareableResult {
  title: string
  description: string
  score: number | null
  score_display: string
  share_url: string
  embed_code: string
}

export const api = new ApiClient()
