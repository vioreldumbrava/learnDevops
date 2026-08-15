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
  const days = daysSince(iso)
  if (days === null) return 'never practiced'
  if (days <= 0) return 'practiced today'
  if (days === 1) return 'practiced yesterday'
  return `practiced ${days}d ago`
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
        // Notes are non-critical; progress tracking remains usable if they fail.
      }
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!draft.trim()) return
    setBusy(true)
    try {
      const note = await addNote(step.id, draft.trim())
      setNotes((prev) => [...prev, note])
      setDraft('')
    } finally {
      setBusy(false)
    }
  }

  const days = daysSince(step.last_practiced_at)
  const stale = step.drill_required && step.drilled && days !== null && days > 30

  return (
    <article className={`card ${step.drilled ? 'drilled' : step.completed ? 'done' : ''} ${stale ? 'stale' : ''}`}>
      <label className="card-head">
        <input type="checkbox" checked={step.completed} onChange={onToggleCompleted} />
        <span className="lab-no">{String(step.lab_no).padStart(2, '0')}</span>
        <span className="title">{step.title}</span>
      </label>
      <p className="topic">{step.topic}</p>
      <p className="summary">{step.summary}</p>

      <div className="curriculum-meta" aria-label="Curriculum metadata">
        <span className="tag">{step.effort_minutes} min</span>
        <span className="tag">{step.cost_class}</span>
        <span className="tag">{step.tier}</span>
      </div>
      {step.requires.length > 0 && (
        <p className="requirements">
          Requires: {step.requires.map((id) => id.slice(0, 2)).join(', ')}
        </p>
      )}

      {step.drill_required ? (
        <label className="drill-head" title="Passed the documented timed drill inside its target">
          <input type="checkbox" checked={step.drilled} onChange={onToggleDrilled} />
          <span>timed drill passed</span>
          <span className={`when ${stale ? 'warn' : 'muted'}`}>{staleness(step.last_practiced_at)}</span>
        </label>
      ) : (
        <p className="drill-optional">No required drill for this lab</p>
      )}

      <div className="meta">
        <span className="tag">{step.maps_to}</span>
        <button className="link" onClick={expand} type="button">
          {open ? 'Hide notes' : 'Notes'}
        </button>
      </div>

      {open && (
        <div className="notes">
          {notes.length === 0 && <p className="muted">No notes yet.</p>}
          <ul>
            {notes.map((note) => (
              <li key={note.id}>{note.body}</li>
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
    </article>
  )
}
