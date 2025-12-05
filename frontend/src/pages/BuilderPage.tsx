import { useCallback, useState } from 'react'
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  Edge,
  BackgroundVariant,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Plus, Save, Code, Trash2, CheckCircle } from 'lucide-react'
import { api } from '../lib/api'

// Evaluation check types
type CheckKind = 'contains' | 'regex' | 'count' | 'tool_called' | 'env_state' | 'equals'
type CheckTarget = 'agent_messages' | 'user_messages' | 'all_messages' | 'tool_calls'

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

// Custom node types
const nodeTypes = {
  stepNode: StepNode,
}

// Initial nodes for a new workflow
const initialNodes: Node[] = [
  {
    id: 'start',
    type: 'input',
    data: { label: 'Start' },
    position: { x: 250, y: 0 },
    style: {
      background: '#f97316',
      color: 'white',
      border: 'none',
      borderRadius: '8px',
      padding: '10px 20px',
    },
  },
]

const initialEdges: Edge[] = []

export default function BuilderPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [showYaml, setShowYaml] = useState(false)
  const [moduleName, setModuleName] = useState('new-module')
  const [evaluationChecks, setEvaluationChecks] = useState<EvaluationCheck[]>([])
  const [activeTab, setActiveTab] = useState<'steps' | 'evaluation'>('steps')
  const [selectedCheck, setSelectedCheck] = useState<EvaluationCheck | null>(null)

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
    setSelectedCheck(null) // Deselect check when selecting node
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
    setSelectedCheck(null)
  }, [])

  const addStepNode = useCallback((type: string) => {
    const newNode: Node = {
      id: `step-${Date.now()}`,
      type: 'stepNode',
      data: {
        stepType: type,
        label: getStepLabel(type),
        params: getDefaultParams(type),
      },
      position: {
        x: 250,
        y: (nodes.length) * 120,
      },
    }
    setNodes((nds) => [...nds, newNode])
  }, [nodes, setNodes])

  const addCheck = useCallback((kind: CheckKind) => {
    const newCheck: EvaluationCheck = {
      id: `check-${Date.now()}`,
      name: `${kind}_check`,
      kind,
      expected: kind === 'contains' || kind === 'regex' ? false : true,
      target: kind === 'count' ? 'agent_messages' : kind === 'contains' || kind === 'regex' ? 'agent_messages' : undefined,
    }
    setEvaluationChecks((checks) => [...checks, newCheck])
    setSelectedCheck(newCheck)
  }, [])

  const updateCheck = useCallback((id: string, updates: Partial<EvaluationCheck>) => {
    setEvaluationChecks((checks) =>
      checks.map((c) => (c.id === id ? { ...c, ...updates } : c))
    )
    if (selectedCheck?.id === id) {
      setSelectedCheck((prev) => prev ? { ...prev, ...updates } : null)
    }
  }, [selectedCheck])

  const removeCheck = useCallback((id: string) => {
    setEvaluationChecks((checks) => checks.filter((c) => c.id !== id))
    if (selectedCheck?.id === id) {
      setSelectedCheck(null)
    }
  }, [selectedCheck])

  const generateYaml = useCallback(() => {
    const steps = nodes
      .filter((n) => n.type === 'stepNode')
      .sort((a, b) => a.position.y - b.position.y)
      .map((node, index) => ({
        id: `step_${index + 1}`,
        action: node.data.stepType,
        params: node.data.params,
      }))

    const slug = moduleName.toLowerCase().replace(/\s+/g, '-')

    // Generate evaluation YAML
    const evalYaml = evaluationChecks.length === 0
      ? 'evaluation: []'
      : `evaluation:
${evaluationChecks.map((check) => {
  const lines = [`  - name: "${check.name}"`, `    kind: "${check.kind}"`]
  if (check.target) lines.push(`    target: "${check.target}"`)
  if (check.value !== undefined) lines.push(`    value: "${check.value}"`)
  if (check.expected !== undefined) lines.push(`    expected: ${check.expected}`)
  if (check.pattern) lines.push(`    pattern: "${check.pattern}"`)
  if (check.min !== undefined) lines.push(`    min: ${check.min}`)
  if (check.max !== undefined) lines.push(`    max: ${check.max}`)
  if (check.tool) lines.push(`    tool: "${check.tool}"`)
  if (check.action) lines.push(`    action: "${check.action}"`)
  if (check.key) lines.push(`    key: "${check.key}"`)
  return lines.join('\n')
}).join('\n\n')}`

    const yaml = `id: "${slug}"
name: "${moduleName}"
description: "Created with Sandboxy Builder"
version: "1.0"

variables: []

steps:
${steps.map((step) => `  - id: "${step.id}"
    action: "${step.action}"
    params:
${Object.entries(step.params || {})
  .map(([key, value]) => `      ${key}: ${JSON.stringify(value)}`)
  .join('\n')}`).join('\n\n')}

${evalYaml}
`
    return yaml
  }, [nodes, moduleName, evaluationChecks])

  const handleSave = async () => {
    const yaml = generateYaml()
    try {
      await api.createModule({
        slug: moduleName.toLowerCase().replace(/\s+/g, '-'),
        name: moduleName,
        description: 'Created with Sandboxy Builder',
        yaml_content: yaml,
      })
      alert('Module saved!')
    } catch (err) {
      alert(`Failed to save: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-64 bg-dark-card border-r border-dark-border p-4 flex flex-col">
        {/* Tabs */}
        <div className="flex mb-4 bg-dark-bg rounded-lg p-1">
          <button
            onClick={() => setActiveTab('steps')}
            className={`flex-1 py-1.5 text-sm rounded-md transition-colors ${
              activeTab === 'steps'
                ? 'bg-dark-card text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Steps
          </button>
          <button
            onClick={() => setActiveTab('evaluation')}
            className={`flex-1 py-1.5 text-sm rounded-md transition-colors ${
              activeTab === 'evaluation'
                ? 'bg-dark-card text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Checks
          </button>
        </div>

        {/* Steps Tab */}
        {activeTab === 'steps' && (
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-white mb-4">Add Steps</h2>
            <div className="space-y-2">
              <StepButton
                label="Inject User Message"
                onClick={() => addStepNode('inject_user')}
              />
              <StepButton
                label="Await User Input"
                onClick={() => addStepNode('await_user')}
              />
              <StepButton
                label="Await Agent Response"
                onClick={() => addStepNode('await_agent')}
              />
              <StepButton
                label="Branch"
                onClick={() => addStepNode('branch')}
              />
            </div>
          </div>
        )}

        {/* Evaluation Tab */}
        {activeTab === 'evaluation' && (
          <div className="flex-1 flex flex-col">
            <h2 className="text-lg font-semibold text-white mb-4">Add Checks</h2>
            <div className="space-y-2 mb-4">
              <CheckButton label="Contains" kind="contains" onClick={() => addCheck('contains')} />
              <CheckButton label="Regex" kind="regex" onClick={() => addCheck('regex')} />
              <CheckButton label="Count" kind="count" onClick={() => addCheck('count')} />
              <CheckButton label="Tool Called" kind="tool_called" onClick={() => addCheck('tool_called')} />
              <CheckButton label="Env State" kind="env_state" onClick={() => addCheck('env_state')} />
            </div>

            {/* Check list */}
            {evaluationChecks.length > 0 && (
              <div className="flex-1 overflow-auto">
                <h3 className="text-sm font-medium text-gray-400 mb-2">Checks ({evaluationChecks.length})</h3>
                <div className="space-y-1">
                  {evaluationChecks.map((check) => (
                    <div
                      key={check.id}
                      onClick={() => setSelectedCheck(check)}
                      className={`flex items-center justify-between px-3 py-2 rounded cursor-pointer transition-colors ${
                        selectedCheck?.id === check.id
                          ? 'bg-accent/20 border border-accent/50'
                          : 'bg-dark-bg hover:bg-dark-hover'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <CheckCircle size={14} className="text-accent shrink-0" />
                        <span className="text-sm text-white truncate">{check.name}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          removeCheck(check.id)
                        }}
                        className="text-gray-500 hover:text-red-400 shrink-0"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <hr className="my-4 border-dark-border" />

        <div className="space-y-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Module Name</label>
            <input
              type="text"
              value={moduleName}
              onChange={(e) => setModuleName(e.target.value)}
              onKeyDown={(e) => e.stopPropagation()}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>

          <button
            onClick={() => setShowYaml(!showYaml)}
            className="w-full flex items-center justify-center gap-2 bg-dark-bg hover:bg-dark-hover text-gray-400 py-2 rounded transition-colors"
          >
            <Code size={16} />
            {showYaml ? 'Hide YAML' : 'View YAML'}
          </button>

          <button
            onClick={handleSave}
            className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover text-white py-2 rounded transition-colors"
          >
            <Save size={16} />
            Save Module
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode={null}
          selectionKeyCode={null}
          multiSelectionKeyCode={null}
          style={{ background: '#0a0a0b' }}
        >
          <Controls
            style={{
              background: '#141415',
              border: '1px solid #2a2a2c',
              borderRadius: '8px',
            }}
          />
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1}
            color="#2a2a2c"
          />
        </ReactFlow>

        {/* YAML Preview */}
        {showYaml && (
          <div className="absolute top-4 right-4 w-96 bg-dark-card border border-dark-border rounded-xl p-4 max-h-[80vh] overflow-auto">
            <h3 className="text-sm font-semibold text-white mb-2">YAML Preview</h3>
            <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono">
              {generateYaml()}
            </pre>
          </div>
        )}
      </div>

      {/* Properties panel - for step nodes */}
      {selectedNode && selectedNode.type === 'stepNode' && !selectedCheck && (() => {
        const currentNode = nodes.find(n => n.id === selectedNode.id)
        if (!currentNode) return null
        return (
          <div
            className="w-72 bg-dark-card border-l border-dark-border p-4"
            onKeyDown={(e) => e.stopPropagation()}
            onKeyUp={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-4">Step Properties</h2>
            <NodeProperties
              node={currentNode}
              onChange={(data) => {
                setNodes((nds) =>
                  nds.map((n) =>
                    n.id === currentNode.id ? { ...n, data: { ...n.data, ...data } } : n
                  )
                )
              }}
            />
          </div>
        )
      })()}

      {/* Properties panel - for evaluation checks */}
      {selectedCheck && (
        <div
          className="w-72 bg-dark-card border-l border-dark-border p-4"
          onKeyDown={(e) => e.stopPropagation()}
          onKeyUp={(e) => e.stopPropagation()}
        >
          <h2 className="text-lg font-semibold text-white mb-4">Check Properties</h2>
          <CheckProperties
            check={evaluationChecks.find(c => c.id === selectedCheck.id) || selectedCheck}
            onChange={(updates) => updateCheck(selectedCheck.id, updates)}
          />
        </div>
      )}
    </div>
  )
}

function StepButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 bg-dark-bg hover:bg-dark-hover text-gray-300 px-3 py-2 rounded-lg transition-colors text-sm"
    >
      <Plus size={16} className="text-accent" />
      {label}
    </button>
  )
}

