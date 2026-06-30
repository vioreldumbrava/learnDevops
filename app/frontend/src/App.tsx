import { useEffect, useMemo, useState } from 'react'
import type { Step } from './types'
import { fetchSteps, setProgress } from './api'
import { StepCard } from './StepCard'

const milestoneNames: Record<number, string> = {
  1: 'Milestone 1 · Runnable foundation',
  2: 'Milestone 2 · Delivery & infrastructure',
  3: 'Milestone 3 · Cloud, scale & Kubernetes',
}

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

  async function toggle(step: Step) {
    // Optimistic update; refetch to revert if the API call fails.
    setSteps((prev) => prev.map((s) => (s.id === step.id ? { ...s, completed: !s.completed } : s)))
    try {
      await setProgress(step.id, !step.completed)
    } catch (e) {
      setError(String(e))
      load()
    }
  }

  const done = steps.filter((s) => s.completed).length
  const pct = steps.length ? Math.round((done / steps.length) * 100) : 0

  const byMilestone = useMemo(() => {
    const m = new Map<number, Step[]>()
    for (const s of steps) {
      const list = m.get(s.milestone) ?? []
      list.push(s)
      m.set(s.milestone, list)
    }
    return [...m.entries()].sort((a, b) => a[0] - b[0])
  }, [steps])

  return (
    <div className="app">
      <header>
        <h1>🥋 DevOps Dojo</h1>
        <p className="tagline">Learn DevOps by deploying the very app that tracks your progress.</p>
        <div className="progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="progress-label">
            {done} / {steps.length} labs · {pct}%
          </span>
        </div>
      </header>

      {loading && <p className="muted">Loading curriculum…</p>}
      {error && <p className="error">Couldn’t reach the API: {error}</p>}

      {byMilestone.map(([m, items]) => (
        <section key={m}>
          <h2>{milestoneNames[m] ?? `Milestone ${m}`}</h2>
          <div className="grid">
            {items.map((s) => (
              <StepCard key={s.id} step={s} onToggle={() => toggle(s)} />
            ))}
          </div>
        </section>
      ))}

      <footer className="muted">
        API health: <code>/healthz</code> · metrics: <code>/metrics</code> · curriculum:{' '}
        <code>docs/CURRICULUM.md</code>
      </footer>
    </div>
  )
}
