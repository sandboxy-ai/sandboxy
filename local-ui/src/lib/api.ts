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
  results?: RunScenarioResponse[]
}

export interface RunResult {
  filename: string
  path: string
  scenario_id: string
  timestamp: string
  metadata: Record<string, unknown>
}

export interface DatasetInfo {
  id: string
  name: string
  description: string
  case_count: number
  path: string
  relative_path: string
}

export interface DatasetCase {
  id: string
  expected: string[]
  variables: Record<string, unknown>
  tool_responses: Record<string, unknown>
  tags: string[]
}

export interface DatasetDetail {
  id: string
  name: string
  description: string
  scenario_id: string | null
  cases: DatasetCase[]
  generator: Record<string, unknown> | null
  path: string
}

export interface ScenarioGoalInfo {
  id: string
  name: string
  description: string
  outcome: boolean
}

export interface ScenarioToolAction {
  name: string
  description: string
}

export interface ScenarioToolInfo {
  name: string
  description: string
  actions: ScenarioToolAction[]
}

export interface RunDatasetRequest {
  scenario_id: string
  dataset_id: string
  model: string
  max_turns?: number
  max_tokens?: number
  temperature?: number
  parallel?: number
}

export interface CaseResultInfo {
  case_id: string
  expected: string[]
  actual_outcome: string | null
  passed: boolean
  goal_score: number
  max_score: number
  percentage: number
  failure_reason: string | null
  latency_ms: number
}

export interface RunDatasetResponse {
  scenario_id: string
  model: string
  dataset_id: string
  total_cases: number
  passed_cases: number
  failed_cases: number
  pass_rate: number
  avg_score: number
  avg_percentage: number
  by_expected: Record<string, { passed: number; failed: number }>
  total_time_ms: number
  case_results: CaseResultInfo[]
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

  async getStatus(): Promise<LocalStatus> {
    return this.fetch<LocalStatus>('/local/status')
  }

  async listScenarios(): Promise<LocalFileInfo[]> {
    return this.fetch<LocalFileInfo[]>('/local/scenarios')
  }

  async getScenario(id: string): Promise<ScenarioDetail> {
    return this.fetch<ScenarioDetail>(`/local/scenarios/${encodeURIComponent(id)}`)
  }

  async getScenarioGoals(id: string): Promise<ScenarioGoalInfo[]> {
    return this.fetch<ScenarioGoalInfo[]>(`/local/scenarios/${encodeURIComponent(id)}/goals`)
  }

  async getScenarioTools(id: string): Promise<ScenarioToolInfo[]> {
    return this.fetch<ScenarioToolInfo[]>(`/local/scenarios/${encodeURIComponent(id)}/tools`)
  }

  async listTools(): Promise<LocalFileInfo[]> {
    return this.fetch<LocalFileInfo[]>('/local/tools')
  }

  async getTool(id: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/local/tools/${encodeURIComponent(id)}`)
  }

  async listAgents(): Promise<LocalFileInfo[]> {
    return this.fetch<LocalFileInfo[]>('/local/agents')
  }

  async getAgent(id: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/local/agents/${encodeURIComponent(id)}`)
  }

  async listModels(): Promise<ModelInfo[]> {
    return this.fetch<ModelInfo[]>('/local/models')
  }

  async listRuns(): Promise<RunResult[]> {
    return this.fetch<RunResult[]>('/local/runs')
  }

  async getRun(filename: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/local/runs/${encodeURIComponent(filename)}`)
  }

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

  async listDatasets(): Promise<DatasetInfo[]> {
    return this.fetch<DatasetInfo[]>('/local/datasets')
  }

  async getDataset(id: string): Promise<DatasetDetail> {
    return this.fetch<DatasetDetail>(`/local/datasets/${encodeURIComponent(id)}`)
  }

  async saveDataset(id: string, content: string): Promise<{ id: string; path: string; message: string }> {
    return this.fetch<{ id: string; path: string; message: string }>('/local/datasets', {
      method: 'POST',
      body: JSON.stringify({ id, content }),
    })
  }

  async updateDataset(id: string, content: string): Promise<{ id: string; path: string; message: string }> {
    return this.fetch<{ id: string; path: string; message: string }>(`/local/datasets/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify({ id, content }),
    })
  }

  async deleteDataset(id: string): Promise<{ message: string }> {
    return this.fetch<{ message: string }>(`/local/datasets/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    })
  }

  async runDataset(request: RunDatasetRequest): Promise<RunDatasetResponse> {
    return this.fetch<RunDatasetResponse>('/local/run-dataset', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }
}

export const api = new ApiClient()
