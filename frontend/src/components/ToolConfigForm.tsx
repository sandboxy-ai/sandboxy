import { useState, useCallback } from 'react'
import { ChevronDown, ChevronRight, Plus, Trash2 } from 'lucide-react'
import type { ToolConfigField } from '../lib/api'

interface ToolConfigFormProps {
  schema: Record<string, ToolConfigField>
  values: Record<string, unknown>
  onChange: (values: Record<string, unknown>) => void
  className?: string
}

export function ToolConfigForm({ schema, values, onChange, className = '' }: ToolConfigFormProps) {
  return (
    <div className={`space-y-4 ${className}`}>
      {Object.entries(schema).map(([key, field]) => (
        <ConfigField
          key={key}
          field={field}
          value={values[key] ?? field.default}
          onChange={(newValue) => onChange({ ...values, [key]: newValue })}
        />
      ))}
    </div>
  )
}

interface ConfigFieldProps {
  field: ToolConfigField
  value: unknown
  onChange: (value: unknown) => void
  depth?: number
}

function ConfigField({ field, value, onChange, depth = 0 }: ConfigFieldProps) {
  const [expanded, setExpanded] = useState(depth === 0)

  const renderInput = () => {
    switch (field.type) {
      case 'number':
        return (
          <NumberField
            value={value as number | undefined}
            onChange={onChange}
            min={field.min}
            max={field.max}
            step={field.step}
          />
        )

      case 'string':
        return (
          <input
            type="text"
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
          />
        )

      case 'boolean':
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => onChange(e.target.checked)}
              className="rounded bg-dark-bg border-dark-border"
            />
            <span className="text-sm text-gray-400">Enabled</span>
          </label>
        )

      case 'select':
        return (
          <select
            value={(value as string) ?? field.options?.[0] ?? ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
          >
            {field.options?.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        )

      case 'object':
        return (
          <ObjectField
            value={(value as Record<string, unknown>) ?? {}}
            onChange={onChange}
            depth={depth}
          />
        )

      case 'array':
        return (
          <ArrayField
            value={(value as unknown[]) ?? []}
            onChange={onChange}
            itemSchema={field.items}
          />
        )

      default:
        return (
          <textarea
            value={typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value ?? '')}
            onChange={(e) => {
              try {
                onChange(JSON.parse(e.target.value))
              } catch {
                onChange(e.target.value)
              }
            }}
            rows={4}
            className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-accent resize-none"
          />
        )
    }
  }

  // For complex types (object/array), show as collapsible section
  if (field.type === 'object' || field.type === 'array') {
    return (
      <div className="border border-dark-border rounded-lg overflow-hidden">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-2 px-4 py-3 bg-dark-card hover:bg-dark-hover transition-colors text-left"
        >
          {expanded ? (
            <ChevronDown size={16} className="text-gray-400" />
          ) : (
            <ChevronRight size={16} className="text-gray-400" />
          )}
          <div className="flex-1">
            <div className="text-sm font-medium text-white">{field.label}</div>
            {field.description && (
              <div className="text-xs text-gray-500 mt-0.5">{field.description}</div>
            )}
          </div>
          <span className="text-xs text-gray-500 bg-dark-bg px-2 py-1 rounded">
            {field.type}
          </span>
        </button>
        {expanded && (
          <div className="p-4 border-t border-dark-border bg-dark-bg/50">
            {renderInput()}
          </div>
        )}
      </div>
    )
  }

  // Simple fields
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-2">
        {field.label}
        {field.description && (
          <span className="block text-xs text-gray-500 mt-0.5">{field.description}</span>
        )}
      </label>
      {renderInput()}
    </div>
  )
}

interface NumberFieldProps {
  value: number | undefined
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
}

function NumberField({ value, onChange, min, max, step }: NumberFieldProps) {
  const hasRange = min !== undefined && max !== undefined

  if (hasRange) {
    return (
      <div className="flex items-center gap-3">
        <input
          type="range"
          value={value ?? min ?? 0}
          onChange={(e) => onChange(Number(e.target.value))}
          min={min}
          max={max}
          step={step ?? 1}
          className="flex-1"
        />
        <input
          type="number"
          value={value ?? min ?? 0}
          onChange={(e) => onChange(Number(e.target.value))}
          min={min}
          max={max}
          step={step ?? 1}
          className="w-20 bg-dark-bg border border-dark-border rounded-lg px-2 py-1 text-white text-sm focus:outline-none focus:border-accent text-center"
        />
      </div>
    )
  }

  return (
    <input
      type="number"
      value={value ?? ''}
      onChange={(e) => onChange(Number(e.target.value))}
      min={min}
      max={max}
      step={step ?? 1}
      className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
    />
  )
}

