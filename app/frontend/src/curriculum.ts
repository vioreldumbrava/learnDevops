import type { Step } from './types'

export type CurriculumView = 'common-core' | 'platform-cka' | 'sre' | 'electives'

export const curriculumViews: Array<{ id: CurriculumView; label: string; description: string }> = [
  {
    id: 'common-core',
    label: 'Common core',
    description: 'The job-first route. Complete this in the order shown before specializing.',
  },
  {
    id: 'platform-cka',
    label: 'Platform / CKA',
    description: 'The focused CKA branch first, followed by role-dependent platform depth.',
  },
  {
    id: 'sre',
    label: 'SRE',
    description: 'Logging, tracing, database operations, and error-budget-based reliability.',
  },
  {
    id: 'electives',
    label: 'Electives',
    description: 'Choose only when a target role or job posting makes the extra breadth useful.',
  },
]

export function belongsToView(step: Step, view: CurriculumView): boolean {
  if (view === 'common-core') return step.tier === 'core'
  if (view === 'electives') return step.tier === 'elective'
  return step.tier === 'specialization' && step.tracks.includes(view)
}
