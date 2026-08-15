export interface Step {
  id: string
  lab_no: number
  title: string
  topic: string
  maps_to: string
  milestone: number
  doc_path: string
  summary: string
  tier: 'core' | 'specialization' | 'elective'
  tracks: Array<'common-core' | 'platform-cka' | 'sre' | 'elective'>
  requires: string[]
  effort_minutes: number
  cost_class: 'free' | 'local' | 'cloud-low' | 'cloud-high'
  /** True only when the manifest points to a timed drill with an explicit pass rule. */
  drill_required: boolean
  /** Worked through the lab with the repo open — recognition. */
  completed: boolean
  /** Passed the lab's closed-book drill inside its time target — recall. See docs/DRILLS.md. */
  drilled: boolean
  /** RFC3339, or null if never touched. Drives the "stalest" spaced-repetition list. */
  last_practiced_at: string | null
}

/** What POST /api/progress/:id returns — the state after the write. */
export interface Progress {
  step_id: string
  completed: boolean
  drilled: boolean
  last_practiced_at: string | null
}

export interface Note {
  id: number
  step_id: string
  body: string
  created_at: string
}
