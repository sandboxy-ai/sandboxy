import { ChevronDown, ChevronUp, Info } from 'lucide-react'
import { useState } from 'react'
import { ContextFieldConfig } from '../lib/api'

interface ContextPanelProps {
  config: ContextFieldConfig[]
  data: Record<string, unknown> | null
}

// Get nested value from object using dot notation (e.g., "inventory.cups_ready")
function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const keys = path.split('.')
  let current: unknown = obj

  for (const key of keys) {
    if (current === null || current === undefined) return undefined
    if (typeof current !== 'object') return undefined
    current = (current as Record<string, unknown>)[key]
  }

  return current
}

// Format value based on config
function formatValue(value: unknown, format: ContextFieldConfig['format']): string {
  if (value === undefined || value === null) return '-'

  switch (format) {
    case 'currency':
      return `$${Number(value).toFixed(2)}`
    case 'number':
      return String(Number(value))
    case 'progress':
      return `${Number(value)}%`
    case 'text':
    default:
      return String(value)
  }
}

// Check if value should show warning
function shouldWarn(value: unknown, field: ContextFieldConfig): boolean {
  if (value === undefined || value === null) return false
  const numValue = Number(value)
  if (isNaN(numValue)) return false

  if (field.warn_below !== undefined && numValue < field.warn_below) return true
  if (field.warn_above !== undefined && numValue > field.warn_above) return true

  return false
}

export default function ContextPanel({ config, data }: ContextPanelProps) {
  const [expanded, setExpanded] = useState(true)

  if (!data) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg p-4">
        <p className="text-sm text-gray-500 text-center">
          Waiting for data...
        </p>
      </div>
    )
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-dark-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <Info size={16} className="text-accent" />
          <span className="text-sm font-medium text-white">Context</span>
        </div>
        {expanded ? (
          <ChevronUp size={16} className="text-gray-400" />
        ) : (
          <ChevronDown size={16} className="text-gray-400" />
        )}
      </button>

      {/* Fields */}
      {expanded && (
        <div className="p-3 border-t border-dark-border space-y-2">
          {config.map((field) => {
            const value = getNestedValue(data, field.key)
            const warn = shouldWarn(value, field)
            const formatted = formatValue(value, field.format)

            if (field.format === 'progress') {
              const numValue = Number(value) || 0
              const max = field.max || 100
              const percentage = Math.min(100, (numValue / max) * 100)

              return (
                <div key={field.key} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      {field.icon && <span>{field.icon}</span>}
                      <span className="text-gray-400">{field.label}</span>
                    </div>
                    <span className={`font-medium ${warn ? 'text-yellow-400' : 'text-white'}`}>
                      {numValue}/{max}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-dark-bg rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        percentage >= 70 ? 'bg-green-500' :
                        percentage >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              )
            }

            return (
              <div key={field.key} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {field.icon && <span>{field.icon}</span>}
                  <span className="text-gray-400">{field.label}</span>
                </div>
                <span className={`font-medium ${warn ? 'text-yellow-400' : 'text-white'}`}>
                  {formatted}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
