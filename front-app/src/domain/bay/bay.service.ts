// Bay placement and collision logic — pure functions, no framework deps

import type { Bay, BayLayout } from './bay.model'
import type { Obstacle } from '../obstacle/obstacle.model'
import type { Warehouse } from '../warehouse/warehouse.model'
import { aabbOverlap, pointInPolygon } from '../../shared/math.utils'

/** Returns true if all four corners of a bay are inside the warehouse polygon */
function bayInsideWarehouse(bay: Bay, warehouse: Warehouse): boolean {
  const corners: [number, number][] = [
    [bay.x, bay.y],
    [bay.x + bay.width, bay.y],
    [bay.x + bay.width, bay.y + bay.depth],
    [bay.x, bay.y + bay.depth],
  ]
  return corners.every(([x, y]) => pointInPolygon(x, y, warehouse.polygon))
}

/** Returns true if a bay's footprint overlaps an obstacle's footprint */
export function bayCollidesWithObstacle(bay: Bay, obstacle: Obstacle): boolean {
  return aabbOverlap(
    bay.x, bay.y, bay.width, bay.depth,
    obstacle.x, obstacle.y, obstacle.width, obstacle.depth,
  )
}

/** Annotates each bay with collision state */
export function computeBayLayout(
  bays: Bay[],
  warehouse: Warehouse,
  obstacles: Obstacle[],
): BayLayout[] {
  return bays.map((bay) => {
    const outsideWarehouse = !bayInsideWarehouse(bay, warehouse)
    const collidesObstacle = obstacles.some((o) => bayCollidesWithObstacle(bay, o))
    const collidesOtherBay = bays
      .filter((b) => b.id !== bay.id)
      .some((b) =>
        aabbOverlap(bay.x, bay.y, bay.width, bay.depth, b.x, b.y, b.width, b.depth),
      )
    return { bay, hasCollision: outsideWarehouse || collidesObstacle || collidesOtherBay }
  })
}
