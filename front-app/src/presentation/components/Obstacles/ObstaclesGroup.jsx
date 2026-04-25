// Maps obstacle list to individual ObstacleMesh components

import ObstacleMesh from './ObstacleMesh'

/** @param {{ obstacles: import('../../../domain/obstacle/obstacle.model').Obstacle[], warehouse: import('../../../domain/warehouse/warehouse.model').Warehouse }} props */
export default function ObstaclesGroup({ obstacles, warehouse }) {
  return (
    <group>
      {obstacles.map((obstacle) => (
        <ObstacleMesh key={obstacle.id} obstacle={obstacle} warehouse={warehouse} />
      ))}
    </group>
  )
}
