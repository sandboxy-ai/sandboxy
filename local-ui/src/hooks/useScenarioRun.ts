/**
 * Hook for running scenarios and tracking state.
 */

import { useState, useCallback } from 'react'
import { api, RunScenarioResponse, CompareModelsResponse } from '../lib/api'

export type RunState = 'idle' | 'running' | 'completed' | 'error'

export interface UseScenarioRunResult {
  state: RunState
  result: RunScenarioResponse | null
  comparison: CompareModelsResponse | null
  error: string | null
  runScenario: (scenarioId: string, model: string, variables?: Record<string, unknown>) => Promise<void>
  compareModels: (scenarioId: string, models: string[], runsPerModel?: number, variables?: Record<string, unknown>) => Promise<void>
  reset: () => void
}

export function useScenarioRun(): UseScenarioRunResult {
  const [state, setState] = useState<RunState>('idle')
  const [result, setResult] = useState<RunScenarioResponse | null>(null)
  const [comparison, setComparison] = useState<CompareModelsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reset = useCallback(() => {
    setState('idle')
    setResult(null)
    setComparison(null)
    setError(null)
  }, [])

  const runScenario = useCallback(async (
    scenarioId: string,
    model: string,
    variables?: Record<string, unknown>
  ) => {
    reset()
    setState('running')

    try {
      const response = await api.runScenario({
        scenario_id: scenarioId,
        model,
        variables,
      })

      if (response.error) {
        setState('error')
        setError(response.error)
      } else {
        setState('completed')
        setResult(response)
      }
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }, [reset])

  const compareModels = useCallback(async (
    scenarioId: string,
    models: string[],
    runsPerModel: number = 1,
    variables?: Record<string, unknown>
  ) => {
    reset()
    setState('running')

    try {
      const response = await api.compareModels({
        scenario_id: scenarioId,
        models,
        runs_per_model: runsPerModel,
        variables,
      })

      setState('completed')
      setComparison(response)
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }, [reset])

  return {
    state,
    result,
    comparison,
    error,
    runScenario,
    compareModels,
    reset,
  }
}
