// Variable-height warehouse: ceiling height is interpolated per polygon vertex along X

import { useMemo, useState } from 'react'
import * as THREE from 'three'
import { Text } from '@react-three/drei'
import { SCALE, COLORS } from '../../../shared/constants'
import { pointInPolygon, sampleStepCtrlPoints } from '../../../shared/math.utils'

/** @param {{ warehouse: import('../../../domain/warehouse/warehouse.model').Warehouse }} props */
export default function WarehouseMesh({ warehouse }) {
  const { polygon, ceilingCtrlPoints } = warehouse
  const [hoveredCorner, setHoveredCorner] = useState(null)

  const { floorGeo, ceilGeo, wallsGeo, stepWallsGeo, corners } = useMemo(() => {
    const eps = 1e-6
    const renderPolygon = insertCeilingXCutsOnPolygon(polygon, ceilingCtrlPoints)
    const n = renderPolygon.length
    const ceilingAtX = (x) => sampleStepCtrlPoints(x, ceilingCtrlPoints) // ceiling.csv => [coordX, ceilingHeight] por tramos
    const cutXs = [...new Set((ceilingCtrlPoints ?? []).map(([x]) => x))].sort((a, b) => a - b)

    // World-space bottom and top for each polygon vertex
    const bottom = renderPolygon.map(([x, y]) => [x * SCALE, 0, -y * SCALE])
    const top    = renderPolygon.map(([x, y]) => [
      x * SCALE,
      ceilingAtX(x) * SCALE,
      -y * SCALE,
    ])
    let corners = []

    function buildGeo(triVerts) {
      const pos = new Float32Array(triVerts.length * 9)
      let p = 0
      for (const [a, b, c] of triVerts) {
        for (const v of [a, b, c]) { pos[p++] = v[0]; pos[p++] = v[1]; pos[p++] = v[2] }
      }
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
      g.computeVertexNormals()
      return g
    }

    // Triangulate floor on full footprint
    const floorContour = renderPolygon.map(([x, y]) => new THREE.Vector2(x * SCALE, -y * SCALE))
    const floorTris = THREE.ShapeUtils.triangulateShape(floorContour, [])
    const floorGeo = buildGeo(floorTris.map(([a, b, c]) => [bottom[c], bottom[b], bottom[a]]))

    // Ceiling as step slices in X (avoids ramps across cuts)
    const polyXs = polygon.map(([x]) => x)
    const minX = Math.min(...polyXs)
    const maxX = Math.max(...polyXs)
    const interiorCuts = cutXs.filter((x) => x > minX + eps && x < maxX - eps)
    const cornersBase = renderPolygon.map(([x, y], idx) => ({
      idx,
      x,
      y,
      z: ceilingAtX(x),
      worldPos: top[idx],
    }))
    const cutJumpCorners = buildCutJumpCorners(renderPolygon, interiorCuts, ceilingAtX, eps)
    corners = dedupeCornersByXYZ([
      ...cornersBase,
      ...cutJumpCorners,
    ])
    const xBounds = [minX, ...interiorCuts, maxX]
    const ceilTriVerts = []

    for (let i = 0; i < xBounds.length - 1; i++) {
      const xL = xBounds[i]
      const xR = xBounds[i + 1]
      if (xR - xL <= eps) continue

      const clipped = clipPolygonByXRange(polygon, xL, xR, eps)
      if (clipped.length < 3) continue

      const h = ceilingAtX((xL + xR) / 2) * SCALE
      const contour = clipped.map(([x, y]) => new THREE.Vector2(x * SCALE, -y * SCALE))
      const tris = THREE.ShapeUtils.triangulateShape(contour, [])
      for (const [a, b, c] of tris) {
        const va = clipped[a]; const vb = clipped[b]; const vc = clipped[c]
        ceilTriVerts.push(
          [va[0] * SCALE, h, -va[1] * SCALE],
          [vb[0] * SCALE, h, -vb[1] * SCALE],
          [vc[0] * SCALE, h, -vc[1] * SCALE],
        )
      }
    }
    const ceilGeo = buildGeo(ceilTriVerts)

    // Walls: split each boundary edge by X cuts and keep constant height per segment
    const wallArr = []
    for (let i = 0; i < polygon.length; i++) {
      const [x0, y0] = polygon[i]
      const [x1, y1] = polygon[(i + 1) % polygon.length]

      const segPts = [{ t: 0, x: x0, y: y0 }, { t: 1, x: x1, y: y1 }]
      if (Math.abs(x1 - x0) > eps) {
        const minX = Math.min(x0, x1) + eps
        const maxX = Math.max(x0, x1) - eps
        for (const xCut of cutXs) {
          if (xCut > minX && xCut < maxX) {
            const t = (xCut - x0) / (x1 - x0)
            segPts.push({ t, x: xCut, y: y0 + t * (y1 - y0) })
          }
        }
      }
      segPts.sort((a, b) => a.t - b.t)

      for (let k = 0; k < segPts.length - 1; k++) {
        const a = segPts[k]
        const b = segPts[k + 1]
        if (Math.hypot(b.x - a.x, b.y - a.y) <= eps) continue

        const h = interiorSegmentHeight(a, b, polygon, ceilingAtX) * SCALE
        const bx0 = a.x * SCALE, by0 = 0, bz0 = -a.y * SCALE
        const bx1 = b.x * SCALE, by1 = 0, bz1 = -b.y * SCALE
        const tx0 = a.x * SCALE, ty0 = h, tz0 = -a.y * SCALE
        const tx1 = b.x * SCALE, ty1 = h, tz1 = -b.y * SCALE

        wallArr.push(
          bx0, by0, bz0,  bx1, by1, bz1,  tx1, ty1, tz1,
          bx0, by0, bz0,  tx1, ty1, tz1,  tx0, ty0, tz0,
        )
      }
    }
    const wallsGeo = new THREE.BufferGeometry()
    wallsGeo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(wallArr), 3))
    wallsGeo.computeVertexNormals()

    // Internal vertical walls at each X cut where height jumps
    const stepWallArr = []
    for (const xCut of interiorCuts) {
      const hL = ceilingAtX(xCut - eps)
      const hR = ceilingAtX(xCut + eps)
      if (Math.abs(hL - hR) < eps) continue

      const hMin = Math.min(hL, hR) * SCALE
      const hMax = Math.max(hL, hR) * SCALE
      const yIntervals = verticalScanlineYIntervals(polygon, xCut, eps)
      for (const [y0, y1] of yIntervals) {
        const xw = xCut * SCALE
        const z0 = -y0 * SCALE
        const z1 = -y1 * SCALE
        stepWallArr.push(
          xw, hMin, z0,  xw, hMin, z1,  xw, hMax, z1,
          xw, hMin, z0,  xw, hMax, z1,  xw, hMax, z0,
        )
      }
    }
    const stepWallsGeo = new THREE.BufferGeometry()
    stepWallsGeo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(stepWallArr), 3))
    stepWallsGeo.computeVertexNormals()

    return { floorGeo, ceilGeo, wallsGeo, stepWallsGeo, corners }
  }, [polygon, ceilingCtrlPoints])

  return (
    <group>
      <mesh geometry={floorGeo} receiveShadow>
        <meshStandardMaterial color={COLORS.floor} side={THREE.FrontSide} />
      </mesh>

      <mesh geometry={ceilGeo}>
        <meshStandardMaterial
          color={COLORS.warehouse} transparent opacity={0.13}
          side={THREE.DoubleSide} depthWrite={false}
        />
      </mesh>

      <mesh geometry={wallsGeo}>
        <meshStandardMaterial
          color={COLORS.warehouse} transparent opacity={0.10}
          side={THREE.DoubleSide} depthWrite={false}
        />
      </mesh>

      <mesh geometry={stepWallsGeo}>
        <meshStandardMaterial
          color={COLORS.warehouse} transparent opacity={0.14}
          side={THREE.DoubleSide} depthWrite={false}
        />
      </mesh>

      <lineSegments>
        <edgesGeometry args={[wallsGeo]} />
        <lineBasicMaterial color={COLORS.warehouseWire} />
      </lineSegments>
      <lineSegments>
        <edgesGeometry args={[ceilGeo]} />
        <lineBasicMaterial color={COLORS.warehouseWire} transparent opacity={0.5} />
      </lineSegments>
      <lineSegments>
        <edgesGeometry args={[stepWallsGeo]} />
        <lineBasicMaterial color={COLORS.warehouseWire} transparent opacity={0.6} />
      </lineSegments>

      {corners.map((corner, i) => {
        const isHovered = hoveredCorner === corner.idx
        const [cx, cy, cz] = corner.worldPos
        return (
          <group key={`${corner.idx}-${i}`} position={[cx, cy, cz]}>
            <mesh
              onPointerOver={(e) => { e.stopPropagation(); setHoveredCorner(corner.idx) }}
              onPointerOut={(e) => { e.stopPropagation(); setHoveredCorner(null) }}
            >
              <sphereGeometry args={[0.06, 16, 16]} />
              <meshStandardMaterial
                color={isHovered ? '#ffee58' : '#80deea'}
                emissive={isHovered ? '#fdd835' : '#006064'}
                emissiveIntensity={isHovered ? 0.9 : 0.2}
                transparent
                opacity={0.95}
              />
            </mesh>

            {isHovered && (
              <Text
                position={[0, 0.2, 0]}
                fontSize={0.13}
                color="#ffffff"
                anchorX="center"
                anchorY="bottom"
                outlineWidth={0.01}
                outlineColor="#000000"
              >
                {`x:${Math.round(corner.x)} y:${Math.round(corner.y)} z:${Math.round(corner.z)}`}
              </Text>
            )}
          </group>
        )
      })}
    </group>
  )
}

