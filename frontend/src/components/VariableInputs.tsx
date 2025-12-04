import { ModuleVariable } from '../lib/api'
import Slider from './Slider'

interface VariableInputsProps {
  variables: ModuleVariable[]
  values: Record<string, unknown>
  onChange: (name: string, value: unknown) => void
}

export default function VariableInputs({
  variables,
  values,
  onChange,
}: VariableInputsProps) {
  if (variables.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-gray-300">Configuration</h3>

      {variables.map((variable) => (
        <div key={variable.name}>
          {variable.type === 'slider' && (
            <Slider
              label={variable.label || variable.name}
              description={variable.description}
              min={variable.min ?? 0}
              max={variable.max ?? 100}
              step={variable.step ?? 1}
              value={(values[variable.name] as number) ?? variable.default ?? variable.min ?? 0}
              onChange={(value) => onChange(variable.name, value)}
              formatValue={(v) => {
                // Format as currency if it looks like money
                if (variable.name.toLowerCase().includes('cash') ||
                    variable.name.toLowerCase().includes('money') ||
                    variable.name.toLowerCase().includes('price')) {
                  return `$${v}`
                }
                return String(v)
              }}
            />
          )}

          {variable.type === 'select' && (
            <div className="space-y-1">
              <label className="block text-sm text-gray-400">
                {variable.label || variable.name}
              </label>
              {variable.description && (
                <p className="text-xs text-gray-500">{variable.description}</p>
              )}
              <select
                value={(values[variable.name] as string) ?? variable.default ?? ''}
                onChange={(e) => onChange(variable.name, e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              >
                {variable.options?.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {variable.type === 'text' && (
            <div className="space-y-1">
              <label className="block text-sm text-gray-400">
                {variable.label || variable.name}
              </label>
              {variable.description && (
                <p className="text-xs text-gray-500">{variable.description}</p>
              )}
              <input
                type="text"
                value={(values[variable.name] as string) ?? variable.default ?? ''}
                onChange={(e) => onChange(variable.name, e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
          )}

          {variable.type === 'number' && (
            <div className="space-y-1">
              <label className="block text-sm text-gray-400">
                {variable.label || variable.name}
              </label>
              {variable.description && (
                <p className="text-xs text-gray-500">{variable.description}</p>
              )}
              <input
                type="number"
                min={variable.min}
                max={variable.max}
                step={variable.step}
                value={(values[variable.name] as number) ?? variable.default ?? 0}
                onChange={(e) => onChange(variable.name, Number(e.target.value))}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent"
              />
            </div>
          )}

          {variable.type === 'boolean' && (
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id={`var-${variable.name}`}
                checked={(values[variable.name] as boolean) ?? variable.default ?? false}
                onChange={(e) => onChange(variable.name, e.target.checked)}
                className="w-4 h-4 rounded border-dark-border bg-dark-bg text-accent focus:ring-accent focus:ring-offset-0"
              />
              <div>
                <label htmlFor={`var-${variable.name}`} className="text-sm text-gray-400 cursor-pointer">
                  {variable.label || variable.name}
                </label>
                {variable.description && (
                  <p className="text-xs text-gray-500">{variable.description}</p>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
