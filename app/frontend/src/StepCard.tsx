import { useState, type FormEvent } from 'react'
import type { Note, Step } from './types'
import { addNote, fetchNotes } from './api'

/** Whole days since an RFC3339 timestamp; null if the lab was never touched. */
export function daysSince(iso: string | null): number | null {
  if (!iso) return null
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return null
  return Math.floor((Date.now() - then) / 86_400_000)
}

/** "today" / "yesterday" / "12d ago" — short enough to sit on a card. */
export function staleness(iso: string | null): string {
  const d = daysSince(iso)
  if (d === null) return 'never practiced'
  if (d <= 0) return 'practiced today'
  if (d === 1) return 'practiced yesterday'
  return `practiced ${d}d ago`
}

export function StepCard({
  step,
  onToggleCompleted,
  onToggleDrilled,
}: {
  step: Step
  onToggleCompleted: () => void
  onToggleDrilled: () => void
}) {
  const [open, setOpen] = useState(false)
  const [notes, setNotes] = useState<Note[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)

  async function expand() {
    const next = !open
    setOpen(next)
    if (next) {
      try {
        setNotes(await fetchNotes(step.id))
      } catch {
        /* notes are non-critical; ignore */
      }
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!draft.trim()) return
    setBusy(true)
    try {
      const n = await addNote(step.id, draft.trim())
      setNotes((prev) => [...prev, n])
      setDraft('')
    } finally {
      setBusy(false)
    }
  }

  // A lab is only "green" once it's been done closed-book; read-only is a lighter state.
  const days = daysSince(step.last_practiced_at)
  const stale = step.drilled && days !== null && days > 30

  return (
    <div className={`card ${step.drilled ? 'drilled' : step.completed ? 'done' : ''} ${stale ? 'stale' : ''}`}>
      <label className="card-head">
        <input type="checkbox" checked={step.completed} onChange={onToggleCompleted} />
        <span className="lab-no">{String(step.lab_no).padStart(2, '0')}</span>
        <span className="title">{step.title}</span>
      </label>
      <p className="topic">{step.topic}</p>
      <p className="summary">{step.summary}</p>

      <label className="drill-head" title="Passed the closed-book drill inside its time target (docs/DRILLS.md)">
        <input type="checkbox" checked={step.drilled} onChange={onToggleDrilled} />
        <span>drilled closed-book</span>
        <span className={`when ${stale ? 'warn' : 'muted'}`}>{staleness(step.last_practiced_at)}</span>
      </label>

      <div className="meta">
        <span className="tag">{step.maps_to}</span>
        <button className="link" onClick={expand}>
          {open ? 'Hide notes' : 'Notes'}
        </button>
      </div>

      {open && (
        <div className="notes">
          {notes.length === 0 && <p className="muted">No notes yet.</p>}
          <ul>
            {notes.map((n) => (
              <li key={n.id}>{n.body}</li>
            ))}
          </ul>
          <form onSubmit={submit}>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Add a note…" />
            <button disabled={busy} type="submit">
              Add
            </button>
          </form>
          <p className="path muted">{step.doc_path}</p>
        </div>
      )}
    </div>
  )
}
