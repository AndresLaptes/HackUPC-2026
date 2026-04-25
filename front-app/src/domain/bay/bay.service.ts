// Bay placement and collision logic — pure functions, no framework deps

import type { Bay, BayLayout } from './bay.model'
import type { Obstacle } from '../obstacle/obstacle.model'
import type { Warehouse } from '../warehouse/warehouse.model'
import { pointInPolygon } from '../../shared/math.utils'

function getBayCenter(bay: Bay): [number, number] {
  const r = ((bay.rotation ?? 0) * Math.PI) / 180
  const cos = Math.cos(r)
  const sin = Math.sin(r)
  const hw = bay.width / 2
  const hd = bay.depth / 2

  if (bay.isCenter) {
    // Keep consistent with current render mapping
    return [bay.x + hw, bay.y + hd]
  }

  // bay.x, bay.y is origin corner before rotation
  return [
    bay.x + hw * cos - hd * sin,
    bay.y + hw * sin + hd * cos,
  ]
}

function getBayFootprint(bay: Bay): [number, number][] {
  const [cx, cy] = getBayCenter(bay)
  const r = ((bay.rotation ?? 0) * Math.PI) / 180
  const cos = Math.cos(r)
  const sin = Math.sin(r)
  const hw = bay.width / 2
  const hd = bay.depth / 2

  const vx: [number, number] = [hw * cos, hw * sin] // local X axis
  const vy: [number, number] = [-hd * sin, hd * cos] // local Y axis

  return [
    [cx - vx[0] - vy[0], cy - vx[1] - vy[1]],
    [cx + vx[0] - vy[0], cy + vx[1] - vy[1]],
    [cx + vx[0] + vy[0], cy + vx[1] + vy[1]],
    [cx - vx[0] + vy[0], cy - vx[1] + vy[1]],
  ]
}

function obstacleFootprint(obstacle: Obstacle): [number, number][] {
  return [
    [obstacle.x, obstacle.y],
    [obstacle.x + obstacle.width, obstacle.y],
    [obstacle.x + obstacle.width, obstacle.y + obstacle.depth],
    [obstacle.x, obstacle.y + obstacle.depth],
  ]
}

function projectPolygon(axis: [number, number], polygon: [number, number][]): [number, number] {
  let min = Infinity
  let max = -Infinity
  for (const [x, y] of polygon) {
    const p = x * axis[0] + y * axis[1]
    if (p < min) min = p
    if (p > max) max = p
  }
  return [min, max]
}

function polygonsOverlapSAT(a: [number, number][], b: [number, number][]): boolean {
  const axes: [number, number][] = []

  const addAxes = (poly: [number, number][]) => {
    for (let i = 0; i < poly.length; i++) {
      const j = (i + 1) % poly.length
      const ex = poly[j][0] - poly[i][0]
      const ey = poly[j][1] - poly[i][1]
      const nx = -ey
      const ny = ex
      const len = Math.hypot(nx, ny)
      if (len > 0) axes.push([nx / len, ny / len])
    }
  }

  addAxes(a)
  addAxes(b)

  for (const axis of axes) {
    const [amin, amax] = projectPolygon(axis, a)
    const [bmin, bmax] = projectPolygon(axis, b)
    if (amax <= bmin || bmax <= amin) return false
  }
  return true
}

/** Returns true if all four corners of a bay are inside the warehouse polygon */
function bayInsideWarehouse(bay: Bay, warehouse: Warehouse): boolean {
  const corners = getBayFootprint(bay)
  return corners.every(([x, y]) => pointInPolygon(x, y, warehouse.polygon))
}

/** Returns true if a bay's footprint overlaps an obstacle's footprint */
export function bayCollidesWithObstacle(bay: Bay, obstacle: Obstacle): boolean {
  return polygonsOverlapSAT(getBayFootprint(bay), obstacleFootprint(obstacle))
}

/** Annotates each bay with collision state */
export function computeBayLayout(
  bays: Bay[],
  warehouse: Warehouse,
  obstacles: Obstacle[],
): BayLayout[] {
  return bays.map((bay, index) => {
    const outsideWarehouse = !bayInsideWarehouse(bay, warehouse)
    const collidesObstacle = obstacles.some((o) => bayCollidesWithObstacle(bay, o))
    const bayPoly = getBayFootprint(bay)
    const collidesOtherBay = bays
      .filter((_, i) => i !== index)
      .some((b) => polygonsOverlapSAT(bayPoly, getBayFootprint(b)))
    return { bay, hasCollision: outsideWarehouse || collidesObstacle || collidesOtherBay }
  })
}
