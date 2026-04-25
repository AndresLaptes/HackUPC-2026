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
  const cx = bay.x * SCALE + w / 2
  const cz = -(bay.y * SCALE + d / 2)   // polygon Y maps to -Z after rotateX(-π/2)
  const cy = h / 2

  const color = hasCollision ? COLORS.bayCollision : hovered ? COLORS.bayHover : COLORS.bay

  return (
    <mesh
      ref={ref}
      position={[cx, cy, cz]}
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
