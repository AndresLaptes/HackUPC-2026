// Bay (storage unit) value types — no framework imports

export interface Bay {
  id: string
  x: number      // mm, left edge
  y: number      // mm, front edge
  width: number  // mm
  depth: number  // mm
  height: number // mm
  gap: number    // mm between adjacent bays
  nLoads: number // number of load levels
  price: number
  label: string
}

export interface BayLayout {
  bay: Bay
  /** Whether the bay collides with an obstacle or exits the warehouse */
  hasCollision: boolean
}

export interface BayType {
  id: number
  width: number
  depth: number
  height: number
  gap: number
  nLoads: number
  price: number
}
