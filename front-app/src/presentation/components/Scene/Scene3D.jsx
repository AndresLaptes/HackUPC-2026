import { Canvas } from '@react-three/fiber'
import { Grid } from '@react-three/drei'
import Lights from './Lights'
import CameraControls from './CameraControls'
import WarehouseMesh from '../Warehouse/WarehouseMesh'
import BaysGroup from '../Bays/BaysGroup'
import ObstaclesGroup from '../Obstacles/ObstaclesGroup'
import { ViewControlsBridge } from './ViewControls'
import { AxisGizmoSync } from './AxisGizmo'

export default function Scene3D({ warehouse, layout, obstacles, typeColorMap, dropProgress = 1, onBayHover, onObstacleHover, bridgeRef, gizmoDomRef, gizmoStateRef, showGaps = true, colorRandomSeed = 0 }) {
  return (
    <Canvas
      shadows
      camera={{ position: [6, 8, 12], fov: 45, near: 0.01, far: 200 }}
      style={{ position: 'absolute', inset: 0, background: '#0f0f0f' }}
    >
      <Lights />
      <CameraControls />
      <Grid
        args={[30, 30]}
        cellSize={1}
        cellThickness={0.4}
        cellColor="#37474f"
        sectionSize={5}
        sectionThickness={0.8}
        sectionColor="#546e7a"
        fadeDistance={50}
        position={[0, -0.001, 0]}
      />
      <WarehouseMesh warehouse={warehouse} />
      <ObstaclesGroup obstacles={obstacles} warehouse={warehouse} onObstacleHover={onObstacleHover} />
      <BaysGroup layout={layout} typeColorMap={typeColorMap} dropProgress={dropProgress} onBayHover={onBayHover} showGaps={showGaps} colorRandomSeed={colorRandomSeed} />
      <ViewControlsBridge ref={bridgeRef} />
      <AxisGizmoSync domRef={gizmoDomRef} stateRef={gizmoStateRef} />
    </Canvas>
  )
}
