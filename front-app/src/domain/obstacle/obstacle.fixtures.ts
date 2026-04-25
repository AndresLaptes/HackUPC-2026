// Three obstacles provided in the problem specification

import type { Obstacle } from './obstacle.model'

export const obstacleFixtures: Obstacle[] = [
  { id: 'obs-A', x: 750,  y: 750,  width: 750,  depth: 750,  height: 2500, label: 'A' },
  { id: 'obs-B', x: 8000, y: 2500, width: 1500, depth: 300,  height: 2500, label: 'B' },
  { id: 'obs-C', x: 1500, y: 4200, width: 200,  depth: 4600, height: 2500, label: 'C' },
]
