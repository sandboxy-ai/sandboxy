import { Link, useLocation } from 'react-router-dom'
import { Home, Wrench } from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', icon: Home, label: 'Scenarios' },
    { path: '/builder', icon: Wrench, label: 'Builder' },
  ]

  return (
    <div className="min-h-screen bg-dark-bg flex">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-card border-r border-dark-border flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-dark-border">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">S</span>
            </div>
            <span className="text-xl font-semibold text-white">Sandboxy</span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map(({ path, icon: Icon, label }) => {
              const isActive = location.pathname === path ||
                (path !== '/' && location.pathname.startsWith(path))

              return (
                <li key={path}>
                  <Link
                    to={path}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-accent text-white'
                        : 'text-gray-400 hover:bg-dark-hover hover:text-white'
                    }`}
                  >
                    <Icon size={20} />
                    <span>{label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-dark-border">
          <p className="text-xs text-gray-500">
            Interactive Agent Simulation
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
