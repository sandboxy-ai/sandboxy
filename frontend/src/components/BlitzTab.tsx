import { useState, useMemo, useEffect } from 'react'
import {
  Zap,
  Loader2,
  Shuffle,
  Copy,
  Share2,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Check,
  ArrowRight,
  Video,
} from 'lucide-react'
import { api } from '../lib/api'
import { FeatureGate } from '../lib/features'
import type {
  ArenaModel,
  BlitzTemplateCategory,
  BlitzTemplate,
  BlitzTemplateVariable,
  CreateBlitzResponse,
} from '../lib/api'

// Popular models optimized for quick, punchy responses
const BLITZ_MODELS = [
  'openai/gpt-4o',
  'anthropic/claude-3.5-sonnet',
  'google/gemini-2.0-flash-exp:free',
  'deepseek/deepseek-chat',
  'x-ai/grok-3',
  'meta-llama/llama-3.3-70b-instruct',
]

interface BlitzTabProps {
  models: ArenaModel[]
  modelsLoading: boolean
}

function VariableInput({
  variable,
  value,
  onChange,
  disabled,
}: {
  variable: BlitzTemplateVariable
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}) {
  const baseInputClass =
    'bg-dark-card border border-dark-border rounded px-2 py-1 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-accent disabled:opacity-50'

  if (variable.type === 'select' && variable.options) {
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={baseInputClass}
      >
        {variable.options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    )
  }

  if (variable.type === 'textarea') {
    return (
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={variable.placeholder || variable.name}
        disabled={disabled}
        rows={2}
        className={`${baseInputClass} w-full resize-none`}
      />
    )
  }

  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={variable.placeholder || variable.name}
      disabled={disabled}
      className={baseInputClass}
    />
  )
}

function TemplateRow({
  template,
  isExpanded,
  onToggle,
  onSelect,
  disabled,
}: {
  template: BlitzTemplate
  isExpanded: boolean
  onToggle: () => void
  onSelect: (text: string) => void
  disabled?: boolean
}) {
  const hasVariables = template.variables && template.variables.length > 0
  const [values, setValues] = useState<Record<string, string>>(() => {
    // Initialize with first option for selects, empty for others
    const initial: Record<string, string> = {}
    template.variables?.forEach((v) => {
      if (v.type === 'select' && v.options?.length) {
        initial[v.name] = v.options[0]
      } else {
        initial[v.name] = ''
      }
    })
    return initial
  })

  const handleClick = () => {
    if (!hasVariables) {
      onSelect(template.text)
    } else {
      onToggle()
    }
  }

  const handleUseTemplate = () => {
    let text = template.text
    for (const [name, value] of Object.entries(values)) {
      text = text.replace(new RegExp(`\\{${name}\\}`, 'g'), value || `{${name}}`)
    }
    onSelect(text)
  }

  const allFilled = template.variables?.every((v) => {
    if (v.type === 'select') return true // selects always have a value
    return values[v.name]?.trim()
  }) ?? true

  return (
    <div className="rounded overflow-hidden">
      <button
        onClick={handleClick}
        disabled={disabled}
        className={`w-full text-left p-2 text-sm text-gray-300 hover:bg-dark-card rounded transition-colors disabled:opacity-50 ${
          isExpanded ? 'bg-dark-card' : ''
        }`}
      >
        <span className="flex items-center gap-2">
          {hasVariables && (
            <span className="text-accent text-xs">⚡</span>
          )}
          <span>{template.text}</span>
        </span>
      </button>

      {isExpanded && hasVariables && (
        <div className="p-3 bg-dark-card/50 border-t border-dark-border space-y-3">
          <div className="flex flex-wrap gap-3">
            {template.variables.map((v) => (
              <div key={v.name} className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 capitalize">{v.name}</label>
                <VariableInput
                  variable={v}
                  value={values[v.name] || ''}
                  onChange={(val) => setValues((prev) => ({ ...prev, [v.name]: val }))}
                  disabled={disabled}
                />
              </div>
            ))}
          </div>
          <button
            onClick={handleUseTemplate}
            disabled={disabled || !allFilled}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-accent text-white text-sm rounded hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Use Template"
          >
            Use Template
            <ArrowRight size={14} />
          </button>
        </div>
      )}
    </div>
  )
}

