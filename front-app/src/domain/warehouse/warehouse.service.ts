// Business logic for warehouse geometry — pure functions, no framework deps

import type { Warehouse } from './warehouse.model'
import { pointInPolygon, sampleStepCtrlPoints } from '../../shared/math.utils'

export function getCeilingHeight(warehouse: Warehouse, xMm: number): number {
  return sampleStepCtrlPoints(xMm, warehouse.ceilingCtrlPoints)
}

export function isPointInside(warehouse: Warehouse, xMm: number, yMm: number): boolean {
  return pointInPolygon(xMm, yMm, warehouse.polygon)
}

export function validateWarehouse(warehouse: Warehouse): string[] {
  const errors: string[] = []
  if (warehouse.polygon.length < 3) errors.push('Polygon must have at least 3 points')
  if (warehouse.ceilingCtrlPoints.length < 1) errors.push('At least one ceiling control point required')
  const negativeHeights = warehouse.ceilingCtrlPoints.filter(([, h]) => h <= 0)
  if (negativeHeights.length) errors.push('All ceiling heights must be positive')
  return errors
}
