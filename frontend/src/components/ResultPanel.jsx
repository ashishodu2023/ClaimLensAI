import { CheckCircle, XCircle, AlertTriangle, AlertOctagon, Clock } from 'lucide-react'

const VERDICT_CONFIG = {
  SUPPORTED: {
    icon: CheckCircle,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
  },
  CONTRADICTED: {
    icon: XCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
  },
  INSUFFICIENT: {
    icon: AlertTriangle,
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
  },
}

const SEV_COLOR = {
  minor: 'text-green-400 bg-green-500/10 border-green-500/25',
  moderate: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/25',
  severe: 'text-orange-400 bg-orange-500/10 border-orange-500/25',
  critical: 'text-red-400 bg-red-500/10 border-red-500/25',
}

const FLAG_SEV = {
  high: 'text-red-400 bg-red-500/10 border-red-500/25',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/25',
  low: 'text-blue-400 bg-blue-500/10 border-blue-500/25',
}

function DetailRow({ label, value, valueClass = '' }) {
  return (
    <div className="flex justify-between py-1.5 border-b border-border/50 last:border-0 text-xs">
      <span className="text-muted">{label}</span>
      <span className={`font-mono font-medium ${valueClass}`}>{value}</span>
    </div>
  )
}

export default function ResultPanel({ result, images }) {
  if (!result) return null
  const vc = VERDICT_CONFIG[result.verdict] || VERDICT_CONFIG.INSUFFICIENT
  const VIcon = vc.icon

  const total = result.risk_flags?.filter(f => f.severity === 'high').length || 0

  return (
    <div className="flex flex-col gap-4">
      {/* Verdict header */}
      <div className={`rounded-xl border p-5 ${vc.bg} ${vc.border}`}>
        <div className="flex items-start gap-4">
          <div className={`rounded-lg p-2.5 ${vc.bg} border ${vc.border} flex-shrink-0`}>
            <VIcon size={28} className={vc.color} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xl font-black tracking-widest ${vc.color}`}>{result.verdict}</span>
              <span className="badge bg-accent/10 text-accent border-accent/25 text-[10px]">
                {result.verdict_confidence} confidence
              </span>
            </div>
            <p className="text-xs font-mono text-muted mb-2">{result.claim_id}</p>
            <p className="text-sm text-white font-medium leading-snug">{result.extracted_claim}</p>
            <div className="flex flex-wrap gap-1.5 mt-3">
              <span className={`badge text-[10px] ${SEV_COLOR[result.severity]}`}>
                {result.severity} severity
              </span>
              <span className="badge text-[10px] bg-purple-500/10 text-purple-400 border-purple-500/25">
                {result.issue_type} · {result.object_part}
              </span>
              <span className={`badge text-[10px] ${
                result.evidence_sufficient
                  ? 'bg-green-500/10 text-green-400 border-green-500/25'
                  : 'bg-red-500/10 text-red-400 border-red-500/25'
              }`}>
                {result.evidence_sufficient ? 'Evidence sufficient' : 'Evidence insufficient'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Reviewer notes */}
      {result.reviewer_notes && result.reviewer_notes !== 'No additional reviewer notes.' && (
        <div className="rounded-lg border border-yellow-500/25 bg-yellow-500/6 p-3.5 flex gap-2.5 text-xs">
          <AlertOctagon size={14} className="text-yellow-400 flex-shrink-0 mt-0.5" />
          <span className="text-yellow-200">{result.reviewer_notes}</span>
        </div>
      )}

      {/* Cards row */}
      <div className="grid grid-cols-2 gap-3">
        {/* Evidence details */}
        <div className="card">
          <p className="section-heading">Evidence details</p>
          <DetailRow label="Object type" value={result.object_type} />
          <DetailRow label="Issue type" value={result.issue_type} />
          <DetailRow label="Object part" value={result.object_part} />
          <DetailRow
            label="Supporting images"
            value={result.supporting_image_ids?.length || 0}
            valueClass={result.supporting_image_ids?.length ? 'text-green-400' : 'text-muted'}
          />
          <DetailRow
            label="Evidence OK"
            value={result.evidence_sufficient ? 'Yes' : 'No'}
            valueClass={result.evidence_sufficient ? 'text-green-400' : 'text-red-400'}
          />
          <DetailRow label="Processed" value={result.processed_at?.replace('T', ' ').replace('Z', '')} />
        </div>

        {/* Risk flags */}
        <div className="card">
          <p className="section-heading">Risk flags ({result.risk_flags?.length || 0})</p>
          {!result.risk_flags?.length ? (
            <p className="text-xs text-green-400 text-center py-4">✓ No risk flags</p>
          ) : (
            <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
              {result.risk_flags.map((f, i) => (
                <div
                  key={i}
                  className={`rounded-md border p-2 text-xs ${FLAG_SEV[f.severity]}`}
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="font-bold uppercase text-[10px] tracking-wide">{f.severity}</span>
                    <span className="font-semibold uppercase text-[10px] tracking-wide opacity-70">
                      {f.flag_type.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-white/80 leading-snug">{f.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Image analysis grid */}
      {images?.length > 0 && (
        <div className="card">
          <p className="section-heading">Image analysis</p>
          <div className="grid grid-cols-3 gap-2.5">
            {images.map((img) => {
              const isSupporting = result.supporting_image_ids?.includes(img.id)
              const imgVerdict = isSupporting
                ? 'SUPPORTED'
                : result.verdict === 'CONTRADICTED'
                ? 'CONTRADICTED'
                : 'INSUFFICIENT'
              const borderColor =
                imgVerdict === 'SUPPORTED'
                  ? 'border-green-500/40'
                  : imgVerdict === 'CONTRADICTED'
                  ? 'border-red-500/40'
                  : 'border-yellow-500/40'
              const dotColor =
                imgVerdict === 'SUPPORTED'
                  ? 'bg-green-400'
                  : imgVerdict === 'CONTRADICTED'
                  ? 'bg-red-400'
                  : 'bg-yellow-400'

              return (
                <div key={img.id} className={`rounded-lg border overflow-hidden bg-surface2 ${borderColor}`}>
                  <img src={img.thumbUrl} alt={img.id} className="w-full h-24 object-cover" />
                  <div className="p-2">
                    <p className="font-mono text-[10px] text-muted truncate">{img.id}</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotColor}`} />
                      <span className="text-[10px] font-bold">{imgVerdict}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          {result.image_analysis_summary && (
            <p className="font-mono text-[10px] text-muted mt-3 leading-relaxed border-t border-border pt-2.5">
              {result.image_analysis_summary}
            </p>
          )}
        </div>
      )}

      {/* Justification */}
      <div className="card border-l-2 border-l-accent">
        <p className="section-heading">AI justification</p>
        <p className="text-sm text-white/90 leading-relaxed">{result.justification}</p>
      </div>

      {/* Reasoning Agent output */}
      {result.chain_of_thought && (
        <div className="card border-l-2 border-l-purple-500">
          <div className="flex items-center gap-2 mb-2">
            <p className="section-heading mb-0">Agent reasoning</p>
            {result.overrode_preliminary && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/25 text-yellow-400">
                OVERRODE PRELIMINARY
              </span>
            )}
          </div>
          <p className="text-sm text-white/90 leading-relaxed">{result.chain_of_thought}</p>
          {result.override_reason && (
            <p className="text-xs text-yellow-400/80 mt-2 pt-2 border-t border-border">
              Override reason: {result.override_reason}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
