// Maps the computed bay layout to individual BayMesh components

import BayMesh from './BayMesh'
import BayOriginArrow from './BayOriginArrow'
import BayGapMesh from './BayGapMesh'

/**
 * @param {{ layout: import('../../../domain/bay/bay.model').BayLayout[],
 *           typeColorMap?: import('../../../shared/type-colors').TypeColorMap,
 *           dropProgress?: number,
 *           onBayHover: (bay: import('../../../domain/bay/bay.model').Bay | null) => void,
 *           showGaps?: boolean,
 *           colorRandomSeed?: number }} props
 */
export default function BaysGroup({ layout, typeColorMap, dropProgress = 1, onBayHover, showGaps = true, colorRandomSeed = 0 }) {
  const total = layout.length

  return (
    <group>
      {layout.map(({ bay }, index) => {
        return (
          <group key={bay.id}>
            <BayMesh
              bay={bay}
              typeColorMap={typeColorMap}
              dropProgress={dropProgress}
              dropIndex={index}
              dropTotal={total}
              onHover={onBayHover}
            />
            <BayOriginArrow
              bay={bay}
              dropProgress={dropProgress}
              dropIndex={index}
              dropTotal={total}
            />
            {showGaps && (
              <BayGapMesh
                bay={bay}
                dropProgress={dropProgress}
                dropIndex={index}
                dropTotal={total}
              />
            )}
          </group>
        )
      })}
    </group>
  )
}
