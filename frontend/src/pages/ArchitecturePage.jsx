import { Suspense, lazy } from 'react'

const MermaidDiagram = lazy(() => import('../components/MermaidDiagram.jsx'))

function Section({ title, children }) {
  return (
    <div className="mb-8">
      <h2 className="text-base font-semibold text-white mb-3 pb-2 border-b border-border">{title}</h2>
      {children}
    </div>
  )
}

function DecisionRow({ condition, yes, no }) {
  return (
    <tr className="border-b border-border/40">
      <td className="py-2 pr-4 text-xs font-mono text-muted">{condition}</td>
      <td className="py-2 pr-4 text-xs text-green-400">{yes}</td>
      <td className="py-2 text-xs text-yellow-400">{no}</td>
    </tr>
  )
}

export default function ArchitecturePage() {
  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">System Architecture</h1>
        <p className="text-sm text-muted">
          ClaimLens uses a 3-stage AI pipeline — claim extraction, parallel Vision analysis, and a Reasoning Agent — to verify damage claims across car, laptop, and package objects.
        </p>
      </div>

      <Section title="Pipeline Flow Diagram">
        <div className="card overflow-x-auto">
          <Suspense fallback={
            <div className="flex items-center justify-center py-20">
              <span className="w-6 h-6 rounded-full border-2 border-accent/30 border-t-accent animate-spin" />
              <span className="ml-3 text-xs text-muted">Rendering Mermaid diagram…</span>
            </div>
          }>
            <MermaidDiagram />
          </Suspense>
        </div>
      </Section>

      <Section title="Stage Details">
        <div className="grid grid-cols-2 gap-3">
          {[
            {
              step: '1', title: 'Input Validation',
              color: 'border-blue-500/30 bg-blue-500/5',
              dot: 'bg-blue-400',
              items: ['object_type ∈ {car, laptop, package}', 'images array not empty', 'conversation not empty', 'Returns 400 immediately on failure'],
            },
            {
              step: '2', title: 'Claim Extraction',
              color: 'border-purple-500/30 bg-purple-500/5',
              dot: 'bg-purple-400',
              items: ['Claude Sonnet text-only call', 'Parses conversation turns', 'Returns 1-sentence damage claim', 'Used as context for vision step'],
            },
            {
              step: '3', title: 'Per-Image Vision Analysis',
              color: 'border-orange-500/30 bg-orange-500/5',
              dot: 'bg-orange-400',
              items: ['1 Claude Vision call per image', 'Structured JSON output enforced', 'Fields: verdict, issue_type, object_part', 'image_quality, authenticity_concerns'],
            },
            {
              step: '4', title: 'Verdict Aggregation',
              color: 'border-teal-500/30 bg-teal-500/5',
              dot: 'bg-teal-400',
              items: ['CONTRADICTED overrides all SUPPORTED', 'count(SUPPORTED) ≥ min_required → SUPPORTED', 'Otherwise → INSUFFICIENT', 'Best confidence & severity selected'],
            },
            {
              step: '5', title: 'Risk Flag Engine',
              color: 'border-red-500/30 bg-red-500/5',
              dot: 'bg-red-400',
              items: ['Runs after verdict (cannot override it)', 'image_quality: poor/fair flags', 'mismatch: wrong object in image', 'user_history: fraud flags, risk score, rejection rate'],
            },
            {
              step: '6', title: 'Response Assembly',
              color: 'border-green-500/30 bg-green-500/5',
              dot: 'bg-green-400',
              items: ['EvidenceReviewResult model', 'verdict + confidence + severity', 'supporting_image_ids list', 'justification + reviewer_notes'],
            },
          ].map((s) => (
            <div key={s.step} className={`rounded-lg border p-3.5 ${s.color}`}>
              <div className="flex items-center gap-2 mb-2.5">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.dot}`} />
                <p className="text-xs font-semibold text-white">{s.step}. {s.title}</p>
              </div>
              <ul className="space-y-1">
                {s.items.map((item, i) => (
                  <li key={i} className="text-[11px] text-muted leading-snug flex gap-1.5">
                    <span className="text-muted/50 flex-shrink-0">—</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Verdict Decision Logic">
        <div className="card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 pr-4 text-xs font-semibold text-muted">Condition</th>
                <th className="text-left py-2 pr-4 text-xs font-semibold text-muted">Outcome</th>
                <th className="text-left py-2 text-xs font-semibold text-muted">Fallthrough</th>
              </tr>
            </thead>
            <tbody>
              <DecisionRow condition="Any image → CONTRADICTED?" yes="CONTRADICTED" no="Check next →" />
              <DecisionRow condition="count(SUPPORTED) ≥ min_required?" yes="SUPPORTED" no="INSUFFICIENT" />
            </tbody>
          </table>
          <p className="text-[11px] text-muted mt-3 pt-3 border-t border-border leading-relaxed">
            Contradiction takes unconditional priority. This prevents selective evidence submission where a bad actor uploads
            one good image alongside multiple photos of actual damage on a different vehicle.
          </p>
        </div>
      </Section>

      <Section title="Risk Flag Categories">
        <div className="card">
          <div className="grid grid-cols-2 gap-3">
            {[
              { type: 'image_quality', sev: 'low/high', desc: 'Poor or fair quality images that cannot reliably confirm damage' },
              { type: 'mismatch', sev: 'high', desc: 'Image shows a different object type than the claim specifies' },
              { type: 'authenticity', sev: 'high', desc: 'Visual signals of editing, staging, or suspicious metadata' },
              { type: 'user_history', sev: 'medium/high', desc: 'Prior fraud flags, elevated risk score, or high rejection rate' },
            ].map((f) => (
              <div key={f.type} className="bg-surface2 rounded-md p-3 border border-border">
                <p className="font-mono text-xs font-medium text-accent mb-1">{f.type}</p>
                <p className="text-[10px] text-muted mb-1">severity: {f.sev}</p>
                <p className="text-xs text-white/80">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section title="API Endpoints">
        <div className="card font-mono text-xs">
          {[
            { method: 'POST', path: '/api/review', desc: 'Single claim analysis' },
            { method: 'POST', path: '/api/batch-review', desc: 'Multiple claims in sequence' },
            { method: 'GET', path: '/health', desc: 'Service health check' },
            { method: 'GET', path: '/', desc: 'Serves this React frontend' },
          ].map((ep) => (
            <div key={ep.path} className="flex items-center gap-3 py-2 border-b border-border/40 last:border-0">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                ep.method === 'GET' ? 'bg-green-500/15 text-green-400' : 'bg-blue-500/15 text-blue-400'
              }`}>{ep.method}</span>
              <span className="text-white">{ep.path}</span>
              <span className="text-muted text-[11px] ml-auto">{ep.desc}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
