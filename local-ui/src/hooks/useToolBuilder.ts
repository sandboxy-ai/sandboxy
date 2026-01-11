/**
 * State management for the tool builder.
 * Supports YAML mock tools, Python tools, and MCP server configs.
 */

import { useState, useCallback, useMemo } from 'react'
import yaml from 'js-yaml'

// Tool type
export type ToolType = 'yaml' | 'python' | 'mcp'

// =============================================================================
// YAML Tool Types
// =============================================================================

export interface ParamSpec {
  name: string
  type: 'string' | 'boolean' | 'integer' | 'number' | 'array'
  required: boolean
  default?: string | boolean | number
  description: string
  enum?: string[]
}

export interface SideEffect {
  set: string
  value: string | boolean | number
}

export interface ConditionalReturn {
  when: string
  value: string
}

export interface ActionSpec {
  id: string
  name: string
  description: string
  params: ParamSpec[]
  returns: string | ConditionalReturn[]
  returnsType: 'simple' | 'conditional'
  errorWhen?: string
  returnsError?: string
  sideEffects: SideEffect[]
}

// =============================================================================
// Python Tool Types
// =============================================================================

export interface PythonActionSpec {
  name: string
  description: string
  params: Array<{ name: string; type: string; description: string }>
}

// =============================================================================
// MCP Server Types
// =============================================================================

export type McpTransport = 'stdio' | 'sse' | 'http'

export interface McpEnvVar {
  key: string
  value: string
}

// =============================================================================
// Combined State
// =============================================================================

export interface ToolBuilderState {
  // Tool type
  toolType: ToolType

  // Common metadata
  name: string
  description: string

  // YAML tool state
  actions: ActionSpec[]

  // Python tool state
  pythonClassName: string
  pythonActions: PythonActionSpec[]

  // MCP server state
  mcpTransport: McpTransport
  mcpCommand: string
  mcpArgs: string[]
  mcpUrl: string
  mcpEnv: McpEnvVar[]
}

const initialState: ToolBuilderState = {
  toolType: 'yaml',
  name: '',
  description: '',
  // YAML
  actions: [],
  // Python
  pythonClassName: '',
  pythonActions: [],
  // MCP
  mcpTransport: 'stdio',
  mcpCommand: '',
  mcpArgs: [],
  mcpUrl: '',
  mcpEnv: [],
}

export interface UseToolBuilderResult {
  state: ToolBuilderState
  preview: string  // YAML or Python code preview
  isValid: boolean
  validationErrors: string[]

  // Tool type
  setToolType: (type: ToolType) => void

  // Metadata
  setName: (name: string) => void
  setDescription: (description: string) => void

  // YAML Actions
  addAction: () => void
  updateAction: (index: number, action: ActionSpec) => void
  removeAction: (index: number) => void

  // YAML Action helpers
  addParam: (actionIndex: number) => void
  updateParam: (actionIndex: number, paramIndex: number, param: ParamSpec) => void
  removeParam: (actionIndex: number, paramIndex: number) => void

  addSideEffect: (actionIndex: number) => void
  updateSideEffect: (actionIndex: number, effectIndex: number, effect: SideEffect) => void
  removeSideEffect: (actionIndex: number, effectIndex: number) => void

  addConditionalReturn: (actionIndex: number) => void
  updateConditionalReturn: (actionIndex: number, returnIndex: number, ret: ConditionalReturn) => void
  removeConditionalReturn: (actionIndex: number, returnIndex: number) => void

  // Python tool helpers
  setPythonClassName: (name: string) => void
  addPythonAction: () => void
  updatePythonAction: (index: number, action: PythonActionSpec) => void
  removePythonAction: (index: number) => void

  // MCP server helpers
  setMcpTransport: (transport: McpTransport) => void
  setMcpCommand: (command: string) => void
  setMcpArgs: (args: string[]) => void
  setMcpUrl: (url: string) => void
  addMcpEnvVar: () => void
  updateMcpEnvVar: (index: number, envVar: McpEnvVar) => void
  removeMcpEnvVar: (index: number) => void

