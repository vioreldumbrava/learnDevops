import type { Note, Step } from './types'

// Relative base works in dev (Vite proxy) and prod (Caddy/Nginx route /api).
const BASE = import.meta.env.VITE_API_BASE || '/api'

export async function fetchSteps(): Promise<Step[]> {
  const res = await fetch(`${BASE}/steps`)
  if (!res.ok) throw new Error(`steps: HTTP ${res.status}`)
  return res.json()
}

export async function setProgress(id: string, completed: boolean): Promise<void> {
  const res = await fetch(`${BASE}/progress/${id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ completed }),
  })
  if (!res.ok) throw new Error(`progress: HTTP ${res.status}`)
}

export async function fetchNotes(stepId: string): Promise<Note[]> {
  const res = await fetch(`${BASE}/notes?step=${encodeURIComponent(stepId)}`)
  if (!res.ok) throw new Error(`notes: HTTP ${res.status}`)
  return res.json()
}

export async function addNote(stepId: string, body: string): Promise<Note> {
  const res = await fetch(`${BASE}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ step_id: stepId, body }),
  })
  if (!res.ok) throw new Error(`addNote: HTTP ${res.status}`)
  return res.json()
}
