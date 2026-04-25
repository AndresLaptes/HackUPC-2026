// Maps the computed bay layout to individual BayMesh components

import BayMesh from './BayMesh'
import BayOriginArrow from './BayOriginArrow'

/**
 * @param {{ layout: import('../../../domain/bay/bay.model').BayLayout[],
 *           onBayHover: (bay: import('../../../domain/bay/bay.model').Bay | null) => void }} props
 */
export default function BaysGroup({ layout, onBayHover }) {
  return (
    <group>
      {layout.map(({ bay }) => (
        <group key={bay.id}>
          <BayMesh
            bay={bay}
            onHover={onBayHover}
          />
          <BayOriginArrow bay={bay} />
        </group>
      ))}
    </group>
  )
}
