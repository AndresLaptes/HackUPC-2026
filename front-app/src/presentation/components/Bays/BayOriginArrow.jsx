// Local axis arrows at bay origin corner (X and Y) to visualize orientation

import { SCALE } from '../../../shared/constants'

/**
 * @param {{
 *   direction: 'x' | 'y',
 *   length: number,
 *   thickness: number,
 *   color: string,
 * }} props
 */
function AxisArrow({ direction, length, thickness, color }) {
  // In this scene, warehouse Y axis is mapped to world -Z.
  const baseRotation = direction === 'x' ? [0, 0, -Math.PI / 2] : [-Math.PI / 2, 0, 0]
  const shaftLength = length * 0.75
  const headLength = length * 0.25

  return (
    <group>
      <mesh rotation={baseRotation} position={[0, 0, 0]}>
        <cylinderGeometry args={[thickness * 0.5, thickness * 0.5, shaftLength, 10]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
      </mesh>

      {direction === 'x' ? (
        <mesh position={[length, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[thickness * 1.6, headLength, 10]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
        </mesh>
      ) : (
        <mesh position={[0, 0, -length]} rotation={[-Math.PI / 2, 0, 0]}>
          <coneGeometry args={[thickness * 1.6, headLength, 10]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
        </mesh>
      )}
    </group>
  )
}

/**
 * @param {{ bay: import('../../../domain/bay/bay.model').Bay }} props
 */
export default function BayOriginArrow({ bay }) {
  const cornerX = bay.x * SCALE
  const cornerZ = -(bay.y * SCALE)
  const cornerY = bay.height * SCALE + 0.04
  const rotationRad = (bay.rotation ?? 0) * Math.PI / 180

  const axisLength = Math.max(0.25, Math.min(bay.width * SCALE, bay.depth * SCALE) * 0.35)
  const axisThickness = Math.max(0.02, axisLength * 0.08)

  return (
    <group position={[cornerX, cornerY, cornerZ]} rotation={[0, rotationRad, 0]}>
      <mesh>
        <sphereGeometry args={[axisThickness * 0.9, 10, 10]} />
        <meshStandardMaterial color="#ffffff" emissive="#ffffff" emissiveIntensity={0.25} />
      </mesh>

      <AxisArrow direction="x" length={axisLength} thickness={axisThickness} color="#ef5350" />
      <AxisArrow direction="y" length={axisLength} thickness={axisThickness} color="#66bb6a" />
    </group>
  )
}
