import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Save,
  Play,
  AlertCircle,
  CheckCircle,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  FileText,
  Wrench,
  Target,
  MessageSquare,
  Variable,
} from 'lucide-react'
import { useScenarioBuilder, GoalSpec, StepSpec, JudgeSpec, VariableSpec } from '../hooks/useScenarioBuilder'
import { api } from '../lib/api'

type TabId = 'basic' | 'variables' | 'interaction' | 'tools' | 'evaluation'

const STYLES = ['', 'brief', 'spicy', 'professional', 'formal', 'wholesome', 'chaotic', 'poetic']

const DETECTION_TYPES = [
  { value: 'tool_called', label: 'Tool Called' },
  { value: 'env_state', label: 'Environment State' },
  { value: 'agent_contains', label: 'Agent Contains' },
  { value: 'any_tool_called', label: 'Any Tool Called' },
]

export default function BuilderPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>('basic')
  const [showYaml, setShowYaml] = useState(true)
  const [availableTools, setAvailableTools] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const builder = useScenarioBuilder()

  // Load available tools
  useEffect(() => {
    api.listTools().then(tools => {
      setAvailableTools(tools.map(t => t.id))
    }).catch(() => {
      // Ignore errors
    })
  }, [])

  const handleSave = async (): Promise<boolean> => {
    if (!builder.isValid) return false

    setSaving(true)
    setSaveMessage(null)

    try {
      const response = await fetch('/api/v1/local/scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: builder.state.id,
          content: builder.yamlPreview,
        }),
      })

      if (response.ok) {
        setSaveMessage({ type: 'success', text: 'Scenario saved successfully!' })
        return true
      } else {
        const error = await response.json()
        setSaveMessage({ type: 'error', text: error.detail || 'Failed to save' })
        return false
      }
    } catch (err) {
      setSaveMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to save' })
      return false
    } finally {
      setSaving(false)
    }
  }

  const handleSaveAndRun = async () => {
    const saved = await handleSave()
    if (saved) {
      navigate(`/run/${builder.state.id}`)
    }
  }

  const tabs = [
    { id: 'basic' as const, label: 'Basic Info', icon: FileText },
    { id: 'variables' as const, label: 'Variables', icon: Variable },
    { id: 'interaction' as const, label: 'Interaction', icon: MessageSquare },
    { id: 'tools' as const, label: 'Tools', icon: Wrench },
    { id: 'evaluation' as const, label: 'Evaluation', icon: Target },
  ]

  return (
    <div className="flex h-full page">
      {/* Main Content */}
      <div className={`flex-1 flex flex-col ${showYaml ? 'lg:mr-96' : ''}`}>
        {/* Header */}
        <div className="p-4 sm:p-6 border-b border-slate-800/70">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="flex items-center gap-2 text-slate-400 hover:text-slate-100"
              >
                <ArrowLeft size={20} />
              </Link>
              <h1 className="text-xl sm:text-2xl font-semibold text-slate-100">Scenario Builder</h1>
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <button
                onClick={() => setShowYaml(!showYaml)}
                className="px-3 py-2 text-slate-400 hover:text-slate-100 border border-slate-700/70 rounded-lg text-sm"
              >
                <span className="hidden sm:inline">{showYaml ? 'Hide' : 'Show'} </span>YAML
              </button>
              <button
                onClick={() => handleSave()}
                disabled={!builder.isValid || saving}
                className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 disabled:text-slate-500 disabled:cursor-not-allowed text-slate-100 px-3 py-2 rounded-lg text-sm"
              >
                <Save size={18} />
                <span className="hidden sm:inline">Save</span>
              </button>
              <button
                onClick={handleSaveAndRun}
                disabled={!builder.isValid || saving}
                className="flex items-center gap-2 bg-emerald-400 hover:bg-emerald-300 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed text-slate-900 px-3 py-2 rounded-lg font-semibold text-sm"
              >
                <Play size={18} />
                <span className="hidden sm:inline">{saving ? 'Saving...' : 'Save & Run'}</span>
              </button>
            </div>
          </div>

          {/* Save Message */}
          {saveMessage && (
            <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 text-sm ${
              saveMessage.type === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-400/40' : 'bg-red-900/30 text-red-400 border border-red-700/60'
            }`}>
              {saveMessage.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
              {saveMessage.text}
            </div>
          )}

          {/* Validation Errors */}
          {builder.validationErrors.length > 0 && (
            <div className="mt-4 p-3 bg-amber-500/10 border border-amber-400/50 rounded-lg">
              <div className="flex items-center gap-2 text-amber-300 font-medium mb-2 text-sm">
                <AlertCircle size={18} />
                Validation Issues
              </div>
              <ul className="list-disc list-inside text-amber-200/80 text-xs sm:text-sm space-y-1">
                {builder.validationErrors.map((error, idx) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Tabs - scrollable on mobile */}
        <div className="flex overflow-x-auto border-b border-slate-800/70 scrollbar-hide">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 sm:px-6 py-3 font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'text-orange-300 border-b-2 border-orange-300'
                  : 'text-slate-400 hover:text-slate-100'
              }`}
            >
              <tab.icon size={18} />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-auto p-4 sm:p-6">
          {activeTab === 'basic' && (
            <BasicInfoSection builder={builder} />
          )}
          {activeTab === 'variables' && (
            <VariablesSection builder={builder} />
          )}
          {activeTab === 'interaction' && (
            <InteractionSection builder={builder} />
          )}
          {activeTab === 'tools' && (
            <ToolsSection builder={builder} availableTools={availableTools} />
          )}
          {activeTab === 'evaluation' && (
            <EvaluationSection builder={builder} />
          )}
        </div>
      </div>

      {/* YAML Preview Panel - overlay on mobile, side panel on desktop */}
      {showYaml && (
        <>
          {/* Mobile backdrop */}
          <div
            className="fixed inset-0 bg-black/50 lg:hidden z-40"
            onClick={() => setShowYaml(false)}
          />
          <div className="fixed right-0 top-0 bottom-0 w-full sm:w-96 bg-slate-950 border-l border-slate-800/70 flex flex-col z-50">
            <div className="p-4 border-b border-slate-800/70 flex items-center justify-between">
              <h2 className="font-semibold text-slate-100">YAML Preview</h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigator.clipboard.writeText(builder.yamlPreview)}
                  className="text-slate-400 hover:text-slate-100 text-sm"
                >
                  Copy
                </button>
                <button
                  onClick={() => setShowYaml(false)}
                  className="lg:hidden text-slate-400 hover:text-slate-100 p-1"
                >
                  <ArrowLeft size={18} />
                </button>
              </div>
            </div>
            <pre className="flex-1 overflow-auto p-4 text-xs sm:text-sm text-slate-300 font-mono">
              {builder.yamlPreview}
            </pre>
          </div>
        </>
      )}
    </div>
  )
}

