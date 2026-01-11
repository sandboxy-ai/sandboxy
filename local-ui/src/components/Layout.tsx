import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, FileText, Wrench } from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/results', label: 'Results', icon: FileText },
  { path: '/builder', label: 'Builder', icon: Wrench },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="p-5 border-b border-slate-800/70">
          <h1 className="text-xl font-semibold text-slate-100">Sandboxy Local</h1>
          <p className="text-sm text-slate-400">Development Server</p>
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
