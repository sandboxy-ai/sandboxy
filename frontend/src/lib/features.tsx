/**
 * Feature flag system for Sandboxy.
 *
 * Features are advertised by the backend via /api/v1/features.
 * Cloud extensions register their features there.
 * Frontend uses this to conditionally enable UI elements.
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api } from './api';

interface FeaturesContextValue {
  features: string[];
  loading: boolean;
  hasFeature: (feature: string) => boolean;
}

const FeaturesContext = createContext<FeaturesContextValue>({
  features: [],
  loading: true,
  hasFeature: () => false,
});

interface FeatureProviderProps {
  children: ReactNode;
}

/**
 * Provider component that fetches available features from the backend.
 *
 * Wrap your app with this to enable feature detection:
 *
 * ```tsx
 * <FeatureProvider>
 *   <App />
 * </FeatureProvider>
 * ```
 */
export function FeatureProvider({ children }: FeatureProviderProps) {
  const [features, setFeatures] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getFeatures()
      .then((response) => {
        setFeatures(response.features || []);
      })
      .catch((err) => {
        console.warn('Failed to fetch features:', err);
        // Default to empty features on error
        setFeatures([]);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const hasFeature = (feature: string) => features.includes(feature);

  return (
    <FeaturesContext.Provider value={{ features, loading, hasFeature }}>
      {children}
    </FeaturesContext.Provider>
  );
}

/**
 * Hook to access feature flags.
 *
 * ```tsx
 * function MyComponent() {
 *   const { hasFeature, loading } = useFeatures();
 *
 *   if (loading) return <Spinner />;
 *
 *   return (
 *     <div>
 *       {hasFeature('video-export') && <VideoExportButton />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useFeatures() {
  return useContext(FeaturesContext);
}

/**
 * Component that only renders children if a feature is enabled.
 *
 * ```tsx
 * <FeatureGate feature="video-export">
 *   <VideoExportButton />
 * </FeatureGate>
 * ```
 */
interface FeatureGateProps {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function FeatureGate({ feature, children, fallback = null }: FeatureGateProps) {
  const { hasFeature, loading } = useFeatures();

  if (loading) return null;
  if (!hasFeature(feature)) return <>{fallback}</>;

  return <>{children}</>;
}
