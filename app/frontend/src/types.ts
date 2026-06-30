export interface Step {
  id: string
  lab_no: number
  title: string
  topic: string
  maps_to: string
  milestone: number
  doc_path: string
  summary: string
  completed: boolean
}

export interface Note {
  id: number
  step_id: string
  body: string
  created_at: string
}
