import { useState } from 'react'
import { Share2, Copy, Check, Twitter, Download } from 'lucide-react'
import { api } from '../lib/api'

interface ShareButtonProps {
  sessionId: string | null
  score?: number | null
  moduleName?: string
}

export default function ShareButton({ sessionId, score, moduleName }: ShareButtonProps) {
  const [showMenu, setShowMenu] = useState(false)
  const [copied, setCopied] = useState(false)

  if (!sessionId) return null

  const shareUrl = `${window.location.origin}/replay/${sessionId}`

  const getScoreEmoji = () => {
    if (score === null || score === undefined) return ''
    if (score >= 0.8) return '🏆'
    if (score >= 0.6) return '✅'
    if (score >= 0.4) return '⚠️'
    return '❌'
  }

  const shareText = moduleName
    ? `${getScoreEmoji()} I just played "${moduleName}" on Sandboxy! Score: ${score !== null ? `${Math.round((score || 0) * 100)}%` : 'N/A'}`
    : `Check out my Sandboxy session!`

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleTwitterShare = () => {
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`
    window.open(url, '_blank', 'width=550,height=420')
    setShowMenu(false)
  }

  const handleDownloadJson = async () => {
    if (!sessionId) return
    try {
      const data = await api.exportSession(sessionId)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sandboxy-session-${sessionId}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setShowMenu(false)
    } catch (err) {
      console.error('Failed to download:', err)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="flex items-center gap-2 px-3 py-1.5 bg-accent hover:bg-accent-hover rounded-lg text-white text-sm transition-colors"
      >
        <Share2 size={16} />
        Share
      </button>

      {showMenu && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowMenu(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 top-full mt-2 z-20 bg-dark-card border border-dark-border rounded-lg shadow-lg overflow-hidden min-w-[200px]">
            <button
              onClick={handleCopyLink}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-dark-hover transition-colors text-gray-300"
            >
              {copied ? (
                <>
                  <Check size={16} className="text-green-400" />
                  <span className="text-green-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy size={16} />
                  <span>Copy Link</span>
                </>
              )}
            </button>

            <button
              onClick={handleTwitterShare}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-dark-hover transition-colors text-gray-300"
            >
              <Twitter size={16} />
              <span>Share on X</span>
            </button>

            <button
              onClick={handleDownloadJson}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-dark-hover transition-colors text-gray-300"
            >
              <Download size={16} />
              <span>Download JSON</span>
            </button>
          </div>
        </>
      )}
    </div>
  )
}
