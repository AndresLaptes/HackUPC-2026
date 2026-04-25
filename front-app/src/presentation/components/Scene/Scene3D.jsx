// Root Three.js canvas — camera, lights, grid, and scene content

import { Canvas } from '@react-three/fiber'
import { Grid } from '@react-three/drei'
import Lights from './Lights'
import CameraControls from './CameraControls'
import WarehouseMesh from '../Warehouse/WarehouseMesh'
import BaysGroup from '../Bays/BaysGroup'
import ObstaclesGroup from '../Obstacles/ObstaclesGroup'

/**
 * @param {{ warehouse: import('../../../domain/warehouse/warehouse.model').Warehouse,
 *           layout: import('../../../domain/bay/bay.model').BayLayout[],
 *           obstacles: import('../../../domain/obstacle/obstacle.model').Obstacle[],
 *           onBayHover: (bay: import('../../../domain/bay/bay.model').Bay | null) => void }} props
 */
export default function Scene3D({ warehouse, layout, obstacles, onBayHover }) {
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
      <ObstaclesGroup obstacles={obstacles} warehouse={warehouse} />
      <BaysGroup layout={layout} onBayHover={onBayHover} />
    </Canvas>
  )
}
