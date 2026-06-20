import { Routes, Route, NavLink } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useEffect, useState } from 'react'
import { Search, GitBranch } from 'lucide-react'
import Header from './components/Header.jsx'
import ReviewPage from './pages/ReviewPage.jsx'
import ArchitecturePage from './pages/ArchitecturePage.jsx'
import { healthCheck } from './utils/api.js'

export default function App() {
  const [apiStatus, setApiStatus] = useState('checking')

  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  const navClass = ({ isActive }) =>
    `flex items-center gap-2 px-4 py-3 text-xs font-medium transition-colors border-b-2 ${
      isActive
        ? 'text-white border-accent'
        : 'text-muted border-transparent hover:text-white'
    }`

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header apiStatus={apiStatus} />

      {/* Nav tabs */}
      <nav className="flex bg-surface border-b border-border px-4">
        <NavLink to="/" end className={navClass}>
          <Search size={13} />
          Claim Review
        </NavLink>
        <NavLink to="/architecture" className={navClass}>
          <GitBranch size={13} />
          Architecture
        </NavLink>
      </nav>

      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<ReviewPage />} />
          <Route path="/architecture" element={
            <div className="h-full overflow-y-auto">
              <ArchitecturePage />
            </div>
          } />
        </Routes>
      </div>

      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#161b2a',
            color: '#e8ecf5',
            border: '1px solid #1e2740',
            fontSize: '13px',
          },
        }}
      />
    </div>
  )
}
