// Canonical L-shaped warehouse fixture used for development and tests

import type { Warehouse } from './warehouse.model'

export const warehouseFixture: Warehouse = {
  label: 'L-Warehouse',
  polygon: [
    [0, 0],
    [10000, 0],
    [10000, 3000],
    [3000, 3000],
    [3000, 10000],
    [0, 10000],
  ],
  ceilingCtrlPoints: [
    [0, 3000],
    [3000, 2000],
    [6000, 3000],
  ],
}