function StepNode({ data }: { data: { label: string; stepType: string } }) {
  const typeColors: Record<string, string> = {
    inject_user: 'border-blue-500',
    await_user: 'border-accent',
    await_agent: 'border-green-500',
    branch: 'border-purple-500',
  }

  return (
    <div
      className={`bg-dark-card border-2 ${typeColors[data.stepType] || 'border-dark-border'} rounded-lg px-4 py-3 min-w-[180px] relative`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-gray-500 !w-3 !h-3 !border-2 !border-dark-card"
      />
      <div className="text-xs text-gray-500 mb-1">{data.stepType}</div>
      <div className="text-white font-medium">{data.label}</div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-accent !w-3 !h-3 !border-2 !border-dark-card"
      />
    </div>
  )
}

function NodeProperties({
  node,
  onChange,
}: {
  node: Node
  onChange: (data: Record<string, unknown>) => void
}) {
  const { stepType, params } = node.data as { stepType: string; params: Record<string, unknown> }

  const updateParam = (key: string, value: unknown) => {
    onChange({ params: { ...params, [key]: value } })
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-1">Step Type</label>
        <div className="text-white bg-dark-bg px-3 py-2 rounded">{stepType}</div>
      </div>

      {stepType === 'inject_user' && (
        <div>
          <label className="block text-sm text-gray-400 mb-1">Message</label>
          <textarea
            value={(params?.content as string) || ''}
            onChange={(e) => updateParam('content', e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent resize-none h-24"
          />
        </div>
      )}

      {stepType === 'await_user' && (
        <div>
          <label className="block text-sm text-gray-400 mb-1">Prompt</label>
          <textarea
            value={(params?.prompt as string) || ''}
            onChange={(e) => updateParam('prompt', e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent resize-none h-24"
          />
        </div>
      )}

      {stepType === 'branch' && (
        <div>
          <label className="block text-sm text-gray-400 mb-1">Condition</label>
          <input
            type="text"
            value={(params?.condition as string) || ''}
            onChange={(e) => updateParam('condition', e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
          />
        </div>
      )}
    </div>
  )
}

function getStepLabel(type: string): string {
  const labels: Record<string, string> = {
    inject_user: 'User Message',
    await_user: 'Wait for Input',
    await_agent: 'Agent Response',
    branch: 'Conditional',
  }
  return labels[type] || type
}

function getDefaultParams(type: string): Record<string, unknown> {
  const defaults: Record<string, Record<string, unknown>> = {
    inject_user: { content: '' },
    await_user: { prompt: 'Enter your message:' },
    await_agent: {},
    branch: { condition: '' },
  }
  return defaults[type] || {}
}

function CheckButton({ label, kind, onClick }: { label: string; kind: CheckKind; onClick: () => void }) {
  const kindColors: Record<CheckKind, string> = {
    contains: 'text-blue-400',
    regex: 'text-purple-400',
    count: 'text-green-400',
    tool_called: 'text-yellow-400',
    env_state: 'text-pink-400',
    equals: 'text-cyan-400',
  }

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 bg-dark-bg hover:bg-dark-hover text-gray-300 px-3 py-2 rounded-lg transition-colors text-sm"
    >
      <CheckCircle size={16} className={kindColors[kind]} />
      {label}
    </button>
  )
}

function CheckProperties({
  check,
  onChange,
}: {
  check: EvaluationCheck
  onChange: (updates: Partial<EvaluationCheck>) => void
}) {
  const kindDescriptions: Record<CheckKind, string> = {
    contains: 'Check if target contains a string',
    regex: 'Check if target matches a pattern',
    count: 'Check count of items',
    tool_called: 'Check if a tool was called',
    env_state: 'Check environment state value',
    equals: 'Check if value equals expected',
  }

  return (
    <div className="space-y-4">
      {/* Name */}
      <div>
        <label className="block text-sm text-gray-400 mb-1">Name</label>
        <input
          type="text"
          value={check.name}
          onChange={(e) => onChange({ name: e.target.value })}
          onKeyDown={(e) => e.stopPropagation()}
          className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
        />
      </div>

      {/* Kind (read-only) */}
      <div>
        <label className="block text-sm text-gray-400 mb-1">Type</label>
        <div className="text-white bg-dark-bg px-3 py-2 rounded text-sm">
          {check.kind}
          <span className="text-gray-500 ml-2 text-xs">{kindDescriptions[check.kind]}</span>
        </div>
      </div>

      {/* Target - for contains, regex, count */}
      {(check.kind === 'contains' || check.kind === 'regex' || check.kind === 'count') && (
        <div>
          <label className="block text-sm text-gray-400 mb-1">Target</label>
          <select
            value={check.target || 'agent_messages'}
            onChange={(e) => onChange({ target: e.target.value as CheckTarget })}
            className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
          >
            <option value="agent_messages">Agent Messages</option>
            <option value="user_messages">User Messages</option>
            <option value="all_messages">All Messages</option>
            <option value="tool_calls">Tool Calls</option>
          </select>
        </div>
      )}

      {/* Value - for contains */}
      {check.kind === 'contains' && (
        <>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Search For</label>
            <input
              type="text"
              value={check.value || ''}
              onChange={(e) => onChange({ value: e.target.value })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="Text to search for..."
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={check.expected === false}
                onChange={(e) => onChange({ expected: !e.target.checked })}
                className="rounded bg-dark-bg border-dark-border"
              />
              Should NOT contain (fail if found)
            </label>
          </div>
        </>
      )}

      {/* Pattern - for regex */}
      {check.kind === 'regex' && (
        <>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Pattern</label>
            <input
              type="text"
              value={check.pattern || ''}
              onChange={(e) => onChange({ pattern: e.target.value })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="Regex pattern..."
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={check.expected === false}
                onChange={(e) => onChange({ expected: !e.target.checked })}
                className="rounded bg-dark-bg border-dark-border"
              />
              Should NOT match (fail if matches)
            </label>
          </div>
        </>
      )}

      {/* Min/Max - for count */}
      {check.kind === 'count' && (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Min</label>
            <input
              type="number"
              value={check.min ?? ''}
              onChange={(e) => onChange({ min: e.target.value ? parseInt(e.target.value) : undefined })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="0"
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Max</label>
            <input
              type="number"
              value={check.max ?? ''}
              onChange={(e) => onChange({ max: e.target.value ? parseInt(e.target.value) : undefined })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="∞"
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
        </div>
      )}

      {/* Tool/Action - for tool_called */}
      {check.kind === 'tool_called' && (
        <>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Tool Name</label>
            <input
              type="text"
              value={check.tool || ''}
              onChange={(e) => onChange({ tool: e.target.value })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="e.g., shopify"
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Action (optional)</label>
            <input
              type="text"
              value={check.action || ''}
              onChange={(e) => onChange({ action: e.target.value })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="e.g., process_refund"
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={check.expected === false}
                onChange={(e) => onChange({ expected: !e.target.checked })}
                className="rounded bg-dark-bg border-dark-border"
              />
              Should NOT be called
            </label>
          </div>
        </>
      )}

      {/* Key/Value - for env_state */}
      {check.kind === 'env_state' && (
        <>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Key (dot notation)</label>
            <input
              type="text"
              value={check.key || ''}
              onChange={(e) => onChange({ key: e.target.value })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="e.g., orders.ORD123.refunded"
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Expected Value</label>
            <input
              type="text"
              value={check.value || ''}
              onChange={(e) => onChange({ value: e.target.value })}
              onKeyDown={(e) => e.stopPropagation()}
              placeholder="true, false, or a value"
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
        </>
      )}
    </div>
  )
}
