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

// =============================================================================
// Tool Types
// =============================================================================

export interface ToolConfigField {
  type: 'number' | 'string' | 'boolean' | 'select' | 'object' | 'array'
  label: string
  description?: string
  default?: unknown
  min?: number
  max?: number
  step?: number
  options?: string[]
  items?: {
    type: string
    properties?: Record<string, ToolConfigField>
  }
}

export interface ToolAction {
  name: string
  description: string
  parameters: {
    type: string
    properties?: Record<string, {
      type: string
      description?: string
    }>
    required?: string[]
  }
}

export interface ToolInfo {
  id: string
  name: string
  description: string | null
  config_schema: Record<string, ToolConfigField>
  actions: ToolAction[]
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

// =============================================================================
// Arena Types
// =============================================================================

export interface ArenaPrompt {
  id: string
  slug: string
  title: string
  text: string
  category: string
  system_prompt: string | null
  judge_config: Record<string, unknown>
  judge_template_id: string | null
  variables: Array<{
    name: string
    description?: string
    default?: unknown
    type?: string
    options?: string[]
  }> | null
  tags: string[] | null
  is_featured: boolean
  run_count?: number
}

export interface JudgeTemplate {
  id: string
  slug: string
  name: string
  description: string | null
  judge_type: string
  model: string | null
  rubric: string | null
  pattern: string | null
  case_sensitive: boolean
  min_length: number | null
  max_length: number | null
  voters: string[] | null
  pass_threshold: number
  is_builtin: boolean
}

export interface JudgeType {
  id: string
  name: string
  description: string
}

export interface ArenaModel {
  id: string
  name: string
  provider: string
  context_length: number
  input_cost_per_million: number | null
  output_cost_per_million: number | null
  supports_vision: boolean
  supports_streaming: boolean
}

export interface ArenaModelResult {
  model_id: string
  response: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
  cost_usd: number | null
  error: string | null
}

export interface ArenaJudgment {
  model_id: string
  score: number
  passed: boolean
  reasoning: string
  judge_type: string
}

export interface ArenaRunResponse {
  id: string
  prompt_text: string
  models: string[]
  results: Record<string, ArenaModelResult>
  judgments: Record<string, ArenaJudgment>
  winner: string | null
  ranking: Array<[string, number]>
  total_latency_ms: number
  total_cost_usd: number | null
}

export interface ArenaRunDetail {
  id: string
  prompt_id: string | null
  prompt_text: string
  system_prompt: string | null
  models: string[]
  variables: Record<string, unknown> | null
  total_latency_ms: number | null
  total_cost_usd: number | null
  created_at: string
  results: Array<{
    model_id: string
    response: string
    latency_ms: number
    input_tokens: number
    output_tokens: number
    cost_usd: number | null
    error: string | null
    score: number | null
    passed: boolean | null
    judgment_reasoning: string | null
    judge_type: string | null
  }>
  video: {
    status: string
    cdn_url: string | null
    thumbnail_url: string | null
  } | null
}

export interface ArenaCategory {
  id: string
  name: string
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

  // Tools
  async getTools(): Promise<ToolInfo[]> {
    const response = await this.request<{ tools: ToolInfo[]; count: number }>('/tools')
    return response.tools
  }

