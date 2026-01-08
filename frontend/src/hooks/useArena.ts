import { useState, useEffect, useCallback } from 'react'
import {
  api,
  ArenaPrompt,
  ArenaModel,
  ArenaCategory,
  ArenaRunResponse,
  JudgeTemplate,
} from '../lib/api'

export function useArenaPrompts(category?: string) {
  const [prompts, setPrompts] = useState<ArenaPrompt[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPrompts = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getArenaPrompts(category)
      setPrompts(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompts')
    } finally {
      setLoading(false)
    }
  }, [category])

  useEffect(() => {
    fetchPrompts()
  }, [fetchPrompts])

  return { prompts, loading, error, refetch: fetchPrompts }
}

export function useArenaModels() {
  const [models, setModels] = useState<ArenaModel[]>([])
  const [providers, setProviders] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchModels = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getArenaModels()
      setModels(data.models)
      setProviders(data.providers)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch models')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchModels()
  }, [fetchModels])

  return { models, providers, loading, error, refetch: fetchModels }
}

export function useArenaCategories() {
  const [categories, setCategories] = useState<ArenaCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getArenaCategories()
      .then(setCategories)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to fetch categories'))
      .finally(() => setLoading(false))
  }, [])

  return { categories, loading, error }
}

export function useArenaJudges() {
  const [judges, setJudges] = useState<JudgeTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchJudges = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getArenaJudges()
      setJudges(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch judges')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchJudges()
  }, [fetchJudges])

  return { judges, loading, error, refetch: fetchJudges }
}

interface UseArenaRunOptions {
  onSuccess?: (result: ArenaRunResponse) => void
  onError?: (error: Error) => void
}

export function useArenaRun(options: UseArenaRunOptions = {}) {
  const [result, setResult] = useState<ArenaRunResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runArena = useCallback(async (params: {
    prompt_id?: string
    prompt_text?: string
    system_prompt?: string
    models: string[]
    variables?: Record<string, unknown>
    temperature?: number
    max_tokens?: number
    judge_template_id?: string
    judge_config?: Record<string, unknown>
  }) => {
    try {
      setLoading(true)
      setError(null)
      setResult(null)
      const data = await api.runArena(params)
      setResult(data)
      options.onSuccess?.(data)
      return data
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Arena run failed')
      setError(error.message)
      options.onError?.(error)
      throw error
    } finally {
      setLoading(false)
    }
  }, [options])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
    setLoading(false)
  }, [])

  return { result, loading, error, runArena, reset }
}