  // Actions
  reset: () => void
  loadFromYaml: (yamlContent: string) => void
}

export function useToolBuilder(): UseToolBuilderResult {
  const [state, setState] = useState<ToolBuilderState>(initialState)

  // Generate preview based on tool type
  const preview = useMemo(() => {
    if (state.toolType === 'yaml') {
      return generateYamlPreview(state)
    } else if (state.toolType === 'python') {
      return generatePythonPreview(state)
    } else {
      return generateMcpPreview(state)
    }
  }, [state])

  // Validation based on tool type
  const validationErrors = useMemo(() => {
    const errors: string[] = []

    // Common validation
    if (!state.name) {
      errors.push('Tool name is required')
    } else if (!/^[a-z0-9_]+$/.test(state.name)) {
      errors.push('Name must be lowercase letters, numbers, and underscores only')
    }

    if (state.toolType === 'yaml') {
      if (state.actions.length === 0) {
        errors.push('At least one action is required')
      }
      state.actions.forEach((action, idx) => {
        if (!action.name) {
          errors.push(`Action ${idx + 1}: Name is required`)
        } else if (!/^[a-z0-9_]+$/.test(action.name)) {
          errors.push(`Action ${idx + 1}: Name must be lowercase letters, numbers, and underscores`)
        }
        // Description is optional - just a warning, not blocking
        action.params.forEach((param, pIdx) => {
          if (!param.name) {
            errors.push(`Action ${idx + 1}, Param ${pIdx + 1}: Name is required`)
          }
        })
      })
    } else if (state.toolType === 'python') {
      if (!state.pythonClassName) {
        errors.push('Class name is required')
      } else if (!/^[A-Z][a-zA-Z0-9]*Tool$/.test(state.pythonClassName)) {
        errors.push('Class name should be PascalCase ending with "Tool" (e.g., MyCustomTool)')
      }
      if (state.pythonActions.length === 0) {
        errors.push('At least one action is required')
      }
    } else if (state.toolType === 'mcp') {
      if (state.mcpTransport === 'stdio' && !state.mcpCommand) {
        errors.push('Command is required for stdio transport')
      }
      if ((state.mcpTransport === 'sse' || state.mcpTransport === 'http') && !state.mcpUrl) {
        errors.push('URL is required for HTTP/SSE transport')
      }
    }

    return errors
  }, [state])

  const isValid = validationErrors.length === 0

  // Tool type setter
  const setToolType = useCallback((toolType: ToolType) => {
    setState(prev => ({ ...prev, toolType }))
  }, [])

  // Metadata setters
  const setName = useCallback((name: string) => {
    setState(prev => ({ ...prev, name }))
  }, [])

  const setDescription = useCallback((description: string) => {
    setState(prev => ({ ...prev, description }))
  }, [])

  // Action management
  const addAction = useCallback(() => {
    setState(prev => ({
      ...prev,
      actions: [...prev.actions, {
        id: `action_${Date.now()}`,
        name: `action_${prev.actions.length + 1}`,
        description: '',
        params: [],
        returns: '',
        returnsType: 'simple',
        sideEffects: [],
      }],
    }))
  }, [])

  const updateAction = useCallback((index: number, action: ActionSpec) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((a, i) => (i === index ? action : a)),
    }))
  }, [])

  const removeAction = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.filter((_, i) => i !== index),
    }))
  }, [])

  // Param helpers
  const addParam = useCallback((actionIndex: number) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        return {
          ...action,
          params: [...action.params, {
            name: `param_${action.params.length + 1}`,
            type: 'string',
            required: true,
            description: '',
          }],
        }
      }),
    }))
  }, [])

  const updateParam = useCallback((actionIndex: number, paramIndex: number, param: ParamSpec) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        return {
          ...action,
          params: action.params.map((p, j) => (j === paramIndex ? param : p)),
        }
      }),
    }))
  }, [])

  const removeParam = useCallback((actionIndex: number, paramIndex: number) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        return {
          ...action,
          params: action.params.filter((_, j) => j !== paramIndex),
        }
      }),
    }))
  }, [])

  // Side effect helpers
  const addSideEffect = useCallback((actionIndex: number) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        return {
          ...action,
          sideEffects: [...action.sideEffects, { set: '', value: '' }],
        }
      }),
    }))
  }, [])

  const updateSideEffect = useCallback((actionIndex: number, effectIndex: number, effect: SideEffect) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        return {
          ...action,
          sideEffects: action.sideEffects.map((e, j) => (j === effectIndex ? effect : e)),
        }
      }),
    }))
  }, [])

  const removeSideEffect = useCallback((actionIndex: number, effectIndex: number) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        return {
          ...action,
          sideEffects: action.sideEffects.filter((_, j) => j !== effectIndex),
        }
      }),
    }))
  }, [])

  // Conditional return helpers
  const addConditionalReturn = useCallback((actionIndex: number) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        const currentReturns = Array.isArray(action.returns) ? action.returns : []
        return {
          ...action,
          returnsType: 'conditional' as const,
          returns: [...currentReturns, { when: '', value: '' }],
        }
      }),
    }))
  }, [])

  const updateConditionalReturn = useCallback((actionIndex: number, returnIndex: number, ret: ConditionalReturn) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        if (!Array.isArray(action.returns)) return action
        return {
          ...action,
          returns: action.returns.map((r, j) => (j === returnIndex ? ret : r)),
        }
      }),
    }))
  }, [])

  const removeConditionalReturn = useCallback((actionIndex: number, returnIndex: number) => {
    setState(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => {
        if (i !== actionIndex) return action
        if (!Array.isArray(action.returns)) return action
        const newReturns = action.returns.filter((_, j) => j !== returnIndex)
        return {
          ...action,
          returnsType: newReturns.length > 0 ? 'conditional' : 'simple',
          returns: newReturns.length > 0 ? newReturns : '',
        }
      }),
    }))
  }, [])

  // Python tool helpers
  const setPythonClassName = useCallback((pythonClassName: string) => {
    setState(prev => ({ ...prev, pythonClassName }))
  }, [])

  const addPythonAction = useCallback(() => {
    setState(prev => ({
      ...prev,
      pythonActions: [...prev.pythonActions, {
        name: `action_${prev.pythonActions.length + 1}`,
        description: '',
        params: [],
      }],
    }))
  }, [])

  const updatePythonAction = useCallback((index: number, action: PythonActionSpec) => {
    setState(prev => ({
      ...prev,
      pythonActions: prev.pythonActions.map((a, i) => (i === index ? action : a)),
    }))
  }, [])

  const removePythonAction = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      pythonActions: prev.pythonActions.filter((_, i) => i !== index),
    }))
  }, [])

  // MCP server helpers
  const setMcpTransport = useCallback((mcpTransport: McpTransport) => {
    setState(prev => ({ ...prev, mcpTransport }))
  }, [])

  const setMcpCommand = useCallback((mcpCommand: string) => {
    setState(prev => ({ ...prev, mcpCommand }))
  }, [])

  const setMcpArgs = useCallback((mcpArgs: string[]) => {
    setState(prev => ({ ...prev, mcpArgs }))
  }, [])

  const setMcpUrl = useCallback((mcpUrl: string) => {
    setState(prev => ({ ...prev, mcpUrl }))
  }, [])

  const addMcpEnvVar = useCallback(() => {
    setState(prev => ({
      ...prev,
      mcpEnv: [...prev.mcpEnv, { key: '', value: '' }],
    }))
  }, [])

  const updateMcpEnvVar = useCallback((index: number, envVar: McpEnvVar) => {
    setState(prev => ({
      ...prev,
      mcpEnv: prev.mcpEnv.map((e, i) => (i === index ? envVar : e)),
    }))
  }, [])

  const removeMcpEnvVar = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      mcpEnv: prev.mcpEnv.filter((_, i) => i !== index),
    }))
  }, [])

  // Actions
  const reset = useCallback(() => {
    setState(initialState)
  }, [])

  const loadFromYaml = useCallback((yamlContent: string) => {
    try {
      const data = yaml.load(yamlContent) as Record<string, unknown>

      const actions: ActionSpec[] = []
      const toolsDef = data.tools as Record<string, Record<string, unknown>> | undefined

      if (toolsDef) {
        for (const [actionName, actionDef] of Object.entries(toolsDef)) {
          const params: ParamSpec[] = []
          const paramsDef = actionDef.params as Record<string, Record<string, unknown>> | undefined

          if (paramsDef) {
            for (const [paramName, paramDef] of Object.entries(paramsDef)) {
              params.push({
                name: paramName,
                type: (paramDef.type as ParamSpec['type']) || 'string',
                required: paramDef.required !== false,
                default: paramDef.default as string | boolean | number | undefined,
                description: (paramDef.description as string) || '',
                enum: paramDef.enum as string[] | undefined,
              })
            }
          }

          const sideEffects: SideEffect[] = []
          const effectsDef = actionDef.side_effects as Array<{ set: string; value: unknown }> | undefined
          if (effectsDef) {
            for (const effect of effectsDef) {
              sideEffects.push({
                set: effect.set,
                value: effect.value as string | boolean | number,
              })
            }
          }

          const returnsDef = actionDef.returns
          let returns: string | ConditionalReturn[] = ''
          let returnsType: 'simple' | 'conditional' = 'simple'

          if (Array.isArray(returnsDef)) {
            returnsType = 'conditional'
            returns = returnsDef.map(r => ({
              when: r.when as string,
              value: r.value as string,
            }))
          } else if (typeof returnsDef === 'string') {
            returns = returnsDef
          }

          actions.push({
            id: `action_${Date.now()}_${actionName}`,
            name: actionName,
            description: (actionDef.description as string) || '',
            params,
            returns,
            returnsType,
            errorWhen: actionDef.error_when as string | undefined,
            returnsError: actionDef.returns_error as string | undefined,
            sideEffects,
          })
        }
      }

      setState(prev => ({
        ...prev,
        toolType: 'yaml',
        name: (data.name as string) || '',
        description: (data.description as string) || '',
        actions,
      }))
    } catch (e) {
      console.error('Failed to parse YAML:', e)
    }
  }, [])

  return {
    state,
    preview,
    isValid,
    validationErrors,
    setToolType,
    setName,
    setDescription,
    addAction,
    updateAction,
    removeAction,
    addParam,
    updateParam,
    removeParam,
    addSideEffect,
    updateSideEffect,
    removeSideEffect,
    addConditionalReturn,
    updateConditionalReturn,
    removeConditionalReturn,
    setPythonClassName,
    addPythonAction,
    updatePythonAction,
    removePythonAction,
    setMcpTransport,
    setMcpCommand,
    setMcpArgs,
    setMcpUrl,
    addMcpEnvVar,
    updateMcpEnvVar,
    removeMcpEnvVar,
    reset,
    loadFromYaml,
  }
}

