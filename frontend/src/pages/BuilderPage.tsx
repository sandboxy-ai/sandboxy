import { useCallback, useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  Plus,
  Save,
  Code,
  Trash2,
  CheckCircle,
  GripVertical,
  Upload,
  Download,
  MessageSquare,
  Clock,
  Bot,
  GitBranch,
  X,
  FileCode,
  Copy,
  Check,
  Settings,
  Wrench,
  Sliders,
  ListChecks,
  Layers,
  ChevronDown,
  ChevronRight,
  Loader2,
} from 'lucide-react'
import yaml from 'js-yaml'
import { api, Agent, ToolInfo, ArenaModel } from '../lib/api'
import { ToolConfigForm } from '../components/ToolConfigForm'

// ============================================================================
// Types
// ============================================================================

type StepType = 'inject_user' | 'await_user' | 'await_agent' | 'branch'
type CheckKind = 'contains' | 'regex' | 'count' | 'tool_called' | 'env_state' | 'equals'
type CheckTarget = 'agent_messages' | 'user_messages' | 'all_messages' | 'tool_calls'
type TabId = 'basics' | 'agent' | 'tools' | 'variables' | 'steps' | 'evaluation'

interface Step {
  id: string
  type: StepType
  params: Record<string, unknown>
}

interface EvaluationCheck {
  id: string
  name: string
  kind: CheckKind
  target?: CheckTarget
  value?: string
  expected?: boolean
  pattern?: string
  min?: number
  max?: number
  tool?: string
  action?: string
  key?: string
}

interface AgentConfig {
  mode: 'select' | 'custom'
  agent_id?: string
  custom?: {
    provider: string
    model: string
    temperature: number
    system_prompt: string
    max_tokens?: number
  }
}

interface ToolSelection {
  tool_id: string
  name: string
  config: Record<string, unknown>
}

interface VariableDefinition {
  id: string
  name: string
  type: 'slider' | 'select' | 'text' | 'number' | 'boolean'
  label: string
  description?: string
  default?: unknown
  min?: number
  max?: number
  step?: number
  options?: Array<{ value: string; label: string }>
}

// ============================================================================
// Constants
// ============================================================================

const TABS: { id: TabId; label: string; icon: typeof Settings }[] = [
  { id: 'basics', label: 'Basics', icon: Settings },
  { id: 'agent', label: 'Agent', icon: Bot },
  { id: 'tools', label: 'Tools', icon: Wrench },
  { id: 'variables', label: 'Variables', icon: Sliders },
  { id: 'steps', label: 'Steps', icon: Layers },
  { id: 'evaluation', label: 'Eval', icon: ListChecks },
]

const STEP_TYPES: Record<StepType, { label: string; icon: typeof MessageSquare; color: string; description: string }> = {
  inject_user: {
    label: 'Inject User Message',
    icon: MessageSquare,
    color: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    description: 'Send a scripted user message',
  },
  await_user: {
    label: 'Await User Input',
    icon: Clock,
    color: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
    description: 'Wait for real user input',
  },
  await_agent: {
    label: 'Await Agent Response',
    icon: Bot,
    color: 'text-green-400 bg-green-500/10 border-green-500/30',
    description: 'Wait for agent to respond',
  },
  branch: {
    label: 'Branch',
    icon: GitBranch,
    color: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
    description: 'Conditional branching',
  },
}

const CATEGORIES = ['game', 'benchmark', 'security', 'custom']

// ============================================================================
// Main Component
// ============================================================================

