import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SessionPage from './pages/SessionPage'
import BuilderPage from './pages/BuilderPage'
import Layout from './components/Layout'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/session/:moduleSlug" element={<SessionPage />} />
        <Route path="/builder" element={<BuilderPage />} />
        <Route path="/builder/:moduleSlug" element={<BuilderPage />} />
      </Routes>
    </Layout>
  )
}

export default App