interface ObjectFieldProps {
  value: Record<string, unknown>
  onChange: (value: Record<string, unknown>) => void
  depth: number
}

function ObjectField({ value, onChange }: ObjectFieldProps) {
  const [newKey, setNewKey] = useState('')

  const addKey = useCallback(() => {
    if (newKey && !(newKey in value)) {
      onChange({ ...value, [newKey]: '' })
      setNewKey('')
    }
  }, [newKey, value, onChange])

  const removeKey = useCallback((key: string) => {
    const newValue = { ...value }
    delete newValue[key]
    onChange(newValue)
  }, [value, onChange])

  const updateKey = useCallback((key: string, newVal: unknown) => {
    onChange({ ...value, [key]: newVal })
  }, [value, onChange])

  return (
    <div className="space-y-2">
      {Object.entries(value).map(([key, val]) => (
        <div key={key} className="flex items-start gap-2">
          <div className="flex-1 bg-dark-card rounded-lg p-3 border border-dark-border">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-300">{key}</span>
              <button
                type="button"
                onClick={() => removeKey(key)}
                className="p-1 text-gray-500 hover:text-red-400 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </div>
            <textarea
              value={typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val ?? '')}
              onChange={(e) => {
                try {
                  updateKey(key, JSON.parse(e.target.value))
                } catch {
                  updateKey(key, e.target.value)
                }
              }}
              rows={typeof val === 'object' ? 4 : 1}
              className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm font-mono focus:outline-none focus:border-accent resize-none"
            />
          </div>
        </div>
      ))}

      <div className="flex gap-2">
        <input
          type="text"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addKey()}
          placeholder="Add new key..."
          className="flex-1 bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
        />
        <button
          type="button"
          onClick={addKey}
          disabled={!newKey}
          className="px-3 py-2 bg-accent/20 text-accent rounded-lg hover:bg-accent/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Add"
        >
          <Plus size={16} />
        </button>
      </div>
    </div>
  )
}

interface ArrayFieldProps {
  value: unknown[]
  onChange: (value: unknown[]) => void
  itemSchema?: {
    type: string
    properties?: Record<string, ToolConfigField>
  }
}

function ArrayField({ value, onChange, itemSchema }: ArrayFieldProps) {
  const addItem = useCallback(() => {
    if (itemSchema?.type === 'object') {
      onChange([...value, {}])
    } else {
      onChange([...value, ''])
    }
  }, [value, onChange, itemSchema])

  const removeItem = useCallback((index: number) => {
    onChange(value.filter((_, i) => i !== index))
  }, [value, onChange])

  const updateItem = useCallback((index: number, newVal: unknown) => {
    const newArray = [...value]
    newArray[index] = newVal
    onChange(newArray)
  }, [value, onChange])

  return (
    <div className="space-y-2">
      {value.map((item, index) => (
        <div key={index} className="flex items-start gap-2">
          <span className="text-xs text-gray-500 pt-2 w-6">{index}</span>
          <div className="flex-1 bg-dark-card rounded-lg p-3 border border-dark-border">
            <div className="flex justify-end mb-2">
              <button
                type="button"
                onClick={() => removeItem(index)}
                className="p-1 text-gray-500 hover:text-red-400 transition-colors"
                aria-label="Remove"
              >
                <Trash2 size={14} />
              </button>
            </div>
            <textarea
              value={typeof item === 'object' ? JSON.stringify(item, null, 2) : String(item ?? '')}
              onChange={(e) => {
                try {
                  updateItem(index, JSON.parse(e.target.value))
                } catch {
                  updateItem(index, e.target.value)
                }
              }}
              rows={typeof item === 'object' ? 4 : 1}
              className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-white text-sm font-mono focus:outline-none focus:border-accent resize-none"
            />
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addItem}
        className="flex items-center gap-2 px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-gray-400 hover:text-white hover:border-accent/50 transition-colors text-sm"
        aria-label="Remove"
      >
        <Plus size={14} />
        Add item
      </button>
    </div>
  )
}