export default function BuilderPage() {
  const { moduleSlug } = useParams<{ moduleSlug?: string }>()
  const navigate = useNavigate()
  const isEditMode = Boolean(moduleSlug)

  // Core state
  const [activeTab, setActiveTab] = useState<TabId>('basics')
  const [loading, setLoading] = useState(isEditMode)
  const [saving, setSaving] = useState(false)

  // Module metadata
  const [moduleName, setModuleName] = useState('New Module')
  const [moduleDescription, setModuleDescription] = useState('')
  const [moduleIcon, setModuleIcon] = useState('')
  const [moduleCategory, setModuleCategory] = useState('custom')

  // Agent configuration
  const [agentConfig, setAgentConfig] = useState<AgentConfig>({
    mode: 'select',
    agent_id: undefined,
    custom: {
      provider: 'openai',
      model: 'gpt-4o',
      temperature: 0.7,
      system_prompt: '',
    },
  })

  // Tools configuration
  const [selectedTools, setSelectedTools] = useState<ToolSelection[]>([])
  const [availableTools, setAvailableTools] = useState<ToolInfo[]>([])
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([])
  const [availableModels, setAvailableModels] = useState<ArenaModel[]>([])
  const [, setAvailableProviders] = useState<string[]>([])

  // Variables
  const [variables, setVariables] = useState<VariableDefinition[]>([])

  // Steps (existing)
  const [steps, setSteps] = useState<Step[]>([])
  const [selectedStep, setSelectedStep] = useState<Step | null>(null)

  // Evaluation checks (existing)
  const [evaluationChecks, setEvaluationChecks] = useState<EvaluationCheck[]>([])
  const [selectedCheck, setSelectedCheck] = useState<EvaluationCheck | null>(null)

  // UI state
  const [showYaml, setShowYaml] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [importYaml, setImportYaml] = useState('')
  const [importError, setImportError] = useState('')
  const [copied, setCopied] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [draggedType, setDraggedType] = useState<StepType | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  // ============================================================================
  // Data Loading
  // ============================================================================

  useEffect(() => {
    // Load available tools, agents, and models
    Promise.all([api.getTools(), api.getAgents(), api.getArenaModels()])
      .then(([tools, agents, modelsData]) => {
        setAvailableTools(tools)
        setAvailableAgents(agents)
        setAvailableModels(modelsData.models)
        setAvailableProviders(modelsData.providers)
        // Set default agent if available
        if (agents.length > 0 && !agentConfig.agent_id) {
          setAgentConfig((prev) => ({ ...prev, agent_id: agents[0].id }))
        }
        // Set default model if available
        if (modelsData.models.length > 0 && !agentConfig.custom?.model) {
          const firstModel = modelsData.models[0]
          setAgentConfig((prev) => ({
            ...prev,
            custom: {
              ...prev.custom!,
              provider: firstModel.provider,
              model: firstModel.id,
            },
          }))
        }
      })
      .catch(console.error)
  }, [])

  useEffect(() => {
    // Load existing module if in edit mode
    if (moduleSlug) {
      setLoading(true)
      api
        .getModule(moduleSlug)
        .then((module) => {
          setModuleName(module.name)
          setModuleDescription(module.description || '')

          // Parse YAML to populate state
          try {
            const parsed = yaml.load(module.yaml_content) as Record<string, unknown>
            if (parsed) {
              populateFromYaml(parsed)
            }
          } catch (e) {
            console.error('Failed to parse YAML:', e)
          }
        })
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [moduleSlug])

  const populateFromYaml = (parsed: Record<string, unknown>) => {
    // Icon and category
    if (parsed.icon) setModuleIcon(String(parsed.icon))
    if (parsed.category) setModuleCategory(String(parsed.category))

    // Agent configuration
    const agentData = parsed.agent as Record<string, unknown> | undefined
    if (agentData) {
      if (agentData.id) {
        setAgentConfig({ mode: 'select', agent_id: String(agentData.id) })
      } else if (agentData.provider || agentData.model || agentData.system_prompt) {
        setAgentConfig({
          mode: 'custom',
          custom: {
            provider: String(agentData.provider || 'openai'),
            model: String(agentData.model || 'gpt-4o'),
            temperature: Number(agentData.temperature || 0.7),
            system_prompt: String(agentData.system_prompt || ''),
            max_tokens: agentData.max_tokens ? Number(agentData.max_tokens) : undefined,
          },
        })
      }
    }

    // Environment/Tools
    const env = parsed.environment as Record<string, unknown> | undefined
    if (env?.tools && Array.isArray(env.tools)) {
      const tools = env.tools as Array<Record<string, unknown>>
      setSelectedTools(
        tools.map((t, i) => ({
          tool_id: String(t.type || t.name || `tool-${i}`),
          name: String(t.name || t.type || `tool-${i}`),
          config: (t.config as Record<string, unknown>) || {},
        }))
      )
    }

    // Variables
    if (parsed.variables && Array.isArray(parsed.variables)) {
      const vars = parsed.variables as Array<Record<string, unknown>>
      setVariables(
        vars.map((v, i) => ({
          id: `var-${Date.now()}-${i}`,
          name: String(v.name || ''),
          type: (v.type as VariableDefinition['type']) || 'text',
          label: String(v.label || v.name || ''),
          description: v.description ? String(v.description) : undefined,
          default: v.default,
          min: v.min ? Number(v.min) : undefined,
          max: v.max ? Number(v.max) : undefined,
          step: v.step ? Number(v.step) : undefined,
          options: v.options as VariableDefinition['options'],
        }))
      )
    }

    // Steps
    if (parsed.steps && Array.isArray(parsed.steps)) {
      const stepsData = parsed.steps as Array<Record<string, unknown>>
      setSteps(
        stepsData.map((s, i) => ({
          id: `step-${Date.now()}-${i}`,
          type: String(s.action) as StepType,
          params: (s.params as Record<string, unknown>) || {},
        }))
      )
    }

    // Evaluation
    if (parsed.evaluation && Array.isArray(parsed.evaluation)) {
      const checks = parsed.evaluation as Array<Record<string, unknown>>
      setEvaluationChecks(
        checks.map((c, i) => ({
          id: `check-${Date.now()}-${i}`,
          name: String(c.name || `check_${i}`),
          kind: String(c.kind) as CheckKind,
          target: c.target as CheckTarget | undefined,
          value: c.value as string | undefined,
          expected: c.expected as boolean | undefined,
          pattern: c.pattern as string | undefined,
          min: c.min as number | undefined,
          max: c.max as number | undefined,
          tool: c.tool as string | undefined,
          action: c.action as string | undefined,
          key: c.key as string | undefined,
        }))
      )
    }
  }

  // ============================================================================
  // Step Management
  // ============================================================================

  const addStep = useCallback((type: StepType) => {
    const newStep: Step = {
      id: `step-${Date.now()}`,
      type,
      params: getDefaultParams(type),
    }
    setSteps((prev) => [...prev, newStep])
    setSelectedStep(newStep)
  }, [])

  const deleteStep = useCallback(
    (id: string) => {
      setSteps((prev) => prev.filter((s) => s.id !== id))
      if (selectedStep?.id === id) {
        setSelectedStep(null)
      }
    },
    [selectedStep]
  )

  const updateStep = useCallback(
    (id: string, params: Record<string, unknown>) => {
      setSteps((prev) => prev.map((s) => (s.id === id ? { ...s, params } : s)))
      if (selectedStep?.id === id) {
        setSelectedStep((prev) => (prev ? { ...prev, params } : null))
      }
    },
    [selectedStep]
  )

  const handleDragStart = (event: DragStartEvent) => {
    const id = event.active.id as string
    setActiveId(id)
    if (id.startsWith('toolbox-')) {
      setDraggedType(id.replace('toolbox-', '') as StepType)
    }
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)
    setDraggedType(null)

    if (!over) return

    if (String(active.id).startsWith('toolbox-')) {
      const type = String(active.id).replace('toolbox-', '') as StepType
      addStep(type)
      return
    }

    if (active.id !== over.id) {
      setSteps((prev) => {
        const oldIndex = prev.findIndex((s) => s.id === active.id)
        const newIndex = prev.findIndex((s) => s.id === over.id)
        return arrayMove(prev, oldIndex, newIndex)
      })
    }
  }

  // ============================================================================
  // Check Management
  // ============================================================================

  const addCheck = useCallback((kind: CheckKind) => {
    const newCheck: EvaluationCheck = {
      id: `check-${Date.now()}`,
      name: `${kind}_check`,
      kind,
      expected: true,
      target: kind === 'contains' || kind === 'regex' || kind === 'count' ? 'agent_messages' : undefined,
    }
    setEvaluationChecks((prev) => [...prev, newCheck])
    setSelectedCheck(newCheck)
  }, [])

  const updateCheck = useCallback(
    (id: string, updates: Partial<EvaluationCheck>) => {
      setEvaluationChecks((prev) => prev.map((c) => (c.id === id ? { ...c, ...updates } : c)))
      if (selectedCheck?.id === id) {
        setSelectedCheck((prev) => (prev ? { ...prev, ...updates } : null))
      }
    },
    [selectedCheck]
  )

  const removeCheck = useCallback(
    (id: string) => {
      setEvaluationChecks((prev) => prev.filter((c) => c.id !== id))
      if (selectedCheck?.id === id) {
        setSelectedCheck(null)
      }
    },
    [selectedCheck]
  )

  // ============================================================================
  // Variable Management
  // ============================================================================

  const addVariable = useCallback(() => {
    const newVar: VariableDefinition = {
      id: `var-${Date.now()}`,
      name: `variable_${variables.length + 1}`,
      type: 'number',
      label: `Variable ${variables.length + 1}`,
      default: 0,
    }
    setVariables((prev) => [...prev, newVar])
  }, [variables.length])

  const updateVariable = useCallback((id: string, updates: Partial<VariableDefinition>) => {
    setVariables((prev) => prev.map((v) => (v.id === id ? { ...v, ...updates } : v)))
  }, [])

  const removeVariable = useCallback((id: string) => {
    setVariables((prev) => prev.filter((v) => v.id !== id))
  }, [])

  // ============================================================================
  // Tool Management
  // ============================================================================

  const toggleTool = useCallback(
    (toolId: string) => {
      const existing = selectedTools.find((t) => t.tool_id === toolId)
      if (existing) {
        setSelectedTools((prev) => prev.filter((t) => t.tool_id !== toolId))
      } else {
        const tool = availableTools.find((t) => t.id === toolId)
        if (tool) {
          // Build default config from schema
          const defaultConfig: Record<string, unknown> = {}
          Object.entries(tool.config_schema).forEach(([key, field]) => {
            if (field.default !== undefined) {
              defaultConfig[key] = field.default
            }
          })
          setSelectedTools((prev) => [
            ...prev,
            { tool_id: toolId, name: toolId, config: defaultConfig },
          ])
        }
      }
    },
    [selectedTools, availableTools]
  )

  const updateToolConfig = useCallback((toolId: string, config: Record<string, unknown>) => {
    setSelectedTools((prev) =>
      prev.map((t) => (t.tool_id === toolId ? { ...t, config } : t))
    )
  }, [])

  // ============================================================================
  // YAML Generation
  // ============================================================================

  const generateYaml = useCallback(() => {
    const moduleSlug = moduleName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')

    const stepsYaml = steps.map((step, index) => ({
      id: `step_${index + 1}`,
      action: step.type,
      params: step.params,
    }))

    const checksYaml = evaluationChecks.map((check) => {
      const c: Record<string, unknown> = { name: check.name, kind: check.kind }
      if (check.target) c.target = check.target
      if (check.value !== undefined) c.value = check.value
      if (check.expected !== undefined) c.expected = check.expected
      if (check.pattern) c.pattern = check.pattern
      if (check.min !== undefined) c.min = check.min
      if (check.max !== undefined) c.max = check.max
      if (check.tool) c.tool = check.tool
      if (check.action) c.action = check.action
      if (check.key) c.key = check.key
      return c
    })

    const varsYaml = variables.map((v) => {
      const varObj: Record<string, unknown> = {
        name: v.name,
        type: v.type,
        label: v.label,
      }
      if (v.description) varObj.description = v.description
      if (v.default !== undefined) varObj.default = v.default
      if (v.min !== undefined) varObj.min = v.min
      if (v.max !== undefined) varObj.max = v.max
      if (v.step !== undefined) varObj.step = v.step
      if (v.options) varObj.options = v.options
      return varObj
    })

    const toolsYaml = selectedTools.map((t) => ({
      name: t.name,
      type: t.tool_id,
      config: t.config,
    }))

    // Build agent section
    let agentSection: Record<string, unknown>
    if (agentConfig.mode === 'select' && agentConfig.agent_id) {
      agentSection = { id: agentConfig.agent_id }
    } else if (agentConfig.custom) {
      agentSection = {
        provider: agentConfig.custom.provider,
        model: agentConfig.custom.model,
        temperature: agentConfig.custom.temperature,
        system_prompt: agentConfig.custom.system_prompt,
      }
      if (agentConfig.custom.max_tokens) {
        agentSection.max_tokens = agentConfig.custom.max_tokens
      }
    } else {
      agentSection = {}
    }

    const moduleData: Record<string, unknown> = {
      id: moduleSlug,
      name: moduleName,
      description: moduleDescription || 'Created with Sandboxy Builder',
      version: '1.0',
    }

    if (moduleIcon) moduleData.icon = moduleIcon
    if (moduleCategory) moduleData.category = moduleCategory

    moduleData.agent = agentSection

    if (toolsYaml.length > 0) {
      moduleData.environment = {
        sandbox_type: 'mock',
        tools: toolsYaml,
      }
    }

    if (varsYaml.length > 0) {
      moduleData.variables = varsYaml
    }

    moduleData.steps = stepsYaml
    moduleData.evaluation = checksYaml

    return yaml.dump(moduleData, { indent: 2, lineWidth: -1 })
  }, [
    moduleName,
    moduleDescription,
    moduleIcon,
    moduleCategory,
    agentConfig,
    selectedTools,
    variables,
    steps,
    evaluationChecks,
  ])

  // ============================================================================
  // Import/Export
  // ============================================================================

  const handleImport = useCallback(() => {
    try {
      const parsed = yaml.load(importYaml) as Record<string, unknown>

      if (parsed.name) setModuleName(String(parsed.name))
      if (parsed.description) setModuleDescription(String(parsed.description))
      populateFromYaml(parsed)

      setShowImport(false)
      setImportYaml('')
      setImportError('')
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Invalid YAML')
    }
  }, [importYaml])

  const handleCopyYaml = useCallback(() => {
    navigator.clipboard.writeText(generateYaml())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [generateYaml])

  const handleDownloadYaml = useCallback(() => {
    const blob = new Blob([generateYaml()], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${moduleName.toLowerCase().replace(/\s+/g, '-')}.yml`
    a.click()
    URL.revokeObjectURL(url)
  }, [generateYaml, moduleName])

  const handleSave = async () => {
    const yamlContent = generateYaml()
    const newSlug = moduleName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')

    setSaving(true)
    try {
      if (isEditMode && moduleSlug) {
        await api.updateModule(moduleSlug, {
          name: moduleName,
          description: moduleDescription || 'Created with Sandboxy Builder',
          yaml_content: yamlContent,
        })
      } else {
        await api.createModule({
          slug: newSlug,
          name: moduleName,
          description: moduleDescription || 'Created with Sandboxy Builder',
          yaml_content: yamlContent,
        })
      }
      navigate('/')
    } catch (err) {
      alert(`Failed to save: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setSaving(false)
    }
  }

  // ============================================================================
  // Keyboard Shortcuts
  // ============================================================================

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedStep) {
        if (
          document.activeElement?.tagName === 'INPUT' ||
          document.activeElement?.tagName === 'TEXTAREA'
        ) {
          return
        }
        e.preventDefault()
        deleteStep(selectedStep.id)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedStep, deleteStep])

  // ============================================================================
  // Render
  // ============================================================================

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="h-full flex">
        {/* Left Sidebar - Tabs */}
        <div className="w-80 bg-dark-card border-r border-dark-border flex flex-col">
          {/* Tab buttons */}
          <div className="flex flex-wrap border-b border-dark-border">
            {TABS.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 min-w-[80px] flex flex-col items-center gap-1 py-3 text-xs font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'text-accent border-b-2 border-accent bg-accent/5'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              )
            })}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === 'basics' && (
              <BasicsTab
                moduleName={moduleName}
                setModuleName={setModuleName}
                moduleDescription={moduleDescription}
                setModuleDescription={setModuleDescription}
                moduleIcon={moduleIcon}
                setModuleIcon={setModuleIcon}
                moduleCategory={moduleCategory}
                setModuleCategory={setModuleCategory}
              />
            )}

            {activeTab === 'agent' && (
              <AgentTab
                agentConfig={agentConfig}
                setAgentConfig={setAgentConfig}
                availableAgents={availableAgents}
                availableModels={availableModels}
              />
            )}

            {activeTab === 'tools' && (
              <ToolsTab
                availableTools={availableTools}
                selectedTools={selectedTools}
                toggleTool={toggleTool}
                updateToolConfig={updateToolConfig}
              />
            )}

            {activeTab === 'variables' && (
              <VariablesTab
                variables={variables}
                addVariable={addVariable}
                updateVariable={updateVariable}
                removeVariable={removeVariable}
              />
            )}

            {activeTab === 'steps' && (
              <StepsTab addStep={addStep} />
            )}

            {activeTab === 'evaluation' && (
              <EvaluationTab
                evaluationChecks={evaluationChecks}
                selectedCheck={selectedCheck}
                setSelectedCheck={setSelectedCheck}
                setSelectedStep={setSelectedStep}
                addCheck={addCheck}
                removeCheck={removeCheck}
              />
            )}
          </div>

          {/* Bottom Actions */}
          <div className="p-4 border-t border-dark-border space-y-2">
            <div className="flex gap-2">
              <button
                onClick={() => setShowImport(true)}
                className="flex-1 flex items-center justify-center gap-2 bg-dark-bg hover:bg-dark-hover text-gray-300 py-2 rounded-lg transition-colors text-sm"
                aria-label="Import"
              >
                <Upload size={16} />
                Import
              </button>
              <button
                onClick={() => setShowYaml(!showYaml)}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-colors text-sm ${
                  showYaml ? 'bg-accent/20 text-accent' : 'bg-dark-bg hover:bg-dark-hover text-gray-300'
                }`}
                aria-label="YAML"
              >
                <Code size={16} />
                YAML
              </button>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white py-2.5 rounded-lg transition-colors font-medium"
              aria-label="Save"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {isEditMode ? 'Update Module' : 'Save Module'}
            </button>
          </div>
        </div>

        {/* Main Canvas */}
        <div className="flex-1 flex flex-col bg-dark-bg overflow-hidden">
          {/* Header */}
          <div className="bg-dark-card border-b border-dark-border px-6 py-4">
            <h1 className="text-lg font-semibold text-white">{moduleName}</h1>
            <p className="text-sm text-gray-400 mt-1">
              {activeTab === 'steps'
                ? `${steps.length} step${steps.length !== 1 ? 's' : ''} • Click to edit, drag to reorder`
                : `Editing ${TABS.find((t) => t.id === activeTab)?.label || activeTab}`}
            </p>
          </div>

          {/* Canvas Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'steps' ? (
              <StepsCanvas
                steps={steps}
                selectedStep={selectedStep}
                setSelectedStep={setSelectedStep}
                setSelectedCheck={setSelectedCheck}
                deleteStep={deleteStep}
              />
            ) : activeTab === 'evaluation' ? (
              <EvaluationCanvas
                evaluationChecks={evaluationChecks}
                selectedCheck={selectedCheck}
              />
            ) : (
              <CanvasPlaceholder tab={activeTab} />
            )}
          </div>
        </div>

        {/* Right Panel - Properties or YAML */}
        {(selectedStep || selectedCheck || showYaml) && (
          <div className="w-80 bg-dark-card border-l border-dark-border flex flex-col">
            {showYaml ? (
              <YamlPanel
                yaml={generateYaml()}
                copied={copied}
                onCopy={handleCopyYaml}
                onDownload={handleDownloadYaml}
                onClose={() => setShowYaml(false)}
              />
            ) : selectedStep ? (
              <StepPropertiesPanel
                step={steps.find((s) => s.id === selectedStep.id) || selectedStep}
                onChange={(params) => updateStep(selectedStep.id, params)}
                onClose={() => setSelectedStep(null)}
              />
            ) : selectedCheck ? (
              <CheckPropertiesPanel
                check={evaluationChecks.find((c) => c.id === selectedCheck.id) || selectedCheck}
                onChange={(updates) => updateCheck(selectedCheck.id, updates)}
                onClose={() => setSelectedCheck(null)}
              />
            ) : null}
          </div>
        )}

        {/* Import Modal */}
        {showImport && (
          <ImportModal
            importYaml={importYaml}
            setImportYaml={setImportYaml}
            importError={importError}
            onImport={handleImport}
            onClose={() => {
              setShowImport(false)
              setImportYaml('')
              setImportError('')
            }}
          />
        )}

        {/* Drag Overlay */}
        <DragOverlay>
          {activeId && draggedType && (
            <div className={`px-4 py-3 rounded-lg border ${STEP_TYPES[draggedType].color} shadow-lg`}>
              <div className="flex items-center gap-3">
                {(() => {
                  const Icon = STEP_TYPES[draggedType].icon
                  return <Icon size={18} />
                })()}
                <span className="font-medium text-white">{STEP_TYPES[draggedType].label}</span>
              </div>
            </div>
          )}
        </DragOverlay>
      </div>
    </DndContext>
  )
}

// ============================================================================
// Tab Components
// ============================================================================

function BasicsTab({
  moduleName,
  setModuleName,
  moduleDescription,
  setModuleDescription,
  moduleIcon,
  setModuleIcon,
  moduleCategory,
  setModuleCategory,
}: {
  moduleName: string
  setModuleName: (v: string) => void
  moduleDescription: string
  setModuleDescription: (v: string) => void
  moduleIcon: string
  setModuleIcon: (v: string) => void
  moduleCategory: string
  setModuleCategory: (v: string) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-2">Module Name</label>
        <input
          type="text"
          value={moduleName}
          onChange={(e) => setModuleName(e.target.value)}
          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-2">Description</label>
        <textarea
          value={moduleDescription}
          onChange={(e) => setModuleDescription(e.target.value)}
          rows={3}
          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent resize-none"
          placeholder="Describe your simulation..."
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-2">Icon (emoji)</label>
        <input
          type="text"
          value={moduleIcon}
          onChange={(e) => setModuleIcon(e.target.value)}
          placeholder="🎮"
          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-2">Category</label>
        <select
          value={moduleCategory}
          onChange={(e) => setModuleCategory(e.target.value)}
          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
        >
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

function AgentTab({
  agentConfig,
  setAgentConfig,
  availableAgents,
  availableModels,
}: {
  agentConfig: AgentConfig
  setAgentConfig: (v: AgentConfig) => void
  availableAgents: Agent[]
  availableModels: ArenaModel[]
}) {
  // Group models by their original provider (openai, anthropic, google, etc.)
  const modelsByProvider = availableModels.reduce((acc, model) => {
    if (!acc[model.provider]) acc[model.provider] = []
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, ArenaModel[]>)

  // Get sorted provider names
  const providerOrder = ['openai', 'anthropic', 'google', 'meta', 'mistral', 'deepseek', 'xai', 'qwen', 'perplexity']
  const sortedProviders = Object.keys(modelsByProvider).sort((a, b) => {
    const aIdx = providerOrder.indexOf(a)
    const bIdx = providerOrder.indexOf(b)
    if (aIdx === -1 && bIdx === -1) return a.localeCompare(b)
    if (aIdx === -1) return 1
    if (bIdx === -1) return -1
    return aIdx - bIdx
  })

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-2">Agent Mode</label>
        <div className="flex gap-2">
          <button
            onClick={() => setAgentConfig({ ...agentConfig, mode: 'select' })}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              agentConfig.mode === 'select'
                ? 'bg-accent text-white'
                : 'bg-dark-bg text-gray-400 hover:text-white'
            }`}
            aria-label="Preset Agent"
          >
            Preset Agent
          </button>
          <button
            onClick={() => setAgentConfig({ ...agentConfig, mode: 'custom' })}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              agentConfig.mode === 'custom'
                ? 'bg-accent text-white'
                : 'bg-dark-bg text-gray-400 hover:text-white'
            }`}
            aria-label="Custom"
          >
            Custom
          </button>
        </div>
      </div>

      {agentConfig.mode === 'select' ? (
        <div>
          <label className="block text-sm text-gray-400 mb-2">Select Preset Agent</label>
          <select
            value={agentConfig.agent_id || ''}
            onChange={(e) => setAgentConfig({ ...agentConfig, agent_id: e.target.value })}
            className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
          >
            <option value="">Choose an agent...</option>
            {availableAgents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} ({agent.model})
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-2">
            Preset agents are defined in agents/core/*.yaml
          </p>
        </div>
      ) : (
        <>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Model</label>
            <select
              value={agentConfig.custom?.model || ''}
              onChange={(e) => {
                const model = availableModels.find(m => m.id === e.target.value)
                setAgentConfig({
                  ...agentConfig,
                  custom: {
                    ...agentConfig.custom!,
                    model: e.target.value,
                    provider: model?.provider || 'openrouter',
                  },
                })
              }}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            >
              <option value="">Choose a model...</option>
              {sortedProviders.map((provider) => (
                <optgroup key={provider} label={provider.charAt(0).toUpperCase() + provider.slice(1)}>
                  {modelsByProvider[provider].map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            {agentConfig.custom?.model && (
              <p className="text-xs text-gray-500 mt-1">
                Model ID: <code className="bg-dark-bg px-1 rounded">{agentConfig.custom.model}</code>
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Temperature: {agentConfig.custom?.temperature ?? 0.7}
            </label>
            <input
              type="range"
              value={agentConfig.custom?.temperature ?? 0.7}
              onChange={(e) =>
                setAgentConfig({
                  ...agentConfig,
                  custom: { ...agentConfig.custom!, temperature: parseFloat(e.target.value) },
                })
              }
              min={0}
              max={2}
              step={0.1}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">System Prompt</label>
            <textarea
              value={agentConfig.custom?.system_prompt || ''}
              onChange={(e) =>
                setAgentConfig({
                  ...agentConfig,
                  custom: { ...agentConfig.custom!, system_prompt: e.target.value },
                })
              }
              rows={8}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-accent resize-none"
              placeholder="You are a helpful assistant..."
            />
          </div>
        </>
      )}
    </div>
  )
}

function ToolsTab({
  availableTools,
  selectedTools,
  toggleTool,
  updateToolConfig,
}: {
  availableTools: ToolInfo[]
  selectedTools: ToolSelection[]
  toggleTool: (toolId: string) => void
  updateToolConfig: (toolId: string, config: Record<string, unknown>) => void
}) {
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  return (
    <div className="space-y-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        Available Tools ({availableTools.length})
      </h3>
      <div className="space-y-2">
        {availableTools.map((tool) => {
          const isSelected = selectedTools.some((t) => t.tool_id === tool.id)
          const selection = selectedTools.find((t) => t.tool_id === tool.id)
          const isExpanded = expandedTool === tool.id

          return (
            <div
              key={tool.id}
              className={`border rounded-lg overflow-hidden transition-colors ${
                isSelected ? 'border-accent/50 bg-accent/5' : 'border-dark-border'
              }`}
            >
              <div className="flex items-center gap-3 p-3">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleTool(tool.id)}
                  className="rounded bg-dark-bg border-dark-border"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white">{tool.id}</div>
                  <div className="text-xs text-gray-500 truncate">
                    {tool.description?.split('\n')[0] || 'No description'}
                  </div>
                </div>
                {isSelected && Object.keys(tool.config_schema).length > 0 && (
                  <button
                    onClick={() => setExpandedTool(isExpanded ? null : tool.id)}
                    className="p-1 text-gray-400 hover:text-white transition-colors"
                  >
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </button>
                )}
              </div>

              {isSelected && isExpanded && Object.keys(tool.config_schema).length > 0 && (
                <div className="px-3 pb-3 pt-0 border-t border-dark-border">
                  <ToolConfigForm
                    schema={tool.config_schema}
                    values={selection?.config || {}}
                    onChange={(config) => updateToolConfig(tool.id, config)}
                    className="mt-3"
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function VariablesTab({
  variables,
  addVariable,
  updateVariable,
  removeVariable,
}: {
  variables: VariableDefinition[]
  addVariable: () => void
  updateVariable: (id: string, updates: Partial<VariableDefinition>) => void
  removeVariable: (id: string) => void
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Variables ({variables.length})
        </h3>
        <button
          onClick={addVariable}
          className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover transition-colors"
          aria-label="Add"
        >
          <Plus size={14} />
          Add
        </button>
      </div>

      {variables.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-4">
          No variables yet. Add variables to let users customize scenarios.
        </p>
      ) : (
        <div className="space-y-3">
          {variables.map((variable) => (
            <VariableEditor
              key={variable.id}
              variable={variable}
              onChange={(updates) => updateVariable(variable.id, updates)}
              onRemove={() => removeVariable(variable.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function VariableEditor({
  variable,
  onChange,
  onRemove,
}: {
  variable: VariableDefinition
  onChange: (updates: Partial<VariableDefinition>) => void
  onRemove: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-dark-border rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 p-3 bg-dark-card">
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 text-gray-400 hover:text-white transition-colors"
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <input
          type="text"
          value={variable.label}
          onChange={(e) => onChange({ label: e.target.value })}
          className="flex-1 bg-transparent text-sm text-white focus:outline-none"
          placeholder="Variable label"
        />
        <span className="text-xs text-gray-500 bg-dark-bg px-2 py-0.5 rounded">{variable.type}</span>
        <button
          onClick={onRemove}
          className="p-1 text-gray-500 hover:text-red-400 transition-colors"
          aria-label="Remove"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {expanded && (
        <div className="p-3 space-y-3 bg-dark-bg/50 border-t border-dark-border">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Name (key)</label>
              <input
                type="text"
                value={variable.name}
                onChange={(e) => onChange({ name: e.target.value })}
                className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                value={variable.type}
                onChange={(e) => onChange({ type: e.target.value as VariableDefinition['type'] })}
                className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm focus:outline-none focus:border-accent"
              >
                <option value="slider">Slider</option>
                <option value="number">Number</option>
                <option value="text">Text</option>
                <option value="boolean">Boolean</option>
                <option value="select">Select</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Description</label>
            <input
              type="text"
              value={variable.description || ''}
              onChange={(e) => onChange({ description: e.target.value })}
              className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm focus:outline-none focus:border-accent"
              placeholder="Optional description"
            />
          </div>

          {(variable.type === 'slider' || variable.type === 'number') && (
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Min</label>
                <input
                  type="number"
                  value={variable.min ?? ''}
                  onChange={(e) => onChange({ min: e.target.value ? Number(e.target.value) : undefined })}
                  className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Max</label>
                <input
                  type="number"
                  value={variable.max ?? ''}
                  onChange={(e) => onChange({ max: e.target.value ? Number(e.target.value) : undefined })}
                  className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Default</label>
                <input
                  type="number"
                  value={variable.default as number ?? ''}
                  onChange={(e) => onChange({ default: e.target.value ? Number(e.target.value) : undefined })}
                  className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm focus:outline-none focus:border-accent"
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StepsTab({ addStep }: { addStep: (type: StepType) => void }) {
  return (
    <div className="space-y-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        Drag to add steps
      </h3>
      <div className="space-y-2">
        {(Object.entries(STEP_TYPES) as [StepType, (typeof STEP_TYPES)[StepType]][]).map(
          ([type, config]) => (
            <DraggableStepType key={type} type={type} config={config} onAdd={() => addStep(type)} />
          )
        )}
      </div>
    </div>
  )
}

function EvaluationTab({
  evaluationChecks,
  selectedCheck,
  setSelectedCheck,
  setSelectedStep,
  addCheck,
  removeCheck,
}: {
  evaluationChecks: EvaluationCheck[]
  selectedCheck: EvaluationCheck | null
  setSelectedCheck: (c: EvaluationCheck | null) => void
  setSelectedStep: (s: Step | null) => void
  addCheck: (kind: CheckKind) => void
  removeCheck: (id: string) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Add Checks</h3>
        <div className="space-y-2">
          <CheckButton label="Contains" kind="contains" onClick={() => addCheck('contains')} />
          <CheckButton label="Regex Match" kind="regex" onClick={() => addCheck('regex')} />
          <CheckButton label="Count" kind="count" onClick={() => addCheck('count')} />
          <CheckButton label="Tool Called" kind="tool_called" onClick={() => addCheck('tool_called')} />
          <CheckButton label="Env State" kind="env_state" onClick={() => addCheck('env_state')} />
        </div>
      </div>

      {evaluationChecks.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Checks ({evaluationChecks.length})
          </h3>
          <div className="space-y-1">
            {evaluationChecks.map((check) => (
              <div
                key={check.id}
                onClick={() => {
                  setSelectedCheck(check)
                  setSelectedStep(null)
                }}
                className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  selectedCheck?.id === check.id
                    ? 'bg-accent/20 border border-accent/50'
                    : 'bg-dark-bg hover:bg-dark-hover'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <CheckCircle size={14} className="text-green-400 shrink-0" />
                  <span className="text-sm text-white truncate">{check.name}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    removeCheck(check.id)
                  }}
                  className="text-gray-500 hover:text-red-400 shrink-0"
                  aria-label="Remove"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Canvas Components
// ============================================================================

function StepsCanvas({
  steps,
  selectedStep,
  setSelectedStep,
  setSelectedCheck,
  deleteStep,
}: {
  steps: Step[]
  selectedStep: Step | null
  setSelectedStep: (s: Step | null) => void
  setSelectedCheck: (c: EvaluationCheck | null) => void
  deleteStep: (id: string) => void
}) {
  if (steps.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 rounded-full bg-dark-card border-2 border-dashed border-dark-border flex items-center justify-center mb-4">
          <Plus size={24} className="text-gray-500" />
        </div>
        <h3 className="text-lg font-medium text-white mb-2">No steps yet</h3>
        <p className="text-gray-400 max-w-sm">
          Drag step types from the sidebar or click them to add steps to your simulation.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <SortableContext items={steps.map((s) => s.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-3">
          {steps.map((step, index) => (
            <SortableStep
              key={step.id}
              step={step}
              index={index}
              isSelected={selectedStep?.id === step.id}
              onSelect={() => {
                setSelectedStep(step)
                setSelectedCheck(null)
              }}
              onDelete={() => deleteStep(step.id)}
            />
          ))}
        </div>
      </SortableContext>
    </div>
  )
}

function EvaluationCanvas({
  evaluationChecks,
  selectedCheck,
}: {
  evaluationChecks: EvaluationCheck[]
  selectedCheck: EvaluationCheck | null
}) {
  if (evaluationChecks.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center">
        <CheckCircle size={48} className="text-gray-500 mb-4" />
        <h3 className="text-lg font-medium text-white mb-2">No evaluation checks</h3>
        <p className="text-gray-400 max-w-sm">
          Add checks from the sidebar to define pass/fail criteria for your scenario.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="space-y-3">
        {evaluationChecks.map((check) => (
          <div
            key={check.id}
            className={`p-4 rounded-lg border transition-colors ${
              selectedCheck?.id === check.id
                ? 'border-accent bg-accent/10'
                : 'border-dark-border bg-dark-card'
            }`}
          >
            <div className="flex items-center gap-3">
              <CheckCircle size={20} className="text-green-400" />
              <div>
                <div className="font-medium text-white">{check.name}</div>
                <div className="text-sm text-gray-400">{check.kind}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CanvasPlaceholder({ tab }: { tab: TabId }) {
  const tabInfo = TABS.find((t) => t.id === tab)
  const Icon = tabInfo?.icon || Settings

  return (
    <div className="h-full flex flex-col items-center justify-center text-center">
      <Icon size={48} className="text-gray-500 mb-4" />
      <h3 className="text-lg font-medium text-white mb-2">{tabInfo?.label} Configuration</h3>
      <p className="text-gray-400 max-w-sm">
        Configure {tabInfo?.label.toLowerCase()} settings in the sidebar.
      </p>
    </div>
  )
}

// ============================================================================
// Utility Components
// ============================================================================

function DraggableStepType({
  type,
  config,
  onAdd,
}: {
  type: StepType
  config: (typeof STEP_TYPES)[StepType]
  onAdd: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useSortable({
    id: `toolbox-${type}`,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  }

  const Icon = config.icon

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onAdd}
      className={`px-3 py-2.5 rounded-lg border cursor-grab active:cursor-grabbing transition-all hover:scale-[1.02] ${config.color}`}
    >
      <div className="flex items-center gap-3">
        <Icon size={18} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-white">{config.label}</div>
          <div className="text-xs text-gray-400 truncate">{config.description}</div>
        </div>
        <Plus size={16} className="text-gray-400" />
      </div>
    </div>
  )
}

function SortableStep({
  step,
  index,
  isSelected,
  onSelect,
  onDelete,
}: {
  step: Step
  index: number
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: step.id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const config = STEP_TYPES[step.type]
  const Icon = config.icon

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={onSelect}
      className={`group flex items-stretch rounded-xl border transition-all ${
        isSelected
          ? 'border-accent bg-accent/10 shadow-lg shadow-accent/10'
          : 'border-dark-border bg-dark-card hover:border-dark-hover'
      }`}
    >
      <div
        {...attributes}
        {...listeners}
        className="flex items-center px-3 cursor-grab active:cursor-grabbing text-gray-500 hover:text-gray-300 transition-colors"
      >
        <GripVertical size={18} />
      </div>

      <div className="flex-1 py-3 pr-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.color}`}>
            <Icon size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-mono">{index + 1}</span>
              <span className="font-medium text-white">{config.label}</span>
            </div>
            <div className="text-sm text-gray-400 truncate mt-0.5">{getStepPreview(step)}</div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="p-2 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
            aria-label="Remove"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}

