// OrbitControls configuration — zoom limits tuned for warehouse scale

import { OrbitControls } from '@react-three/drei'

export default function CameraControls() {
  return (
    <OrbitControls
      makeDefault
      minDistance={1}
      maxDistance={30}
enableDamping
      dampingFactor={0.08}
    />
  )
}
