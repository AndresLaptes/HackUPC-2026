// Visualize the gap (separation space) around each bay

import { SCALE } from '../../../shared/constants'

function clamp01(v) {
  return Math.max(0, Math.min(1, v))
}

function smootherStep(t) {
  const x = clamp01(t)
  return x * x * x * (x * (x * 6 - 15) + 10)
}

/**
 * @param {{ bay: import('../../../domain/bay/bay.model').Bay,
 *           dropProgress?: number,
 *           dropIndex?: number,
 *           dropTotal?: number }} props
 */
export default function BayGapMesh({ bay, dropProgress = 1, dropIndex = 0, dropTotal = 1 }) {
  // Always render gaps if bay has gap data (regardless of gapSide value)
  if (!bay.gap || bay.gap <= 0) {
    return null
  }

  const w = bay.width * SCALE
  const d = bay.depth * SCALE
  const h = bay.height * SCALE
  const g = bay.gap * SCALE
  const rotationRad = (bay.rotation ?? 0) * Math.PI / 180

  // Calculate bay center position (same as BayMesh)
  let cx, cz
  if (bay.isCenter) {
    cx = bay.x * SCALE + w / 2
    cz = -(bay.y * SCALE + d / 2)
  } else {
    const cos_r = Math.cos(rotationRad)
    const sin_r = Math.sin(rotationRad)
    const ux = w / 2
    const uy = d / 2
    const rotated_offset_x = ux * cos_r - uy * sin_r
    const rotated_offset_y = ux * sin_r + uy * cos_r
    cx = bay.x * SCALE + rotated_offset_x
    cz = -(bay.y * SCALE + rotated_offset_y)
  }

  // Animate opacity with the bay drop
  const staggerMax = 0.35
  const stagger = dropTotal > 1 ? (dropIndex / (dropTotal - 1)) * staggerMax : 0
  const localP = clamp01((dropProgress - stagger) / (1 - stagger))
  const eased = smootherStep(localP)
  const settleWindow = clamp01((localP - 0.72) / 0.28)
  const settleOsc = Math.sin(settleWindow * Math.PI * 2.2)
  const settleAmp = (1 - settleWindow) * 0.07
  const settle = settleOsc * settleAmp
  const dropHeight = Math.max(3.2, h * 4.8 + 1.8)
  const baseCy = h / 2
  const cy = baseCy + (1 - eased) * dropHeight + settle

  // Gap geometry: single separation space at the back of the bay
  // The gap extends along the Y axis (depth) behind the bay
  // It's a rectangular volume: [width, height, gapDepth]
  
  let gapPosOffsets = []
  let gapSizes = []

  // Only render if bay has gap data
  if (bay.gap && bay.gap > 0) {
    // Base offset in local space: centered along X, behind the bay in Z
    const baseOffset = [0, 0, -(d / 2 + g / 2)]
    gapSizes.push([w, h, g])

    // Apply rotation to offset
    const cos_r = Math.cos(rotationRad)
    const sin_r = Math.sin(rotationRad)
    const rotated_x = baseOffset[0] * cos_r - baseOffset[2] * sin_r
    const rotated_z = baseOffset[0] * sin_r + baseOffset[2] * cos_r
    gapPosOffsets.push([rotated_x, baseOffset[1], rotated_z])
  }

  const gapOpacity = 0.15 + 0.25 * eased

  return (
    <>
      {gapPosOffsets.map((offset, idx) => (
        <mesh
          key={`gap-${bay.id}-${idx}`}
          position={[cx + offset[0], cy + offset[1], cz + offset[2]]}
          rotation={[0, rotationRad, 0]}
          castShadow={false}
          receiveShadow={false}
        >
          <boxGeometry args={gapSizes[idx]} />
          <meshStandardMaterial
            color="#ffeb3b"
            emissive="#ffeb3b"
            emissiveIntensity={0.4}
            metalness={0.1}
            roughness={0.8}
            transparent
            opacity={gapOpacity}
            wireframe={false}
          />
        </mesh>
      ))}
    </>
  )
}
