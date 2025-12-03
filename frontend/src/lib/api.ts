const API_BASE = '/api/v1'

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
}

export const api = new ApiClient()
