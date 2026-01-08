/**
 * @sandboxy/frontend - Reusable components, hooks, and utilities for Sandboxy.
 *
 * This package exports the core frontend functionality that can be used
 * by both the OSS frontend and Cloud frontend.
 *
 * @example
 * ```tsx
 * import { api, useSession, ShareButton } from '@sandboxy/frontend';
 * import '@sandboxy/frontend/styles';
 * ```
 */

// =============================================================================
// Components
// =============================================================================

export { default as Slider } from './components/Slider';
export { default as VariableInputs } from './components/VariableInputs';
export { default as ContextPanel } from './components/ContextPanel';
export { default as EventPanel } from './components/EventPanel';
export { default as ShareButton } from './components/ShareButton';
export { default as ResultsDashboard } from './components/ResultsDashboard';
export { ToolConfigForm } from './components/ToolConfigForm';
export { default as BlitzTab } from './components/BlitzTab';
// Note: Layout is NOT exported - it's specific to the OSS app shell

// =============================================================================
// Hooks
// =============================================================================

export { useSession } from './hooks/useSession';
export type { ChatMessage } from './hooks/useSession';

export { useModules, useModule, useAgents } from './hooks/useModules';

export {
  useArenaPrompts,
  useArenaModels,
  useArenaCategories,
  useArenaJudges,
  useArenaRun,
} from './hooks/useArena';

// =============================================================================
// API Client
// =============================================================================

export { api } from './lib/api';

// Export all API types
export type {
  Module,
  Agent,
  Session,
  SessionEvent,
  SessionExport,
  ContextFieldConfig,
  EventConfig,
  EventsConfig,
  ModuleVariable,
  ModuleUI,
  ToolInfo,
  ToolConfigField,
  ToolAction,
  ArenaPrompt,
  ArenaModel,
  JudgeTemplate,
  ArenaRunResponse,
  ArenaRunDetail,
  AutoSimScenario,
  AutoSimScenarioDetail,
  AutoSimPersonality,
  AutoSimEvent,
  AutoSimRunResponse,
  AutoSimRunDetail,
  AutoSimResults,
  ChallengeSummary,
  ChallengeDetail,
  ChallengeGoal,
  ChallengeStartResponse,
  ChallengeCompleteResponse,
  GoalResult,
  // Blitz types
  BlitzResponse,
  CreateBlitzRequest,
  CreateBlitzResponse,
  BlitzDetail,
  BlitzTemplate,
  BlitzTemplateCategory,
  BlitzTemplateVariable,
} from './lib/api';

// =============================================================================
// Features
// =============================================================================

export { FeatureProvider, useFeatures, FeatureGate } from './lib/features';
