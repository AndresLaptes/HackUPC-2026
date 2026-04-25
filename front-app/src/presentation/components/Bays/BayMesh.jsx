// Single bay rendered as a BoxGeometry; highlights on hover and red when collision

import { useRef, useState } from 'react'
import { SCALE, COLORS } from '../../../shared/constants'

/**
 * @param {{ bay: import('../../../domain/bay/bay.model').Bay,
 *           hasCollision: boolean,
 *           onHover: (bay: import('../../../domain/bay/bay.model').Bay | null) => void }} props
 */
export default function BayMesh({ bay, hasCollision, onHover }) {
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
  
  const cy = h / 2

  const color = hasCollision ? COLORS.bayCollision : hovered ? COLORS.bayHover : COLORS.bay

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
      <meshStandardMaterial color={color} metalness={0.2} roughness={0.7} />
    </mesh>
  )
}