// =============================================================================
// Section Components
// =============================================================================

function BasicInfoSection({ builder }: { builder: ReturnType<typeof useScenarioBuilder> }) {
  return (
    <div className="space-y-6 max-w-2xl">
      {/* ID */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Scenario ID <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={builder.state.id}
          onChange={(e) => builder.setId(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
          placeholder="my-scenario"
          className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
        <p className="mt-1 text-xs text-slate-500">Lowercase letters, numbers, and hyphens only</p>
      </div>

      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Display Name
        </label>
        <input
          type="text"
          value={builder.state.name}
          onChange={(e) => builder.setName(e.target.value)}
          placeholder="My Scenario"
          className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Description
        </label>
        <textarea
          value={builder.state.description}
          onChange={(e) => builder.setDescription(e.target.value)}
          placeholder="Describe what this scenario tests..."
          rows={3}
          className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
      </div>

      {/* Category */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Category
        </label>
        <input
          type="text"
          value={builder.state.category}
          onChange={(e) => builder.setCategory(e.target.value)}
          placeholder="e.g., customer-service, coding, reasoning"
          className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Tags
        </label>
        <input
          type="text"
          value={builder.state.tags.join(', ')}
          onChange={(e) => builder.setTags(e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
          placeholder="tag1, tag2, tag3"
          className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
        <p className="mt-1 text-xs text-slate-500">Comma-separated tags</p>
      </div>
    </div>
  )
}

const VARIABLE_TYPES = [
  { value: 'string', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Yes/No' },
  { value: 'select', label: 'Dropdown' },
]

function VariablesSection({ builder }: { builder: ReturnType<typeof useScenarioBuilder> }) {
  const addVariable = () => {
    builder.addVariable({
      name: `var_${builder.state.variables.length + 1}`,
      label: '',
      type: 'string',
      default: '',
      options: [],
      required: true,
    })
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-slate-400">Scenario Variables</h3>
          <p className="text-xs text-slate-500 mt-1">
            Define variables that can be filled in when running the scenario. Use <code className="text-orange-300">{'{variable_name}'}</code> in prompts.
          </p>
        </div>
        <button
          onClick={addVariable}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-400 hover:bg-orange-300 text-slate-900 rounded font-semibold shrink-0"
        >
          <Plus size={14} /> Add Variable
        </button>
      </div>

      {builder.state.variables.length === 0 ? (
        <div className="text-center py-8 text-slate-500 border border-dashed border-slate-800/70 rounded-lg">
          No variables defined. Add a variable to make your scenario parameterizable.
        </div>
      ) : (
        <div className="space-y-4">
          {builder.state.variables.map((variable, idx) => (
            <VariableCard
              key={idx}
              variable={variable}
              onUpdate={(updated) => builder.updateVariable(idx, updated)}
              onRemove={() => builder.removeVariable(idx)}
            />
          ))}
        </div>
      )}

      {builder.state.variables.length > 0 && (
        <div className="p-4 panel-subtle rounded-lg">
          <h4 className="text-xs font-medium text-slate-400 mb-2">Usage Example</h4>
          <code className="text-sm text-orange-300">
            {builder.state.variables.map(v => `{${v.name}}`).join(', ')}
          </code>
          <p className="text-xs text-slate-500 mt-2">
            Use these placeholders in your prompts, system prompt, or step content.
          </p>
        </div>
      )}
    </div>
  )
}

function VariableCard({
  variable,
  onUpdate,
  onRemove,
}: {
  variable: VariableSpec
  onUpdate: (variable: VariableSpec) => void
  onRemove: () => void
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="panel-card overflow-hidden">
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-800/60"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        <code className="text-orange-300">{`{${variable.name}}`}</code>
        <span className="text-slate-400 text-sm flex-1">
          {variable.label || variable.name}
        </span>
        <span className="text-xs text-slate-500 px-2 py-0.5 bg-slate-800 rounded">
          {variable.type}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onRemove() }}
          className="text-slate-500 hover:text-red-400"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {expanded && (
        <div className="p-4 border-t border-slate-800/70 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Variable Name</label>
              <input
                type="text"
                value={variable.name}
                onChange={(e) => onUpdate({ ...variable, name: e.target.value.replace(/[^a-z0-9_]/gi, '_').toLowerCase() })}
                placeholder="variable_name"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Type</label>
              <select
                value={variable.type}
                onChange={(e) => onUpdate({ ...variable, type: e.target.value as VariableSpec['type'] })}
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              >
                {VARIABLE_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Display Label</label>
            <input
              type="text"
              value={variable.label}
              onChange={(e) => onUpdate({ ...variable, label: e.target.value })}
              placeholder="Human-readable label"
              className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Default Value</label>
              {variable.type === 'boolean' ? (
                <select
                  value={String(variable.default)}
                  onChange={(e) => onUpdate({ ...variable, default: e.target.value === 'true' })}
                  className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
                >
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              ) : variable.type === 'number' ? (
                <input
                  type="number"
                  value={variable.default as number}
                  onChange={(e) => onUpdate({ ...variable, default: Number(e.target.value) })}
                  className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
                />
              ) : variable.type === 'select' && variable.options.length > 0 ? (
                <select
                  value={String(variable.default)}
                  onChange={(e) => onUpdate({ ...variable, default: e.target.value })}
                  className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
                >
                  {variable.options.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={String(variable.default)}
                  onChange={(e) => onUpdate({ ...variable, default: e.target.value })}
                  placeholder="Default value"
                  className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
                />
              )}
            </div>
            <div className="flex items-center sm:pt-5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={variable.required}
                  onChange={(e) => onUpdate({ ...variable, required: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 text-orange-400 focus:ring-orange-400"
                />
                <span className="text-sm text-slate-400">Required</span>
              </label>
            </div>
          </div>

          {variable.type === 'select' && (
            <div>
              <label className="block text-xs text-slate-500 mb-1">Options (comma-separated)</label>
              <input
                type="text"
                value={variable.options.join(', ')}
                onChange={(e) => onUpdate({
                  ...variable,
                  options: e.target.value.split(',').map(o => o.trim()).filter(Boolean),
                })}
                placeholder="option1, option2, option3"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function InteractionSection({ builder }: { builder: ReturnType<typeof useScenarioBuilder> }) {
  return (
    <div className="space-y-6 max-w-2xl">
      {/* Mode Toggle */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Interaction Mode
        </label>
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
          <button
            onClick={() => builder.setInteractionMode('prompt')}
            className={`flex-1 p-3 sm:p-4 rounded-lg border transition-colors ${
              builder.state.interactionMode === 'prompt'
                ? 'border-orange-400/60 bg-orange-500/10'
                : 'border-slate-800/70 hover:border-slate-700'
            }`}
          >
            <div className="font-medium text-slate-100">Single-Turn</div>
            <div className="text-xs sm:text-sm text-slate-400">Simple prompt → response</div>
          </button>
          <button
            onClick={() => builder.setInteractionMode('steps')}
            className={`flex-1 p-3 sm:p-4 rounded-lg border transition-colors ${
              builder.state.interactionMode === 'steps'
                ? 'border-orange-400/60 bg-orange-500/10'
                : 'border-slate-800/70 hover:border-slate-700'
            }`}
          >
            <div className="font-medium text-slate-100">Multi-Turn</div>
            <div className="text-xs sm:text-sm text-slate-400">Conversation steps with tools</div>
          </button>
        </div>
      </div>

      {/* System Prompt (always shown) */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          System Prompt
        </label>
        <textarea
          value={builder.state.systemPrompt}
          onChange={(e) => builder.setSystemPrompt(e.target.value)}
          placeholder="Instructions for the AI agent..."
          rows={4}
          className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400 font-mono text-sm"
        />
      </div>

      {builder.state.interactionMode === 'prompt' ? (
        <>
          {/* Prompt */}
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Prompt <span className="text-red-400">*</span>
            </label>
            <textarea
              value={builder.state.prompt}
              onChange={(e) => builder.setPrompt(e.target.value)}
              placeholder="Enter the prompt for the AI..."
              rows={4}
              className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
            />
          </div>

          {/* Style */}
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Response Style
            </label>
            <select
              value={builder.state.style}
              onChange={(e) => builder.setStyle(e.target.value)}
              className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
            >
              {STYLES.map(style => (
                <option key={style} value={style}>
                  {style || '(None)'}
                </option>
              ))}
            </select>
          </div>
        </>
      ) : (
        <StepsEditor builder={builder} />
      )}
    </div>
  )
}

function StepsEditor({ builder }: { builder: ReturnType<typeof useScenarioBuilder> }) {
  const addStep = (action: StepSpec['action']) => {
    const newStep: StepSpec = {
      id: `step_${builder.state.steps.length + 1}`,
      action,
      params: action === 'inject_user' ? { content: '' } : {},
    }
    builder.addStep(newStep)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <label className="block text-sm font-medium text-slate-400">
          Conversation Steps
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => addStep('inject_user')}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-400 hover:bg-orange-300 text-slate-900 rounded font-semibold"
          >
            <Plus size={14} /> User
          </button>
          <button
            onClick={() => addStep('await_agent')}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-emerald-400 hover:bg-emerald-300 text-slate-900 rounded font-semibold"
          >
            <Plus size={14} /> Agent
          </button>
        </div>
      </div>

      {builder.state.steps.length === 0 ? (
        <div className="text-center py-8 text-slate-500 border border-dashed border-slate-800/70 rounded-lg">
          No steps yet. Add a step to start building your conversation.
        </div>
      ) : (
        <div className="space-y-3">
          {builder.state.steps.map((step, idx) => (
            <StepCard
              key={idx}
              step={step}
              onUpdate={(updated) => builder.updateStep(idx, updated)}
              onRemove={() => builder.removeStep(idx)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function StepCard({
  step,
  onUpdate,
  onRemove,
}: {
  step: StepSpec
  onUpdate: (step: StepSpec) => void
  onRemove: () => void
}) {
  const [expanded, setExpanded] = useState(true)

  const actionColors: Record<string, string> = {
    inject_user: 'bg-orange-400 text-slate-900',
    await_agent: 'bg-emerald-400 text-slate-900',
    await_user: 'bg-amber-300 text-slate-900',
  }

  return (
    <div className="panel-card overflow-hidden">
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-800/60"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        <span className={`px-2 py-0.5 rounded text-xs text-white ${actionColors[step.action] || 'bg-slate-700 text-slate-200'}`}>
          {step.action}
        </span>
        <span className="text-slate-400 text-sm flex-1">
          {step.id}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onRemove() }}
          className="text-slate-500 hover:text-red-400"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {expanded && (
        <div className="p-3 border-t border-slate-800/70 space-y-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Step ID</label>
            <input
              type="text"
              value={step.id}
              onChange={(e) => onUpdate({ ...step, id: e.target.value })}
              className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
            />
          </div>

          {step.action === 'inject_user' && (
            <div>
              <label className="block text-xs text-slate-500 mb-1">Content</label>
              <textarea
                value={(step.params.content as string) || ''}
                onChange={(e) => onUpdate({ ...step, params: { ...step.params, content: e.target.value } })}
                rows={3}
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ToolsSection({
  builder,
  availableTools,
}: {
  builder: ReturnType<typeof useScenarioBuilder>
  availableTools: string[]
}) {
  // Local state for JSON editing - allows typing invalid JSON temporarily
  const [jsonText, setJsonText] = useState(() =>
    JSON.stringify(builder.state.initialState, null, 2) || '{}'
  )
  const [jsonError, setJsonError] = useState<string | null>(null)

  const toggleTool = (tool: string) => {
    if (builder.state.toolsFrom.includes(tool)) {
      builder.setToolsFrom(builder.state.toolsFrom.filter(t => t !== tool))
    } else {
      builder.setToolsFrom([...builder.state.toolsFrom, tool])
    }
  }

  const handleJsonChange = (value: string) => {
    setJsonText(value)
    try {
      const parsed = JSON.parse(value)
      builder.setInitialState(parsed)
      setJsonError(null)
    } catch (e) {
      setJsonError('Invalid JSON')
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Tool Libraries */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Import Tool Libraries
        </label>
        {availableTools.length === 0 ? (
          <div className="text-slate-500 text-sm">
            No tool libraries found in tools/ directory.
          </div>
        ) : (
          <div className="space-y-2">
            {availableTools.map(tool => (
              <label
                key={tool}
                className="flex items-center gap-3 p-3 panel-subtle rounded-lg cursor-pointer hover:border-slate-600/70"
              >
                <input
                  type="checkbox"
                  checked={builder.state.toolsFrom.includes(tool)}
                  onChange={() => toggleTool(tool)}
                  className="w-4 h-4 rounded border-slate-600 text-orange-400 focus:ring-orange-400"
                />
                <code className="text-orange-300">{tool}</code>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Initial State */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Initial State (JSON)
        </label>
        <textarea
          value={jsonText}
          onChange={(e) => handleJsonChange(e.target.value)}
          placeholder='{"key": "value"}'
          rows={4}
          className={`w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 font-mono text-sm ${
            jsonError ? 'focus:ring-red-400 border-red-500/50' : 'focus:ring-orange-400'
          }`}
        />
        {jsonError && (
          <p className="mt-1 text-xs text-red-400">{jsonError}</p>
        )}
      </div>
    </div>
  )
}

function EvaluationSection({ builder }: { builder: ReturnType<typeof useScenarioBuilder> }) {
  return (
    <div className="space-y-6 max-w-3xl">
      {/* Goals */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <label className="block text-sm font-medium text-slate-400">
            Goals (Rule-Based Scoring)
          </label>
          <button
            onClick={() => builder.addGoal({
              id: `goal_${builder.state.goals.length + 1}`,
              name: '',
              description: '',
              points: 10,
              detection: { type: '' },
            })}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-400 hover:bg-orange-300 text-slate-900 rounded font-semibold shrink-0"
          >
            <Plus size={14} /> Add Goal
          </button>
        </div>

        {builder.state.goals.length === 0 ? (
          <div className="text-center py-8 text-slate-500 border border-dashed border-slate-800/70 rounded-lg">
            No goals defined. Add a goal to enable rule-based scoring.
          </div>
        ) : (
          <div className="space-y-4">
            {builder.state.goals.map((goal, idx) => (
              <GoalCard
                key={idx}
                goal={goal}
                onUpdate={(updated) => builder.updateGoal(idx, updated)}
                onRemove={() => builder.removeGoal(idx)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Judge */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <label className="block text-sm font-medium text-slate-400">
            Judge (LLM-Based Scoring)
          </label>
          {!builder.state.judge ? (
            <button
              onClick={() => builder.setJudge({
                type: 'llm',
                model: 'gpt-4o-mini',
                rubric: '',
                pass_threshold: 0.5,
              })}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-emerald-400 hover:bg-emerald-300 text-slate-900 rounded font-semibold shrink-0"
            >
              <Plus size={14} /> Add Judge
            </button>
          ) : (
            <button
              onClick={() => builder.setJudge(null)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-500 hover:bg-red-400 text-slate-900 rounded font-semibold shrink-0"
            >
              <Trash2 size={14} /> Remove Judge
            </button>
          )}
        </div>

        {builder.state.judge && (
          <JudgeCard
            judge={builder.state.judge}
            onUpdate={(updated) => builder.setJudge(updated)}
          />
        )}
      </div>

      {/* Max Score */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Max Score (Optional)
        </label>
        <input
          type="number"
          value={builder.state.maxScore ?? ''}
          onChange={(e) => builder.setMaxScore(e.target.value ? Number(e.target.value) : null)}
          placeholder="Auto-calculated from goals"
          className="w-48 panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
      </div>
    </div>
  )
}

function GoalCard({
  goal,
  onUpdate,
  onRemove,
}: {
  goal: GoalSpec
  onUpdate: (goal: GoalSpec) => void
  onRemove: () => void
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="panel-card overflow-hidden">
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-800/60"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        <span className="text-slate-100 font-medium flex-1">
          {goal.name || goal.id}
        </span>
        <span className="text-emerald-300 text-sm">+{goal.points} pts</span>
        <button
          onClick={(e) => { e.stopPropagation(); onRemove() }}
          className="text-slate-500 hover:text-red-400"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {expanded && (
        <div className="p-4 border-t border-slate-800/70 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Goal ID</label>
              <input
                type="text"
                value={goal.id}
                onChange={(e) => onUpdate({ ...goal, id: e.target.value })}
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Points</label>
              <input
                type="number"
                value={goal.points}
                onChange={(e) => onUpdate({ ...goal, points: Number(e.target.value) })}
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Name</label>
            <input
              type="text"
              value={goal.name}
              onChange={(e) => onUpdate({ ...goal, name: e.target.value })}
              placeholder="Human-readable name"
              className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Detection Type</label>
            <select
              value={goal.detection.type}
              onChange={(e) => onUpdate({ ...goal, detection: { type: e.target.value } })}
              className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
            >
              <option value="">Select type...</option>
              {DETECTION_TYPES.map(dt => (
                <option key={dt.value} value={dt.value}>{dt.label}</option>
              ))}
            </select>
          </div>

          {goal.detection.type === 'tool_called' && (
            <div>
              <label className="block text-xs text-slate-500 mb-1">Tool Name</label>
              <input
                type="text"
                value={(goal.detection.tool as string) || ''}
                onChange={(e) => onUpdate({ ...goal, detection: { ...goal.detection, tool: e.target.value } })}
                placeholder="e.g., check_status"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
          )}

          {goal.detection.type === 'env_state' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">State Key</label>
                <input
                  type="text"
                  value={(goal.detection.key as string) || ''}
                  onChange={(e) => onUpdate({ ...goal, detection: { ...goal.detection, key: e.target.value } })}
                  placeholder="e.g., order_complete"
                  className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Expected Value</label>
                <input
                  type="text"
                  value={String(goal.detection.value ?? '')}
                  onChange={(e) => {
                    let value: unknown = e.target.value
                    if (value === 'true') value = true
                    else if (value === 'false') value = false
                    else if (!isNaN(Number(value))) value = Number(value)
                    onUpdate({ ...goal, detection: { ...goal.detection, value } })
                  }}
                  placeholder="true, false, or value"
                  className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
                />
              </div>
            </div>
          )}

          {goal.detection.type === 'agent_contains' && (
            <div>
              <label className="block text-xs text-slate-500 mb-1">Patterns (comma-separated)</label>
              <input
                type="text"
                value={((goal.detection.patterns as string[]) || []).join(', ')}
                onChange={(e) => onUpdate({
                  ...goal,
                  detection: {
                    ...goal.detection,
                    patterns: e.target.value.split(',').map(p => p.trim()).filter(Boolean),
                  },
                })}
                placeholder="sorry, apologize, my mistake"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function JudgeCard({
  judge,
  onUpdate,
}: {
  judge: JudgeSpec
  onUpdate: (judge: JudgeSpec) => void
}) {
  return (
    <div className="panel-card p-4 space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Judge Type</label>
          <select
            value={judge.type}
            onChange={(e) => onUpdate({ ...judge, type: e.target.value as JudgeSpec['type'] })}
            className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
          >
            <option value="llm">LLM Judge</option>
            <option value="contains">Contains</option>
            <option value="regex">Regex</option>
            <option value="exact">Exact Match</option>
            <option value="length">Length</option>
          </select>
        </div>

        {judge.type === 'llm' && (
          <div>
            <label className="block text-xs text-slate-500 mb-1">Judge Model</label>
            <input
              type="text"
              value={judge.model || ''}
              onChange={(e) => onUpdate({ ...judge, model: e.target.value })}
              placeholder="gpt-4o-mini"
              className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
            />
          </div>
        )}
      </div>

      {judge.type === 'llm' && (
        <div>
          <label className="block text-xs text-slate-500 mb-1">Rubric</label>
          <textarea
            value={judge.rubric || ''}
            onChange={(e) => onUpdate({ ...judge, rubric: e.target.value })}
            placeholder="Score the response from 0.0 to 1.0 based on..."
            rows={4}
            className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
          />
        </div>
      )}

      {(judge.type === 'contains' || judge.type === 'regex' || judge.type === 'exact') && (
        <div>
          <label className="block text-xs text-slate-500 mb-1">Pattern</label>
          <input
            type="text"
            value={judge.pattern || ''}
            onChange={(e) => onUpdate({ ...judge, pattern: e.target.value })}
            placeholder={judge.type === 'regex' ? '\\d+' : 'expected text'}
            className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
          />
        </div>
      )}

      {judge.type === 'length' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Min Length</label>
            <input
              type="number"
              value={judge.min_length ?? ''}
              onChange={(e) => onUpdate({ ...judge, min_length: e.target.value ? Number(e.target.value) : undefined })}
              className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Max Length</label>
            <input
              type="number"
              value={judge.max_length ?? ''}
              onChange={(e) => onUpdate({ ...judge, max_length: e.target.value ? Number(e.target.value) : undefined })}
              className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
            />
          </div>
        </div>
      )}

      <div>
        <label className="block text-xs text-slate-500 mb-1">Pass Threshold (0.0 - 1.0)</label>
        <input
          type="number"
          step="0.1"
          min="0"
          max="1"
          value={judge.pass_threshold ?? 0.5}
          onChange={(e) => onUpdate({ ...judge, pass_threshold: Number(e.target.value) })}
          className="w-32 panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
        />
      </div>
    </div>
  )
}
