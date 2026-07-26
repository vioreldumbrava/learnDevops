import { useEffect, useMemo, useState } from 'react'
import type { Step } from './types'
import { fetchSteps, setProgress } from './api'
import { StepCard, daysSince, staleness } from './StepCard'

const milestoneNames: Record<number, string> = {
  1: 'Milestone 1 · Runnable foundation',
  2: 'Milestone 2 · Delivery & infrastructure',
  3: 'Milestone 3 · Cloud, scale & Kubernetes',
  4: 'Milestone 4 · Operate, automate & prove it',
  5: 'Milestone 5 · Ecosystem breadth & portability',
  6: 'Kubernetes deep-dive · Platform/SRE · CKA/CKS',
  7: 'Polyglot extra',
}

/** How many labs the weekly cadence asks you to re-drill (docs/WEEKLY.md). */
const STALEST_COUNT = 5

export default function App() {
  const [steps, setSteps] = useState<Step[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      setSteps(await fetchSteps())
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // One writer for both flags: send only the one that changed, then trust the API's
  // response (it also stamps last_practiced_at, which we can't compute client-side).
  async function toggle(step: Step, field: 'completed' | 'drilled') {
    const patch = { [field]: !step[field] } as { completed: boolean } | { drilled: boolean }
    setSteps((prev) => prev.map((s) => (s.id === step.id ? { ...s, [field]: !s[field] } : s)))
    try {
      const p = await setProgress(step.id, patch)
      setSteps((prev) =>
        prev.map((s) =>
          s.id === step.id
            ? { ...s, completed: p.completed, drilled: p.drilled, last_practiced_at: p.last_practiced_at }
            : s,
        ),
      )
    } catch (e) {
      setError(String(e))
      load() // revert the optimistic update
    }
  }

  const done = steps.filter((s) => s.completed).length
  const drilled = steps.filter((s) => s.drilled).length
  const pct = steps.length ? Math.round((done / steps.length) * 100) : 0
  const drilledPct = steps.length ? Math.round((drilled / steps.length) * 100) : 0

  // What to practise next: labs you've completed but never drilled come first (the gap
  // between "I read it" and "I can do it"), then the ones you drilled longest ago.
  const stalest = useMemo(() => {
    const candidates = steps.filter((s) => s.completed || s.drilled)
    return [...candidates]
      .sort((a, b) => {
        if (a.drilled !== b.drilled) return a.drilled ? 1 : -1
        return (daysSince(b.last_practiced_at) ?? 1e9) - (daysSince(a.last_practiced_at) ?? 1e9)
      })
      .slice(0, STALEST_COUNT)
  }, [steps])

  // Group in the order the API returns (ORDER BY sort_order = the curriculum's own
  // sequence), NOT by milestone number — the K8s deep-dive sits between 3 and 4.
  const byMilestone = useMemo(() => {
    const m = new Map<number, Step[]>()
    for (const s of steps) {
      const list = m.get(s.milestone) ?? []
      list.push(s)
      m.set(s.milestone, list)
    }
    return [...m.entries()]
  }, [steps])

  return (
    <div className="app">
      <header>
        <h1>🥋 DevOps Dojo</h1>
        <p className="tagline">Learn DevOps by deploying the very app that tracks your progress.</p>
        <div className="progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
            <div className="progress-fill drilled" style={{ width: `${drilledPct}%` }} />
          </div>
          <span className="progress-label">
            {done} / {steps.length} completed · <strong>{drilled} drilled closed-book</strong>
          </span>
        </div>
      </header>

      {loading && <p className="muted">Loading curriculum…</p>}
      {error && <p className="error">Couldn’t reach the API: {error}</p>}

      {stalest.length > 0 && (
        <section className="stalest">
          <h2>🔁 Drill next</h2>
          <p className="muted">
            Completed but not yet drilled first, then longest since practised — this is the
            Mon/Wed/Thu slot in <code>docs/WEEKLY.md</code>.
          </p>
          <ol>
            {stalest.map((s) => (
              <li key={s.id}>
                <span className="lab-no">{String(s.lab_no).padStart(2, '0')}</span> {s.title}
                <span className="muted"> — {s.drilled ? staleness(s.last_practiced_at) : 'never drilled'}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {byMilestone.map(([m, items]) => (
        <section key={m}>
          <h2>{milestoneNames[m] ?? `Milestone ${m}`}</h2>
          <div className="grid">
            {items.map((s) => (
              <StepCard
                key={s.id}
                step={s}
                onToggleCompleted={() => toggle(s, 'completed')}
                onToggleDrilled={() => toggle(s, 'drilled')}
              />
            ))}
          </div>
        </section>
      ))}

      <footer className="muted">
        API health: <code>/healthz</code> · metrics: <code>/metrics</code> · curriculum:{' '}
        <code>docs/CURRICULUM.md</code> · drills: <code>docs/DRILLS.md</code>
      </footer>
    </div>
  )
}
