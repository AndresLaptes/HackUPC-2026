// Local axis arrows at bay origin corner (X and Y) to visualize orientation

import { SCALE } from '../../../shared/constants'

function clamp01(v) {
  return Math.max(0, Math.min(1, v))
}

function smootherStep(t) {
  const x = clamp01(t)
  return x * x * x * (x * (x * 6 - 15) + 10)
}

/**
 * @param {{
 *   direction: 'x' | 'y',
 *   length: number,
 *   thickness: number,
 *   color: string,
 * }} props
 */
function AxisArrow({ direction, length, thickness, color, opacity = 1 }) {
  // In this scene, warehouse Y axis is mapped to world -Z.
  const baseRotation = direction === 'x' ? [0, 0, -Math.PI / 2] : [-Math.PI / 2, 0, 0]
  const shaftLength = length * 0.75
  const headLength = length * 0.25

  return (
    <group>
      <mesh rotation={baseRotation} position={[0, 0, 0]}>
        <cylinderGeometry args={[thickness * 0.5, thickness * 0.5, shaftLength, 10]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} transparent opacity={opacity} />
      </mesh>

      {direction === 'x' ? (
        <mesh position={[length, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[thickness * 1.6, headLength, 10]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} transparent opacity={opacity} />
        </mesh>
      ) : (
        <mesh position={[0, 0, -length]} rotation={[-Math.PI / 2, 0, 0]}>
          <coneGeometry args={[thickness * 1.6, headLength, 10]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} transparent opacity={opacity} />
        </mesh>
      )}
    </group>
  )
}

/**
 * @param {{ bay: import('../../../domain/bay/bay.model').Bay,
 *           dropProgress?: number,
 *           dropIndex?: number,
 *           dropTotal?: number }} props
 */
export default function BayOriginArrow({ bay, dropProgress = 1, dropIndex = 0, dropTotal = 1 }) {
  const cornerX = bay.x * SCALE
  const cornerZ = -(bay.y * SCALE)
  const baseCornerY = bay.height * SCALE + 0.04
  const rotationRad = (bay.rotation ?? 0) * Math.PI / 180

  const h = bay.height * SCALE
  const staggerMax = 0.45
  const stagger = dropTotal > 1 ? (dropIndex / (dropTotal - 1)) * staggerMax : 0
  const localP = clamp01((dropProgress - stagger) / (1 - stagger))
  const eased = smootherStep(localP)
  const dropHeight = Math.max(3.2, h * 4.8 + 1.8)
  const cornerY = baseCornerY + (1 - eased) * dropHeight
  const opacity = clamp01((localP - 0.08) / 0.92)

  const axisLength = Math.max(0.25, Math.min(bay.width * SCALE, bay.depth * SCALE) * 0.35)
  const axisThickness = Math.max(0.02, axisLength * 0.08)

  return (
    <group position={[cornerX, cornerY, cornerZ]} rotation={[0, rotationRad, 0]}>
      <mesh>
        <sphereGeometry args={[axisThickness * 0.9, 10, 10]} />
        <meshStandardMaterial color="#ffffff" emissive="#ffffff" emissiveIntensity={0.25} transparent opacity={opacity} />
      </mesh>

      <AxisArrow direction="x" length={axisLength} thickness={axisThickness} color="#ef5350" opacity={opacity} />
      <AxisArrow direction="y" length={axisLength} thickness={axisThickness} color="#66bb6a" opacity={opacity} />
    </group>
  )
}
