// Maps the computed bay layout to individual BayMesh components

import BayMesh from './BayMesh'

/**
 * @param {{ layout: import('../../../domain/bay/bay.model').BayLayout[],
 *           onBayHover: (bay: import('../../../domain/bay/bay.model').Bay | null) => void }} props
 */
export default function BaysGroup({ layout, onBayHover }) {
  return (
    <group>
      {layout.map(({ bay, hasCollision }) => (
        <BayMesh
          key={bay.id}
          bay={bay}
          hasCollision={hasCollision}
          onHover={onBayHover}
        />
      ))}
    </group>
  )
}