  async getTool(toolId: string): Promise<ToolInfo> {
    return this.request<ToolInfo>(`/tools/${toolId}`)
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

  // =============================================================================
  // Arena API
  // =============================================================================

  async getArenaPrompts(category?: string, featured?: boolean): Promise<ArenaPrompt[]> {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (featured !== undefined) params.set('featured', String(featured))
    const query = params.toString()
    return this.request<ArenaPrompt[]>(`/arena/prompts${query ? `?${query}` : ''}`)
  }

  async getArenaPrompt(promptId: string): Promise<ArenaPrompt> {
    return this.request<ArenaPrompt>(`/arena/prompts/${promptId}`)
  }

  async createArenaPrompt(data: {
    slug: string
    title: string
    text: string
    category?: string
    system_prompt?: string
    judge_type?: string
    judge_config?: Record<string, unknown>
    variables?: Array<Record<string, unknown>>
    tags?: string[]
    viral_potential?: string
  }): Promise<ArenaPrompt> {
    return this.request<ArenaPrompt>('/arena/prompts', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getArenaModels(): Promise<{ models: ArenaModel[]; providers: string[] }> {
    return this.request<{ models: ArenaModel[]; providers: string[] }>('/arena/models')
  }

  async getArenaCategories(): Promise<ArenaCategory[]> {
    return this.request<ArenaCategory[]>('/arena/categories')
  }

  async getArenaJudges(): Promise<JudgeTemplate[]> {
    return this.request<JudgeTemplate[]>('/arena/judges')
  }

  async getArenaJudge(judgeId: string): Promise<JudgeTemplate> {
    return this.request<JudgeTemplate>(`/arena/judges/${judgeId}`)
  }

  async getArenaJudgeTypes(): Promise<JudgeType[]> {
    return this.request<JudgeType[]>('/arena/judge-types')
  }

  async runArena(data: {
    prompt_id?: string
    prompt_text?: string
    system_prompt?: string
    models: string[]
    variables?: Record<string, unknown>
    temperature?: number
    max_tokens?: number
    judge_template_id?: string
    judge_config?: Record<string, unknown>
  }): Promise<ArenaRunResponse> {
    return this.request<ArenaRunResponse>('/arena/run', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getArenaRun(runId: string): Promise<ArenaRunDetail> {
    return this.request<ArenaRunDetail>(`/arena/run/${runId}`)
  }

  // =============================================================================
  // Auto-Sim API
  // =============================================================================

  async getAutoSimScenarios(): Promise<AutoSimScenario[]> {
    return this.request<AutoSimScenario[]>('/autosim/scenarios')
  }

  async getAutoSimScenario(scenarioId: string): Promise<AutoSimScenarioDetail> {
    return this.request<AutoSimScenarioDetail>(`/autosim/scenarios/${scenarioId}`)
  }

  async startAutoSimRun(data: {
    scenario: string
    models: string[]
    turns?: number
    seed?: number
    counterparty_type?: string
    counterparty_personality?: string
    events_mode?: string
    events_probability?: number
  }): Promise<AutoSimRunResponse> {
    return this.request<AutoSimRunResponse>('/autosim/run', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getAutoSimRun(runId: string): Promise<AutoSimRunDetail> {
    return this.request<AutoSimRunDetail>(`/autosim/run/${runId}`)
  }

  async getAutoSimRunResults(runId: string): Promise<AutoSimResults> {
    return this.request<AutoSimResults>(`/autosim/run/${runId}/results`)
  }

  async getAutoSimRuns(limit = 20, offset = 0): Promise<{ runs: AutoSimRunSummary[]; total: number }> {
    return this.request<{ runs: AutoSimRunSummary[]; total: number }>(`/autosim/runs?limit=${limit}&offset=${offset}`)
  }

  // =============================================================================
  // Challenge API
  // =============================================================================

  async getChallenges(category?: string, difficulty?: string): Promise<ChallengeSummary[]> {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (difficulty) params.set('difficulty', difficulty)
    const query = params.toString()
    const response = await this.request<{ challenges: ChallengeSummary[]; count: number }>(
      `/challenges${query ? `?${query}` : ''}`
    )
    return response.challenges
  }

  async getChallenge(challengeId: string): Promise<ChallengeDetail> {
    return this.request<ChallengeDetail>(`/challenges/${challengeId}`)
  }

  async startChallenge(challengeId: string): Promise<ChallengeStartResponse> {
    return this.request<ChallengeStartResponse>(`/challenges/${challengeId}/start`, {
      method: 'POST',
    })
  }

  async completeChallenge(
    challengeId: string,
    sessionId: string,
    playerName?: string
  ): Promise<ChallengeCompleteResponse> {
    return this.request<ChallengeCompleteResponse>(`/challenges/${challengeId}/complete`, {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        player_name: playerName,
      }),
    })
  }

  // =========================================================================
  // Features
  // =========================================================================

  /**
   * Get enabled features from the backend.
   * Cloud extensions register their features here.
   */
  async getFeatures(): Promise<{ features: string[] }> {
    return this.request<{ features: string[] }>('/features')
  }

  // =============================================================================
  // Blitz API
  // =============================================================================

  async createBlitz(data: CreateBlitzRequest): Promise<CreateBlitzResponse> {
    return this.request<CreateBlitzResponse>('/blitz', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getBlitz(blitzId: string): Promise<BlitzDetail> {
    return this.request<BlitzDetail>(`/blitz/${blitzId}`)
  }

  async getBlitzes(limit = 20, offset = 0): Promise<BlitzDetail[]> {
    return this.request<BlitzDetail[]>(`/blitz?limit=${limit}&offset=${offset}`)
  }

  async getBlitzTemplateCategories(): Promise<BlitzTemplateCategory[]> {
    return this.request<BlitzTemplateCategory[]>('/blitz/templates/categories')
  }

  async getBlitzTemplates(): Promise<Array<BlitzTemplate & { category: string; category_name: string; category_icon: string }>> {
    return this.request<Array<BlitzTemplate & { category: string; category_name: string; category_icon: string }>>('/blitz/templates/all')
  }

  async getBlitzStyles(): Promise<Record<string, string>> {
    return this.request<Record<string, string>>('/blitz/styles')
  }
}

// =============================================================================
// Auto-Sim Types
// =============================================================================

export interface AutoSimScenario {
  id: string
  name: string
  description: string
}

export interface AutoSimPersonality {
  id: string
  name: string
  style: string
  patience: number
}

export interface AutoSimEvent {
  id: string
  message: string
  probability: number
  effects: string[]
}

export interface AutoSimScenarioDetail {
  id: string
  name: string
  description: string
  defaults: {
    turns?: number
    counterparty?: {
      type?: string
      personality?: string
    }
    events?: {
      mode?: string
      probability?: number
    }
  }
  personalities: AutoSimPersonality[]
  events: AutoSimEvent[]
}

export interface AutoSimRunResponse {
  run_id: string
  status: string
  stream_url: string
}

export interface AutoSimCheckResult {
  name: string
  check_type: string
  passed: boolean
  points: number
  max_points: number
  reason: string
  details?: Record<string, unknown>
}

export interface AutoSimScore {
  total_score: number
  max_score: number
  percentage: number
  checks: AutoSimCheckResult[]
  summary: string
}

export interface AutoSimModelResult {
  model_id: string
  transcript: Array<{ role: string; content: string }>
  turns: Array<{
    turn: number
    counterparty_message: string | null
    events: Array<Record<string, unknown>>
    agent_response: string | null
    tool_calls: Array<Record<string, unknown>>
  }>
  tool_calls: Array<Record<string, unknown>>
  final_state: Record<string, unknown>
  score: AutoSimScore | null
  latency_ms: number
  total_tokens: number
  cost_usd: number | null
  error: string | null
}

export interface AutoSimRunDetail {
  run_id: string
  status: string
  config?: {
    scenario: string
    models: string[]
    turns: number
    seed: number | null
  }
  results?: Record<string, AutoSimModelResult>
  winner?: string | null
  comparison?: {
    rankings: Array<{
      model_id: string
      total_score: number
      max_score: number
      percentage: number
      latency_ms: number
      tokens: number
      cost_usd: number | null
    }>
    key_differences: string[]
  }
}

export interface AutoSimResults {
  run_id: string
  scenario: string
  results: AutoSimModelResult[]
  winner: string | null
  comparison: {
    rankings: Array<{
      model_id: string
      total_score: number
      max_score: number
      percentage: number
      latency_ms: number
      tokens: number
      cost_usd: number | null
    }>
    key_differences: string[]
  }
}

export interface AutoSimRunSummary {
  id: string
  scenario: string
  models: string[]
  winner: string | null
  started_at: string
  completed_at: string | null
}

// =============================================================================
// Challenge Types
// =============================================================================

export interface ChallengeGoal {
  id: string
  name: string
  description: string
  points: number
  achieved?: boolean
  points_earned?: number
}

export interface ChallengeSummary {
  id: string
  name: string
  description: string
  category: string
  difficulty: string
  max_turns: number
  tags: string[]
}

export interface ChallengeDetail {
  id: string
  name: string
  description: string
  category: string
  difficulty: string
  max_turns: number
  time_limit_seconds: number | null
  tags: string[]
  goals: ChallengeGoal[]
  scoring_info: {
    turn_bonus: Record<string, unknown>
    max_turns: number
  }
}

export interface ChallengeStartResponse {
  session_id: string
  challenge_id: string
  challenge_name: string
  max_turns: number
  goals: ChallengeGoal[]
  message: string
}

export interface GoalResult {
  id: string
  name: string
  description: string
  achieved: boolean
  points_earned: number
}

export interface ChallengeCompleteResponse {
  challenge_id: string
  challenge_name: string
  session_id: string
  score: number
  max_score: number
  goals_completed: number
  goals_total: number
  goals: GoalResult[]
  turn_bonus: number
  turns_used: number
  max_turns: number
  breakdown: Record<string, number>
  player_name: string | null
}

// =============================================================================
// Blitz Types
// =============================================================================

export interface BlitzResponse {
  content: string
  latency_ms: number
  tokens: number
}

export interface CreateBlitzRequest {
  prompt: string
  models: string[]
  style?: string
  template_id?: string
}

export interface CreateBlitzResponse {
  id: string
  prompt: string
  style: string
  models: string[]
  responses: Record<string, BlitzResponse>
}

export interface BlitzDetail {
  id: string
  prompt: string
  prompt_template_id: string | null
  style: string
  models: string[]
  responses: Record<string, BlitzResponse & { error?: string | null }>
  view_count: number
  video_url: string | null
  thumbnail_url: string | null
  created_at: string
}

export interface BlitzTemplateVariable {
  name: string
  type: 'text' | 'textarea' | 'select'
  placeholder?: string
  options?: string[]
}

export interface BlitzTemplate {
  id: string
  text: string
  variables: BlitzTemplateVariable[]
}

export interface BlitzTemplateCategory {
  id: string
  name: string
  icon: string
  templates: BlitzTemplate[]
}

export const api = new ApiClient()
