// Renders a single obstacle as a BoxGeometry with hover interaction

import { useRef, useState } from 'react'
import { Text } from '@react-three/drei'
import { SCALE, COLORS } from '../../../shared/constants'
import { sampleStepCtrlPoints } from '../../../shared/math.utils'

/**
 * @param {{ obstacle: import('../../../domain/obstacle/obstacle.model').Obstacle,
 *           warehouse?: import('../../../domain/warehouse/warehouse.model').Warehouse,
 *           onHover: (obstacle: import('../../../domain/obstacle/obstacle.model').Obstacle | null) => void }} props
 */
export default function ObstacleMesh({ obstacle, warehouse, onHover }) {
  const ref = useRef(null)
  const [hovered, setHovered] = useState(false)
  const w = obstacle.width * SCALE
  const d = obstacle.depth * SCALE
  const inferredHeight = warehouse
    ? sampleStepCtrlPoints(obstacle.x + obstacle.width / 2, warehouse.ceilingCtrlPoints ?? [])
    : 2500
  const h = (obstacle.height ?? inferredHeight) * SCALE
  const cx = obstacle.x * SCALE + w / 2
  const cz = -(obstacle.y * SCALE + d / 2)   // polygon Y maps to -Z after rotateX(-π/2)
  const cy = h / 2

  return (
    <group ref={ref} position={[cx, cy, cz]}>
      <mesh
        castShadow
        receiveShadow
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(obstacle) }}
        onPointerOut={() => { setHovered(false); onHover(null) }}
      >
        <boxGeometry args={[w, h, d]} />
        <meshStandardMaterial
          color={COLORS.obstacle}
          emissive={COLORS.obstacle}
          emissiveIntensity={hovered ? 0.3 : 0.08}
          metalness={0.1}
          roughness={0.8}
        />
      </mesh>
      <Text
        position={[0, h / 2 + 0.15, 0]}
        fontSize={0.18}
        color="#ffffff"
        anchorX="center"
        anchorY="bottom"
      >
        {obstacle.label}
      </Text>
    </group>
  )
}
