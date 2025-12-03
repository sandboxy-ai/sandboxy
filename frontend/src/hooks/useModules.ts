import { useState, useEffect, useCallback } from 'react'
import { api, Module, Agent } from '../lib/api'

export function useModules() {
  const [modules, setModules] = useState<Module[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchModules = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getModules()
      setModules(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch modules')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchModules()
  }, [fetchModules])

  return { modules, loading, error, refetch: fetchModules }
}

export function useModule(slug: string | undefined) {
  const [module, setModule] = useState<Module | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchModule = useCallback(async () => {
    if (!slug) {
      setModule(null)
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await api.getModule(slug)
      setModule(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch module')
    } finally {
      setLoading(false)
    }
  }, [slug])

  useEffect(() => {
    fetchModule()
  }, [fetchModule])

  return { module, loading, error, refetch: fetchModule }
}

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAgents = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getAgents()
      setAgents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch agents')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAgents()
  }, [fetchAgents])

  return { agents, loading, error, refetch: fetchAgents }
}
