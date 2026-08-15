import { useEffect, useMemo, useState } from 'react'
import type { Step } from './types'
import { fetchSteps, setProgress } from './api'
import { StepCard, daysSince, staleness } from './StepCard'
import { belongsToView, curriculumViews, type CurriculumView } from './curriculum'

/** How many required labs the weekly cadence asks you to re-drill. */
const STALEST_COUNT = 5

export default function App() {
  const [steps, setSteps] = useState<Step[]>([])
  const [view, setView] = useState<CurriculumView>('common-core')
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

  // Send only the flag that changed. The response supplies both flags and the
  // server timestamp, so progress writes remain backward compatible.
  async function toggle(step: Step, field: 'completed' | 'drilled') {
    const patch = { [field]: !step[field] } as { completed: boolean } | { drilled: boolean }
    setSteps((prev) => prev.map((s) => (s.id === step.id ? { ...s, [field]: !s[field] } : s)))
    try {
      const progress = await setProgress(step.id, patch)
      setSteps((prev) =>
        prev.map((s) =>
          s.id === step.id
            ? {
                ...s,
                completed: progress.completed,
                drilled: progress.drilled,
                last_practiced_at: progress.last_practiced_at,
              }
            : s,
        ),
      )
    } catch (e) {
      setError(String(e))
      load()
    }
  }

  // Array.filter is stable, so this preserves the manifest's job-first sort order.
  const visibleSteps = useMemo(() => steps.filter((step) => belongsToView(step, view)), [steps, view])
  const activeView = curriculumViews.find((item) => item.id === view) ?? curriculumViews[0]

  const done = steps.filter((step) => step.completed).length
  const requiredDrills = steps.filter((step) => step.drill_required)
  const drilled = requiredDrills.filter((step) => step.drilled).length
  const pct = steps.length ? Math.round((done / steps.length) * 100) : 0
  const drilledPct = requiredDrills.length ? Math.round((drilled / requiredDrills.length) * 100) : 0

  // Only labs with a documented timed drill and pass rule enter spaced repetition.
  const stalest = useMemo(() => {
    const candidates = steps.filter((step) => step.drill_required && (step.completed || step.drilled))
    return [...candidates]
      .sort((a, b) => {
        if (a.drilled !== b.drilled) return a.drilled ? 1 : -1
        return (daysSince(b.last_practiced_at) ?? 1e9) - (daysSince(a.last_practiced_at) ?? 1e9)
      })
      .slice(0, STALEST_COUNT)
  }, [steps])

  return (
    <div className="app">
      <header>
        <h1>🥋 DevOps Dojo</h1>
        <p className="tagline">Learn DevOps by deploying the application that tracks your progress.</p>
        <div className="progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
            <div className="progress-fill drilled" style={{ width: `${drilledPct}%` }} />
          </div>
          <span className="progress-label">
            {done} / {steps.length} completed · <strong>{drilled} / {requiredDrills.length} required drills</strong>
          </span>
        </div>
      </header>

      {loading && <p className="muted">Loading curriculum…</p>}
      {error && <p className="error">Couldn’t reach the API: {error}</p>}

      {!loading && (
        <nav className="curriculum-filters" aria-label="Curriculum track">
          {curriculumViews.map((item) => {
            const count = steps.filter((step) => belongsToView(step, item.id)).length
            return (
              <button
                className={view === item.id ? 'active' : ''}
                key={item.id}
                onClick={() => setView(item.id)}
                type="button"
              >
                {item.label} <span>{count}</span>
              </button>
            )
          })}
        </nav>
      )}

      {stalest.length > 0 && (
        <section className="stalest">
          <h2>🔁 Drill next</h2>
          <p className="muted">
            Required drills only: completed but not yet drilled first, then longest since practiced.
          </p>
          <ol>
            {stalest.map((step) => (
              <li key={step.id}>
                <span className="lab-no">{String(step.lab_no).padStart(2, '0')}</span> {step.title}
                <span className="muted"> — {step.drilled ? staleness(step.last_practiced_at) : 'never drilled'}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {!loading && (
        <section className="curriculum-view">
          <h2>{activeView.label}</h2>
          <p className="view-description">{activeView.description}</p>
          <div className="grid">
            {visibleSteps.map((step) => (
              <StepCard
                key={step.id}
                step={step}
                onToggleCompleted={() => toggle(step, 'completed')}
                onToggleDrilled={() => toggle(step, 'drilled')}
              />
            ))}
          </div>
        </section>
      )}

      <footer className="muted">
        API health: <code>/healthz</code> · metrics: <code>/metrics</code> · curriculum:{' '}
        <code>curriculum/manifest.json</code> · drills: <code>docs/DRILLS.md</code>
      </footer>
    </div>
  )
}
