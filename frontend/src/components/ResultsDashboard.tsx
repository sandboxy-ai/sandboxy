import { useMemo } from 'react'
import {
  Trophy,
  Target,
  CheckCircle,
  XCircle,
  Activity,
  BarChart3,
  Zap,
} from 'lucide-react'

interface EvaluationResult {
  score?: number
  checks?: Record<string, CheckResult>
  num_events?: number
  status?: string
}

interface CheckResult {
  passed?: boolean
  value?: number | string | boolean
  found?: boolean
  expected?: boolean | string | number
  count?: number
  min?: number
  max?: number
  called?: boolean
  actual?: unknown
  key?: string
  target?: string
  pattern?: string
  tool?: string
  action?: string
}

interface ResultsDashboardProps {
  evaluation: EvaluationResult
  moduleName?: string
  agentName?: string
  duration?: number
}

export default function ResultsDashboard({
  evaluation,
  moduleName,
  agentName,
  duration,
}: ResultsDashboardProps) {
  const { score, checks, num_events } = evaluation

  // Calculate stats
  const stats = useMemo(() => {
    if (!checks) return { total: 0, passed: 0, failed: 0, passRate: 0 }

    const entries = Object.entries(checks)
    const total = entries.length
    const passed = entries.filter(([, r]) => r.passed === true).length
    const failed = entries.filter(([, r]) => r.passed === false).length

    return {
      total,
      passed,
      failed,
      passRate: total > 0 ? (passed / total) * 100 : 0,
    }
  }, [checks])

  // Get score color and label
  const getScoreStyle = (s: number) => {
    if (s >= 0.8) return { color: 'text-green-400', bg: 'bg-green-500', label: 'Excellent' }
    if (s >= 0.6) return { color: 'text-yellow-400', bg: 'bg-yellow-500', label: 'Good' }
    if (s >= 0.4) return { color: 'text-orange-400', bg: 'bg-orange-500', label: 'Fair' }
    return { color: 'text-red-400', bg: 'bg-red-500', label: 'Needs Work' }
  }

  const scoreStyle = score !== undefined ? getScoreStyle(score) : null

  return (
    <div className="bg-dark-card border border-dark-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-accent/20 to-purple-500/20 px-6 py-4 border-b border-dark-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Trophy className="text-accent" size={24} />
              Results Dashboard
            </h2>
            {(moduleName || agentName) && (
              <p className="text-sm text-gray-400 mt-1">
                {moduleName && <span>{moduleName}</span>}
                {moduleName && agentName && <span className="mx-2">•</span>}
                {agentName && <span>{agentName}</span>}
              </p>
            )}
          </div>
          {score !== undefined && scoreStyle && (
            <div className="text-right">
              <div className={`text-4xl font-bold ${scoreStyle.color}`}>
                {Math.round(score * 100)}%
              </div>
              <div className={`text-sm ${scoreStyle.color}`}>{scoreStyle.label}</div>
            </div>
          )}
        </div>
      </div>

      {/* Score Bar */}
      {score !== undefined && (
        <div className="px-6 py-4 border-b border-dark-border">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-400 w-16">Score</span>
            <div className="flex-1">
              <div className="h-3 bg-dark-bg rounded-full overflow-hidden">
                <div
                  className={`h-full ${scoreStyle?.bg} transition-all duration-500 ease-out`}
                  style={{ width: `${Math.min(100, score * 100)}%` }}
                />
              </div>
            </div>
            <span className="text-sm font-mono text-white w-12 text-right">
              {(score * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      )}

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 border-b border-dark-border">
        <StatCard
          icon={Target}
          label="Total Checks"
          value={stats.total}
          color="text-blue-400"
        />
        <StatCard
          icon={CheckCircle}
          label="Passed"
          value={stats.passed}
          color="text-green-400"
        />
        <StatCard
          icon={XCircle}
          label="Failed"
          value={stats.failed}
          color="text-red-400"
        />
        <StatCard
          icon={Activity}
          label="Events"
          value={num_events || 0}
          color="text-purple-400"
        />
      </div>

      {/* Pass Rate Gauge */}
      {stats.total > 0 && (
        <div className="px-6 py-4 border-b border-dark-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-400">Pass Rate</span>
            <span className="text-sm font-mono text-white">{stats.passRate.toFixed(1)}%</span>
          </div>
          <div className="flex gap-1 h-8">
            {stats.total > 0 && [...Array(stats.total)].map((_, i) => {
              const checkEntries = Object.entries(checks || {})
              const check = checkEntries[i]
              const passed = check ? check[1].passed : undefined

              return (
                <div
                  key={i}
                  className={`flex-1 rounded transition-colors ${
                    passed === true
                      ? 'bg-green-500'
                      : passed === false
                      ? 'bg-red-500'
                      : 'bg-gray-600'
                  }`}
                  title={check ? check[0] : undefined}
                />
              )
            })}
          </div>
        </div>
      )}

      {/* Detailed Checks */}
      {checks && Object.keys(checks).length > 0 && (
        <div className="p-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <BarChart3 size={16} />
            Detailed Results
          </h3>
          <div className="space-y-3">
            {Object.entries(checks).map(([name, result]) => (
              <CheckResultRow key={name} name={name} result={result} />
            ))}
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      {duration !== undefined && (
        <div className="px-6 py-4 bg-dark-bg/50 border-t border-dark-border">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Zap size={14} className="text-yellow-400" />
            <span>Completed in {(duration / 1000).toFixed(2)}s</span>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Trophy
  label: string
  value: number | string
  color: string
}) {
  return (
    <div className="bg-dark-bg rounded-lg p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-dark-card ${color}`}>
          <Icon size={18} />
        </div>
        <div>
          <div className="text-2xl font-bold text-white">{value}</div>
          <div className="text-xs text-gray-400">{label}</div>
        </div>
      </div>
    </div>
  )
}

function CheckResultRow({ name, result }: { name: string; result: CheckResult }) {
  const passed = result.passed
  const hasValue = result.value !== undefined

  // Format the result details
  const getDetails = () => {
    const parts: string[] = []

    if (result.target) parts.push(`in ${result.target}`)
    if (result.tool) parts.push(`tool: ${result.tool}`)
    if (result.action) parts.push(`action: ${result.action}`)
    if (result.pattern) parts.push(`pattern: ${result.pattern}`)
    if (result.key) parts.push(`key: ${result.key}`)
    if (result.count !== undefined) parts.push(`count: ${result.count}`)
    if (result.min !== undefined || result.max !== undefined) {
      const range = []
      if (result.min !== undefined) range.push(`min: ${result.min}`)
      if (result.max !== undefined) range.push(`max: ${result.max}`)
      parts.push(range.join(', '))
    }

    return parts.join(' • ')
  }

  const details = getDetails()

  return (
    <div
      className={`flex items-center gap-4 p-3 rounded-lg border transition-colors ${
        passed === true
          ? 'bg-green-500/5 border-green-500/20'
          : passed === false
          ? 'bg-red-500/5 border-red-500/20'
          : 'bg-dark-bg border-dark-border'
      }`}
    >
      {/* Status Icon */}
      <div
        className={`shrink-0 ${
          passed === true ? 'text-green-400' : passed === false ? 'text-red-400' : 'text-gray-400'
        }`}
      >
        {passed === true ? (
          <CheckCircle size={20} />
        ) : passed === false ? (
          <XCircle size={20} />
        ) : (
          <Target size={20} />
        )}
      </div>

      {/* Name and Details */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-white">{name}</div>
        {details && <div className="text-xs text-gray-500 truncate mt-0.5">{details}</div>}
      </div>

      {/* Value */}
      {hasValue && (
        <div className="text-right shrink-0">
          <div className="text-sm font-mono text-gray-300">
            {typeof result.value === 'number'
              ? result.value.toFixed(2)
              : typeof result.value === 'boolean'
              ? result.value ? 'true' : 'false'
              : String(result.value)}
          </div>
          {result.expected !== undefined && (
            <div className="text-xs text-gray-500">
              expected: {String(result.expected)}
            </div>
          )}
        </div>
      )}

      {/* Pass/Fail Badge */}
      <div
        className={`px-2 py-1 rounded text-xs font-medium shrink-0 ${
          passed === true
            ? 'bg-green-500/20 text-green-400'
            : passed === false
            ? 'bg-red-500/20 text-red-400'
            : 'bg-gray-500/20 text-gray-400'
        }`}
      >
        {passed === true ? 'PASS' : passed === false ? 'FAIL' : 'N/A'}
      </div>
    </div>
  )
}