function CheckButton({
  label,
  onClick,
}: {
  label: string
  kind: CheckKind
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 bg-dark-bg hover:bg-dark-hover text-gray-300 px-3 py-2 rounded-lg transition-colors text-sm"
      aria-label="Add"
    >
      <Plus size={14} className="text-green-400" />
      {label}
    </button>
  )
}

// ============================================================================
// Panel Components
// ============================================================================

function YamlPanel({
  yaml,
  copied,
  onCopy,
  onDownload,
  onClose,
}: {
  yaml: string
  copied: boolean
  onCopy: () => void
  onDownload: () => void
  onClose: () => void
}) {
  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <FileCode size={16} className="text-accent" />
          YAML Output
        </h3>
        <div className="flex gap-2">
          <button onClick={onCopy} className="p-1.5 text-gray-400 hover:text-white transition-colors" title="Copy" aria-label="Copy">
            {copied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
          </button>
          <button onClick={onDownload} className="p-1.5 text-gray-400 hover:text-white transition-colors" title="Download" aria-label="Download">
            <Download size={16} />
          </button>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-white transition-colors" aria-label="Close">
            <X size={16} />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{yaml}</pre>
      </div>
    </div>
  )
}

function StepPropertiesPanel({
  step,
  onChange,
  onClose,
}: {
  step: Step
  onChange: (params: Record<string, unknown>) => void
  onClose: () => void
}) {
  const config = STEP_TYPES[step.type]
  const Icon = config.icon

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
        <h3 className="text-sm font-semibold text-white">Step Properties</h3>
        <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-white transition-colors" aria-label="Close">
          <X size={16} />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        <div className={`flex items-center gap-3 p-3 rounded-lg ${config.color}`}>
          <Icon size={20} />
          <div>
            <div className="text-sm font-medium text-white">{config.label}</div>
            <div className="text-xs text-gray-400">{config.description}</div>
          </div>
        </div>

        {step.type === 'inject_user' && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">Message Content</label>
            <textarea
              value={(step.params.content as string) || ''}
              onChange={(e) => onChange({ ...step.params, content: e.target.value })}
              rows={6}
              placeholder="Enter the user message to inject..."
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent resize-none"
            />
          </div>
        )}

        {step.type === 'await_user' && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">Prompt</label>
            <textarea
              value={(step.params.prompt as string) || ''}
              onChange={(e) => onChange({ ...step.params, prompt: e.target.value })}
              rows={3}
              placeholder="Prompt shown to the user..."
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent resize-none"
            />
          </div>
        )}

        {step.type === 'await_agent' && (
          <div className="text-sm text-gray-400">
            This step waits for the agent to respond. No additional configuration needed.
          </div>
        )}

        {step.type === 'branch' && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">Branch Name</label>
            <input
              type="text"
              value={(step.params.branch_name as string) || ''}
              onChange={(e) => onChange({ ...step.params, branch_name: e.target.value })}
              placeholder="e.g., success, failure"
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
        )}

        <div className="pt-4 border-t border-dark-border">
          <p className="text-xs text-gray-500">
            Press <kbd className="px-1.5 py-0.5 bg-dark-bg rounded text-gray-400">Delete</kbd> to remove
          </p>
        </div>
      </div>
    </div>
  )
}

