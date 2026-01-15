import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, FileText, Wrench, Database, Sun, Moon } from 'lucide-react'
import { useState, useEffect } from 'react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/results', label: 'Results', icon: FileText },
  { path: '/builder', label: 'Builder', icon: Wrench },
  { path: '/datasets', label: 'Datasets', icon: Database },
]

export default function Layout() {
  const location = useLocation()
  const [isLight, setIsLight] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'light'
    }
    return false
  })

  useEffect(() => {
    if (isLight) {
      document.documentElement.classList.add('light')
      localStorage.setItem('theme', 'light')
    } else {
      document.documentElement.classList.remove('light')
      localStorage.setItem('theme', 'dark')
    }
  }, [isLight])

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="p-5 border-b border-slate-800/70">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold" style={{ color: 'var(--app-text)' }}>Sandboxy Local</h1>
              <p className="text-sm" style={{ color: 'var(--app-muted)' }}>Development Server</p>
            </div>
            <button
              onClick={() => setIsLight(!isLight)}
              className="p-2 rounded-lg transition-colors hover:bg-slate-500/20"
              title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
            >
              {isLight ? <Moon size={20} style={{ color: 'var(--app-muted)' }} /> : <Sun size={20} style={{ color: 'var(--app-muted)' }} />}
            </button>
          </div>
        </div>

        <nav className="p-4">
          <ul className="space-y-2">
            {navItems.map(({ path, label, icon: Icon }) => (
              <li key={path}>
                <Link
                  to={path}
                  data-active={location.pathname === path}
                  className="nav-link"
                >
                  <Icon size={20} />
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
