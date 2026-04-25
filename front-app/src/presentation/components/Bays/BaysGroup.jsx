// Maps the computed bay layout to individual BayMesh components

import BayMesh from './BayMesh'
import BayOriginArrow from './BayOriginArrow'

/**
 * @param {{ layout: import('../../../domain/bay/bay.model').BayLayout[],
 *           typeColorMap?: import('../../../shared/type-colors').TypeColorMap,
 *           onBayHover: (bay: import('../../../domain/bay/bay.model').Bay | null) => void }} props
 */
export default function BaysGroup({ layout, typeColorMap, onBayHover }) {
  return (
    <group>
      {layout.map(({ bay }) => (
        <group key={bay.id}>
          <BayMesh
            bay={bay}
            typeColorMap={typeColorMap}
            onHover={onBayHover}
          />
          <BayOriginArrow bay={bay} />
        </group>
      ))}
    </group>
  )
}
