// Single bay rendered as a BoxGeometry; highlights on hover

import { useRef, useState } from 'react'
import { SCALE, COLORS } from '../../../shared/constants'
import { getTypeColor, parseTypeIdFromLabel } from '../../../shared/type-colors'

function clamp01(v) {
  return Math.max(0, Math.min(1, v))
}

function smootherStep(t) {
  const x = clamp01(t)
  return x * x * x * (x * (x * 6 - 15) + 10)
}

/**
 * @param {{ bay: import('../../../domain/bay/bay.model').Bay,
 *           typeColorMap?: import('../../../shared/type-colors').TypeColorMap,
 *           dropProgress?: number,
 *           dropIndex?: number,
 *           dropTotal?: number,
 *           onHover: (bay: import('../../../domain/bay/bay.model').Bay | null) => void }} props
 */
export default function BayMesh({ bay, typeColorMap, dropProgress = 1, dropIndex = 0, dropTotal = 1, onHover }) {
  const ref = useRef(null)
  const [hovered, setHovered] = useState(false)

  const w = bay.width * SCALE
  const d = bay.depth * SCALE
  const h = bay.height * SCALE
  const rotationRad = (bay.rotation ?? 0) * Math.PI / 180  // convert degrees to radians
  
  let cx, cz
  
  if (bay.isCenter) {
    // x,y is the center, add half-offsets (no rotation compensation)
    cx = bay.x * SCALE + w / 2
    cz = -(bay.y * SCALE + d / 2)
  } else {
    // x,y is the corner; apply rotation compensation to keep corner at original position
    const cos_r = Math.cos(rotationRad)
    const sin_r = Math.sin(rotationRad)
    
    // Unrotated center offset from corner
    const ux = w / 2
    const uy = d / 2
    
    // Rotated center offset (to keep corner at original position)
    const rotated_offset_x = ux * cos_r - uy * sin_r
    const rotated_offset_y = ux * sin_r + uy * cos_r
    
    cx = bay.x * SCALE + rotated_offset_x
    cz = -(bay.y * SCALE + rotated_offset_y)
  }
  
  const baseCy = h / 2

  const staggerMax = 0.35
  const stagger = dropTotal > 1 ? (dropIndex / (dropTotal - 1)) * staggerMax : 0
  const localP = clamp01((dropProgress - stagger) / (1 - stagger))

  // Base curve: very smooth accel/decel
  const eased = smootherStep(localP)

  // Subtle damped settle near the end (adds fluid feel without harsh bounce)
  const settleWindow = clamp01((localP - 0.72) / 0.28)
  const settleOsc = Math.sin(settleWindow * Math.PI * 2.2)
  const settleAmp = (1 - settleWindow) * 0.07
  const settle = settleOsc * settleAmp

  const dropHeight = Math.max(3.2, h * 4.8 + 1.8)
  const cy = baseCy + (1 - eased) * dropHeight + settle

  const typeId = bay.bayTypeId ?? parseTypeIdFromLabel(bay.label)
  const baseColor = getTypeColor(typeId, typeColorMap, COLORS.bay)

  return (
    <mesh
      ref={ref}
      position={[cx, cy, cz]}
      rotation={[0, rotationRad, 0]}
      castShadow
      receiveShadow
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(bay) }}
      onPointerOut={() => { setHovered(false); onHover(null) }}
    >
      <boxGeometry args={[w, h, d]} />
      <meshStandardMaterial
        color={baseColor}
        emissive={baseColor}
        emissiveIntensity={hovered ? 0.28 : 0.08}
        metalness={0.2}
        roughness={0.65}
        transparent
        opacity={0.28 + 0.72 * eased}
      />
    </mesh>
  )
}
