/**
 * State management for the scenario builder.
 */

import { useState, useCallback, useMemo } from 'react'
import yaml from 'js-yaml'

export interface GoalSpec {
  id: string
  name: string
  description: string
  points: number
  detection: {
    type: string
    [key: string]: unknown
  }
}

export interface StepSpec {
  id: string
  action: 'inject_user' | 'await_agent' | 'await_user'
  params: Record<string, unknown>
}

export interface JudgeSpec {
  type: 'llm' | 'contains' | 'regex' | 'exact' | 'length'
  model?: string
  rubric?: string
  pattern?: string
  case_sensitive?: boolean
  min_length?: number
  max_length?: number
  pass_threshold?: number
}

export interface VariableSpec {
  name: string
  label: string
  type: 'string' | 'number' | 'boolean' | 'select'
  default: string | number | boolean
  options: string[]  // For select type
  required: boolean
}

export interface ScenarioBuilderState {
  // Metadata
  id: string
  name: string
  description: string
  category: string
  tags: string[]

  // Variables
  variables: VariableSpec[]

  // Interaction mode
  interactionMode: 'prompt' | 'steps'

  // Single-turn
  prompt: string
  style: string

  // Multi-turn
  systemPrompt: string
  steps: StepSpec[]

  // Tools
  toolsFrom: string[]
  inlineTools: Record<string, unknown>

  // State
  initialState: Record<string, unknown>

  // Evaluation
  goals: GoalSpec[]
  judge: JudgeSpec | null

  // Scoring
  maxScore: number | null
}

const initialState: ScenarioBuilderState = {
  id: '',
  name: '',
  description: '',
  category: '',
  tags: [],
  variables: [],
  interactionMode: 'prompt',
  prompt: '',
  style: '',
  systemPrompt: '',
  steps: [],
  toolsFrom: [],
  inlineTools: {},
  initialState: {},
  goals: [],
  judge: null,
  maxScore: null,
}

export interface UseScenarioBuilderResult {
  state: ScenarioBuilderState
  yamlPreview: string
  isValid: boolean
  validationErrors: string[]

  // Metadata
  setId: (id: string) => void
  setName: (name: string) => void
  setDescription: (description: string) => void
  setCategory: (category: string) => void
  setTags: (tags: string[]) => void

  // Variables
  addVariable: (variable: VariableSpec) => void
  updateVariable: (index: number, variable: VariableSpec) => void
  removeVariable: (index: number) => void

  // Interaction
  setInteractionMode: (mode: 'prompt' | 'steps') => void
  setPrompt: (prompt: string) => void
  setStyle: (style: string) => void
  setSystemPrompt: (systemPrompt: string) => void

  // Steps
  addStep: (step: StepSpec) => void
  updateStep: (index: number, step: StepSpec) => void
  removeStep: (index: number) => void
  reorderSteps: (fromIndex: number, toIndex: number) => void

  // Tools
  setToolsFrom: (tools: string[]) => void
  setInlineTools: (tools: Record<string, unknown>) => void

  // State
  setInitialState: (state: Record<string, unknown>) => void

  // Evaluation
  addGoal: (goal: GoalSpec) => void
  updateGoal: (index: number, goal: GoalSpec) => void
  removeGoal: (index: number) => void
  setJudge: (judge: JudgeSpec | null) => void
  setMaxScore: (score: number | null) => void

  // Actions
  reset: () => void
  loadFromYaml: (yamlContent: string) => void
}