function TemplateSelector({
  categories,
  onSelect,
  disabled,
}: {
  categories: BlitzTemplateCategory[]
  onSelect: (template: { text: string; id: string }) => void
  disabled?: boolean
}) {
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null)

  return (
    <div className="space-y-2">
      {categories.map((cat) => (
        <div key={cat.id} className="border border-dark-border rounded-lg overflow-hidden">
          <button
            onClick={() => {
              setExpandedCategory(expandedCategory === cat.id ? null : cat.id)
              setExpandedTemplate(null)
            }}
            disabled={disabled}
            className="w-full flex items-center justify-between p-3 bg-dark-card hover:bg-dark-card/80 transition-colors disabled:opacity-50"
          >
            <span className="flex items-center gap-2 text-white">
              <span>{cat.icon}</span>
              <span className="font-medium">{cat.name}</span>
              <span className="text-xs text-gray-500">({cat.templates.length})</span>
            </span>
            {expandedCategory === cat.id ? (
              <ChevronUp size={16} className="text-gray-400" />
            ) : (
              <ChevronDown size={16} className="text-gray-400" />
            )}
          </button>
          {expandedCategory === cat.id && (
            <div className="p-2 bg-dark-bg space-y-1">
              {cat.templates.map((template) => (
                <TemplateRow
                  key={template.id}
                  template={template}
                  isExpanded={expandedTemplate === template.id}
                  onToggle={() =>
                    setExpandedTemplate(expandedTemplate === template.id ? null : template.id)
                  }
                  onSelect={(text) => {
                    onSelect({ text, id: template.id })
                    setExpandedTemplate(null)
                  }}
                  disabled={disabled}
                />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ModelChip({
  model,
  selected,
  onClick,
  disabled,
}: {
  model: ArenaModel
  selected: boolean
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
        selected
          ? 'bg-accent text-white'
          : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {model.name}
    </button>
  )
}

function ResponseCard({
  modelId,
  content,
  latencyMs,
  tokens,
  error,
}: {
  modelId: string
  content: string
  latencyMs: number
  tokens: number
  error?: string | null
}) {
  const [copied, setCopied] = useState(false)
  const modelName = modelId.split('/').pop() || modelId

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-xl overflow-hidden">
      <div className="p-3 border-b border-dark-border flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-white">{modelName}</h4>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {latencyMs}ms
            </span>
            <span>{tokens} tokens</span>
          </div>
        </div>
        <button
          onClick={handleCopy}
          className="p-2 text-gray-400 hover:text-white hover:bg-dark-bg rounded-lg transition-colors"
          title="Copy response"
        >
          {copied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
        </button>
      </div>
      <div className="p-4">
        {error ? (
          <div className="flex items-start gap-2 text-red-400">
            <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
            <span className="text-sm">{error}</span>
          </div>
        ) : (
          <p className="text-gray-200 whitespace-pre-wrap">{content}</p>
        )}
      </div>
    </div>
  )
}

function BlitzResults({
  blitz,
  onReset,
}: {
  blitz: CreateBlitzResponse
  onReset: () => void
}) {
  const [copied, setCopied] = useState(false)
  const [videoStatus, setVideoStatus] = useState<'idle' | 'checking' | 'ready' | 'pending'>('idle')

  const handleShare = () => {
    const url = `${window.location.origin}/blitz/${blitz.id}`
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExportVideo = async () => {
    setVideoStatus('checking')
    try {
      const res = await fetch(`/api/v1/blitz/${blitz.id}/video`, {
        redirect: 'manual', // Don't follow redirects automatically
      })

      if (res.type === 'opaqueredirect' || res.status === 307 || res.status === 302) {
        // Video is ready - get the redirect URL and open it
        const redirectUrl = res.headers.get('location')
        if (redirectUrl) {
          setVideoStatus('ready')
          window.open(redirectUrl, '_blank')
        } else {
          // Fallback: try fetching again letting redirect happen
          window.open(`/api/v1/blitz/${blitz.id}/video`, '_blank')
          setVideoStatus('ready')
        }
      } else {
        const data = await res.json()
        if (data.status === 'pending') {
          setVideoStatus('pending')
          setTimeout(() => setVideoStatus('idle'), 3000)
        }
      }
    } catch (err) {
      console.error('Failed to check video status:', err)
      setVideoStatus('idle')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onReset}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <Shuffle size={16} />
          New Blitz
        </button>
        <div className="flex items-center gap-2">
          <FeatureGate feature="video-export">
            <button
              onClick={handleExportVideo}
              disabled={videoStatus === 'checking'}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              aria-label="Export Video"
            >
              {videoStatus === 'checking' ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Video size={16} />
              )}
              {videoStatus === 'checking'
                ? 'Checking...'
                : videoStatus === 'pending'
                  ? 'Still rendering...'
                  : 'Export Video'}
            </button>
          </FeatureGate>
          <button
            onClick={handleShare}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
            aria-label="Share"
          >
            {copied ? <Check size={16} /> : <Share2 size={16} />}
            {copied ? 'Copied!' : 'Share'}
          </button>
        </div>
      </div>

      {/* Prompt */}
      <div className="bg-gradient-to-r from-accent/10 to-purple-500/10 border border-accent/20 rounded-xl p-6">
        <p className="text-lg text-white font-medium">{blitz.prompt}</p>
        <p className="text-sm text-gray-400 mt-2 capitalize">Style: {blitz.style}</p>
      </div>

      {/* Responses grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {blitz.models.map((modelId) => {
          const response = blitz.responses[modelId]
          if (!response) return null
          return (
            <ResponseCard
              key={modelId}
              modelId={modelId}
              content={response.content}
              latencyMs={response.latency_ms}
              tokens={response.tokens}
            />
          )
        })}
      </div>
    </div>
  )
}

export default function BlitzTab({ models, modelsLoading }: BlitzTabProps) {
  const [prompt, setPrompt] = useState('')
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [style, setStyle] = useState('brief')
  const [styles, setStyles] = useState<Record<string, string>>({})
  const [stylesLoading, setStylesLoading] = useState(true)
  const [categories, setCategories] = useState<BlitzTemplateCategory[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CreateBlitzResponse | null>(null)

  // Load styles and templates from backend
  useEffect(() => {
    setStylesLoading(true)
    Promise.all([
      api.getBlitzStyles(),
      api.getBlitzTemplateCategories().catch(() => []),
    ]).then(([s, t]) => {
      setStyles(s)
      setCategories(t)
    }).catch(console.error)
      .finally(() => setStylesLoading(false))
  }, [])

  // Filter to popular blitz models
  const blitzModels = useMemo(() => {
    return models.filter(m => BLITZ_MODELS.includes(m.id))
  }, [models])

  // Auto-select some models
  useEffect(() => {
    if (blitzModels.length > 0 && selectedModels.length === 0) {
      // Select first 3 by default
      setSelectedModels(blitzModels.slice(0, 3).map(m => m.id))
    }
  }, [blitzModels, selectedModels.length])

  const handleToggleModel = (modelId: string) => {
    setSelectedModels(prev =>
      prev.includes(modelId)
        ? prev.filter(id => id !== modelId)
        : prev.length < 6 ? [...prev, modelId] : prev
    )
  }

  const handleSelectTemplate = (template: { text: string; id: string }) => {
    setPrompt(template.text)
  }

  const handleGenerate = async () => {
    if (!prompt.trim() || selectedModels.length < 2) return

    setLoading(true)
    setError(null)

    try {
      const blitz = await api.createBlitz({
        prompt: prompt.trim(),
        models: selectedModels,
        style,
      })
      setResult(blitz)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run blitz')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setResult(null)
    setPrompt('')
  }

  // Show results if we have them
  if (result) {
    return (
      <div className="p-6">
        <BlitzResults blitz={result} onReset={handleReset} />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-xl flex items-center justify-center">
          <Zap size={20} className="text-white" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Blitz</h2>
          <p className="text-sm text-gray-400">Quick AI showdowns with short, punchy responses</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left: Prompt */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">Prompt</label>
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-yellow-400" />
              <span className="text-xs text-gray-500">Use a template or write your own</span>
            </div>
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask something spicy... e.g. 'Rate this dating bio: I'm 6'4 if that matters'"
            rows={4}
            className="w-full bg-dark-card border border-dark-border rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-accent resize-none"
            disabled={loading}
          />

          {/* Style selector */}
          <div>
            <label className="text-sm text-gray-400 mb-2 block">Response Style</label>
            {stylesLoading ? (
              <div className="flex items-center gap-2 text-gray-500">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Loading styles...</span>
              </div>
            ) : Object.keys(styles).length === 0 ? (
              <p className="text-sm text-gray-500">Start backend to load styles</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {Object.entries(styles).map(([key, description]) => (
                  <button
                    key={key}
                    onClick={() => setStyle(key)}
                    disabled={loading}
                    title={description}
                    className={`px-3 py-1.5 rounded-lg text-sm capitalize transition-all ${
                      style === key
                        ? 'bg-accent text-white'
                        : 'bg-dark-bg border border-dark-border text-gray-300 hover:border-accent/50'
                    } disabled:opacity-50`}
                  >
                    {key}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Template browser */}
          {categories.length > 0 && (
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Or pick a template</label>
              <div className="max-h-64 overflow-y-auto">
                <TemplateSelector
                  categories={categories}
                  onSelect={handleSelectTemplate}
                  disabled={loading}
                />
              </div>
            </div>
          )}
        </div>

        {/* Right: Models */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">Models</label>
            <span className="text-xs text-gray-500">
              {selectedModels.length}/6 selected (min 2)
            </span>
          </div>

          {modelsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-accent" size={24} />
            </div>
          ) : blitzModels.length === 0 ? (
            <div className="bg-dark-card border border-dark-border rounded-xl p-6 text-center">
              <AlertCircle className="mx-auto text-yellow-400 mb-3" size={32} />
              <h3 className="font-semibold text-white mb-2">No Models Available</h3>
              <p className="text-sm text-gray-400">
                Set <code className="bg-dark-bg px-1.5 py-0.5 rounded text-accent">OPENROUTER_API_KEY</code> to access models.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {blitzModels.map(model => (
                  <ModelChip
                    key={model.id}
                    model={model}
                    selected={selectedModels.includes(model.id)}
                    onClick={() => handleToggleModel(model.id)}
                    disabled={loading || (selectedModels.length >= 6 && !selectedModels.includes(model.id))}
                  />
                ))}
              </div>

              {/* Show all models option */}
              <p className="text-xs text-gray-500">
                Optimized for fast, punchy responses.
              </p>
            </div>
          )}

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={loading || !prompt.trim() || selectedModels.length < 2}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white font-semibold px-6 py-3 rounded-xl transition-all shadow-lg shadow-orange-500/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            aria-label="Run Blitz"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={18} />
                Running...
              </>
            ) : (
              <>
                <Zap size={18} />
                Run Blitz
              </>
            )}
          </button>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
