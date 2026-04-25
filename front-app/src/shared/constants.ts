// Global scale and design tokens shared across all layers

export const SCALE = 0.001 // 1 mm → 0.001 Three.js units

export const COLORS = {
  warehouse: '#b0bec5',
  warehouseWire: '#546e7a',
  bay: '#1565c0',
  bayHover: '#42a5f5',
  bayCollision: '#c62828',
  obstacle: '#e65100',
  obstacleWire: '#bf360c',
  floor: '#263238',
  grid: '#37474f',
  ambient: '#ffffff',
  directional: '#ffffff',
} as const

export const BAY_DEFAULTS = {
  width: 2700,   // mm
  depth: 1100,   // mm
  height: 2000,  // mm
  gap: 100,      // mm between bays
  nLoads: 3,
  price: 0,
} as const
