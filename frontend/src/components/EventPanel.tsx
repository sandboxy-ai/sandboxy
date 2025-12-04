import { useState } from 'react'
import { Zap, ChevronDown, ChevronUp } from 'lucide-react'
import { EventsConfig } from '../lib/api'

interface EventPanelProps {
  config: EventsConfig
  onInjectEvent: (eventId: string, toolName: string) => void
  disabled?: boolean
  lastEventMessage?: string | null
}

export default function EventPanel({
  config,
  onInjectEvent,
  disabled = false,
  lastEventMessage,
}: EventPanelProps) {
  const [expanded, setExpanded] = useState(true)
  const [recentlyClicked, setRecentlyClicked] = useState<string | null>(null)

  const handleClick = (eventId: string) => {
    if (disabled) return
    onInjectEvent(eventId, config.tool)
    setRecentlyClicked(eventId)
    setTimeout(() => setRecentlyClicked(null), 1000)
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-dark-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-accent" />
          <span className="text-sm font-medium text-white">Events</span>
        </div>
        {expanded ? (
          <ChevronUp size={16} className="text-gray-400" />
        ) : (
          <ChevronDown size={16} className="text-gray-400" />
        )}
      </button>

      {/* Last event notification */}
      {lastEventMessage && (
        <div className="px-3 py-2 bg-accent/10 border-t border-dark-border animate-event-flash">
          <p className="text-xs text-accent">{lastEventMessage}</p>
        </div>
      )}

      {/* Event buttons */}
      {expanded && (
        <div className="p-3 border-t border-dark-border space-y-3">
          {Object.entries(config.categories).map(([category, events]) => (
            <div key={category}>
              <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                {category}
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {events.map((event) => (
                  <button
                    key={event.id}
                    onClick={() => handleClick(event.id)}
                    disabled={disabled}
                    title={event.description}
                    className={`
                      flex items-center gap-2 px-2 py-1.5 rounded text-left
                      text-xs transition-all
                      ${disabled
                        ? 'opacity-50 cursor-not-allowed bg-dark-bg'
                        : 'bg-dark-bg hover:bg-dark-hover hover:border-accent border border-dark-border cursor-pointer'
                      }
                      ${recentlyClicked === event.id ? 'ring-2 ring-accent ring-opacity-50' : ''}
                    `}
                  >
                    {event.icon && <span className="text-sm">{event.icon}</span>}
                    <span className="text-gray-300 truncate">{event.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
