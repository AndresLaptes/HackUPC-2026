import { Text } from '@react-three/drei'

const L = 0.7   // arm length
const CR = 0.03 // cylinder radius
const HR = 0.18 // head sphere radius

// cylRot rotates a Y-axis cylinder to point along each axis direction
const AXES = [
  { key: '+x', color: '#e53935', label: 'X',  headPos: [L, 0, 0],  cylRot: [0, 0, -Math.PI / 2] },
  { key: '-x', color: '#c62828', label: null, headPos: [-L, 0, 0], cylRot: [0, 0, Math.PI / 2] },
  { key: '+y', color: '#43a047', label: 'Y',  headPos: [0, L, 0],  cylRot: [0, 0, 0] },
  { key: '-y', color: '#2e7d32', label: null, headPos: [0, -L, 0], cylRot: [Math.PI, 0, 0] },
  { key: '+z', color: '#1e88e5', label: 'Z',  headPos: [0, 0, L],  cylRot: [Math.PI / 2, 0, 0] },
  { key: '-z', color: '#1565c0', label: null, headPos: [0, 0, -L], cylRot: [-Math.PI / 2, 0, 0] },
]

export default function CustomGizmoViewport({ bridgeRef }) {
  return (
    <>
      {AXES.map(({ key, color, label, headPos, cylRot }) => (
        <group key={key}>
          {/* axis stick — cylinder centered at half-length along local Y, then rotated */}
          <group rotation={cylRot}>
            <mesh position={[0, L / 2, 0]}>
              <cylinderGeometry args={[CR, CR, L, 8]} />
              <meshBasicMaterial color={color} />
            </mesh>
          </group>

          {/* clickable head */}
          <mesh
            position={headPos}
            onClick={(e) => { e.stopPropagation(); bridgeRef.current?.setView(key) }}
            onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = 'pointer' }}
            onPointerOut={(e) => { e.stopPropagation(); document.body.style.cursor = '' }}
          >
            <sphereGeometry args={[HR, 16, 16]} />
            <meshBasicMaterial color={color} />
          </mesh>

          {/* axis label on the positive heads only */}
          {label && (
            <Text
              position={headPos}
              fontSize={0.25}
              color="white"
              anchorX="center"
              anchorY="middle"
              renderOrder={1}
              depthOffset={-1}
            >
              {label}
            </Text>
          )}
        </group>
      ))}
    </>
  )
}
