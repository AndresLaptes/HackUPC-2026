// Pure math helpers — no framework dependencies

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

export function interpolate(t: number, a: number, b: number): number {
  return a + (b - a) * clamp(t, 0, 1)
}

/** Linear interpolation between a sorted list of [x, y] control points */
export function interpolateCtrlPoints(
  x: number,
  ctrlPoints: [number, number][],
): number {
  const sorted = [...ctrlPoints].sort((a, b) => a[0] - b[0])
  if (x <= sorted[0][0]) return sorted[0][1]
  if (x >= sorted[sorted.length - 1][0]) return sorted[sorted.length - 1][1]
  for (let i = 0; i < sorted.length - 1; i++) {
    const [x0, y0] = sorted[i]
    const [x1, y1] = sorted[i + 1]
    if (x >= x0 && x <= x1) {
      return interpolate((x - x0) / (x1 - x0), y0, y1)
    }
  }
  return sorted[0][1]
}

/**
 * Step function sampling for [x, y] control points.
 * Meaning: each control point starts a new constant segment.
 * Example: [0,3000], [3000,2000], [6000,3000]
 * -> [0,3000):3000, [3000,6000):2000, [6000,+inf):3000
 */
export function sampleStepCtrlPoints(
  x: number,
  ctrlPoints: [number, number][],
): number {
  const sorted = [...ctrlPoints].sort((a, b) => a[0] - b[0])
  if (!sorted.length) return 0

  if (x < sorted[0][0]) return sorted[0][1]
  for (let i = sorted.length - 1; i >= 0; i--) {
    if (x >= sorted[i][0]) return sorted[i][1]
  }
  return sorted[0][1]
}

/** Ray-casting point-in-polygon test for a flat 2D polygon */
export function pointInPolygon(px: number, py: number, polygon: [number, number][]): boolean {
  let inside = false
  const n = polygon.length
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [xi, yi] = polygon[i]
    const [xj, yj] = polygon[j]
    const intersect =
      yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi
    if (intersect) inside = !inside
  }
  return inside
}

/** Axis-aligned bounding box overlap check */
export function aabbOverlap(
  ax: number, ay: number, aw: number, ad: number,
  bx: number, by: number, bw: number, bd: number,
): boolean {
  return ax < bx + bw && ax + aw > bx && ay < by + bd && ay + ad > by
}
