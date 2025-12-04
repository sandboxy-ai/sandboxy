import { useState, useEffect } from 'react'

interface SliderProps {
  label: string
  description?: string
  min: number
  max: number
  step?: number
  value: number
  onChange: (value: number) => void
  showValue?: boolean
  formatValue?: (value: number) => string
}

export default function Slider({
  label,
  description,
  min,
  max,
  step = 1,
  value,
  onChange,
  showValue = true,
  formatValue = (v) => String(v),
}: SliderProps) {
  const [localValue, setLocalValue] = useState(value)

  useEffect(() => {
    setLocalValue(value)
  }, [value])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = Number(e.target.value)
    setLocalValue(newValue)
    onChange(newValue)
  }

  const percentage = ((localValue - min) / (max - min)) * 100

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm text-gray-400">{label}</label>
        {showValue && (
          <span className="text-sm font-medium text-accent">
            {formatValue(localValue)}
          </span>
        )}
      </div>

      {description && (
        <p className="text-xs text-gray-500">{description}</p>
      )}

      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={localValue}
          onChange={handleChange}
          className="w-full h-2 bg-dark-bg rounded-lg appearance-none cursor-pointer slider-thumb"
          style={{
            background: `linear-gradient(to right, #f97316 0%, #f97316 ${percentage}%, #1a1a1c ${percentage}%, #1a1a1c 100%)`,
          }}
        />
      </div>

      <div className="flex justify-between text-xs text-gray-500">
        <span>{formatValue(min)}</span>
        <span>{formatValue(max)}</span>
      </div>
    </div>
  )
}
