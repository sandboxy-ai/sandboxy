import { Routes, Route, useParams } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import HomePage from './pages/HomePage'
import SessionPage from './pages/SessionPage'
import BuilderPage from './pages/BuilderPage'
import Layout from './components/Layout'

// Wrapper to force remount when slug changes
function SessionPageWrapper() {
  const { moduleSlug } = useParams()
  return <SessionPage key={moduleSlug} />
}

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/scenarios" element={<HomePage />} />
        <Route path="/session/:moduleSlug" element={<SessionPageWrapper />} />
        <Route path="/builder" element={<BuilderPage />} />
        <Route path="/builder/:moduleSlug" element={<BuilderPage />} />
      </Routes>
    </Layout>
  )
}

export default App
