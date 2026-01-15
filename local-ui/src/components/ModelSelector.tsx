import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check, X, Search } from 'lucide-react'
import { ModelInfo } from '../lib/api'

interface ModelSelectorProps {
  models: ModelInfo[]
  value: string
  onChange: (modelId: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ModelSelector({ models, value, onChange, disabled, placeholder = 'Select a model...' }: ModelSelectorProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const selectedModel = models.find(m => m.id === value)

  // Close on click outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Focus search when opened
  useEffect(() => {
    if (open && searchRef.current) {
      searchRef.current.focus()
    }
  }, [open])

  const filteredModels = models.filter(m =>
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.id.toLowerCase().includes(search.toLowerCase())
  )

  // Group models by provider
  const groupedModels = filteredModels.reduce((acc, model) => {
    const provider = model.id.split('/')[0] || 'other'
    if (!acc[provider]) acc[provider] = []
    acc[provider].push(model)
    return acc
  }, {} as Record<string, ModelInfo[]>)

  const providerOrder = ['openai', 'anthropic', 'google', 'x-ai', 'deepseek', 'meta-llama', 'mistralai', 'qwen', 'perplexity']
  const sortedProviders = Object.keys(groupedModels).sort((a, b) => {
    const aIdx = providerOrder.indexOf(a)
    const bIdx = providerOrder.indexOf(b)
    if (aIdx === -1 && bIdx === -1) return a.localeCompare(b)
    if (aIdx === -1) return 1
    if (bIdx === -1) return -1
    return aIdx - bIdx
  })

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className={`w-full flex items-center justify-between gap-2 px-4 py-2.5 panel-subtle text-left transition-colors ${
          disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-800 cursor-pointer'
        } ${open ? 'ring-2 ring-orange-400' : ''}`}
      >
        {selectedModel ? (
          <div className="flex items-center justify-between flex-1 min-w-0">
            <span className="text-slate-100 truncate">{selectedModel.name}</span>
            <span className="text-xs text-slate-500 ml-2 shrink-0">{selectedModel.price}</span>
          </div>
        ) : (
          <span className="text-slate-500">{placeholder}</span>
        )}
        <ChevronDown size={18} className={`text-slate-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-50 w-full mt-1 panel-card border border-slate-700/80 dark:border-slate-700/80 shadow-xl max-h-[28rem] overflow-hidden flex flex-col">
          {/* Search */}
          <div className="p-2 border-b border-slate-800/70">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                ref={searchRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search models..."
                className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800/70 rounded text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-400/60"
              />
            </div>
          </div>

          {/* Model list */}
          <div className="overflow-y-auto flex-1">
            {sortedProviders.map(provider => (
              <div key={provider}>
                <div className="px-3 py-1.5 text-xs font-medium text-slate-500 uppercase bg-slate-900 sticky top-0">
                  {provider}
                </div>
                {groupedModels[provider].map(model => (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => {
                      onChange(model.id)
                      setOpen(false)
                      setSearch('')
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                      model.id === value
                        ? 'bg-orange-500/20 text-orange-300'
                        : 'hover:bg-slate-800 text-slate-100'
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{model.name}</div>
                    </div>
                    <span className="text-xs text-slate-500 shrink-0">{model.price}</span>
                    {model.id === value && <Check size={16} className="text-orange-400 shrink-0" />}
                  </button>
                ))}
              </div>
            ))}
            {filteredModels.length === 0 && (
              <div className="px-3 py-4 text-center text-slate-500 text-sm">
                No models found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface MultiModelSelectorProps {
  models: ModelInfo[]
  selected: string[]
  onChange: (modelIds: string[]) => void
  disabled?: boolean
}

export function MultiModelSelector({ models, selected, onChange, disabled }: MultiModelSelectorProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  // Close on click outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    if (open && searchRef.current) {
      searchRef.current.focus()
    }
  }, [open])

  const toggleModel = (modelId: string) => {
    if (selected.includes(modelId)) {
      onChange(selected.filter(id => id !== modelId))
    } else {
      onChange([...selected, modelId])
    }
  }

  const removeModel = (modelId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(selected.filter(id => id !== modelId))
  }

  const filteredModels = models.filter(m =>
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.id.toLowerCase().includes(search.toLowerCase())
  )

  // Group models by provider
  const groupedModels = filteredModels.reduce((acc, model) => {
    const provider = model.id.split('/')[0] || 'other'
    if (!acc[provider]) acc[provider] = []
    acc[provider].push(model)
    return acc
  }, {} as Record<string, ModelInfo[]>)

  const providerOrder = ['openai', 'anthropic', 'google', 'x-ai', 'deepseek', 'meta-llama', 'mistralai', 'qwen', 'perplexity']
  const sortedProviders = Object.keys(groupedModels).sort((a, b) => {
    const aIdx = providerOrder.indexOf(a)
    const bIdx = providerOrder.indexOf(b)
    if (aIdx === -1 && bIdx === -1) return a.localeCompare(b)
    if (aIdx === -1) return 1
    if (bIdx === -1) return -1
    return aIdx - bIdx
  })

  return (
    <div ref={ref} className="relative">
      {/* Selected models chips */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {selected.map(modelId => {
            const model = models.find(m => m.id === modelId)
            return (
              <span
                key={modelId}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-orange-500/20 border border-orange-400/40 rounded-full text-sm text-slate-100"
              >
                {model?.name || modelId}
                <button
                  type="button"
                  onClick={(e) => removeModel(modelId, e)}
                  className="hover:text-red-400 transition-colors"
                  disabled={disabled}
                >
                  <X size={14} />
                </button>
              </span>
            )
          })}
        </div>
      )}

      <button
        type="button"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className={`w-full flex items-center justify-between gap-2 px-4 py-2.5 panel-subtle text-left transition-colors ${
          disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-800 cursor-pointer'
        } ${open ? 'ring-2 ring-orange-400' : ''}`}
      >
        <span className="text-slate-500">
          {selected.length === 0 ? 'Click to add models...' : 'Add more models...'}
        </span>
        <ChevronDown size={18} className={`text-slate-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-50 w-full mt-1 panel-card border border-slate-700/80 dark:border-slate-700/80 shadow-xl max-h-[28rem] overflow-hidden flex flex-col">
          {/* Search */}
          <div className="p-2 border-b border-slate-800/70">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                ref={searchRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search models..."
                className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800/70 rounded text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-400/60"
              />
            </div>
          </div>

          {/* Model list */}
          <div className="overflow-y-auto flex-1">
            {sortedProviders.map(provider => (
              <div key={provider}>
                <div className="px-3 py-1.5 text-xs font-medium text-slate-500 uppercase bg-slate-900 sticky top-0">
                  {provider}
                </div>
                {groupedModels[provider].map(model => {
                  const isSelected = selected.includes(model.id)
                  return (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => toggleModel(model.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                        isSelected
                          ? 'bg-orange-500/20 text-orange-300'
                          : 'hover:bg-slate-800 text-slate-100'
                      }`}
                    >
                      <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-orange-400 border-orange-400' : 'border-slate-600'
                      }`}>
                        {isSelected && <Check size={12} className="text-slate-900" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="truncate">{model.name}</div>
                      </div>
                      <span className="text-xs text-slate-500 shrink-0">{model.price}</span>
                    </button>
                  )
                })}
              </div>
            ))}
            {filteredModels.length === 0 && (
              <div className="px-3 py-4 text-center text-slate-500 text-sm">
                No models found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
