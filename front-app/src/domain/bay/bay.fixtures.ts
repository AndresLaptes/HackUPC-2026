// Sample bays placed inside the L-shaped warehouse for development

import type { Bay } from './bay.model'

export const bayFixtures: Bay[] = [
  {
    id: 'bay-1',
    x: 200, y: 200,
    width: 2700, depth: 1100, height: 2000,
    gap: 100, nLoads: 3, price: 1200, label: 'R-01',
  },
  {
    id: 'bay-2',
    x: 3100, y: 200,
    width: 2700, depth: 1100, height: 2000,
    gap: 100, nLoads: 3, price: 1200, label: 'R-02',
  },
  {
    id: 'bay-3',
    x: 200, y: 1500,
    width: 2700, depth: 1100, height: 2000,
    gap: 100, nLoads: 3, price: 1200, label: 'R-03',
  },
]

// Test fixtures for Case 0
export const case0BayFixtures: Bay[] = [
  {
    id: 'bay-0',
    x: 6600, y: 2900,
    width: 800, depth: 1200, height: 2800,
    gap: 200, nLoads: 4, price: 2000, label: 'Bay-0',
    rotation: 180,
  },
  {
    id: 'bay-1',
    x: 1000, y: 1600,
    width: 1600, depth: 1200, height: 2800,
    gap: 200, nLoads: 8, price: 2500, label: 'Bay-1',
    rotation: 70,
    isCenter: true,
  },
  {
    id: 'bay-2a',
    x: 0, y: 5400,
    width: 2400, depth: 1200, height: 2800,
    gap: 200, nLoads: 12, price: 2800, label: 'Bay-2a',
    rotation: 270,
  },
  {
    id: 'bay-2b',
    x: 0, y: 9900,
    width: 2400, depth: 1200, height: 2800,
    gap: 200, nLoads: 12, price: 2800, label: 'Bay-2b',
    rotation: 270,
  },
  {
    id: 'bay-2c',
    x: 5000, y: 0,
    width: 2400, depth: 1200, height: 2800,
    gap: 200, nLoads: 12, price: 2800, label: 'Bay-2c',
    rotation: 0,
  },
  {
    id: 'bay-4',
    x: 4400, y: 2900,
    width: 1600, depth: 1000, height: 1800,
    gap: 150, nLoads: 6, price: 2300, label: 'Bay-4',
    rotation: 180,
  },
  {
    id: 'bay-5',
    x: 2000, y: 0,
    width: 2400, depth: 1000, height: 1800,
    gap: 150, nLoads: 9, price: 2600, label: 'Bay-5',
    rotation: 0,
  },
]
