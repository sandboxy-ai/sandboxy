import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import RunPage from './pages/RunPage'
import ResultsPage from './pages/ResultsPage'
import BuilderPage from './pages/BuilderPage'
import ToolBuilderPage from './pages/ToolBuilderPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="run/:scenarioId" element={<RunPage />} />
        <Route path="results" element={<ResultsPage />} />
        <Route path="builder" element={<BuilderPage />} />
        <Route path="tool-builder" element={<ToolBuilderPage />} />
      </Route>
    </Routes>
  )
}

export default App
