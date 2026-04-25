import { useThree } from '@react-three/fiber'
import { useRef, forwardRef, useImperativeHandle } from 'react'
import * as THREE from 'three'

// Exported imperative handle — call setView(axis) from outside the Canvas
export const ViewControlsBridge = forwardRef(function ViewControlsBridge(_, ref) {
  const { camera, controls } = useThree()

  useImperativeHandle(ref, () => ({
    setView(axis) {
      const distance = camera.position.length() || 14
      const targets = {
        '+x': [distance, 0, 0],
        '-x': [-distance, 0, 0],
        '+y': [0, distance, 0],
        '-y': [0, -distance, 0],
        '+z': [0, 0, distance],
        '-z': [0, 0, -distance],
      }
      const pos = targets[axis] ?? targets['+y']
      camera.position.set(...pos)
      camera.lookAt(0, 0, 0)
      if (controls) {
        controls.target.set(0, 0, 0)
        controls.update()
      }
    },
  }))

  return null
})

const BTN_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  position: 'absolute',
  top: 12,
  right: 120, // leave room for gizmo (~110 px wide)
  zIndex: 10,
}

const btn = (color) => ({
  width: 36,
  height: 28,
  border: 'none',
  borderRadius: 5,
  background: color,
  color: '#fff',
  fontWeight: 700,
  fontSize: 11,
  letterSpacing: 0.5,
  cursor: 'pointer',
  boxShadow: '0 2px 6px rgba(0,0,0,0.5)',
  transition: 'filter 0.15s',
})

const VIEWS = [
  { label: '+X', axis: '+x', color: '#c62828' },
  { label: '-X', axis: '-x', color: '#8d1a1a' },
  { label: '+Y', axis: '+y', color: '#2e7d32' },
  { label: '-Y', axis: '-y', color: '#1b4d1e' },
  { label: '+Z', axis: '+z', color: '#1565c0' },
  { label: '-Z', axis: '-z', color: '#0d3b6e' },
]

export default function ViewControlsOverlay({ bridgeRef }) {
  return (
    <div style={BTN_STYLE}>
      {VIEWS.map(({ label, axis, color }) => (
        <button
          key={axis}
          style={btn(color)}
          title={`Vista desde eje ${label}`}
          onMouseEnter={(e) => (e.currentTarget.style.filter = 'brightness(1.3)')}
          onMouseLeave={(e) => (e.currentTarget.style.filter = '')}
          onClick={() => bridgeRef.current?.setView(axis)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
