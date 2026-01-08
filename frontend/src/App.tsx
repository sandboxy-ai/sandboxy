import { Routes, Route, useParams } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import HomePage from './pages/HomePage'
import SessionPage from './pages/SessionPage'
import BuilderPage from './pages/BuilderPage'
import ArenaPage from './pages/ArenaPage'
import AutoSimPage from './pages/AutoSimPage'
import ReplayPage from './pages/ReplayPage'
import ChallengePage from './pages/ChallengePage'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import { FeatureProvider } from './lib/features'

// Wrapper to force remount when slug changes
function SessionPageWrapper() {
  const { moduleSlug } = useParams()
  return <SessionPage key={moduleSlug} />
}

function App() {
  return (
    <FeatureProvider>
      <ErrorBoundary>
        <Layout>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/simulations" element={<HomePage />} />
            {/* Legacy redirect */}
            <Route path="/scenarios" element={<HomePage />} />
            <Route path="/session/:moduleSlug" element={<SessionPageWrapper />} />
            <Route path="/builder" element={<BuilderPage />} />
            <Route path="/builder/:moduleSlug" element={<BuilderPage />} />
            <Route path="/arena" element={<ArenaPage />} />
            <Route path="/autosim" element={<AutoSimPage />} />
            <Route path="/challenge" element={<ChallengePage />} />
            <Route path="/challenge/:challengeId" element={<ChallengePage />} />
            <Route path="/replay/:sessionId" element={<ReplayPage />} />
          </Routes>
        </Layout>
      </ErrorBoundary>
    </FeatureProvider>
  )
}

export default App
