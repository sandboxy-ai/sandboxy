import { Link } from 'react-router-dom'
import { Play, Shield, BarChart3, Gamepad2, Github, ChevronRight, Zap, Bot, Target, Sparkles, ArrowRight } from 'lucide-react'
import { useModules } from '../hooks/useModules'

export default function LandingPage() {
  const { modules } = useModules()

  // Featured scenarios
  const featuredScenarios = modules.slice(0, 3)

  return (
    <div className="min-h-screen overflow-hidden">
      {/* Hero Section */}
      <section className="relative py-24 px-8">
        {/* Animated background */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-accent/30 rounded-full blur-[100px] animate-pulse" />
          <div className="absolute top-20 -left-40 w-96 h-96 bg-purple-500/20 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
          <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-blue-500/20 rounded-full blur-[80px] animate-pulse" style={{ animationDelay: '2s' }} />
        </div>

        {/* Grid pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px',
          }}
        />

        <div className="max-w-6xl mx-auto text-center relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-gradient-to-r from-accent/20 to-purple-500/20 border border-accent/30 rounded-full px-5 py-2 text-sm mb-8 backdrop-blur-sm">
            <Sparkles size={14} className="text-accent" />
            <span className="text-gray-300">Open Source AI Agent Testing Platform</span>
            <span className="text-accent font-medium">v0.2</span>
          </div>

          {/* Main headline */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight tracking-tight">
            <span className="text-white">Test AI Agents in</span>
            <br />
            <span className="bg-gradient-to-r from-accent via-purple-400 to-blue-400 bg-clip-text text-transparent">
              Controlled Chaos
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Run AI agents through simulated scenarios. Find vulnerabilities,
            benchmark performance, or watch them hilariously fail at running
            a lemonade stand.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/scenarios"
              className="group inline-flex items-center justify-center gap-2 bg-gradient-to-r from-accent to-accent-hover hover:from-accent-hover hover:to-accent text-white font-semibold px-8 py-4 rounded-xl transition-all shadow-lg shadow-accent/25 hover:shadow-accent/40 hover:scale-105"
            >
              <Play size={20} />
              Try a Scenario
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </Link>
            <a
              href="https://github.com/sandboxy-ai/sandboxy"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 hover:border-white/20 text-white font-semibold px-8 py-4 rounded-xl transition-all"
            >
              <Github size={20} />
              View on GitHub
            </a>
          </div>

          {/* Stats */}
          <div className="flex justify-center gap-12 mt-16 pt-8 border-t border-white/5">
            <div className="text-center">
              <div className="text-3xl font-bold text-white">5+</div>
              <div className="text-sm text-gray-500 mt-1">Scenarios</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white">6</div>
              <div className="text-sm text-gray-500 mt-1">Mock Tools</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white">100%</div>
              <div className="text-sm text-gray-500 mt-1">Open Source</div>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20 px-8 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-accent/5 to-transparent" />

        <div className="max-w-6xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">
              Three Ways to Use Sandboxy
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto text-lg">
              Whether you're securing AI systems, comparing models, or creating
              viral content, Sandboxy has you covered.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {/* Security */}
            <div className="group relative bg-gradient-to-br from-dark-card to-dark-bg border border-dark-border rounded-2xl p-8 hover:border-red-500/50 transition-all hover:-translate-y-1">
              <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
              <div className="relative">
                <div className="w-14 h-14 bg-red-500/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Shield className="text-red-400" size={28} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Security Testing</h3>
                <p className="text-gray-400 mb-6 leading-relaxed">
                  Red-team your AI agents. Test for prompt injection, social engineering
                  vulnerabilities, and policy violations in a safe environment.
                </p>
                <ul className="text-sm text-gray-500 space-y-2">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-red-400 rounded-full" />
                    Prompt injection attacks
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-red-400 rounded-full" />
                    Social engineering defense
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-red-400 rounded-full" />
                    Policy compliance testing
                  </li>
                </ul>
              </div>
            </div>

            {/* Benchmarking */}
            <div className="group relative bg-gradient-to-br from-dark-card to-dark-bg border border-dark-border rounded-2xl p-8 hover:border-blue-500/50 transition-all hover:-translate-y-1">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
              <div className="relative">
                <div className="w-14 h-14 bg-blue-500/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <BarChart3 className="text-blue-400" size={28} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Benchmarking</h3>
                <p className="text-gray-400 mb-6 leading-relaxed">
                  Compare AI models head-to-head. Run the same scenario across
                  GPT-4, Claude, Gemini and more. Get numeric scores for easy comparison.
                </p>
                <ul className="text-sm text-gray-500 space-y-2">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                    Multi-model comparison
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                    Deterministic scoring
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                    CSV/JSON export
                  </li>
                </ul>
              </div>
            </div>

            {/* Gaming/Content */}
            <div className="group relative bg-gradient-to-br from-dark-card to-dark-bg border border-dark-border rounded-2xl p-8 hover:border-purple-500/50 transition-all hover:-translate-y-1">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
              <div className="relative">
                <div className="w-14 h-14 bg-purple-500/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Gamepad2 className="text-purple-400" size={28} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Interactive Play</h3>
                <p className="text-gray-400 mb-6 leading-relaxed">
                  Watch AI try (and fail) at running businesses, handling bridezillas,
                  or negotiating with you. Perfect for creating viral content.
                </p>
                <ul className="text-sm text-gray-500 space-y-2">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-purple-400 rounded-full" />
                    Inject chaos events
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-purple-400 rounded-full" />
                    Share results
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-purple-400 rounded-full" />
                    Create viral clips
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Scenarios */}
      {featuredScenarios.length > 0 && (
        <section className="py-20 px-8">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-12">
              <div>
                <h2 className="text-4xl font-bold text-white mb-3">Featured Scenarios</h2>
                <p className="text-gray-400 text-lg">Try one of our most popular scenarios</p>
              </div>
              <Link
                to="/scenarios"
                className="group flex items-center gap-2 text-accent hover:text-accent-hover transition-colors font-medium"
              >
                View All
                <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {featuredScenarios.map((module, index) => (
                <Link
                  key={module.id}
                  to={`/session/${module.slug}`}
                  className="group relative overflow-hidden bg-dark-card border border-dark-border rounded-2xl p-6 hover:border-accent/50 transition-all hover:-translate-y-1"
                >
                  {/* Gradient overlay on hover */}
                  <div className="absolute inset-0 bg-gradient-to-br from-accent/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                  {/* Number badge */}
                  <div className="absolute top-4 right-4 w-8 h-8 bg-dark-bg rounded-lg flex items-center justify-center text-sm font-bold text-gray-500 group-hover:text-accent transition-colors">
                    {index + 1}
                  </div>

                  <div className="relative">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-accent/20 to-purple-500/20 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Bot className="text-accent" size={24} />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-white group-hover:text-accent transition-colors">
                          {module.name}
                        </h3>
                        {module.category && (
                          <span className="text-xs text-gray-500 capitalize">{module.category}</span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-gray-400 line-clamp-2 mb-4">
                      {module.description || 'No description available'}
                    </p>
                    <div className="flex items-center text-sm text-accent font-medium">
                      <span>Try now</span>
                      <ArrowRight size={14} className="ml-1 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* How It Works */}
      <section className="py-20 px-8 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-dark-card/50 to-transparent" />

        <div className="max-w-6xl mx-auto relative z-10">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            How It Works
          </h2>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              { num: '01', title: 'Choose a Scenario', desc: 'Pick from our library or create your own using YAML' },
              { num: '02', title: 'Configure Variables', desc: 'Adjust difficulty, agent model, and parameters' },
              { num: '03', title: 'Run & Interact', desc: 'Watch the agent work, inject events, or chat' },
              { num: '04', title: 'Review Results', desc: 'See scores, export data, and share results' },
            ].map((step, i) => (
              <div key={i} className="text-center relative">
                {/* Connector line */}
                {i < 3 && (
                  <div className="hidden md:block absolute top-8 left-[60%] w-[80%] h-px bg-gradient-to-r from-accent/50 to-transparent" />
                )}

                <div className="w-16 h-16 bg-gradient-to-br from-accent/20 to-purple-500/20 border border-accent/30 rounded-2xl flex items-center justify-center mx-auto mb-5">
                  <span className="text-accent font-bold text-lg">{step.num}</span>
                </div>
                <h3 className="font-semibold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-8">
        <div className="max-w-4xl mx-auto">
          <div className="relative overflow-hidden bg-gradient-to-br from-accent/20 via-purple-500/10 to-blue-500/20 border border-accent/20 rounded-3xl p-12">
            {/* Background effects */}
            <div className="absolute -top-20 -right-20 w-40 h-40 bg-accent/30 rounded-full blur-[60px]" />
            <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-purple-500/30 rounded-full blur-[60px]" />

            <div className="relative text-center">
              <Target className="mx-auto text-accent mb-6" size={56} />
              <h2 className="text-4xl font-bold text-white mb-4">
                Ready to Test Your AI?
              </h2>
              <p className="text-gray-300 mb-8 text-lg max-w-lg mx-auto">
                Start with a pre-built scenario or create your own.
                No account required.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/scenarios"
                  className="group inline-flex items-center justify-center gap-2 bg-white text-dark-bg font-semibold px-8 py-4 rounded-xl transition-all hover:bg-gray-100 shadow-lg"
                >
                  <Play size={20} />
                  Browse Scenarios
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link
                  to="/builder"
                  className="inline-flex items-center justify-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 text-white font-semibold px-8 py-4 rounded-xl transition-all hover:bg-white/20"
                >
                  Create Your Own
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 px-8 border-t border-dark-border">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-accent to-purple-500 rounded-xl flex items-center justify-center">
              <Bot size={22} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-white text-lg">Sandboxy</span>
              <p className="text-xs text-gray-500">AI Agent Testing Platform</p>
            </div>
          </div>

          <div className="flex items-center gap-8 text-sm">
            <a href="https://github.com/sandboxy-ai/sandboxy" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
              GitHub
            </a>
            <a href="https://github.com/sandboxy-ai/sandboxy/blob/main/docs/README.md" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
              Docs
            </a>
            <a href="https://discord.gg/sandboxy" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
              Discord
            </a>
            <span className="text-gray-600">MIT License</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
