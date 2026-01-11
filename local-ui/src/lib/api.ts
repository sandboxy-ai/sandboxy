/**
 * API client for local Sandboxy server.
 */

const API_BASE = '/api/v1'

export interface LocalFileInfo {
  id: string
  name: string
  description: string
  type: string | null
  path: string
  relative_path: string
}

export interface LocalStatus {
  mode: string
  root_dir: string
  scenarios: LocalFileInfo[]
  tools: LocalFileInfo[]
  agents: LocalFileInfo[]
}

export interface VariableInfo {
  name: string
  label: string
  type: 'string' | 'number' | 'boolean' | 'select'
  default: unknown
  options: string[]
  required: boolean
}

export interface ScenarioDetail {
  id: string
  name: string
  description: string
  type: string | null
  path: string
  content: Record<string, unknown>
  variables: VariableInfo[]
}

export interface ModelInfo {
  id: string
  name: string
  price: string
}

export interface RunScenarioRequest {
  scenario_id: string
  model: string
  variables?: Record<string, unknown>
  max_turns?: number
  max_tokens?: number
  temperature?: number
}

export interface HistoryMessage {
  role: string
  content: string
}

export interface ToolCall {
  tool: string
  action: string
  args: Record<string, unknown>
  result?: unknown
  success: boolean
  error?: string | null
}

export interface GoalResult {
  id: string
  name: string
  achieved: boolean
  points: number
  reason: string
}

export interface EvaluationResult {
  goals: GoalResult[]
  judge: {
    score: number
    passed: boolean
    reasoning: string
    judge_type: string
  } | null
  total_score: number
  max_score: number
  percentage: number
}

export interface RunScenarioResponse {
  id: string
  scenario_id: string
  model: string
  response: string
  history: HistoryMessage[]
  tool_calls: ToolCall[]
  final_state: Record<string, unknown>
  evaluation: EvaluationResult | null
  latency_ms: number
  input_tokens: number
  output_tokens: number
  cost_usd: number | null
  error: string | null
}

export interface CompareModelsRequest {
  scenario_id: string
  models: string[]
  runs_per_model?: number
  variables?: Record<string, unknown>
  max_turns?: number
}

export interface ModelStats {
  model: string
  runs: number
  avg_score: number
  min_score: number
  max_score: number
  std_score: number
  avg_latency_ms: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost_usd: number | null
  avg_cost_usd: number | null
  avg_messages: number
  avg_tool_calls: number
  errors: number
  goal_rates: Record<string, number>
  avg_judge_score: number | null
}

export interface CompareModelsResponse {
  scenario_id: string
  scenario_name: string
  models: string[]
  runs_per_model: number
  stats: Record<string, ModelStats>
  ranking: string[]
  winner: string | null
  results?: RunScenarioResponse[]  // Individual run results
}

export interface RunResult {
  filename: string
  path: string
  scenario_id: string
  timestamp: string
  metadata: Record<string, unknown>
}

class ApiClient {
  private async fetch<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Status
  async getStatus(): Promise<LocalStatus> {
    return this.fetch<LocalStatus>('/local/status')
  }

  // Scenarios
  async listScenarios(): Promise<LocalFileInfo[]> {
    return this.fetch<LocalFileInfo[]>('/local/scenarios')
  }

  async getScenario(id: string): Promise<ScenarioDetail> {
    return this.fetch<ScenarioDetail>(`/local/scenarios/${encodeURIComponent(id)}`)
  }

  // Tools
  async listTools(): Promise<LocalFileInfo[]> {
    return this.fetch<LocalFileInfo[]>('/local/tools')
  }

  async getTool(id: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/local/tools/${encodeURIComponent(id)}`)
  }

  // Agents
  async listAgents(): Promise<LocalFileInfo[]> {
    return this.fetch<LocalFileInfo[]>('/local/agents')
  }

  async getAgent(id: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/local/agents/${encodeURIComponent(id)}`)
  }

  // Models
  async listModels(): Promise<ModelInfo[]> {
    return this.fetch<ModelInfo[]>('/local/models')
  }

  // Runs
  async listRuns(): Promise<RunResult[]> {
    return this.fetch<RunResult[]>('/local/runs')
  }

  async getRun(filename: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/local/runs/${encodeURIComponent(filename)}`)
  }

  // Execute scenarios
  async runScenario(request: RunScenarioRequest): Promise<RunScenarioResponse> {
    return this.fetch<RunScenarioResponse>('/local/run', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async compareModels(request: CompareModelsRequest): Promise<CompareModelsResponse> {
    return this.fetch<CompareModelsResponse>('/local/compare', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }
}

export const api = new ApiClient()
