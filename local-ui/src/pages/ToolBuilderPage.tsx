import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  Save,
  AlertCircle,
  CheckCircle,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  Wrench,
  Settings,
  Zap,
  Code,
  Server,
  FileCode,
} from 'lucide-react'
import {
  useToolBuilder,
  ToolType,
  ActionSpec,
  ParamSpec,
  SideEffect,
  ConditionalReturn,
  PythonActionSpec,
  McpEnvVar,
} from '../hooks/useToolBuilder'

const PARAM_TYPES = [
  { value: 'string', label: 'String' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'integer', label: 'Integer' },
  { value: 'number', label: 'Number' },
  { value: 'array', label: 'Array' },
]

const TOOL_TYPES: Array<{ value: ToolType; label: string; icon: typeof Wrench; description: string }> = [
  { value: 'yaml', label: 'Mock (YAML)', icon: FileCode, description: 'Declarative tools with params, returns, and side effects' },
  { value: 'python', label: 'Python', icon: Code, description: 'Code-based tools for complex logic' },
  { value: 'mcp', label: 'MCP Server', icon: Server, description: 'Connect to an external MCP server' },
]

export default function ToolBuilderPage() {
  const [showPreview, setShowPreview] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const builder = useToolBuilder()

  const handleSave = async (): Promise<boolean> => {
    if (!builder.isValid) return false

    setSaving(true)
    setSaveMessage(null)

    try {
      const response = await fetch('/api/v1/local/tools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: builder.state.name,
          toolType: builder.state.toolType,
          content: builder.preview,
        }),
      })

      if (response.ok) {
        setSaveMessage({ type: 'success', text: 'Tool saved successfully!' })
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

  const previewLanguage = builder.state.toolType === 'python' ? 'python' : 'yaml'

  return (
    <div className="flex h-full page">
      {/* Main Content */}
      <div className={`flex-1 flex flex-col ${showPreview ? 'mr-[28rem]' : ''}`}>
        {/* Header */}
        <div className="p-6 border-b border-slate-800/70">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="flex items-center gap-2 text-slate-400 hover:text-slate-100"
              >
                <ArrowLeft size={20} />
              </Link>
              <h1 className="text-2xl font-semibold text-slate-100">Tool Builder</h1>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="px-4 py-2 text-slate-400 hover:text-slate-100 border border-slate-700/70 rounded-lg"
              >
                {showPreview ? 'Hide' : 'Show'} Preview
              </button>
              <button
                onClick={() => handleSave()}
                disabled={!builder.isValid || saving}
                className="flex items-center gap-2 bg-orange-400 hover:bg-orange-300 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed text-slate-900 px-4 py-2 rounded-lg font-semibold"
              >
                <Save size={18} />
                {saving ? 'Saving...' : 'Save Tool'}
              </button>
            </div>
          </div>

          {/* Save Message */}
          {saveMessage && (
            <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
              saveMessage.type === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-400/40' : 'bg-red-900/30 text-red-400 border border-red-700/60'
            }`}>
              {saveMessage.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
              {saveMessage.text}
            </div>
          )}

          {/* Validation Errors */}
          {builder.validationErrors.length > 0 && (
            <div className="mt-4 p-3 bg-amber-500/10 border border-amber-400/50 rounded-lg">
              <div className="flex items-center gap-2 text-amber-300 font-medium mb-2">
                <AlertCircle size={18} />
                Validation Issues
              </div>
              <ul className="list-disc list-inside text-amber-200/80 text-sm space-y-1">
                {builder.validationErrors.map((error, idx) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="space-y-8 max-w-3xl">
            {/* Tool Type Selector */}
            <section>
              <h2 className="text-lg font-medium text-slate-100 mb-4">Tool Type</h2>
              <div className="grid grid-cols-3 gap-4">
                {TOOL_TYPES.map(type => (
                  <button
                    key={type.value}
                    onClick={() => builder.setToolType(type.value)}
                    className={`p-4 rounded-lg border text-left transition-colors ${
                      builder.state.toolType === type.value
                        ? 'border-orange-400/60 bg-orange-500/10'
                        : 'border-slate-800/70 hover:border-slate-700'
                    }`}
                  >
                    <type.icon size={24} className={builder.state.toolType === type.value ? 'text-orange-400' : 'text-slate-400'} />
                    <div className="font-medium text-slate-100 mt-2">{type.label}</div>
                    <div className="text-xs text-slate-400 mt-1">{type.description}</div>
                  </button>
                ))}
              </div>
            </section>

            {/* Common Metadata */}
            <section>
              <h2 className="text-lg font-medium text-slate-100 mb-4 flex items-center gap-2">
                <Settings size={20} />
                Basic Info
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    Tool Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={builder.state.name}
                    onChange={(e) => builder.setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                    placeholder="my_custom_tool"
                    className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
                  />
                  <p className="mt-1 text-xs text-slate-500">Lowercase letters, numbers, and underscores only</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    Description
                  </label>
                  <textarea
                    value={builder.state.description}
                    onChange={(e) => builder.setDescription(e.target.value)}
                    placeholder="Describe what this tool does..."
                    rows={2}
                    className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
                  />
                </div>
              </div>
            </section>

            {/* Type-specific sections */}
            {builder.state.toolType === 'yaml' && (
              <YamlToolSection builder={builder} />
            )}
            {builder.state.toolType === 'python' && (
              <PythonToolSection builder={builder} />
            )}
            {builder.state.toolType === 'mcp' && (
              <McpToolSection builder={builder} />
            )}
          </div>
        </div>
      </div>

      {/* Preview Panel */}
      {showPreview && (
        <div className="fixed right-0 top-0 bottom-0 w-[28rem] bg-slate-950/80 border-l border-slate-800/70 flex flex-col">
          <div className="p-4 border-b border-slate-800/70 flex items-center justify-between">
            <h2 className="font-semibold text-slate-100">
              {previewLanguage === 'python' ? 'Python Code' : 'YAML'} Preview
            </h2>
            <button
              onClick={() => navigator.clipboard.writeText(builder.preview)}
              className="text-slate-400 hover:text-slate-100 text-sm"
            >
              Copy
            </button>
          </div>
          <pre className={`flex-1 overflow-auto p-4 text-sm text-slate-300 font-mono ${
            previewLanguage === 'python' ? 'text-xs' : ''
          }`}>
            {builder.preview}
          </pre>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// YAML Tool Section
// =============================================================================

function YamlToolSection({ builder }: { builder: ReturnType<typeof useToolBuilder> }) {
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-slate-100 flex items-center gap-2">
          <Wrench size={20} />
          Actions
        </h2>
        <button
          onClick={builder.addAction}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-400 hover:bg-orange-300 text-slate-900 rounded font-semibold"
        >
          <Plus size={14} /> Add Action
        </button>
      </div>

      {builder.state.actions.length === 0 ? (
        <div className="text-center py-12 text-slate-500 border border-dashed border-slate-800/70 rounded-lg">
          <Wrench size={32} className="mx-auto mb-3 opacity-50" />
          <p>No actions defined yet.</p>
          <p className="text-sm mt-1">Add an action to define what this tool can do.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {builder.state.actions.map((action, idx) => (
            <YamlActionCard
              key={action.id}
              action={action}
              index={idx}
              builder={builder}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function YamlActionCard({
  action,
  index,
  builder,
}: {
  action: ActionSpec
  index: number
  builder: ReturnType<typeof useToolBuilder>
}) {
  const [expanded, setExpanded] = useState(true)

  const updateField = <K extends keyof ActionSpec>(field: K, value: ActionSpec[K]) => {
    builder.updateAction(index, { ...action, [field]: value })
  }

  return (
    <div className="panel-card overflow-hidden">
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-slate-800/60"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        <code className="text-orange-300 font-medium">{action.name || 'unnamed_action'}</code>
        <span className="text-slate-500 text-sm flex-1 truncate">
          {action.description || 'No description'}
        </span>
        <span className="text-xs text-slate-500 px-2 py-0.5 bg-slate-800 rounded">
          {action.params.length} params
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); builder.removeAction(index) }}
          className="text-slate-500 hover:text-red-400"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {expanded && (
        <div className="p-4 border-t border-slate-800/70 space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Action Name *</label>
              <input
                type="text"
                value={action.name}
                onChange={(e) => updateField('name', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                placeholder="action_name"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Description</label>
              <input
                type="text"
                value={action.description}
                onChange={(e) => updateField('description', e.target.value)}
                placeholder="What does this action do?"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
          </div>

          {/* Parameters */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-400">Parameters</label>
              <button
                onClick={() => builder.addParam(index)}
                className="flex items-center gap-1 px-2 py-0.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
              >
                <Plus size={12} /> Add Param
              </button>
            </div>
            {action.params.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No parameters</p>
            ) : (
              <div className="space-y-2">
                {action.params.map((param, pIdx) => (
                  <ParamRow
                    key={pIdx}
                    param={param}
                    onUpdate={(p) => builder.updateParam(index, pIdx, p)}
                    onRemove={() => builder.removeParam(index, pIdx)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Returns */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-400">Returns</label>
              <div className="flex gap-2">
                <button
                  onClick={() => updateField('returnsType', 'simple')}
                  className={`px-2 py-0.5 text-xs rounded ${
                    action.returnsType === 'simple' ? 'bg-orange-400 text-slate-900' : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  Simple
                </button>
                <button
                  onClick={() => {
                    updateField('returnsType', 'conditional')
                    if (!Array.isArray(action.returns)) {
                      updateField('returns', [])
                    }
                  }}
                  className={`px-2 py-0.5 text-xs rounded ${
                    action.returnsType === 'conditional' ? 'bg-orange-400 text-slate-900' : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  Conditional
                </button>
              </div>
            </div>

            {action.returnsType === 'simple' ? (
              <textarea
                value={typeof action.returns === 'string' ? action.returns : ''}
                onChange={(e) => updateField('returns', e.target.value)}
                placeholder="Return value with {param} interpolation"
                rows={2}
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100 font-mono"
              />
            ) : (
              <div className="space-y-2">
                {Array.isArray(action.returns) && action.returns.map((ret, rIdx) => (
                  <ConditionalReturnRow
                    key={rIdx}
                    ret={ret}
                    onUpdate={(r) => builder.updateConditionalReturn(index, rIdx, r)}
                    onRemove={() => builder.removeConditionalReturn(index, rIdx)}
                  />
                ))}
                <button
                  onClick={() => builder.addConditionalReturn(index)}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
                >
                  <Plus size={12} /> Add Condition
                </button>
              </div>
            )}
            <p className="mt-1 text-xs text-slate-500">
              Use <code className="text-orange-300">{'{param_name}'}</code> or <code className="text-orange-300">{'{state.key}'}</code> for interpolation
            </p>
          </div>

          {/* Error Handling */}
          <div>
            <label className="text-xs font-medium text-slate-400 mb-2 block">Error Handling (Optional)</label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                value={action.errorWhen || ''}
                onChange={(e) => updateField('errorWhen', e.target.value)}
                placeholder="error_when condition"
                className="panel-subtle rounded px-3 py-1.5 text-xs text-slate-100 font-mono"
              />
              <input
                type="text"
                value={action.returnsError || ''}
                onChange={(e) => updateField('returnsError', e.target.value)}
                placeholder="Error message"
                className="panel-subtle rounded px-3 py-1.5 text-xs text-slate-100"
              />
            </div>
          </div>

          {/* Side Effects */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-400 flex items-center gap-1">
                <Zap size={12} />
                Side Effects
              </label>
              <button
                onClick={() => builder.addSideEffect(index)}
                className="flex items-center gap-1 px-2 py-0.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
              >
                <Plus size={12} /> Add Effect
              </button>
            </div>
            {action.sideEffects.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No side effects (tool doesn't modify state)</p>
            ) : (
              <div className="space-y-2">
                {action.sideEffects.map((effect, eIdx) => (
                  <SideEffectRow
                    key={eIdx}
                    effect={effect}
                    onUpdate={(e) => builder.updateSideEffect(index, eIdx, e)}
                    onRemove={() => builder.removeSideEffect(index, eIdx)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function ParamRow({
  param,
  onUpdate,
  onRemove,
}: {
  param: ParamSpec
  onUpdate: (param: ParamSpec) => void
  onRemove: () => void
}) {
  const [showEnum, setShowEnum] = useState(param.enum && param.enum.length > 0)

  return (
    <div className="p-2 bg-slate-900/50 rounded space-y-2">
      <div className="flex gap-2 items-start">
        <div className="flex-1 grid grid-cols-4 gap-2">
          <input
            type="text"
            value={param.name}
            onChange={(e) => onUpdate({ ...param, name: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
            placeholder="name"
            className="panel-subtle rounded px-2 py-1 text-xs text-slate-100"
          />
          <select
            value={param.type}
            onChange={(e) => onUpdate({ ...param, type: e.target.value as ParamSpec['type'] })}
            className="panel-subtle rounded px-2 py-1 text-xs text-slate-100"
          >
            {PARAM_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <input
            type="text"
            value={param.description}
            onChange={(e) => onUpdate({ ...param, description: e.target.value })}
            placeholder="description"
            className="panel-subtle rounded px-2 py-1 text-xs text-slate-100"
          />
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={param.required}
                onChange={(e) => onUpdate({ ...param, required: e.target.checked })}
                className="w-3 h-3"
              />
              Req
            </label>
            {param.type === 'string' && (
              <label className="flex items-center gap-1 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={showEnum}
                  onChange={(e) => {
                    setShowEnum(e.target.checked)
                    if (!e.target.checked) {
                      onUpdate({ ...param, enum: undefined })
                    }
                  }}
                  className="w-3 h-3"
                />
                Enum
              </label>
            )}
          </div>
        </div>
        <button onClick={onRemove} className="text-slate-500 hover:text-red-400 p-1">
          <Trash2 size={14} />
        </button>
      </div>

      {showEnum && param.type === 'string' && (
        <input
          type="text"
          value={(param.enum || []).join(', ')}
          onChange={(e) => onUpdate({
            ...param,
            enum: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
          })}
          placeholder="option1, option2, option3"
          className="w-full panel-subtle rounded px-2 py-1 text-xs text-slate-100"
        />
      )}
    </div>
  )
}

function SideEffectRow({
  effect,
  onUpdate,
  onRemove,
}: {
  effect: SideEffect
  onUpdate: (effect: SideEffect) => void
  onRemove: () => void
}) {
  return (
    <div className="flex gap-2 items-center">
      <span className="text-xs text-slate-500">set</span>
      <input
        type="text"
        value={effect.set}
        onChange={(e) => onUpdate({ ...effect, set: e.target.value })}
        placeholder="state_key"
        className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100 font-mono"
      />
      <span className="text-xs text-slate-500">=</span>
      <input
        type="text"
        value={String(effect.value)}
        onChange={(e) => {
          let value: string | boolean | number = e.target.value
          if (value === 'true') value = true
          else if (value === 'false') value = false
          else if (!isNaN(Number(value)) && value !== '') value = Number(value)
          onUpdate({ ...effect, value })
        }}
        placeholder="value"
        className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100 font-mono"
      />
      <button onClick={onRemove} className="text-slate-500 hover:text-red-400 p-1">
        <Trash2 size={14} />
      </button>
    </div>
  )
}

function ConditionalReturnRow({
  ret,
  onUpdate,
  onRemove,
}: {
  ret: ConditionalReturn
  onUpdate: (ret: ConditionalReturn) => void
  onRemove: () => void
}) {
  return (
    <div className="flex gap-2 items-start p-2 bg-slate-900/50 rounded">
      <div className="flex-1 space-y-1">
        <div className="flex gap-2 items-center">
          <span className="text-xs text-slate-500 w-12">when:</span>
          <input
            type="text"
            value={ret.when}
            onChange={(e) => onUpdate({ ...ret, when: e.target.value })}
            placeholder="condition or 'default'"
            className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100 font-mono"
          />
        </div>
        <div className="flex gap-2 items-center">
          <span className="text-xs text-slate-500 w-12">value:</span>
          <input
            type="text"
            value={ret.value}
            onChange={(e) => onUpdate({ ...ret, value: e.target.value })}
            placeholder="Return value"
            className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100 font-mono"
          />
        </div>
      </div>
      <button onClick={onRemove} className="text-slate-500 hover:text-red-400 p-1">
        <Trash2 size={14} />
      </button>
    </div>
  )
}

// =============================================================================
// Python Tool Section
// =============================================================================

function PythonToolSection({ builder }: { builder: ReturnType<typeof useToolBuilder> }) {
  return (
    <section className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Class Name <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={builder.state.pythonClassName}
          onChange={(e) => builder.setPythonClassName(e.target.value)}
          placeholder="MyCustomTool"
          className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
        <p className="mt-1 text-xs text-slate-500">PascalCase class name ending with "Tool"</p>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-slate-100 flex items-center gap-2">
            <Code size={20} />
            Actions
          </h3>
          <button
            onClick={builder.addPythonAction}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-400 hover:bg-orange-300 text-slate-900 rounded font-semibold"
          >
            <Plus size={14} /> Add Action
          </button>
        </div>

        {builder.state.pythonActions.length === 0 ? (
          <div className="text-center py-8 text-slate-500 border border-dashed border-slate-800/70 rounded-lg">
            <p>Define the actions your Python tool will support.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {builder.state.pythonActions.map((action, idx) => (
              <PythonActionCard
                key={idx}
                action={action}
                index={idx}
                builder={builder}
              />
            ))}
          </div>
        )}
      </div>

      <div className="p-4 panel-subtle rounded-lg">
        <h4 className="text-sm font-medium text-slate-300 mb-2">What happens when you save:</h4>
        <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
          <li>A Python file will be created in your <code className="text-orange-300">tools/</code> directory</li>
          <li>The file includes TODO comments where you need to add your logic</li>
          <li>The tool will be automatically discovered and available to use</li>
        </ul>
      </div>
    </section>
  )
}

function PythonActionCard({
  action,
  index,
  builder,
}: {
  action: PythonActionSpec
  index: number
  builder: ReturnType<typeof useToolBuilder>
}) {
  const [expanded, setExpanded] = useState(true)

  const updateAction = (updates: Partial<PythonActionSpec>) => {
    builder.updatePythonAction(index, { ...action, ...updates })
  }

  const addParam = () => {
    updateAction({
      params: [...action.params, { name: '', type: 'string', description: '' }],
    })
  }

  const updateParam = (pIdx: number, updates: Partial<{ name: string; type: string; description: string }>) => {
    updateAction({
      params: action.params.map((p, i) => i === pIdx ? { ...p, ...updates } : p),
    })
  }

  const removeParam = (pIdx: number) => {
    updateAction({
      params: action.params.filter((_, i) => i !== pIdx),
    })
  }

  return (
    <div className="panel-card overflow-hidden">
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-slate-800/60"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        <code className="text-orange-300 font-medium">{action.name || 'unnamed'}</code>
        <span className="text-slate-500 text-sm flex-1 truncate">
          {action.description || 'No description'}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); builder.removePythonAction(index) }}
          className="text-slate-500 hover:text-red-400"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {expanded && (
        <div className="p-4 border-t border-slate-800/70 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Action Name</label>
              <input
                type="text"
                value={action.name}
                onChange={(e) => updateAction({ name: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                placeholder="do_something"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Description</label>
              <input
                type="text"
                value={action.description}
                onChange={(e) => updateAction({ description: e.target.value })}
                placeholder="What does this do?"
                className="w-full panel-subtle rounded px-3 py-1.5 text-sm text-slate-100"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-400">Parameters</label>
              <button
                onClick={addParam}
                className="flex items-center gap-1 px-2 py-0.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
              >
                <Plus size={12} /> Add
              </button>
            </div>
            {action.params.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No parameters</p>
            ) : (
              <div className="space-y-2">
                {action.params.map((param, pIdx) => (
                  <div key={pIdx} className="flex gap-2 items-center">
                    <input
                      type="text"
                      value={param.name}
                      onChange={(e) => updateParam(pIdx, { name: e.target.value })}
                      placeholder="name"
                      className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100"
                    />
                    <select
                      value={param.type}
                      onChange={(e) => updateParam(pIdx, { type: e.target.value })}
                      className="panel-subtle rounded px-2 py-1 text-xs text-slate-100"
                    >
                      <option value="string">string</option>
                      <option value="number">number</option>
                      <option value="boolean">boolean</option>
                      <option value="dict">dict</option>
                      <option value="list">list</option>
                    </select>
                    <input
                      type="text"
                      value={param.description}
                      onChange={(e) => updateParam(pIdx, { description: e.target.value })}
                      placeholder="description"
                      className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100"
                    />
                    <button onClick={() => removeParam(pIdx)} className="text-slate-500 hover:text-red-400 p-1">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// MCP Tool Section
// =============================================================================

function McpToolSection({ builder }: { builder: ReturnType<typeof useToolBuilder> }) {
  return (
    <section className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Transport Type
        </label>
        <div className="flex gap-4">
          {(['stdio', 'sse', 'http'] as const).map(transport => (
            <button
              key={transport}
              onClick={() => builder.setMcpTransport(transport)}
              className={`flex-1 p-3 rounded-lg border text-center transition-colors ${
                builder.state.mcpTransport === transport
                  ? 'border-orange-400/60 bg-orange-500/10'
                  : 'border-slate-800/70 hover:border-slate-700'
              }`}
            >
              <div className="font-medium text-slate-100">{transport.toUpperCase()}</div>
              <div className="text-xs text-slate-400 mt-1">
                {transport === 'stdio' ? 'Local process' : transport === 'sse' ? 'Server-sent events' : 'HTTP endpoint'}
              </div>
            </button>
          ))}
        </div>
      </div>

      {builder.state.mcpTransport === 'stdio' ? (
        <>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Command <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={builder.state.mcpCommand}
              onChange={(e) => builder.setMcpCommand(e.target.value)}
              placeholder="python -m my_mcp_server"
              className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400 font-mono"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Arguments (optional)
            </label>
            <input
              type="text"
              value={builder.state.mcpArgs.join(' ')}
              onChange={(e) => builder.setMcpArgs(e.target.value.split(' ').filter(Boolean))}
              placeholder="--port 8080 --debug"
              className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400 font-mono"
            />
          </div>
        </>
      ) : (
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            URL <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={builder.state.mcpUrl}
            onChange={(e) => builder.setMcpUrl(e.target.value)}
            placeholder="https://api.example.com/mcp"
            className="w-full panel-subtle px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-400 font-mono"
          />
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-slate-400">Environment Variables</label>
          <button
            onClick={builder.addMcpEnvVar}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
          >
            <Plus size={12} /> Add
          </button>
        </div>
        {builder.state.mcpEnv.length === 0 ? (
          <p className="text-xs text-slate-500 italic">No environment variables</p>
        ) : (
          <div className="space-y-2">
            {builder.state.mcpEnv.map((envVar, idx) => (
              <McpEnvVarRow
                key={idx}
                envVar={envVar}
                onUpdate={(e) => builder.updateMcpEnvVar(idx, e)}
                onRemove={() => builder.removeMcpEnvVar(idx)}
              />
            ))}
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Use <code className="text-orange-300">{'${ENV_VAR}'}</code> to reference system environment variables
        </p>
      </div>

      <div className="p-4 panel-subtle rounded-lg">
        <h4 className="text-sm font-medium text-slate-300 mb-2">How MCP tools work:</h4>
        <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
          <li>MCP servers expose tools via the Model Context Protocol</li>
          <li>The server will be started/connected when the tool is used</li>
          <li>Tools are automatically discovered from the server</li>
        </ul>
      </div>
    </section>
  )
}

function McpEnvVarRow({
  envVar,
  onUpdate,
  onRemove,
}: {
  envVar: McpEnvVar
  onUpdate: (envVar: McpEnvVar) => void
  onRemove: () => void
}) {
  return (
    <div className="flex gap-2 items-center">
      <input
        type="text"
        value={envVar.key}
        onChange={(e) => onUpdate({ ...envVar, key: e.target.value })}
        placeholder="KEY"
        className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100 font-mono"
      />
      <span className="text-slate-500">=</span>
      <input
        type="text"
        value={envVar.value}
        onChange={(e) => onUpdate({ ...envVar, value: e.target.value })}
        placeholder="value or ${ENV_VAR}"
        className="flex-1 panel-subtle rounded px-2 py-1 text-xs text-slate-100 font-mono"
      />
      <button onClick={onRemove} className="text-slate-500 hover:text-red-400 p-1">
        <Trash2 size={14} />
      </button>
    </div>
  )
}
