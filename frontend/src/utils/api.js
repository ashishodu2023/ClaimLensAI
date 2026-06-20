/**
 * API client — optimized for high-throughput use
 *
 * Optimizations:
 *  1. Request deduplication — identical in-flight requests share one fetch (no double-submit)
 *  2. Exponential backoff retry on 429/502/503
 *  3. AbortController support — stale requests cancelled when component unmounts
 *  4. Streaming-ready structure — swap fetch for EventSource when backend adds SSE
 */

const BASE = '/api'
const DEFAULT_TIMEOUT_MS = 120_000

// ─── In-flight deduplication map ─────────────────────────────────────────────
// Key: SHA-256 of request body. Value: Promise<Response>.
// Prevents duplicate network calls when user double-clicks Submit.
const _inflight = new Map()

async function _sha256(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('')
}

// ─── Retry with exponential backoff ──────────────────────────────────────────
async function _fetchWithRetry(url, options, maxRetries = 3) {
  const RETRYABLE = new Set([429, 502, 503, 529])
  let lastErr

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    if (attempt > 0) {
      const delay = Math.min(1000 * 2 ** (attempt - 1) + Math.random() * 200, 15_000)
      await new Promise(r => setTimeout(r, delay))
    }
    try {
      const res = await fetch(url, options)
      if (RETRYABLE.has(res.status) && attempt < maxRetries) {
        lastErr = new Error(`HTTP ${res.status}`)
        continue
      }
      return res
    } catch (err) {
      lastErr = err
    }
  }
  throw lastErr
}

// ─── Core POST with deduplication ─────────────────────────────────────────────
async function _post(path, payload, signal) {
  const body = JSON.stringify(payload)
  const key  = path + ':' + await _sha256(body)

  // Return existing in-flight promise if identical request already running
  if (_inflight.has(key)) return _inflight.get(key)

  const controller = new AbortController()
  const timeout    = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)
  if (signal) signal.addEventListener('abort', () => controller.abort())

  const promise = _fetchWithRetry(
    BASE + path,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      signal: controller.signal,
    }
  )
    .then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw Object.assign(new Error(err.detail || JSON.stringify(err)), { status: res.status })
      }
      return res.json()
    })
    .finally(() => {
      clearTimeout(timeout)
      _inflight.delete(key)
    })

  _inflight.set(key, promise)
  return promise
}

// ─── Public API ───────────────────────────────────────────────────────────────

export async function reviewClaim(payload, signal) {
  return _post('/review', payload, signal)
}

export async function batchReview(payloads, signal) {
  return _post('/batch-review', payloads, signal)
}

export async function healthCheck() {
  const res = await fetch('/health', { cache: 'no-store' })
  return res.json()
}

export async function getMetrics() {
  const res = await fetch('/metrics', { cache: 'no-store' })
  return res.json()
}
