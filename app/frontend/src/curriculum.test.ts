import { describe, expect, it } from 'vitest'

import { belongsToView } from './curriculum'
import type { Step } from './types'

function step(overrides: Partial<Step>): Step {
  return {
    id: '00-prerequisites',
    lab_no: 0,
    title: 'Prerequisites',
    topic: 'Setup',
    maps_to: 'Foundation',
    milestone: 1,
    doc_path: 'labs/00-prerequisites/',
    summary: '',
    tier: 'core',
    tracks: ['common-core'],
    requires: [],
    effort_minutes: 60,
    cost_class: 'free',
    drill_required: true,
    completed: false,
    drilled: false,
    last_practiced_at: null,
    ...overrides,
  }
}

describe('curriculum navigation', () => {
  it('keeps common core distinct from specialization and electives', () => {
    const core = step({})
    const platform = step({ tier: 'specialization', tracks: ['platform-cka'] })
    const sre = step({ tier: 'specialization', tracks: ['sre'] })
    const elective = step({ tier: 'elective', tracks: ['elective'] })

    expect([core, platform, sre, elective].filter((item) => belongsToView(item, 'common-core'))).toEqual([core])
    expect([core, platform, sre, elective].filter((item) => belongsToView(item, 'platform-cka'))).toEqual([
      platform,
    ])
    expect([core, platform, sre, elective].filter((item) => belongsToView(item, 'sre'))).toEqual([sre])
    expect([core, platform, sre, elective].filter((item) => belongsToView(item, 'electives'))).toEqual([
      elective,
    ])
  })

  it('does not include role-dependent platform depth in electives', () => {
    const platformDepth = step({
      id: '29-k8s-kyverno',
      tier: 'specialization',
      tracks: ['platform-cka'],
      drill_required: false,
    })
    expect(belongsToView(platformDepth, 'platform-cka')).toBe(true)
    expect(belongsToView(platformDepth, 'electives')).toBe(false)
  })
})
