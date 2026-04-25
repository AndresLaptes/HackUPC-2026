// Obstacle geometry helpers — pure functions, no framework deps

import type { Obstacle } from './obstacle.model'

export interface AABB {
  minX: number; maxX: number; minY: number; maxY: number
}

export function getObstacleBounds(obstacle: Obstacle): AABB {
  return {
    minX: obstacle.x,
    maxX: obstacle.x + obstacle.width,
    minY: obstacle.y,
    maxY: obstacle.y + obstacle.depth,
  }
}

export function collidesWithBay(
  obstacle: Obstacle,
  bayX: number, bayY: number, bayW: number, bayD: number,
): boolean {
  const b = getObstacleBounds(obstacle)
  return bayX < b.maxX && bayX + bayW > b.minX && bayY < b.maxY && bayY + bayD > b.minY
}