// =============================================================================
// Preview Generators
// =============================================================================

function generateYamlPreview(state: ToolBuilderState): string {
  const output: Record<string, unknown> = {}

  if (state.name) output.name = state.name
  if (state.description) output.description = state.description

  if (state.actions.length > 0) {
    const tools: Record<string, unknown> = {}

    for (const action of state.actions) {
      const actionDef: Record<string, unknown> = {}

      if (action.description) actionDef.description = action.description

      if (action.params.length > 0) {
        const params: Record<string, unknown> = {}
        for (const param of action.params) {
          const paramDef: Record<string, unknown> = { type: param.type }
          if (param.required) paramDef.required = true
          if (param.default !== undefined && param.default !== '') paramDef.default = param.default
          if (param.description) paramDef.description = param.description
          if (param.enum && param.enum.length > 0) paramDef.enum = param.enum
          params[param.name] = paramDef
        }
        actionDef.params = params
      }

      if (action.errorWhen) actionDef.error_when = action.errorWhen
      if (action.returnsError) actionDef.returns_error = action.returnsError

      if (action.returnsType === 'conditional' && Array.isArray(action.returns)) {
        actionDef.returns = action.returns.map(r => ({ when: r.when, value: r.value }))
      } else if (typeof action.returns === 'string' && action.returns) {
        actionDef.returns = action.returns
      }

      if (action.sideEffects.length > 0) {
        actionDef.side_effects = action.sideEffects.map(e => ({ set: e.set, value: e.value }))
      }

      tools[action.name] = actionDef
    }

    output.tools = tools
  }

  return yaml.dump(output, { lineWidth: -1, noRefs: true })
}

