// Obstacle (pillar, wall, equipment) value types — no framework imports

export interface Obstacle {
  id: string
  x: number      // mm, left edge
  y: number      // mm, front edge
  width: number  // mm
  depth: number  // mm
  height?: number // mm, optional visual height
  label: string
}
