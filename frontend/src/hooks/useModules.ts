import { useState, useEffect, useCallback } from 'react'
import yaml from 'js-yaml'
import { api, Module, Agent, ModuleVariable, ModuleEnvironment, ModuleMetadata, ModuleUI } from '../lib/api'

// Parse YAML content and extract structured fields
function parseModuleYaml(module: Module): Module {
  if (!module.yaml_content) return module

  try {
    const parsed = yaml.load(module.yaml_content) as Record<string, unknown>

    return {
      ...module,
      variables: (parsed.variables as ModuleVariable[]) || [],
      environment: (parsed.environment as ModuleEnvironment) || undefined,
      metadata: (parsed.metadata as ModuleMetadata) || undefined,
      ui: (parsed.ui as ModuleUI) || undefined,
    }
  } catch {
    console.error('Failed to parse module YAML:', module.slug)
    return module
  }
}

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

  useEffect(() => {
    if (!slug) {
      setModule(null)
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)
    setModule(null) // Reset module when slug changes

    api.getModule(slug)
      .then(data => {
        if (!cancelled) {
          setModule(parseModuleYaml(data))
          setLoading(false)
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch module')
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [slug])

  const refetch = useCallback(() => {
    if (slug) {
      setLoading(true)
      api.getModule(slug)
        .then(data => setModule(parseModuleYaml(data)))
        .catch(err => setError(err instanceof Error ? err.message : 'Failed to fetch module'))
        .finally(() => setLoading(false))
    }
  }, [slug])

  return { module, loading, error, refetch }
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