function generatePythonPreview(state: ToolBuilderState): string {
  const className = state.pythonClassName || 'MyCustomTool'
  const toolName = state.name || 'my_custom_tool'

  let code = `"""${state.description || 'Custom tool implementation.'}

Tool name: ${toolName}
"""

from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult


class ${className}(BaseTool):
    """${state.description || 'Custom tool implementation.'}"""

    def __init__(self, config: ToolConfig) -> None:
        super().__init__(config)
        # Add your initialization here
        self.data: dict = {}

    def invoke(self, action: str, args: dict, env_state: dict) -> ToolResult:
        """Handle tool actions."""
        handlers = {
`

  for (const action of state.pythonActions) {
    code += `            "${action.name}": self._${action.name},\n`
  }

  code += `        }

        handler = handlers.get(action)
        if not handler:
            return ToolResult(success=False, error=f"Unknown action: {action}")

        return handler(args, env_state)
`

  for (const action of state.pythonActions) {
    const paramDocs = action.params.map(p => `            ${p.name}: ${p.description || p.type}`).join('\n')

    code += `
    def _${action.name}(self, args: dict, env_state: dict) -> ToolResult:
        """${action.description || 'TODO: Add description'}

        Args:
${paramDocs || '            (no parameters)'}
        """
        # TODO: Implement this action
        ${action.params.map(p => `${p.name} = args.get("${p.name}")`).join('\n        ')}

        return ToolResult(success=True, data={"result": "TODO"})
`
  }

  code += `
    def get_actions(self) -> list[dict]:
        """Define available actions with their schemas."""
        return [
`

  for (const action of state.pythonActions) {
    code += `            {
                "name": "${action.name}",
                "description": "${action.description || ''}",
                "parameters": {
                    "type": "object",
                    "properties": {
`
    for (const param of action.params) {
      code += `                        "${param.name}": {"type": "${param.type}", "description": "${param.description || ''}"},\n`
    }
    code += `                    },
                    "required": [${action.params.map(p => `"${p.name}"`).join(', ')}],
                },
            },
`
  }

  code += `        ]
`

  return code
}

function generateMcpPreview(state: ToolBuilderState): string {
  const output: Record<string, unknown> = {
    name: state.name || 'my_mcp_server',
    type: 'mcp',
    transport: state.mcpTransport,
  }

  if (state.description) output.description = state.description

  if (state.mcpTransport === 'stdio') {
    if (state.mcpCommand) output.command = state.mcpCommand
    if (state.mcpArgs.length > 0) output.args = state.mcpArgs
  } else {
    if (state.mcpUrl) output.url = state.mcpUrl
  }

  if (state.mcpEnv.length > 0) {
    const env: Record<string, string> = {}
    for (const e of state.mcpEnv) {
      if (e.key) env[e.key] = e.value
    }
    if (Object.keys(env).length > 0) output.env = env
  }

  return yaml.dump(output, { lineWidth: -1, noRefs: true })
}