function clipPolygonByXRange(polygon, xMin, xMax, eps) {
  const clippedMin = clipPolygonAgainstXMin(polygon, xMin - eps)
  const clipped = clipPolygonAgainstXMax(clippedMin, xMax + eps)
  return dedupeConsecutivePoints(clipped, eps)
}

function clipPolygonAgainstXMin(polygon, xMin) {
  return clipPolygon(polygon, (p) => p[0] >= xMin, (a, b) => {
    const t = (xMin - a[0]) / (b[0] - a[0])
    return [xMin, a[1] + t * (b[1] - a[1])]
  })
}

function clipPolygonAgainstXMax(polygon, xMax) {
  return clipPolygon(polygon, (p) => p[0] <= xMax, (a, b) => {
    const t = (xMax - a[0]) / (b[0] - a[0])
    return [xMax, a[1] + t * (b[1] - a[1])]
  })
}

function clipPolygon(polygon, isInside, intersect) {
  if (!polygon.length) return []
  const out = []
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i]
    const b = polygon[(i + 1) % polygon.length]
    const aInside = isInside(a)
    const bInside = isInside(b)

    if (aInside && bInside) {
      out.push(b)
    } else if (aInside && !bInside) {
      out.push(intersect(a, b))
    } else if (!aInside && bInside) {
      out.push(intersect(a, b))
      out.push(b)
    }
  }
  return out
}

