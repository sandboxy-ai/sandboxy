import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Database,
  Plus,
  ChevronDown,
  ChevronRight,
  Play,
  Trash2,
  Edit2,
  Save,
  X,
  AlertCircle,
  Copy,
  Code,
} from 'lucide-react'
import { api, DatasetInfo, DatasetDetail, DatasetCase, LocalFileInfo, ScenarioGoalInfo, ScenarioToolInfo } from '../lib/api'

interface ToolResponseOverride {
  tool: string
  action: string
  mode: 'fields' | 'json'
  fields: Array<{ key: string; value: string }>
  rawJson: string
}

interface EditableCase {
  id: string
  expected: string[]
  variables: Array<{ key: string; value: string }>
  toolResponses: ToolResponseOverride[]
  tags: string[]
}

interface EditableDataset {
  id: string
  name: string
  description: string
  scenarioId: string
  cases: EditableCase[]
}

export default function DatasetPage() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const [scenarios, setScenarios] = useState<LocalFileInfo[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedDataset, setSelectedDataset] = useState<DatasetDetail | null>(null)
  const [expandedCases, setExpandedCases] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState<EditableDataset | null>(null)
  const [showYaml, setShowYaml] = useState(false)

  const [outcomeGoals, setOutcomeGoals] = useState<ScenarioGoalInfo[]>([])
  const [scenarioTools, setScenarioTools] = useState<ScenarioToolInfo[]>([])
  const [showNewForm, setShowNewForm] = useState(false)

  useEffect(() => {
    loadDatasets()
  }, [])

  useEffect(() => {
    if (!editData?.scenarioId) {
      setOutcomeGoals([])
      setScenarioTools([])
      return
    }

    api.getScenarioGoals(editData.scenarioId)
      .then((goals) => {
        const outcomes = goals.filter(g => g.outcome)
        setOutcomeGoals(outcomes.length > 0 ? outcomes : goals)
      })
      .catch(() => setOutcomeGoals([]))

    api.getScenarioTools(editData.scenarioId)
      .then(setScenarioTools)
      .catch(() => setScenarioTools([]))
  }, [editData?.scenarioId])

  useEffect(() => {
    if (selectedId) {
      api.getDataset(selectedId)
        .then((detail) => {
          setSelectedDataset(detail)
          setError(null)
        })
        .catch((e) => setError(e.message))
    } else {
      setSelectedDataset(null)
    }
  }, [selectedId])

  async function loadDatasets() {
    setLoading(true)
    try {
      const [datasetList, scenarioList] = await Promise.all([
        api.listDatasets(),
        api.listScenarios(),
      ])
      setDatasets(datasetList)
      setScenarios(scenarioList)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load datasets')
    } finally {
      setLoading(false)
    }
  }

  function toggleCase(caseId: string) {
    const newExpanded = new Set(expandedCases)
    if (newExpanded.has(caseId)) {
      newExpanded.delete(caseId)
    } else {
      newExpanded.add(caseId)
    }
    setExpandedCases(newExpanded)
  }

  function startEditing() {
    if (!selectedDataset) return
    setEditData(datasetToEditable(selectedDataset))
    setIsEditing(true)
  }

  function startNew() {
    setEditData({
      id: '',
      name: '',
      description: '',
      scenarioId: '',
      cases: [{
        id: 'case_001',
        expected: [],
        variables: [{ key: '', value: '' }],
        toolResponses: [],
        tags: [],
      }],
    })
    setShowNewForm(true)
    setIsEditing(true)
  }

  async function handleSave() {
    if (!editData) return

    const id = showNewForm ? editData.id : selectedId
    if (!id) {
      setError('Dataset ID is required')
      return
    }

    // Validate ID format
    if (!/^[a-z0-9_-]+$/.test(id)) {
      setError('Dataset ID must contain only lowercase letters, numbers, hyphens, and underscores')
      return
    }

    setSaving(true)
    try {
      const yaml = editableToYaml(editData)

      if (showNewForm) {
        await api.saveDataset(id, yaml)
      } else {
        await api.updateDataset(id, yaml)
      }

      setIsEditing(false)
      setShowNewForm(false)
      setEditData(null)
      await loadDatasets()
      setSelectedId(id)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save dataset')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm(`Delete dataset "${id}"?`)) return

    try {
      await api.deleteDataset(id)
      if (selectedId === id) {
        setSelectedId(null)
        setSelectedDataset(null)
      }
      await loadDatasets()
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete dataset')
    }
  }

  function cancelEdit() {
    setIsEditing(false)
    setShowNewForm(false)
    setEditData(null)
  }

  if (loading) {
    return (
      <div className="p-8 page">
        <div className="text-slate-400">Loading datasets...</div>
      </div>
    )
  }

  return (
    <div className="p-8 page">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-100 mb-2 flex items-center gap-2">
          <Database size={24} />
          Datasets
        </h1>
        <p className="text-slate-400">
          Manage test case datasets for multi-case benchmarking
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-300">
          <AlertCircle size={16} />
          {error}
          <button onClick={() => setError(null)} className="ml-auto">
            <X size={16} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left panel - Dataset list */}
        <div className="panel-card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-200">Datasets</h2>
            <button
              onClick={startNew}
              className="flex items-center gap-1 px-2 py-1 bg-blue-500 hover:bg-blue-400 text-white rounded text-sm"
            >
              <Plus size={14} />
              New
            </button>
          </div>

          {datasets.length === 0 ? (
            <p className="text-slate-500 text-sm">
              No datasets found. Create one to get started.
            </p>
          ) : (
            <div className="space-y-2">
              {datasets.map((ds) => (
                <div
                  key={ds.id}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedId === ds.id
                      ? 'bg-blue-500/20 border border-blue-500/50'
                      : 'panel-subtle hover:bg-slate-700/50'
                  }`}
                  onClick={() => {
                    setSelectedId(ds.id)
                    setIsEditing(false)
                    setShowNewForm(false)
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-200">{ds.name}</span>
                    <span className="text-xs text-slate-500">{ds.case_count} cases</span>
                  </div>
                  {ds.description && (
                    <p className="text-sm text-slate-400 mt-1 line-clamp-1">
                      {ds.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right panel - Dataset detail/editor */}
        <div className="lg:col-span-2 panel-card p-4 overflow-auto max-h-[80vh]">
          {isEditing && editData ? (
            <DatasetEditor
              data={editData}
              isNew={showNewForm}
              saving={saving}
              showYaml={showYaml}
              scenarios={scenarios}
              outcomeGoals={outcomeGoals}
              scenarioTools={scenarioTools}
              onDataChange={setEditData}
              onToggleYaml={() => setShowYaml(!showYaml)}
              onSave={handleSave}
              onCancel={cancelEdit}
            />
          ) : selectedDataset ? (
            <DatasetDetailView
              dataset={selectedDataset}
              expandedCases={expandedCases}
              onToggleCase={toggleCase}
              onEdit={startEditing}
              onDelete={() => handleDelete(selectedDataset.id)}
            />
          ) : (
            <div className="text-center text-slate-500 py-12">
              Select a dataset or create a new one
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Dataset Editor Component
interface DatasetEditorProps {
  data: EditableDataset
  isNew: boolean
  saving: boolean
  showYaml: boolean
  scenarios: LocalFileInfo[]
  outcomeGoals: ScenarioGoalInfo[]
  scenarioTools: ScenarioToolInfo[]
  onDataChange: (data: EditableDataset) => void
  onToggleYaml: () => void
  onSave: () => void
  onCancel: () => void
}

function DatasetEditor({
  data,
  isNew,
  saving,
  showYaml,
  scenarios,
  outcomeGoals,
  scenarioTools,
  onDataChange,
  onToggleYaml,
  onSave,
  onCancel,
}: DatasetEditorProps) {
  const updateCase = (index: number, updates: Partial<EditableCase>) => {
    const newCases = [...data.cases]
    newCases[index] = { ...newCases[index], ...updates }
    onDataChange({ ...data, cases: newCases })
  }

  const addCase = () => {
    const newId = `case_${String(data.cases.length + 1).padStart(3, '0')}`
    onDataChange({
      ...data,
      cases: [...data.cases, {
        id: newId,
        expected: [],
        variables: [{ key: '', value: '' }],
        toolResponses: [],
        tags: [],
      }],
    })
  }

  const removeCase = (index: number) => {
    if (data.cases.length <= 1) return
    onDataChange({
      ...data,
      cases: data.cases.filter((_, i) => i !== index),
    })
  }

  const duplicateCase = (index: number) => {
    const original = data.cases[index]
    const newId = `${original.id}_copy`
    const newCase = {
      ...original,
      id: newId,
      variables: [...original.variables.map(v => ({ ...v }))],
      toolResponses: original.toolResponses.map(t => ({
        ...t,
        fields: [...t.fields.map(f => ({ ...f }))],
        rawJson: t.rawJson,
      })),
      tags: [...original.tags],
    }
    onDataChange({
      ...data,
      cases: [...data.cases.slice(0, index + 1), newCase, ...data.cases.slice(index + 1)],
    })
  }

  if (showYaml) {
    return (
      <>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-slate-100">
            {isNew ? 'New Dataset' : `Edit: ${data.name}`}
          </h2>
          <div className="flex gap-2">
            <button
              onClick={onToggleYaml}
              className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-sm"
            >
              <Edit2 size={14} />
              Form View
            </button>
            <button
              onClick={onCancel}
              className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-sm"
              disabled={saving}
            >
              <X size={14} />
              Cancel
            </button>
            <button
              onClick={onSave}
              className="flex items-center gap-1 px-3 py-1.5 bg-green-500 hover:bg-green-400 text-white rounded text-sm"
              disabled={saving}
            >
              <Save size={14} />
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
        <pre className="p-4 bg-slate-800 rounded-lg text-sm text-slate-300 overflow-auto max-h-[60vh]">
          {editableToYaml(data)}
        </pre>
      </>
    )
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-slate-100">
          {isNew ? 'New Dataset' : `Edit: ${data.name}`}
        </h2>
        <div className="flex gap-2">
          <button
            onClick={onToggleYaml}
            className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-sm"
          >
            <Code size={14} />
            YAML
          </button>
          <button
            onClick={onCancel}
            className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-sm"
            disabled={saving}
          >
            <X size={14} />
            Cancel
          </button>
          <button
            onClick={onSave}
            className="flex items-center gap-1 px-3 py-1.5 bg-green-500 hover:bg-green-400 text-white rounded text-sm"
            disabled={saving}
          >
            <Save size={14} />
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Dataset Metadata */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {isNew && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Dataset ID <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={data.id}
              onChange={(e) => onDataChange({ ...data, id: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '-') })}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
              placeholder="my-test-cases"
            />
          </div>
        )}
        <div className={isNew ? '' : 'col-span-2'}>
          <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
          <input
            type="text"
            value={data.name}
            onChange={(e) => onDataChange({ ...data, name: e.target.value })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
            placeholder="My Test Cases"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Scenario <span className="text-slate-500">(for goal dropdown)</span>
          </label>
          <select
            value={data.scenarioId}
            onChange={(e) => onDataChange({ ...data, scenarioId: e.target.value })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
          >
            <option value="">Select a scenario...</option>
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          {!data.scenarioId && (
            <p className="mt-1 text-xs text-slate-500">
              Link to a scenario to enable outcome goal dropdown in case editor
            </p>
          )}
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-slate-300 mb-1">Description</label>
          <textarea
            value={data.description}
            onChange={(e) => onDataChange({ ...data, description: e.target.value })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
            rows={2}
            placeholder="Test cases for evaluating..."
          />
        </div>
      </div>

      {/* Cases */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-slate-200">
          Test Cases ({data.cases.length})
        </h3>
        <button
          onClick={addCase}
          className="flex items-center gap-1 px-2 py-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded text-sm"
        >
          <Plus size={14} />
          Add Case
        </button>
      </div>

      <div className="space-y-4">
        {data.cases.map((c, index) => (
          <CaseEditor
            key={index}
            case_={c}
            index={index}
            outcomeGoals={outcomeGoals}
            scenarioTools={scenarioTools}
            onChange={(updates) => updateCase(index, updates)}
            onRemove={() => removeCase(index)}
            onDuplicate={() => duplicateCase(index)}
            canRemove={data.cases.length > 1}
          />
        ))}
      </div>
    </>
  )
}

// Case Editor Component
interface CaseEditorProps {
  case_: EditableCase
  index: number
  outcomeGoals: ScenarioGoalInfo[]
  scenarioTools: ScenarioToolInfo[]
  onChange: (updates: Partial<EditableCase>) => void
  onRemove: () => void
  onDuplicate: () => void
  canRemove: boolean
}

function CaseEditor({ case_, index, outcomeGoals, scenarioTools, onChange, onRemove, onDuplicate, canRemove }: CaseEditorProps) {
  const [expanded, setExpanded] = useState(true)

  const toggleExpected = (goalId: string) => {
    if (case_.expected.includes(goalId)) {
      onChange({ expected: case_.expected.filter(e => e !== goalId) })
    } else {
      onChange({ expected: [...case_.expected, goalId] })
    }
  }

  const addVariable = () => {
    onChange({ variables: [...case_.variables, { key: '', value: '' }] })
  }

  const updateVariable = (varIndex: number, key: string, value: string) => {
    const newVars = [...case_.variables]
    newVars[varIndex] = { key, value }
    onChange({ variables: newVars })
  }

  const removeVariable = (varIndex: number) => {
    onChange({ variables: case_.variables.filter((_, i) => i !== varIndex) })
  }

  const addToolResponse = () => {
    onChange({
      toolResponses: [...case_.toolResponses, {
        tool: '',
        action: '',
        mode: 'fields',
        fields: [{ key: '', value: '' }],
        rawJson: '{\n  \n}',
      }],
    })
  }

  const updateToolResponse = (trIndex: number, updates: Partial<ToolResponseOverride>) => {
    const newTr = [...case_.toolResponses]
    newTr[trIndex] = { ...newTr[trIndex], ...updates }
    onChange({ toolResponses: newTr })
  }

  const removeToolResponse = (trIndex: number) => {
    onChange({ toolResponses: case_.toolResponses.filter((_, i) => i !== trIndex) })
  }

  const addField = (trIndex: number) => {
    const newTr = [...case_.toolResponses]
    newTr[trIndex] = {
      ...newTr[trIndex],
      fields: [...newTr[trIndex].fields, { key: '', value: '' }],
    }
    onChange({ toolResponses: newTr })
  }

  const updateField = (trIndex: number, fieldIndex: number, key: string, value: string) => {
    const newTr = [...case_.toolResponses]
    const newFields = [...newTr[trIndex].fields]
    newFields[fieldIndex] = { key, value }
    newTr[trIndex] = { ...newTr[trIndex], fields: newFields }
    onChange({ toolResponses: newTr })
  }

  const removeField = (trIndex: number, fieldIndex: number) => {
    const newTr = [...case_.toolResponses]
    newTr[trIndex] = {
      ...newTr[trIndex],
      fields: newTr[trIndex].fields.filter((_, i) => i !== fieldIndex),
    }
    onChange({ toolResponses: newTr })
  }

  const updateTags = (tagsStr: string) => {
    const tags = tagsStr.split(',').map(t => t.trim()).filter(Boolean)
    onChange({ tags })
  }

  return (
    <div className="panel-subtle rounded-lg overflow-hidden">
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-700/50"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <span className="font-medium text-slate-200">Case {index + 1}: {case_.id}</span>
        {case_.expected.length > 0 && (
          <span className="text-sm text-blue-400">
            expected: {case_.expected.join(' or ')}
          </span>
        )}
        <div className="ml-auto flex gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onDuplicate}
            className="p-1 text-slate-400 hover:text-slate-200"
            title="Duplicate case"
          >
            <Copy size={14} />
          </button>
          {canRemove && (
            <button
              onClick={onRemove}
              className="p-1 text-red-400 hover:text-red-300"
              title="Remove case"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-700 space-y-4">
          {/* Basic fields */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Case ID</label>
              <input
                type="text"
                value={case_.id}
                onChange={(e) => onChange({ id: e.target.value })}
                className="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
                placeholder="case_001"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Expected Outcome(s) {case_.expected.length > 1 && <span className="text-blue-400">(any)</span>}
              </label>
              {outcomeGoals.length > 0 ? (
                <div className="space-y-1.5 max-h-32 overflow-y-auto p-2 bg-slate-800 border border-slate-700 rounded">
                  {outcomeGoals.map((goal) => (
                    <label
                      key={goal.id}
                      className="flex items-center gap-2 cursor-pointer hover:bg-slate-700/50 p-1 rounded"
                    >
                      <input
                        type="checkbox"
                        checked={case_.expected.includes(goal.id)}
                        onChange={() => toggleExpected(goal.id)}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500"
                      />
                      <span className="text-sm text-slate-200">{goal.name || goal.id}</span>
                      {goal.description && (
                        <span className="text-xs text-slate-500 truncate">{goal.description}</span>
                      )}
                    </label>
                  ))}
                </div>
              ) : (
                <input
                  type="text"
                  value={case_.expected.join(', ')}
                  onChange={(e) => onChange({ expected: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                  className="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
                  placeholder="goal_id (link scenario for dropdown)"
                />
              )}
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Tags (comma-separated)</label>
            <input
              type="text"
              value={case_.tags.join(', ')}
              onChange={(e) => updateTags(e.target.value)}
              className="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
              placeholder="basic, edge-case, high-value"
            />
          </div>

          {/* Variables */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-400">Variables</label>
              <button
                onClick={addVariable}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                + Add Variable
              </button>
            </div>
            <div className="space-y-2">
              {case_.variables.map((v, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    value={v.key}
                    onChange={(e) => updateVariable(i, e.target.value, v.value)}
                    className="w-1/3 px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
                    placeholder="key"
                  />
                  <input
                    type="text"
                    value={v.value}
                    onChange={(e) => updateVariable(i, v.key, e.target.value)}
                    className="flex-1 px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
                    placeholder="value"
                  />
                  <button
                    onClick={() => removeVariable(i)}
                    className="p-1.5 text-red-400 hover:text-red-300"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Tool Response Overrides */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-400">Tool Response Overrides</label>
              <button
                onClick={addToolResponse}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                + Add Override
              </button>
            </div>
            <div className="space-y-3">
              {case_.toolResponses.map((tr, i) => {
                // Get available actions for the selected tool
                const selectedTool = scenarioTools.find(t => t.name === tr.tool)
                const availableActions = selectedTool?.actions || []

                return (
                  <div key={i} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
                    {/* Row 1: Tool + Action */}
                    <div className="flex gap-2 items-center">
                      <div className="flex-1 grid grid-cols-2 gap-2">
                        {scenarioTools.length > 0 ? (
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Tool</label>
                            <select
                              value={tr.tool}
                              onChange={(e) => {
                                const newTool = e.target.value
                                const toolInfo = scenarioTools.find(t => t.name === newTool)
                                // Auto-set action to "call" for single-action tools
                                const autoAction = toolInfo?.actions.length === 1 && toolInfo.actions[0].name === 'call'
                                  ? 'call'
                                  : ''
                                updateToolResponse(i, { tool: newTool, action: autoAction })
                              }}
                              className="w-full px-2 py-1.5 bg-slate-800 border border-slate-600 rounded text-slate-200 text-sm"
                            >
                              <option value="">Select tool...</option>
                              {scenarioTools.map((tool) => (
                                <option key={tool.name} value={tool.name}>
                                  {tool.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        ) : (
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Tool</label>
                            <input
                              type="text"
                              value={tr.tool}
                              onChange={(e) => updateToolResponse(i, { tool: e.target.value })}
                              className="w-full px-2 py-1.5 bg-slate-800 border border-slate-600 rounded text-slate-200 text-sm"
                              placeholder="tool_name"
                            />
                          </div>
                        )}
                        {/* Hide action if only "call" is available (single-action tool) */}
                        {availableActions.length === 1 && availableActions[0].name === 'call' ? (
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Action</label>
                            <div className="px-2 py-1.5 bg-slate-900 border border-slate-600 rounded text-slate-400 text-sm">
                              call <span className="text-xs">(single-action)</span>
                            </div>
                          </div>
                        ) : availableActions.length > 0 ? (
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Action</label>
                            <select
                              value={tr.action}
                              onChange={(e) => updateToolResponse(i, { action: e.target.value })}
                              className="w-full px-2 py-1.5 bg-slate-800 border border-slate-600 rounded text-slate-200 text-sm"
                            >
                              <option value="">Select action...</option>
                              {availableActions.map((action) => (
                                <option key={action.name} value={action.name}>
                                  {action.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        ) : (
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Action</label>
                            <input
                              type="text"
                              value={tr.action}
                              onChange={(e) => updateToolResponse(i, { action: e.target.value })}
                              className="w-full px-2 py-1.5 bg-slate-800 border border-slate-600 rounded text-slate-200 text-sm"
                              placeholder="call"
                            />
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => removeToolResponse(i)}
                        className="p-1.5 text-red-400 hover:text-red-300 self-end mb-1"
                        title="Remove override"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    {/* Response Data - Toggle between modes */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <label className="text-xs text-slate-500">Response Data</label>
                          <div className="flex text-xs bg-slate-900 rounded overflow-hidden border border-slate-600">
                            <button
                              onClick={() => updateToolResponse(i, { mode: 'fields' })}
                              className={`px-2 py-1 ${tr.mode === 'fields' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                            >
                              Fields
                            </button>
                            <button
                              onClick={() => updateToolResponse(i, { mode: 'json' })}
                              className={`px-2 py-1 ${tr.mode === 'json' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                            >
                              JSON
                            </button>
                          </div>
                        </div>
                        {tr.mode === 'fields' && (
                          <button
                            onClick={() => addField(i)}
                            className="text-xs text-blue-400 hover:text-blue-300"
                          >
                            + Add Field
                          </button>
                        )}
                      </div>

                      {tr.mode === 'fields' ? (
                        <>
                          <div className="space-y-2">
                            {tr.fields.map((field, fi) => (
                              <div key={fi} className="flex gap-2">
                                <input
                                  type="text"
                                  value={field.key}
                                  onChange={(e) => updateField(i, fi, e.target.value, field.value)}
                                  className="w-1/3 px-2 py-1.5 bg-slate-900 border border-slate-600 rounded text-slate-200 text-sm"
                                  placeholder="field_name"
                                />
                                <input
                                  type="text"
                                  value={field.value}
                                  onChange={(e) => updateField(i, fi, field.key, e.target.value)}
                                  className="flex-1 px-2 py-1.5 bg-slate-900 border border-slate-600 rounded text-slate-200 text-sm"
                                  placeholder="value (strings, numbers, or JSON)"
                                />
                                {tr.fields.length > 1 && (
                                  <button
                                    onClick={() => removeField(i, fi)}
                                    className="p-1.5 text-red-400 hover:text-red-300"
                                  >
                                    <X size={14} />
                                  </button>
                                )}
                              </div>
                            ))}
                          </div>
                          <p className="mt-2 text-xs text-slate-500">
                            Each field becomes a key in the response object. Values are auto-parsed (numbers, booleans, JSON).
                          </p>
                        </>
                      ) : (
                        <>
                          <textarea
                            value={tr.rawJson}
                            onChange={(e) => updateToolResponse(i, { rawJson: e.target.value })}
                            className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded text-slate-200 text-sm font-mono"
                            rows={6}
                            placeholder='{"status": "open", "priority": "high", "items": [1, 2, 3]}'
                          />
                          <p className="mt-2 text-xs text-slate-500">
                            Enter the complete JSON response object. This replaces the tool's normal return value.
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
              {case_.toolResponses.length === 0 && (
                <p className="text-xs text-slate-500 p-3 bg-slate-800/30 rounded-lg border border-dashed border-slate-700">
                  {scenarioTools.length > 0
                    ? 'Add overrides to inject custom tool responses for this test case'
                    : 'Link a scenario above to enable tool dropdowns, or add overrides manually'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Dataset Detail View (read-only)
interface DatasetDetailViewProps {
  dataset: DatasetDetail
  expandedCases: Set<string>
  onToggleCase: (id: string) => void
  onEdit: () => void
  onDelete: () => void
}

function DatasetDetailView({
  dataset,
  expandedCases,
  onToggleCase,
  onEdit,
  onDelete,
}: DatasetDetailViewProps) {
  const [parallel, setParallel] = useState(5)

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">{dataset.name}</h2>
          <p className="text-slate-400 text-sm">{dataset.description}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-sm"
          >
            <Edit2 size={14} />
            Edit
          </button>
          <button
            onClick={onDelete}
            className="flex items-center gap-1 px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded text-sm"
          >
            <Trash2 size={14} />
            Delete
          </button>
        </div>
      </div>

      <div className="mb-4 text-sm text-slate-400">
        {dataset.cases.length} test case{dataset.cases.length !== 1 ? 's' : ''}
        {dataset.generator && ' (generated)'}
      </div>

      <div className="space-y-2 max-h-[50vh] overflow-y-auto">
        {dataset.cases.map((c) => (
          <CaseRow
            key={c.id}
            case_={c}
            expanded={expandedCases.has(c.id)}
            onToggle={() => onToggleCase(c.id)}
          />
        ))}
      </div>

      {dataset.cases.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="flex items-center gap-4">
            <Link
              to={`/run?dataset=${dataset.id}&parallel=${parallel}`}
              className="flex items-center gap-2 px-4 py-2 bg-orange-400 hover:bg-orange-300 text-slate-900 rounded-lg font-medium"
            >
              <Play size={16} />
              Run All Cases
            </Link>
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-400">Parallel:</label>
              <input
                type="number"
                min={1}
                max={20}
                value={parallel}
                onChange={(e) => setParallel(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                className="w-16 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-200 text-sm"
              />
              <span className="text-xs text-slate-500">concurrent runs</span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

interface CaseRowProps {
  case_: DatasetCase
  expanded: boolean
  onToggle: () => void
}

function CaseRow({ case_, expanded, onToggle }: CaseRowProps) {
  return (
    <div className="panel-subtle rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-slate-700/50 transition-colors"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <span className="font-medium text-slate-200">{case_.id}</span>
        {case_.expected.length > 0 && (
          <span className="text-sm text-blue-400">
            expected: {case_.expected.join(' or ')}
          </span>
        )}
        {case_.tags.length > 0 && (
          <div className="flex gap-1 ml-auto">
            {case_.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-slate-700">
          {Object.keys(case_.variables).length > 0 && (
            <div className="mb-3">
              <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">
                Variables
              </h4>
              <pre className="text-sm text-slate-300 bg-slate-800 p-2 rounded overflow-x-auto">
                {JSON.stringify(case_.variables, null, 2)}
              </pre>
            </div>
          )}
          {Object.keys(case_.tool_responses).length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">
                Tool Response Overrides
              </h4>
              <pre className="text-sm text-slate-300 bg-slate-800 p-2 rounded overflow-x-auto">
                {JSON.stringify(case_.tool_responses, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function datasetToEditable(dataset: DatasetDetail): EditableDataset {
  return {
    id: dataset.id,
    name: dataset.name,
    description: dataset.description,
    scenarioId: dataset.scenario_id || '',
    cases: dataset.cases.map((c) => ({
      id: c.id,
      expected: c.expected || [],
      variables: Object.entries(c.variables).map(([key, value]) => ({
        key,
        value: typeof value === 'string' ? value : JSON.stringify(value),
      })),
      toolResponses: Object.entries(c.tool_responses).map(([toolAction, fieldsObj]) => {
        const parts = toolAction.split('.')
        const tool = parts[0] || toolAction
        const action = parts.slice(1).join('.') || ''
        const fields: Array<{ key: string; value: string }> = []
        let hasComplexValues = false

        if (typeof fieldsObj === 'object' && fieldsObj !== null) {
          for (const [key, value] of Object.entries(fieldsObj)) {
            if (typeof value === 'object' && value !== null) {
              hasComplexValues = true
            }
            fields.push({
              key,
              value: typeof value === 'string' ? value : JSON.stringify(value),
            })
          }
        }
        if (fields.length === 0) {
          fields.push({ key: '', value: '' })
        }

        return {
          tool,
          action,
          mode: hasComplexValues ? 'json' as const : 'fields' as const,
          fields,
          rawJson: JSON.stringify(fieldsObj, null, 2),
        }
      }),
      tags: c.tags,
    })),
  }
}

function editableToYaml(data: EditableDataset): string {
  const lines: string[] = []

  if (data.name) {
    lines.push(`name: "${data.name}"`)
  }
  if (data.description) {
    lines.push(`description: |`)
    data.description.split('\n').forEach(line => {
      lines.push(`  ${line}`)
    })
  }
  if (data.scenarioId) {
    lines.push(`scenario_id: ${data.scenarioId}`)
  }
  lines.push('')
  lines.push('cases:')

  for (const c of data.cases) {
    lines.push(`  - id: ${c.id}`)
    if (c.expected.length === 1) {
      lines.push(`    expected: ${c.expected[0]}`)
    } else if (c.expected.length > 1) {
      lines.push(`    expected: [${c.expected.join(', ')}]`)
    }

    const validVars = c.variables.filter(v => v.key.trim())
    if (validVars.length > 0) {
      lines.push(`    variables:`)
      for (const v of validVars) {
        const value = parseValue(v.value)
        if (typeof value === 'string') {
          lines.push(`      ${v.key}: "${value}"`)
        } else {
          lines.push(`      ${v.key}: ${JSON.stringify(value)}`)
        }
      }
    }

    const validTr = c.toolResponses.filter(t => {
      if (!t.tool.trim()) return false
      if (t.mode === 'json') return t.rawJson.trim().length > 0
      return t.fields.some(f => f.key.trim())
    })
    if (validTr.length > 0) {
      lines.push(`    tool_responses:`)
      for (const tr of validTr) {
        const toolAction = tr.action ? `${tr.tool}.${tr.action}` : tr.tool
        lines.push(`      ${toolAction}:`)

        if (tr.mode === 'json') {
          try {
            const jsonObj = JSON.parse(tr.rawJson)
            if (typeof jsonObj === 'object' && jsonObj !== null) {
              for (const [key, value] of Object.entries(jsonObj)) {
                if (typeof value === 'string') {
                  lines.push(`        ${key}: "${value}"`)
                } else {
                  lines.push(`        ${key}: ${JSON.stringify(value)}`)
                }
              }
            }
          } catch {
            lines.push(`        # Invalid JSON`)
          }
        } else {
          for (const field of tr.fields) {
            if (!field.key.trim()) continue
            const parsed = parseValue(field.value)
            if (typeof parsed === 'string') {
              lines.push(`        ${field.key}: "${parsed}"`)
            } else {
              lines.push(`        ${field.key}: ${JSON.stringify(parsed)}`)
            }
          }
        }
      }
    }

    if (c.tags.length > 0) {
      lines.push(`    tags: [${c.tags.join(', ')}]`)
    }
  }

  return lines.join('\n')
}

function parseValue(value: string): string | number | boolean | object {
  // Try to parse as JSON
  try {
    return JSON.parse(value)
  } catch {
    // Try number
    const num = Number(value)
    if (!isNaN(num) && value.trim() !== '') {
      return num
    }
    // Try boolean
    if (value.toLowerCase() === 'true') return true
    if (value.toLowerCase() === 'false') return false
    // Return as string
    return value
  }
}
