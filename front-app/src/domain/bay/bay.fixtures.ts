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