function dedupeConsecutivePoints(points, eps) {
  const out = []
  for (const p of points) {
    const last = out[out.length - 1]
    if (!last || Math.abs(last[0] - p[0]) > eps || Math.abs(last[1] - p[1]) > eps) {
      out.push(p)
    }
  }
  if (out.length > 1) {
    const first = out[0]
    const last = out[out.length - 1]
    if (Math.abs(first[0] - last[0]) <= eps && Math.abs(first[1] - last[1]) <= eps) out.pop()
  }
  return out
}

function verticalScanlineYIntervals(polygon, x, eps) {
  const yHits = []
  for (let i = 0; i < polygon.length; i++) {
    const j = (i + 1) % polygon.length
    const [x0, y0] = polygon[i]
    const [x1, y1] = polygon[j]

    if (Math.abs(x1 - x0) < eps) continue
    const intersects = (x0 <= x && x < x1) || (x1 <= x && x < x0)
    if (!intersects) continue
    const t = (x - x0) / (x1 - x0)
    yHits.push(y0 + t * (y1 - y0))
  }

  yHits.sort((a, b) => a - b)
  const intervals = []
  for (let i = 0; i + 1 < yHits.length; i += 2) {
    intervals.push([yHits[i], yHits[i + 1]])
  }
  return intervals
}

