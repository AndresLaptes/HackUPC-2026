import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const S = 100     // CSS size in px
const C = S / 2   // center
const ARM = 36    // axis arm length in px
const HR = 9      // head radius in px

const AXES = [
  { dir: new THREE.Vector3(1, 0, 0),  color: '#e53935', key: '+x', label: 'X' },
  { dir: new THREE.Vector3(-1, 0, 0), color: '#c62828', key: '-x', label: null },
  { dir: new THREE.Vector3(0, 1, 0),  color: '#43a047', key: '+y', label: 'Y' },
  { dir: new THREE.Vector3(0, -1, 0), color: '#2e7d32', key: '-y', label: null },
  { dir: new THREE.Vector3(0, 0, 1),  color: '#1e88e5', key: '+z', label: 'Z' },
  { dir: new THREE.Vector3(0, 0, -1), color: '#1565c0', key: '-z', label: null },
]

// Lives inside Canvas — reads camera each frame, draws to 2D overlay canvas
export function AxisGizmoSync({ domRef, stateRef }) {
  useFrame(({ camera }) => {
    const canvas = domRef.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    const bw = Math.round(S * dpr)
    if (canvas.width !== bw) { canvas.width = bw; canvas.height = bw }

    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.save()
    ctx.scale(dpr, dpr)

    const projected = AXES.map(({ dir, color, key, label }) => {
      const v = dir.clone().transformDirection(camera.matrixWorldInverse)
      return { x: C + v.x * ARM, y: C - v.y * ARM, z: v.z, color, key, label }
    })

    // store for click detection
    stateRef.current = projected

    // draw back-to-front
    const sorted = [...projected].sort((a, b) => b.z - a.z)

    for (const p of sorted) {
      ctx.beginPath()
      ctx.moveTo(C, C)
      ctx.lineTo(p.x, p.y)
      ctx.strokeStyle = p.color
      ctx.lineWidth = 2.5
      ctx.stroke()
    }

    for (const p of sorted) {
      ctx.beginPath()
      ctx.arc(p.x, p.y, HR, 0, Math.PI * 2)
      ctx.fillStyle = p.color
      ctx.fill()

      if (p.label) {
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 11px system-ui,sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(p.label, p.x, p.y)
      }
    }

    ctx.restore()
  })

  return null
}

// Lives outside Canvas — HTML canvas overlay
export default function AxisGizmoOverlay({ domRef, stateRef, bridgeRef }) {
  function handleClick(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    const cx = e.clientX - rect.left
    const cy = e.clientY - rect.top

    let closest = null
    let minDist = HR * 2.5
    for (const p of stateRef.current) {
      const d = Math.hypot(cx - p.x, cy - p.y)
      if (d < minDist) { minDist = d; closest = p }
    }
    if (closest) bridgeRef.current?.setView(closest.key)
  }

  return (
    <canvas
      ref={domRef}
      width={S}
      height={S}
      style={{
        position: 'absolute',
        top: 8,
        right: 8,
        width: S,
        height: S,
        zIndex: 10,
        cursor: 'crosshair',
        borderRadius: 8,
        background: 'rgba(0,0,0,0.25)',
      }}
      title="Click an axis to snap view"
      onClick={handleClick}
    />
  )
}
