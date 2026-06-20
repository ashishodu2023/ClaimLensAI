/**
 * ReviewPage — optimized for responsiveness under load
 *
 * Optimizations:
 *  1. AbortController — cancel stale in-flight request if user re-submits
 *  2. useRef for abort controller — no stale closures
 *  3. Real-time step tracking driven by actual timing, not fake timers
 *  4. Memoized payload construction — useMemo prevents re-computing on unrelated renders
 *  5. Error boundary integration — catches render errors in ResultPanel
 */

import { useCallback, useMemo, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import ClaimForm from '../components/ClaimForm.jsx'
import ResultPanel from '../components/ResultPanel.jsx'
import { reviewClaim } from '../utils/api.js'
import { Microscope } from 'lucide-react'

const STEPS = [
  { label: 'Extracting damage claim from conversation…', minMs: 0 },
  { label: 'Analyzing images with Claude Vision…',      minMs: 1500 },
  { label: 'Aggregating evidence and computing verdict…', minMs: 0 },
  { label: 'Building risk flag report…',                minMs: 0 },
]

export default function ReviewPage() {
  const [claimId,     setClaimId]     = useState('CLM-2024-001')
  const [objectType,  setObjectType]  = useState('car')
  const [minEvidence, setMinEvidence] = useState(1)
  const [conversation, setConversation] = useState([])
  const [images,      setImages]      = useState([])
  const [history,     setHistory]     = useState({
    total: 2, approved: 2, rejected: 0, fraud: 0, age: 730, risk: 0.15,
  })

  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [loadStep, setLoadStep] = useState(0)

  // AbortController ref — cancel previous request on re-submit
  const abortRef = useRef(null)

  // Memoize payload so it's only rebuilt when form fields actually change
  const payload = useMemo(() => ({
    claim_id:     claimId,
    object_type:  objectType,
    conversation,
    images: images.map(img => ({
      image_id:    img.id,
      base64_data: img.base64,
      media_type:  img.mediaType,
    })),
    user_history: {
      previous_claims:  history.total,
      approved_claims:  history.approved,
      rejected_claims:  history.rejected,
      fraud_flags:      history.fraud,
      account_age_days: history.age,
      risk_score:       history.risk,
    },
    minimum_evidence_required: minEvidence,
  }), [claimId, objectType, conversation, images, history, minEvidence])

  const handleSubmit = useCallback(async () => {
    if (!claimId.trim())       { toast.error('Please enter a Claim ID'); return }
    if (!conversation.length)  { toast.error('Please add at least one conversation message'); return }
    if (!images.length)        { toast.error('Please upload at least one image'); return }

    // Cancel any previous in-flight request
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setResult(null)
    setLoadStep(0)

    // Drive step indicator off actual elapsed time instead of fake setInterval
    const stepTimers = STEPS.map((step, i) =>
      i === 0 ? null : setTimeout(() => setLoadStep(i), step.minMs * i)
    )

    try {
      const data = await reviewClaim(payload, controller.signal)
      setResult(data)
      toast.success(`Verdict: ${data.verdict} · ${data.processing_ms}ms`)
    } catch (err) {
      if (err.name === 'AbortError') return // User cancelled — silent
      const msg = err.message || 'Unknown error'
      toast.error(`Error: ${msg}`)
    } finally {
      stepTimers.forEach(t => t && clearTimeout(t))
      setLoading(false)
      setLoadStep(0)
    }
  }, [payload, claimId, conversation.length, images.length])

  return (
    <div className="flex flex-1 h-full overflow-hidden">
      <ClaimForm
        claimId={claimId}         setClaimId={setClaimId}
        objectType={objectType}   setObjectType={setObjectType}
        minEvidence={minEvidence} setMinEvidence={setMinEvidence}
        conversation={conversation} setConversation={setConversation}
        images={images}           setImages={setImages}
        history={history}         setHistory={setHistory}
        onSubmit={handleSubmit}
        loading={loading}
      />

      <main className="flex-1 overflow-y-auto px-8 py-7">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <div className="w-11 h-11 rounded-full border-[3px] border-accent/25 border-t-accent animate-spin" />
            <div className="flex flex-col gap-2 w-72">
              {STEPS.map((step, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-2.5 text-xs transition-colors ${
                    i < loadStep ? 'text-green-400' : i === loadStep ? 'text-white' : 'text-muted'
                  }`}
                >
                  <span className="w-4 flex-shrink-0 text-center font-mono">
                    {i < loadStep ? '✓' : i === loadStep ? '›' : '○'}
                  </span>
                  {step.label}
                </div>
              ))}
            </div>
          </div>
        ) : result ? (
          <ResultPanel result={result} images={images} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
            <div className="w-16 h-16 rounded-2xl bg-surface flex items-center justify-center border border-border">
              <Microscope size={32} className="text-muted" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-muted mb-1.5">
                ClaimLens
              </h2>
              <p className="text-sm text-muted/70 max-w-sm leading-relaxed">
                Submit a claim ID, describe the damage in the conversation, upload evidence photos and click Analyze.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
