import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Dashboard } from '@/pages/Dashboard'
import { ProjectWorkspace } from '@/pages/ProjectWorkspace'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects/:projectId" element={<ProjectWorkspace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