function CheckPropertiesPanel({
  check,
  onChange,
  onClose,
}: {
  check: EvaluationCheck
  onChange: (updates: Partial<EvaluationCheck>) => void
  onClose: () => void
}) {
  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
        <h3 className="text-sm font-semibold text-white">Check Properties</h3>
        <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-white transition-colors" aria-label="Close">
          <X size={16} />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-2">Name</label>
          <input
            type="text"
            value={check.name}
            onChange={(e) => onChange({ name: e.target.value })}
            className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-2">Type</label>
          <div className="bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm">
            {check.kind}
          </div>
        </div>

        {(check.kind === 'contains' || check.kind === 'regex' || check.kind === 'count') && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">Target</label>
            <select
              value={check.target || 'agent_messages'}
              onChange={(e) => onChange({ target: e.target.value as CheckTarget })}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            >
              <option value="agent_messages">Agent Messages</option>
              <option value="user_messages">User Messages</option>
              <option value="all_messages">All Messages</option>
              <option value="tool_calls">Tool Calls</option>
            </select>
          </div>
        )}

        {check.kind === 'contains' && (
          <>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Search For</label>
              <input
                type="text"
                value={check.value || ''}
                onChange={(e) => onChange({ value: e.target.value })}
                placeholder="Text to search for..."
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={check.expected !== false}
                onChange={(e) => onChange({ expected: e.target.checked })}
                className="rounded bg-dark-bg border-dark-border"
              />
              Should contain (pass if found)
            </label>
          </>
        )}

        {check.kind === 'regex' && (
          <>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Pattern</label>
              <input
                type="text"
                value={check.pattern || ''}
                onChange={(e) => onChange({ pattern: e.target.value })}
                placeholder="Regex pattern..."
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-accent"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={check.expected !== false}
                onChange={(e) => onChange({ expected: e.target.checked })}
                className="rounded bg-dark-bg border-dark-border"
              />
              Should match (pass if matches)
            </label>
          </>
        )}

        {check.kind === 'count' && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Min</label>
              <input
                type="number"
                value={check.min ?? ''}
                onChange={(e) => onChange({ min: e.target.value ? parseInt(e.target.value) : undefined })}
                placeholder="0"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Max</label>
              <input
                type="number"
                value={check.max ?? ''}
                onChange={(e) => onChange({ max: e.target.value ? parseInt(e.target.value) : undefined })}
                placeholder="∞"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
          </div>
        )}

        {check.kind === 'tool_called' && (
          <>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Tool Name</label>
              <input
                type="text"
                value={check.tool || ''}
                onChange={(e) => onChange({ tool: e.target.value })}
                placeholder="e.g., shopify"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Action (optional)</label>
              <input
                type="text"
                value={check.action || ''}
                onChange={(e) => onChange({ action: e.target.value })}
                placeholder="e.g., process_refund"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={check.expected !== false}
                onChange={(e) => onChange({ expected: e.target.checked })}
                className="rounded bg-dark-bg border-dark-border"
              />
              Should be called (pass if called)
            </label>
          </>
        )}

        {check.kind === 'env_state' && (
          <>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Key (dot notation)</label>
              <input
                type="text"
                value={check.key || ''}
                onChange={(e) => onChange({ key: e.target.value })}
                placeholder="e.g., orders.ORD123.refunded"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Expected Value</label>
              <input
                type="text"
                value={check.value || ''}
                onChange={(e) => onChange({ value: e.target.value })}
                placeholder="true, false, or a value"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function ImportModal({
  importYaml,
  setImportYaml,
  importError,
  onImport,
  onClose,
}: {
  importYaml: string
  setImportYaml: (v: string) => void
  importError: string
  onImport: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-dark-card border border-dark-border rounded-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
          <h3 className="text-lg font-semibold text-white">Import MDL YAML</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors" aria-label="Close">
            <X size={20} />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <textarea
            value={importYaml}
            onChange={(e) => setImportYaml(e.target.value)}
            placeholder="Paste your MDL YAML here..."
            rows={12}
            className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-white font-mono text-sm focus:outline-none focus:border-accent resize-none"
          />
          {importError && <p className="text-sm text-red-400">{importError}</p>}
          <div className="flex gap-3">
            <button onClick={onClose} className="flex-1 py-2 text-gray-400 hover:text-white transition-colors" aria-label="Close">
              Cancel
            </button>
            <button
              onClick={onImport}
              disabled={!importYaml.trim()}
              className="flex-1 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white py-2 rounded-lg transition-colors font-medium"
              aria-label="Import"
            >
              Import
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Helpers
// ============================================================================

function getStepPreview(step: Step): string {
  switch (step.type) {
    case 'inject_user':
      return (step.params.content as string) || 'No message set'
    case 'await_user':
      return (step.params.prompt as string) || 'Waiting for user input'
    case 'await_agent':
      return 'Waiting for agent response'
    case 'branch':
      return (step.params.condition as string) || 'No condition set'
    default:
      return ''
  }
}

function getDefaultParams(type: StepType): Record<string, unknown> {
  switch (type) {
    case 'inject_user':
      return { content: '' }
    case 'await_user':
      return { prompt: 'Enter your message:' }
    case 'await_agent':
      return {}
    case 'branch':
      return { condition: '' }
    default:
      return {}
  }
}
