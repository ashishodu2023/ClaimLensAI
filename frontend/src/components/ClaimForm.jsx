import { Car, Laptop, Package, Zap } from 'lucide-react'
import ConversationBuilder from './ConversationBuilder.jsx'
import ImageUploader from './ImageUploader.jsx'
import { PRESETS } from '../utils/helpers.js'

const PRESET_ICONS = { car: Car, laptop: Laptop, package: Package }
const PRESET_LABELS = {
  car: { label: 'Car — Rear Bumper Dent', sub: 'Low risk · 1 image' },
  laptop: { label: 'Laptop — Cracked Screen', sub: 'Medium risk · 2 images required' },
  package: { label: 'Package — Crushed + Resealed', sub: 'New user · 3 images' },
}

export default function ClaimForm({
  claimId, setClaimId,
  objectType, setObjectType,
  minEvidence, setMinEvidence,
  conversation, setConversation,
  images, setImages,
  history, setHistory,
  onSubmit, loading,
}) {
  function loadPreset(type) {
    const p = PRESETS[type]
    setClaimId(p.claimId)
    setObjectType(p.objectType)
    setMinEvidence(p.minEvidence)
    setConversation([...p.conversation])
    setHistory({ ...p.history })
  }

  function updateHistory(key, val) {
    setHistory((h) => ({ ...h, [key]: val }))
  }

  return (
    <aside className="w-[360px] flex-shrink-0 bg-surface border-r border-border flex flex-col overflow-y-auto">

      {/* Presets */}
      <div className="px-4 py-4 border-b border-border">
        <p className="section-heading">Quick-load presets</p>
        <div className="flex flex-col gap-2">
          {Object.entries(PRESET_LABELS).map(([type, info]) => {
            const Icon = PRESET_ICONS[type]
            return (
              <button
                key={type}
                onClick={() => loadPreset(type)}
                className="flex items-center gap-3 bg-surface2 border border-border hover:border-accent/50 hover:bg-accent/5 rounded-lg px-3 py-2.5 text-left transition-all group"
              >
                <span className="text-lg">{type === 'car' ? '🚗' : type === 'laptop' ? '💻' : '📦'}</span>
                <div>
                  <p className="text-xs font-semibold text-white group-hover:text-accent transition-colors">{info.label}</p>
                  <p className="text-[10px] text-muted mt-0.5">{info.sub}</p>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Claim setup */}
      <div className="px-4 py-4 border-b border-border">
        <p className="section-heading">Claim setup</p>
        <div className="mb-3">
          <label className="label">Claim ID</label>
          <input className="input-field" value={claimId} onChange={(e) => setClaimId(e.target.value)} placeholder="CLM-2024-001" />
        </div>
        <div className="mb-3">
          <label className="label">Object type</label>
          <select className="select-field" value={objectType} onChange={(e) => setObjectType(e.target.value)}>
            <option value="car">🚗 Car</option>
            <option value="laptop">💻 Laptop</option>
            <option value="package">📦 Package</option>
          </select>
        </div>
        <div>
          <label className="label">Min images required</label>
          <input
            type="number" min="1" max="10"
            className="input-field"
            value={minEvidence}
            onChange={(e) => setMinEvidence(parseInt(e.target.value) || 1)}
          />
        </div>
      </div>

      {/* Conversation */}
      <div className="px-4 py-4 border-b border-border">
        <p className="section-heading">Claim conversation</p>
        <ConversationBuilder conversation={conversation} setConversation={setConversation} />
      </div>

      {/* Images */}
      <div className="px-4 py-4 border-b border-border">
        <p className="section-heading">Evidence images</p>
        <ImageUploader images={images} setImages={setImages} />
      </div>

      {/* User history */}
      <div className="px-4 py-4 border-b border-border">
        <p className="section-heading">User history (risk context)</p>
        <div className="grid grid-cols-2 gap-2.5">
          {[
            ['Total claims', 'total'],
            ['Approved', 'approved'],
            ['Rejected', 'rejected'],
            ['Fraud flags', 'fraud'],
            ['Account age (days)', 'age'],
            ['Risk score (0–1)', 'risk'],
          ].map(([label, key]) => (
            <div key={key}>
              <label className="label">{label}</label>
              <input
                type="number"
                step={key === 'risk' ? '0.01' : '1'}
                min="0"
                max={key === 'risk' ? '1' : undefined}
                className="input-field"
                value={history[key]}
                onChange={(e) => updateHistory(key, key === 'risk' ? parseFloat(e.target.value) : parseInt(e.target.value) || 0)}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Submit */}
      <div className="px-4 py-4 mt-auto">
        <button onClick={onSubmit} disabled={loading} className="btn-primary flex items-center justify-center gap-2">
          {loading ? (
            <>
              <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              Analyzing…
            </>
          ) : (
            <>
              <Zap size={15} />
              Analyze Claim
            </>
          )}
        </button>
      </div>
    </aside>
  )
}
