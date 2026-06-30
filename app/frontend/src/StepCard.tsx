import { useState, type FormEvent } from 'react'
import type { Note, Step } from './types'
import { addNote, fetchNotes } from './api'

export function StepCard({ step, onToggle }: { step: Step; onToggle: () => void }) {
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

  return (
    <div className={`card ${step.completed ? 'done' : ''}`}>
      <label className="card-head">
        <input type="checkbox" checked={step.completed} onChange={onToggle} />
        <span className="lab-no">{String(step.lab_no).padStart(2, '0')}</span>
        <span className="title">{step.title}</span>
      </label>
      <p className="topic">{step.topic}</p>
      <p className="summary">{step.summary}</p>
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
