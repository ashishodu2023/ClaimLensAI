/**
 * ImageUploader — optimized for large batches
 *
 * Optimizations:
 *  1. Web Worker offload — base64 encoding runs off the main thread (no UI freeze)
 *  2. createImageBitmap — GPU-accelerated thumbnail generation, no canvas blocking
 *  3. Concurrent processing — all dropped files processed in parallel via Promise.all
 *  4. 5 MB client-side guard — oversized files rejected before wasting network
 *  5. Object URL thumbnails — no base64 in <img src>, zero copy in memory
 *  6. Cleanup on unmount — object URLs revoked to prevent memory leaks
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, AlertTriangle } from 'lucide-react'
import { genImageId } from '../utils/helpers.js'

const MAX_SIZE_BYTES = 5 * 1024 * 1024
const MAX_IMAGES     = 20

// ─── Web Worker source (inline blob) ─────────────────────────────────────────
// Runs base64 encoding off main thread so UI stays responsive during large uploads.
const WORKER_SRC = `
self.onmessage = async ({ data: { id, buffer, mediaType } }) => {
  try {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    const chunk = 8192
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk))
    }
    const b64 = btoa(binary)
    self.postMessage({ id, b64, error: null })
  } catch (e) {
    self.postMessage({ id, b64: null, error: e.message })
  }
}
`

function createWorker() {
  const blob = new Blob([WORKER_SRC], { type: 'application/javascript' })
  return new Worker(URL.createObjectURL(blob))
}

// ─── Encode file via Web Worker ───────────────────────────────────────────────
function encodeFileInWorker(worker, file, taskId) {
  return new Promise((resolve, reject) => {
    const handler = ({ data }) => {
      if (data.id !== taskId) return
      worker.removeEventListener('message', handler)
      if (data.error) reject(new Error(data.error))
      else resolve(data.b64)
    }
    worker.addEventListener('message', handler)
    file.arrayBuffer().then(buf => {
      worker.postMessage({ id: taskId, buffer: buf, mediaType: file.type }, [buf])
    })
  })
}

// ─── GPU thumbnail via createImageBitmap ──────────────────────────────────────
async function makeThumbnail(file) {
  try {
    const bitmap = await createImageBitmap(file, { resizeWidth: 160, resizeQuality: 'medium' })
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height)
    canvas.getContext('2d').drawImage(bitmap, 0, 0)
    const blob = await canvas.convertToBlob({ type: 'image/webp', quality: 0.7 })
    bitmap.close()
    return URL.createObjectURL(blob)
  } catch {
    // Fallback: plain object URL from original file
    return URL.createObjectURL(file)
  }
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function ImageUploader({ images, setImages }) {
  const workerRef  = useRef(null)
  const [errs, setErrs] = useState([])

  // Lazily create worker on first use, reuse across all uploads
  function getWorker() {
    if (!workerRef.current) workerRef.current = createWorker()
    return workerRef.current
  }

  // Clean up worker and object URLs on unmount
  useEffect(() => {
    return () => {
      workerRef.current?.terminate()
      images.forEach(img => { try { URL.revokeObjectURL(img.thumbUrl) } catch {} })
    }
  }, [])

  const onDrop = useCallback(async (accepted, rejected) => {
    setErrs([])
    const newErrs = []

    // Report dropzone rejections (wrong type / too large)
    rejected.forEach(({ file, errors }) => {
      errors.forEach(e => newErrs.push(`${file.name}: ${e.message}`))
    })

    // Enforce total image cap
    const slots = MAX_IMAGES - images.length
    if (accepted.length > slots) {
      newErrs.push(`Max ${MAX_IMAGES} images allowed. ${accepted.length - slots} file(s) skipped.`)
      accepted = accepted.slice(0, slots)
    }

    if (newErrs.length) setErrs(newErrs)
    if (!accepted.length) return

    const worker = getWorker()

    // Process all accepted files concurrently
    const processed = await Promise.allSettled(
      accepted.map(async (file, i) => {
        const taskId = `${Date.now()}-${i}`
        const [b64, thumbUrl] = await Promise.all([
          encodeFileInWorker(worker, file, taskId),
          makeThumbnail(file),
        ])
        return {
          id:        genImageId(images.length + i),
          name:      file.name,
          base64:    b64,
          mediaType: file.type || 'image/jpeg',
          thumbUrl,
          size:      file.size,
        }
      })
    )

    const good = processed
      .filter(r => r.status === 'fulfilled')
      .map(r => r.value)

    const failed = processed.filter(r => r.status === 'rejected')
    if (failed.length) {
      setErrs(prev => [...prev, ...failed.map(r => `Encoding failed: ${r.reason?.message}`)])
    }

    if (good.length) setImages(prev => [...prev, ...good])
  }, [images.length, setImages])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxSize: MAX_SIZE_BYTES,
    multiple: true,
  })

  const remove = useCallback((id) => {
    setImages(prev => {
      const img = prev.find(i => i.id === id)
      if (img?.thumbUrl) try { URL.revokeObjectURL(img.thumbUrl) } catch {}
      return prev.filter(i => i.id !== id)
    })
  }, [setImages])

  return (
    <div>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-all ${
          isDragActive
            ? 'border-accent bg-accent/10'
            : 'border-border hover:border-accent/50 hover:bg-accent/5'
        }`}
      >
        <input {...getInputProps()} />
        <Upload size={22} className="mx-auto mb-2 text-muted" />
        <p className="text-xs text-muted">
          {isDragActive ? 'Drop images here…' : 'Drop images or click to browse'}
        </p>
        <p className="text-[11px] text-muted/60 mt-0.5">
          JPEG · PNG · WebP · max {MAX_SIZE_BYTES / 1024 / 1024} MB · up to {MAX_IMAGES} images
        </p>
      </div>

      {errs.length > 0 && (
        <div className="mt-2 space-y-1">
          {errs.map((e, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[11px] text-yellow-400 bg-yellow-500/8 border border-yellow-500/20 rounded px-2 py-1.5">
              <AlertTriangle size={11} className="flex-shrink-0 mt-0.5" />
              {e}
            </div>
          ))}
        </div>
      )}

      {images.length > 0 && (
        <div className="mt-2.5 flex flex-col gap-1.5 max-h-60 overflow-y-auto pr-1">
          {images.map((img) => (
            <div
              key={img.id}
              className="flex items-center gap-2.5 bg-surface2 border border-border rounded-md p-2"
            >
              <img
                src={img.thumbUrl}
                alt={img.name}
                loading="lazy"
                decoding="async"
                className="w-10 h-10 object-cover rounded border border-border flex-shrink-0"
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate text-white">{img.name}</p>
                <p className="text-[10px] text-muted font-mono">
                  {img.id} · {(img.size / 1024).toFixed(0)} KB
                </p>
              </div>
              <button
                onClick={() => remove(img.id)}
                className="text-muted hover:text-red-400 transition-colors flex-shrink-0"
                aria-label={`Remove ${img.name}`}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
