import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { SCALE, COLORS } from '../../shared/constants'
import { getTypeColor } from '../../shared/type-colors'

/**
 * Floating popup with bay type stats + mini 3D preview.
 * Positioned to the right of the cursor/sidebar.
 *
 * @param {{ type: import('../../domain/bay/bay.model').BayType, typeColorMap?: import('../../shared/type-colors').TypeColorMap, anchorEl: HTMLElement | null }} props
 */
export default function BayTypePopup({ type, typeColorMap, anchorEl }) {
  if (!type || !anchorEl) return null

  const rect = anchorEl.getBoundingClientRect()
  const top  = Math.min(rect.top, window.innerHeight - 320)
  const left = rect.right + 12

  const w = type.width  * SCALE
  const d = type.depth  * SCALE
  const h = type.height * SCALE
  const typeColor = getTypeColor(type.id, typeColorMap, COLORS.bay)

  // Camera sits at a 45° angle to show all three faces
  const maxDim = Math.max(w, d, h)
  const camDist = maxDim * 2.8
  const camPos  = [camDist * 0.9, camDist * 0.7, camDist * 0.9]

  return (
    <div style={{ ...styles.popup, top, left }}>
      <div style={styles.header}>
        <span style={{ ...styles.typeSwatch, background: typeColor }} />
        <span>Type {type.id}</span>
      </div>

      <div style={styles.preview}>
        <Canvas
          camera={{ position: camPos, fov: 40, near: 0.001, far: 100 }}
          style={{ width: '100%', height: '100%', background: '#0a1014' }}
        >
          <ambientLight intensity={0.5} />
          <directionalLight position={[3, 5, 4]} intensity={0.8} />
          <directionalLight position={[-2, 2, -2]} intensity={0.3} />
          <mesh>
            <boxGeometry args={[w, h, d]} />
            <meshStandardMaterial
              color={typeColor}
              emissive={typeColor}
              emissiveIntensity={0.08}
              metalness={0.2}
              roughness={0.6}
            />
          </mesh>
          {/* Shelf lines to convey loads */}
          {Array.from({ length: type.nLoads }, (_, i) => {
            const loadY = -h / 2 + (h / (type.nLoads + 1)) * (i + 1)
            return (
              <mesh key={i} position={[0, loadY, 0]}>
                <boxGeometry args={[w + 0.002, 0.004, d + 0.002]} />
                <meshStandardMaterial color="#90caf9" />
              </mesh>
            )
          })}
          <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={2} />
        </Canvas>
      </div>

      <div style={styles.stats}>
        <Stat label="Width"   value={`${type.width} mm`} />
        <Stat label="Depth"   value={`${type.depth} mm`} />
        <Stat label="Height"  value={`${type.height} mm`} />
        <Stat label="Gap"     value={`${type.gap} mm`} />
        <Stat label="Loads"   value={type.nLoads} />
        <Stat label="Price"   value={`€ ${type.price}`} />
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div style={styles.stat}>
      <span style={styles.statLabel}>{label}</span>
      <span style={styles.statValue}>{value}</span>
    </div>
  )
}

const styles = {
  popup: {
    position: 'fixed',
    zIndex: 100,
    width: 220,
    background: 'rgba(8, 18, 24, 0.97)',
    border: '1px solid #1e3a4a',
    borderRadius: 10,
    boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
    overflow: 'hidden',
    pointerEvents: 'none',
  },
  header: {
    padding: '8px 12px',
    fontSize: 13,
    fontWeight: 700,
    color: '#eceff1',
    borderBottom: '1px solid #1e2d35',
    background: '#0f2230',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  typeSwatch: {
    width: 10,
    height: 10,
    borderRadius: 999,
    border: '1px solid rgba(255,255,255,0.35)',
    boxShadow: '0 0 6px rgba(255,255,255,0.18) inset',
    flex: '0 0 auto',
  },
  preview: {
    width: '100%',
    height: 150,
  },
  stats: {
    padding: '8px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  stat: {
    display: 'flex',
    justifyContent: 'space-between',
  },
  statLabel: { fontSize: 11, color: '#546e7a' },
  statValue: { fontSize: 11, color: '#b0bec5', fontWeight: 500 },
}