export function useScenarioBuilder(): UseScenarioBuilderResult {
  const [state, setState] = useState<ScenarioBuilderState>(initialState)

  // Generate YAML preview
  const yamlPreview = useMemo(() => {
    const output: Record<string, unknown> = {}

    // Always include id
    if (state.id) output.id = state.id
    if (state.name) output.name = state.name
    if (state.description) output.description = state.description
    if (state.category) output.category = state.category
    if (state.tags.length > 0) output.tags = state.tags

    // Variables
    if (state.variables.length > 0) {
      output.variables = state.variables.map(v => {
        const varDef: Record<string, unknown> = {
          name: v.name,
          type: v.type,
        }
        if (v.label) varDef.label = v.label
        if (v.default !== '' && v.default !== undefined) varDef.default = v.default
        if (v.type === 'select' && v.options.length > 0) varDef.options = v.options
        if (!v.required) varDef.required = false
        return varDef
      })
    }

    // System prompt
    if (state.systemPrompt) output.system_prompt = state.systemPrompt

    // Interaction
    if (state.interactionMode === 'prompt') {
      if (state.prompt) output.prompt = state.prompt
      if (state.style) output.style = state.style
    } else {
      if (state.steps.length > 0) {
        output.steps = state.steps.map(s => ({
          id: s.id,
          action: s.action,
          params: s.params,
        }))
      }
    }

    // Tools
    if (state.toolsFrom.length > 0) output.tools_from = state.toolsFrom
    if (Object.keys(state.inlineTools).length > 0) output.tools = state.inlineTools

    // Initial state
    if (Object.keys(state.initialState).length > 0) output.initial_state = state.initialState

    // Evaluation
    const evaluation: Record<string, unknown> = {}
    if (state.goals.length > 0) {
      evaluation.goals = state.goals.map(g => ({
        id: g.id,
        name: g.name,
        description: g.description,
        points: g.points,
        detection: g.detection,
      }))
    }
    if (state.judge) {
      evaluation.judge = state.judge
    }
    if (state.maxScore !== null) {
      evaluation.max_score = state.maxScore
    }
    if (Object.keys(evaluation).length > 0) {
      output.evaluation = evaluation
    }

    return yaml.dump(output, { lineWidth: -1, noRefs: true })
  }, [state])

  // Validation
  const validationErrors = useMemo(() => {
    const errors: string[] = []

    if (!state.id) {
      errors.push('Scenario ID is required')
    } else if (!/^[a-z0-9-]+$/.test(state.id)) {
      errors.push('ID must be lowercase letters, numbers, and hyphens only')
    }

    if (state.interactionMode === 'prompt' && !state.prompt) {
      errors.push('Prompt is required for single-turn scenarios')
    }

    if (state.interactionMode === 'steps' && state.steps.length === 0) {
      errors.push('At least one step is required for multi-turn scenarios')
    }

    // Validate steps
    state.steps.forEach((step, idx) => {
      if (!step.id) {
        errors.push(`Step ${idx + 1}: ID is required`)
      }
      if (step.action === 'inject_user' && !step.params.content) {
        errors.push(`Step ${idx + 1}: Content is required for inject_user`)
      }
    })

    // Validate goals
    state.goals.forEach((goal, idx) => {
      if (!goal.id) {
        errors.push(`Goal ${idx + 1}: ID is required`)
      }
      if (!goal.detection.type) {
        errors.push(`Goal ${idx + 1}: Detection type is required`)
      }
    })

    return errors
  }, [state])

  const isValid = validationErrors.length === 0

  // Setters
  const setId = useCallback((id: string) => {
    setState(prev => ({ ...prev, id }))
  }, [])

  const setName = useCallback((name: string) => {
    setState(prev => ({ ...prev, name }))
  }, [])

  const setDescription = useCallback((description: string) => {
    setState(prev => ({ ...prev, description }))
  }, [])

  const setCategory = useCallback((category: string) => {
    setState(prev => ({ ...prev, category }))
  }, [])

  const setTags = useCallback((tags: string[]) => {
    setState(prev => ({ ...prev, tags }))
  }, [])

  // Variables
  const addVariable = useCallback((variable: VariableSpec) => {
    setState(prev => ({ ...prev, variables: [...prev.variables, variable] }))
  }, [])

  const updateVariable = useCallback((index: number, variable: VariableSpec) => {
    setState(prev => ({
      ...prev,
      variables: prev.variables.map((v, i) => (i === index ? variable : v)),
    }))
  }, [])

  const removeVariable = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      variables: prev.variables.filter((_, i) => i !== index),
    }))
  }, [])

  const setInteractionMode = useCallback((interactionMode: 'prompt' | 'steps') => {
    setState(prev => ({ ...prev, interactionMode }))
  }, [])

  const setPrompt = useCallback((prompt: string) => {
    setState(prev => ({ ...prev, prompt }))
  }, [])

  const setStyle = useCallback((style: string) => {
    setState(prev => ({ ...prev, style }))
  }, [])

  const setSystemPrompt = useCallback((systemPrompt: string) => {
    setState(prev => ({ ...prev, systemPrompt }))
  }, [])

  // Steps
  const addStep = useCallback((step: StepSpec) => {
    setState(prev => ({ ...prev, steps: [...prev.steps, step] }))
  }, [])

  const updateStep = useCallback((index: number, step: StepSpec) => {
    setState(prev => ({
      ...prev,
      steps: prev.steps.map((s, i) => (i === index ? step : s)),
    }))
  }, [])

  const removeStep = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      steps: prev.steps.filter((_, i) => i !== index),
    }))
  }, [])

  const reorderSteps = useCallback((fromIndex: number, toIndex: number) => {
    setState(prev => {
      const steps = [...prev.steps]
      const [removed] = steps.splice(fromIndex, 1)
      steps.splice(toIndex, 0, removed)
      return { ...prev, steps }
    })
  }, [])

  // Tools
  const setToolsFrom = useCallback((toolsFrom: string[]) => {
    setState(prev => ({ ...prev, toolsFrom }))
  }, [])

  const setInlineTools = useCallback((inlineTools: Record<string, unknown>) => {
    setState(prev => ({ ...prev, inlineTools }))
  }, [])

  // State
  const setInitialState = useCallback((initialState: Record<string, unknown>) => {
    setState(prev => ({ ...prev, initialState }))
  }, [])

  // Goals
  const addGoal = useCallback((goal: GoalSpec) => {
    setState(prev => ({ ...prev, goals: [...prev.goals, goal] }))
  }, [])

  const updateGoal = useCallback((index: number, goal: GoalSpec) => {
    setState(prev => ({
      ...prev,
      goals: prev.goals.map((g, i) => (i === index ? goal : g)),
    }))
  }, [])

  const removeGoal = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      goals: prev.goals.filter((_, i) => i !== index),
    }))
  }, [])

  const setJudge = useCallback((judge: JudgeSpec | null) => {
    setState(prev => ({ ...prev, judge }))
  }, [])

  const setMaxScore = useCallback((maxScore: number | null) => {
    setState(prev => ({ ...prev, maxScore }))
  }, [])

  // Actions
  const reset = useCallback(() => {
    setState(initialState)
  }, [])

  const loadFromYaml = useCallback((yamlContent: string) => {
    try {
      const data = yaml.load(yamlContent) as Record<string, unknown>

      setState({
        id: (data.id as string) || '',
        name: (data.name as string) || '',
        description: (data.description as string) || '',
        category: (data.category as string) || '',
        tags: (data.tags as string[]) || [],
        variables: ((data.variables as VariableSpec[]) || []).map((v) => ({
          name: v.name || '',
          label: v.label || '',
          type: v.type || 'string',
          default: v.default ?? '',
          options: v.options || [],
          required: v.required !== false,
        })),
        interactionMode: data.steps ? 'steps' : 'prompt',
        prompt: (data.prompt as string) || '',
        style: (data.style as string) || '',
        systemPrompt: (data.system_prompt as string) || '',
        steps: ((data.steps as StepSpec[]) || []).map((s, idx) => ({
          id: s.id || `step_${idx}`,
          action: s.action || 'await_agent',
          params: s.params || {},
        })),
        toolsFrom: (data.tools_from as string[]) || [],
        inlineTools: (data.tools as Record<string, unknown>) || {},
        initialState: (data.initial_state as Record<string, unknown>) || {},
        goals: (((data.evaluation as Record<string, unknown>)?.goals || data.goals) as GoalSpec[])?.map((g, idx) => ({
          id: g.id || `goal_${idx}`,
          name: g.name || '',
          description: g.description || '',
          points: g.points || 0,
          detection: g.detection || { type: '' },
        })) || [],
        judge: ((data.evaluation as Record<string, unknown>)?.judge as JudgeSpec) || null,
        maxScore: ((data.evaluation as Record<string, unknown>)?.max_score as number) || null,
      })
    } catch (e) {
      console.error('Failed to parse YAML:', e)
    }
  }, [])

  return {
    state,
    yamlPreview,
    isValid,
    validationErrors,
    setId,
    setName,
    setDescription,
    setCategory,
    setTags,
    addVariable,
    updateVariable,
    removeVariable,
    setInteractionMode,
    setPrompt,
    setStyle,
    setSystemPrompt,
    addStep,
    updateStep,
    removeStep,
    reorderSteps,
    setToolsFrom,
    setInlineTools,
    setInitialState,
    addGoal,
    updateGoal,
    removeGoal,
    setJudge,
    setMaxScore,
    reset,
    loadFromYaml,
  }
}