function interiorSegmentHeight(a, b, polygon, ceilingAtX) {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const len = Math.hypot(dx, dy)
  if (len <= 1e-9) return ceilingAtX(a.x)

  const mx = (a.x + b.x) / 2
  const my = (a.y + b.y) / 2
  const nx = -dy / len
  const ny = dx / len
  const probe = 0.5 // mm towards the interior

  const p1x = mx + nx * probe
  const p1y = my + ny * probe
  if (pointInPolygon(p1x, p1y, polygon)) return ceilingAtX(p1x)

  const p2x = mx - nx * probe
  const p2y = my - ny * probe
  if (pointInPolygon(p2x, p2y, polygon)) return ceilingAtX(p2x)

  return ceilingAtX(mx)
}

function insertCeilingXCutsOnPolygon(polygon, ceilingCtrlPoints) {
  if (!polygon?.length || !ceilingCtrlPoints?.length) return polygon ?? []

  const eps = 1e-6
  const cutXs = [...new Set(ceilingCtrlPoints.map(([x]) => x))]
  const out = []

  for (let i = 0; i < polygon.length; i++) {
    const [x0, y0] = polygon[i]
    const [x1, y1] = polygon[(i + 1) % polygon.length]

    out.push([x0, y0])

    if (Math.abs(x1 - x0) < eps) continue

    const minX = Math.min(x0, x1) + eps
    const maxX = Math.max(x0, x1) - eps
    const cutsOnEdge = cutXs
      .filter((x) => x > minX && x < maxX)
      .map((x) => {
        const t = (x - x0) / (x1 - x0)
        return { t, x, y: y0 + t * (y1 - y0) }
      })
      .sort((a, b) => a.t - b.t)

    for (const c of cutsOnEdge) {
      out.push([c.x, c.y])
    }
  }

  const deduped = []
  for (const p of out) {
    const last = deduped[deduped.length - 1]
    if (!last || Math.abs(last[0] - p[0]) > eps || Math.abs(last[1] - p[1]) > eps) {
      deduped.push(p)
    }
  }
  return deduped
}

function buildCutJumpCorners(renderPolygon, interiorCuts, ceilingAtX, eps) {
  const out = []
  for (const [x, y] of renderPolygon) {
    const xCut = interiorCuts.find((xc) => Math.abs(x - xc) <= eps * 10)
    if (xCut == null) continue
    const hL = ceilingAtX(xCut - eps)
    const hR = ceilingAtX(xCut + eps)
    if (Math.abs(hL - hR) < eps) continue

    out.push({ idx: `cut-${x}-${y}-a`, x, y, z: hL, worldPos: [x * SCALE, hL * SCALE, -y * SCALE] })
    out.push({ idx: `cut-${x}-${y}-b`, x, y, z: hR, worldPos: [x * SCALE, hR * SCALE, -y * SCALE] })
  }
  return out
}

function dedupeCornersByXYZ(corners) {
  const seen = new Set()
  const out = []
  for (const c of corners) {
    const k = `${Math.round(c.x * 1000)}|${Math.round(c.y * 1000)}|${Math.round(c.z * 1000)}`
    if (seen.has(k)) continue
    seen.add(k)
    out.push(c)
  }
  return out
}
