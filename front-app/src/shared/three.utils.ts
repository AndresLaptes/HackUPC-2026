// Three.js geometry helpers — imported only by presentation layer

import * as THREE from 'three'
import { SCALE } from './constants'

/** Convert mm coordinates to a Three.js Vector3 (Y-up, Z as depth) */
export function toVec3(xMm: number, yMm: number, zMm: number): THREE.Vector3 {
  return new THREE.Vector3(xMm * SCALE, zMm * SCALE, yMm * SCALE)
}

/** Build a THREE.Shape from a flat list of [x, y] polygon points (in mm) */
export function buildShapeFromPoints(points: [number, number][]): THREE.Shape {
  const shape = new THREE.Shape()
  shape.moveTo(points[0][0] * SCALE, points[0][1] * SCALE)
  for (let i = 1; i < points.length; i++) {
    shape.lineTo(points[i][0] * SCALE, points[i][1] * SCALE)
  }
  shape.closePath()
  return shape
}
