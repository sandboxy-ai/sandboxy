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
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Plus, Save, Code } from 'lucide-react'
import { api } from '../lib/api'

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

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
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

  const generateYaml = useCallback(() => {
    const steps = nodes
      .filter((n) => n.type === 'stepNode')
      .sort((a, b) => a.position.y - b.position.y)
      .map((node, index) => ({
        id: `step_${index + 1}`,
        action: node.data.stepType,
        params: node.data.params,
      }))

    const yaml = `name: "${moduleName}"
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

evaluation:
  checks: []
`
    return yaml
  }, [nodes, moduleName])

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
      {/* Sidebar - Step palette */}
      <div className="w-64 bg-dark-card border-r border-dark-border p-4">
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

        <hr className="my-4 border-dark-border" />

        <div className="space-y-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Module Name</label>
            <input
              type="text"
              value={moduleName}
              onChange={(e) => setModuleName(e.target.value)}
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
          nodeTypes={nodeTypes}
          fitView
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

      {/* Properties panel */}
      {selectedNode && selectedNode.type === 'stepNode' && (
        <div className="w-72 bg-dark-card border-l border-dark-border p-4">
          <h2 className="text-lg font-semibold text-white mb-4">Properties</h2>
          <NodeProperties
            node={selectedNode}
            onChange={(data) => {
              setNodes((nds) =>
                nds.map((n) =>
                  n.id === selectedNode.id ? { ...n, data: { ...n.data, ...data } } : n
                )
              )
            }}
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
      className={`bg-dark-card border-2 ${typeColors[data.stepType] || 'border-dark-border'} rounded-lg px-4 py-3 min-w-[180px]`}
    >
      <div className="text-xs text-gray-500 mb-1">{data.stepType}</div>
      <div className="text-white font-medium">{data.label}</div>
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
