// Core warehouse value types — no framework imports

export interface Warehouse {
  /** Outline polygon as [x, y] pairs in mm */
  polygon: [number, number][]
  /** Variable ceiling defined by [x, height] control points in mm */
  ceilingCtrlPoints: [number, number][]
  label: string
}
