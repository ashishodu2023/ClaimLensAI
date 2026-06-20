import { ScanSearch } from 'lucide-react'

export default function Header({ apiStatus }) {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-surface flex items-center gap-3 px-6 py-3.5">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center flex-shrink-0">
        <ScanSearch size={16} className="text-white" />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="font-bold text-[16px] tracking-tight text-white">ClaimLens</span>
        <span className="text-muted text-[11px] hidden sm:block">AI-Powered Damage Claim Intelligence</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
          apiStatus === 'ok'
            ? 'bg-green-500/10 border-green-500/30 text-green-400'
            : apiStatus === 'error'
            ? 'bg-red-500/10 border-red-500/30 text-red-400'
            : 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
        }`}>
          {apiStatus === 'ok' ? '● API Live' : apiStatus === 'error' ? '● Offline' : '● Connecting…'}
        </span>
      </div>
    </header>
  )
}
