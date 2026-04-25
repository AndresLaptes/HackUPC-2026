import { useMemo, useRef, useState } from 'react'
import BayTypePopup from './BayTypePopup'
import { sampleStepCtrlPoints } from '../../shared/math.utils'
import { getTypeColor, parseTypeIdFromLabel } from '../../shared/type-colors'

export default function CaseSidebar({ warehouse, obstacles = [], bayTypes = [], layout = [], typeColorMap, solveElapsedSeconds = null, dropProgress = 1, hoveredBay, hoveredObstacle }) {
  const [collapsed, setCollapsed] = useState(false)
  const [hoveredType, setHoveredType] = useState(null)
  const [anchorEl, setAnchorEl] = useState(null)

  const kpis = useMemo(() => {
    if (!warehouse?.polygon?.length) return null

    const warehouseArea = polygonAreaMm2(warehouse.polygon)
    const obstaclesArea = obstacles.reduce((sum, o) => sum + o.width * o.depth, 0)
    // Gap does not count as used area. Area depends on which side the gap is on:
    // gapSide 1 (top) or 2 (bottom) → gap runs along width; 3 (left) or 4 (right) → along depth.
    const occupiedArea = layout.reduce((sum, item) => {
      const { width, depth, gap = 0, gapSide = -1 } = item.bay
      const bayArea = width * depth
      let gapArea = 0
      if (gap > 0) {
        if (gapSide === 1 || gapSide === 2) gapArea = gap * width
        else if (gapSide === 3 || gapSide === 4) gapArea = gap * depth
      }
      return sum + bayArea - gapArea
    }, 0)
    const usableArea = Math.max(0, warehouseArea - obstaclesArea)
    const freeArea = Math.max(0, usableArea - occupiedArea)
    const occupiedDensity = usableArea > 0 ? Math.min(100, (occupiedArea / usableArea) * 100) : 0

    return {
      occupiedDensity,
      freeArea,
      occupiedArea,
      usableArea,
    }
  }, [warehouse, obstacles, layout])

  const selectedTypeId = hoveredBay
    ? (hoveredBay.bayTypeId ?? parseTypeIdFromLabel(hoveredBay.label))
    : null

  const hoveredObstacleHeight = hoveredObstacle
    ? obstacleTopHeight(hoveredObstacle, warehouse)
    : null

  return (
    <>
      <aside style={{ ...styles.aside, width: collapsed ? 40 : 288 }}>
        <button style={styles.collapseBtn} onClick={() => setCollapsed((c) => !c)}>
          {collapsed ? '›' : '‹'}
        </button>

        {!collapsed && (
          <>
            {kpis && (
              <section style={styles.section}>
                <h2 style={styles.heading}>KPIs</h2>
                {typeof solveElapsedSeconds === 'number' && (
                  <Row label="Tiempo algoritmo" value={`${solveElapsedSeconds.toFixed(2)} s`} />
                )}
                {layout.length > 0 && dropProgress < 1 && (
                  <Row label="Animación" value={`${Math.round(dropProgress * 100)} %`} />
                )}
                <Row label="Densidad ocupada" value={`${kpis.occupiedDensity.toFixed(1)} %`} />
                <Row label="Área libre" value={`${mm2ToM2(kpis.freeArea)} m²`} />
                <Row label="Área ocupada" value={`${mm2ToM2(kpis.occupiedArea)} m²`} />
                <Row label="Área útil" value={`${mm2ToM2(kpis.usableArea)} m²`} />
              </section>
            )}

            {bayTypes.length > 0 && (
              <section style={styles.section}>
                <h2 style={styles.heading}>Bay types — hover to preview</h2>
                <TypeLegend bayTypes={bayTypes} typeColorMap={typeColorMap} />
                <div style={styles.typeList}>
                  {bayTypes.map((t) => (
                    <BayTypeRow
                      key={t.id}
                      type={t}
                      onEnter={(el) => { setHoveredType(t); setAnchorEl(el) }}
                      onLeave={() => { setHoveredType(null); setAnchorEl(null) }}
                    />
                  ))}
                </div>
              </section>
            )}

            {hoveredBay && (
              <section style={styles.section}>
                <h2 style={styles.heading}>Selected Bay</h2>
                <Row label="ID"    value={selectedTypeId ?? '-'} />
                <Row label="Pos"   value={`(${hoveredBay.x}, ${hoveredBay.y})`} />
                <Row label="Size"  value={`${hoveredBay.width}×${hoveredBay.depth}×${hoveredBay.height}`} />
                <Row label="Loads" value={hoveredBay.nLoads} />
                <Row label="Price" value={`€ ${hoveredBay.price}`} />
              </section>
            )}

            {hoveredObstacle && (
              <section style={styles.section}>
                <h2 style={styles.heading}>Selected Obstacle</h2>
                <Row label="ID"    value={hoveredObstacle.id} />
                <Row label="Label" value={hoveredObstacle.label} />
                <Row label="Pos"   value={`(${hoveredObstacle.x}, ${hoveredObstacle.y})`} />
                <Row label="Size"  value={`${hoveredObstacle.width}×${hoveredObstacle.depth}×${hoveredObstacleHeight}`} />
              </section>
            )}

          </>
        )}
      </aside>

      <BayTypePopup type={hoveredType} typeColorMap={typeColorMap} anchorEl={anchorEl} />
    </>
  )
}

function TypeLegend({ bayTypes, typeColorMap }) {
  return (
    <div style={styles.legendWrap}>
      {bayTypes.map((t) => (
        <div key={`legend-${t.id}`} style={styles.legendItem}>
          <span style={{ ...styles.legendSwatch, background: getTypeColor(t.id, typeColorMap) }} />
          <span style={styles.legendText}>ID {t.id}</span>
        </div>
      ))}
    </div>
  )
}

function polygonAreaMm2(polygon) {
  if (!polygon?.length) return 0
  let acc = 0
  for (let i = 0; i < polygon.length; i++) {
    const [x1, y1] = polygon[i]
    const [x2, y2] = polygon[(i + 1) % polygon.length]
    acc += x1 * y2 - x2 * y1
  }
  return Math.abs(acc) / 2
}

function mm2ToM2(mm2) {
  return (mm2 / 1_000_000).toFixed(2)
}

function Views2D({ warehouse, obstacles }) {
  const top = buildTopView(warehouse, obstacles)
  const xSide = buildXSideView(warehouse, obstacles)
  const ySide = buildYSideView(warehouse, obstacles)

  return (
    <div style={styles.viewsGrid}>
      <MiniSvgView title="Top (XY)" data={top} />
      <MiniSvgView title="Side X (XZ)" data={xSide} />
      <MiniSvgView title="Side Y (YZ)" data={ySide} />
    </div>
  )
}

function MiniSvgView({ title, data }) {
  return (
    <div style={styles.miniView}>
      <div style={styles.miniViewTitle}>{title}</div>
      <svg viewBox="0 0 240 140" style={styles.miniSvg}>
        <rect x="0" y="0" width="240" height="140" fill="#071017" stroke="#1a2a33" />

        {data.paths.map((d, i) => (
          <polyline
            key={`p-${i}`}
            points={d.points}
            fill={d.fill ?? 'none'}
            stroke={d.stroke}
            strokeWidth={d.strokeWidth ?? 1.5}
            opacity={d.opacity ?? 1}
          />
        ))}

        {data.rects.map((r, i) => (
          <rect
            key={`r-${i}`}
            x={r.x}
            y={r.y}
            width={r.w}
            height={r.h}
            fill={r.fill}
            stroke={r.stroke}
            strokeWidth={1}
            opacity={r.opacity ?? 0.6}
          />
        ))}
      </svg>
    </div>
  )
}

function ObstacleVertices({ obstacle, warehouse }) {
  const h = obstacleTopHeight(obstacle, warehouse)
  const x0 = obstacle.x
  const y0 = obstacle.y
  const x1 = obstacle.x + obstacle.width
  const y1 = obstacle.y + obstacle.depth

  const verts = [
    [x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0],
    [x0, y0, h], [x1, y0, h], [x1, y1, h], [x0, y1, h],
  ]

  return (
    <div style={styles.obstacleCard}>
      <div style={styles.obstacleCardTitle}>{obstacle.label} ({obstacle.id})</div>
      <div style={styles.vertexList}>
        {verts.map((v, idx) => (
          <div key={`${obstacle.id}-v-${idx}`} style={styles.vertexRow}>
            <span style={styles.vertexIdx}>V{idx}</span>
            <span style={styles.vertexValue}>({fmt(v[0])}, {fmt(v[1])}, {fmt(v[2])})</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function buildTopView(warehouse, obstacles) {
  const W = 240
  const H = 140
  const pad = 12
  const xs = warehouse.polygon.map(([x]) => x)
  const ys = warehouse.polygon.map(([, y]) => y)

  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  const sx = (W - pad * 2) / Math.max(1, maxX - minX)
  const sy = (H - pad * 2) / Math.max(1, maxY - minY)
  const s = Math.min(sx, sy)
  const drawW = (maxX - minX) * s
  const drawH = (maxY - minY) * s
  const offX = (W - drawW) / 2
  const offY = (H - drawH) / 2

  const tx = (x) => offX + (x - minX) * s
  const ty = (y) => H - offY - (y - minY) * s

  const whPoints = warehouse.polygon.map(([x, y]) => `${tx(x)},${ty(y)}`).join(' ')
  const paths = [{ points: `${whPoints} ${whPoints.split(' ')[0]}`, fill: '#102532', stroke: '#8ecae6', opacity: 0.9 }]
  const rects = obstacles.map((o) => ({
    x: tx(o.x),
    y: ty(o.y + o.depth),
    w: Math.max(1, o.width * s),
    h: Math.max(1, o.depth * s),
    fill: '#ff8f00',
    stroke: '#ffe082',
    opacity: 0.75,
  }))

  return { paths, rects }
}

function buildXSideView(warehouse, obstacles) {
  const W = 240
  const H = 140
  const pad = 12

  const xs = warehouse.polygon.map(([x]) => x)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const maxZ = Math.max(
    ...warehouse.ceilingCtrlPoints.map(([, z]) => z),
    ...obstacles.map((o) => obstacleTopHeight(o, warehouse)),
    1,
  )

  const sx = (W - pad * 2) / Math.max(1, maxX - minX)
  const sz = (H - pad * 2) / Math.max(1, maxZ)
  const s = Math.min(sx, sz)
  const drawW = (maxX - minX) * s
  const drawH = maxZ * s
  const offX = (W - drawW) / 2
  const offY = (H - drawH) / 2

  const tx = (x) => offX + (x - minX) * s
  const tz = (z) => H - offY - z * s

  const ceilingSorted = [...warehouse.ceilingCtrlPoints].sort((a, b) => a[0] - b[0])
  const profilePoints = [`${tx(minX)},${tz(0)}`]
  for (const [x, z] of ceilingSorted) profilePoints.push(`${tx(x)},${tz(z)}`)
  profilePoints.push(`${tx(maxX)},${tz(0)}`)
  profilePoints.push(`${tx(minX)},${tz(0)}`)

  const paths = [{ points: profilePoints.join(' '), fill: '#14351e', stroke: '#8bc34a', opacity: 0.88 }]
  const rects = obstacles.map((o) => ({
    x: tx(o.x),
    y: tz(obstacleTopHeight(o, warehouse)),
    w: Math.max(1, o.width * s),
    h: Math.max(1, obstacleTopHeight(o, warehouse) * s),
    fill: '#ffa726',
    stroke: '#ffe0b2',
    opacity: 0.65,
  }))

  return { paths, rects }
}

function buildYSideView(warehouse, obstacles) {
  const W = 240
  const H = 140
  const pad = 12

  const ys = warehouse.polygon.map(([, y]) => y)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const maxZ = Math.max(
    ...warehouse.ceilingCtrlPoints.map(([, z]) => z),
    ...obstacles.map((o) => obstacleTopHeight(o, warehouse)),
    1,
  )

  const sy = (W - pad * 2) / Math.max(1, maxY - minY)
  const sz = (H - pad * 2) / Math.max(1, maxZ)
  const s = Math.min(sy, sz)
  const drawW = (maxY - minY) * s
  const drawH = maxZ * s
  const offX = (W - drawW) / 2
  const offY = (H - drawH) / 2

  const ty = (y) => offX + (y - minY) * s
  const tz = (z) => H - offY - z * s

  const samples = 70
  const topProfile = []
  for (let i = 0; i <= samples; i++) {
    const y = minY + (i / samples) * (maxY - minY)
    const zTop = maxCeilingAtY(warehouse.polygon, warehouse.ceilingCtrlPoints, y)
    topProfile.push([ty(y), tz(zTop)])
  }

  const envelope = [
    `${ty(minY)},${tz(0)}`,
    ...topProfile.map(([py, pz]) => `${py},${pz}`),
    `${ty(maxY)},${tz(0)}`,
    `${ty(minY)},${tz(0)}`,
  ]

  const paths = [{ points: envelope.join(' '), fill: '#2a1d35', stroke: '#ba68c8', opacity: 0.88 }]
  const rects = obstacles.map((o) => ({
    x: ty(o.y),
    y: tz(obstacleTopHeight(o, warehouse)),
    w: Math.max(1, o.depth * s),
    h: Math.max(1, obstacleTopHeight(o, warehouse) * s),
    fill: '#ffb74d',
    stroke: '#ffe0b2',
    opacity: 0.65,
  }))

  return { paths, rects }
}

function maxCeilingAtY(polygon, ceilingCtrlPoints, y) {
  const intervals = scanlineXIntervalsAtY(polygon, y)
  if (!intervals.length) return 0

  let maxZ = 0
  for (const [x0, x1] of intervals) {
    maxZ = Math.max(maxZ, ceilingMaxOnXInterval(x0, x1, ceilingCtrlPoints))
  }
  return maxZ
}

function scanlineXIntervalsAtY(polygon, y) {
  const xHits = []
  for (let i = 0; i < polygon.length; i++) {
    const j = (i + 1) % polygon.length
    const [x0, y0] = polygon[i]
    const [x1, y1] = polygon[j]

    // semiclosed rule to avoid counting vertices twice
    const intersects = (y0 <= y && y < y1) || (y1 <= y && y < y0)
    if (!intersects) continue
    const t = (y - y0) / (y1 - y0)
    xHits.push(x0 + t * (x1 - x0))
  }

  xHits.sort((a, b) => a - b)
  const intervals = []
  for (let i = 0; i + 1 < xHits.length; i += 2) {
    intervals.push([xHits[i], xHits[i + 1]])
  }
  return intervals
}

function ceilingMaxOnXInterval(x0, x1, ctrlPoints) {
  if (!ctrlPoints?.length) return 0
  const lo = Math.min(x0, x1)
  const hi = Math.max(x0, x1)
  const xs = [lo, hi]
  for (const [x] of ctrlPoints) {
    if (x > lo && x < hi) xs.push(x)
  }
  let maxZ = 0
  for (const x of xs) {
    maxZ = Math.max(maxZ, sampleStepCtrlPoints(x, ctrlPoints))
  }
  return maxZ
}

function obstacleTopHeight(obstacle, warehouse) {
  if (obstacle.height != null) return obstacle.height
  if (!warehouse?.ceilingCtrlPoints?.length) return 2500
  return sampleStepCtrlPoints(obstacle.x + obstacle.width / 2, warehouse.ceilingCtrlPoints)
}

function warehouseVerticesWithCeilingCuts(polygon, ceilingCtrlPoints) {
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
    const cuts = cutXs
      .filter((x) => x > minX && x < maxX)
      .map((x) => {
        const t = (x - x0) / (x1 - x0)
        return { t, x, y: y0 + t * (y1 - y0) }
      })
      .sort((a, b) => a.t - b.t)

    for (const c of cuts) out.push([c.x, c.y])
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

function warehouseVerticesXYZForDisplay(polygon, ceilingCtrlPoints) {
  const pts = warehouseVerticesWithCeilingCuts(polygon, ceilingCtrlPoints)
  if (!ceilingCtrlPoints?.length) return pts.map(([x, y]) => [x, y, 0])

  const eps = 1e-6
  const xs = polygon.map(([x]) => x)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const interiorCuts = [...new Set(ceilingCtrlPoints.map(([x]) => x))]
    .filter((x) => x > minX + eps && x < maxX - eps)

  const out = []
  for (const [x, y] of pts) {
    const xCut = interiorCuts.find((xc) => Math.abs(x - xc) <= eps * 10)
    if (xCut == null) {
      out.push([x, y, sampleStepCtrlPoints(x, ceilingCtrlPoints)])
      continue
    }

    const zLeft = sampleStepCtrlPoints(xCut - eps, ceilingCtrlPoints)
    const zRight = sampleStepCtrlPoints(xCut + eps, ceilingCtrlPoints)
    if (Math.abs(zLeft - zRight) <= eps) {
      out.push([x, y, zRight])
      continue
    }

    const zTop = Math.max(zLeft, zRight)
    const zBottom = Math.min(zLeft, zRight)
    out.push([x, y, zTop])
    out.push([x, y, zBottom])
  }

  return dedupeXYZ(out)
}

function dedupeXYZ(points) {
  const seen = new Set()
  const out = []
  for (const [x, y, z] of points) {
    const k = `${Math.round(x * 1000)}|${Math.round(y * 1000)}|${Math.round(z * 1000)}`
    if (seen.has(k)) continue
    seen.add(k)
    out.push([x, y, z])
  }
  return out
}

function fmt(n) {
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function BayTypeRow({ type, onEnter, onLeave }) {
  const ref = useRef(null)
  const [hov, setHov] = useState(false)

  function handleEnter() {
    setHov(true)
    onEnter(ref.current)
  }
  function handleLeave() {
    setHov(false)
    onLeave()
  }

  return (
    <div
      ref={ref}
      style={{ ...styles.typeRow, ...(hov ? styles.typeRowHov : {}) }}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <span style={styles.typeId}>T{type.id}</span>
      <span style={styles.typeDims}>{type.width}×{type.depth}×{type.height}</span>
      <span style={styles.typeLoads}>{type.nLoads} loads</span>
      <span style={styles.typePrice}>€{type.price}</span>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div style={styles.row}>
      <span style={styles.rowLabel}>{label}</span>
      <span style={styles.rowValue}>{value}</span>
    </div>
  )
}

function boundingBox(polygon) {
  const xs = polygon.map(([x]) => x)
  const ys = polygon.map(([, y]) => y)
  return {
    w: Math.max(...xs) - Math.min(...xs),
    h: Math.max(...ys) - Math.min(...ys),
  }
}

const styles = {
  aside: {
    position: 'absolute', top: 12, left: 12, bottom: 12,
    zIndex: 10,
    background: 'rgba(10, 20, 24, 0.90)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 12,
    padding: '48px 14px 20px',
    display: 'flex', flexDirection: 'column', gap: 20,
    overflowY: 'auto',
    transition: 'width 0.2s ease',
    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
  },
  collapseBtn: {
    position: 'absolute', top: 10, right: 10,
    background: 'transparent', border: '1px solid #37474f',
    borderRadius: 6, color: '#90a4ae', fontSize: 18, lineHeight: 1,
    width: 24, height: 24, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0,
  },
  title:    { fontSize: 15, fontWeight: 700, color: '#eceff1', margin: 0 },
  heading:  { fontSize: 10, fontWeight: 600, color: '#546e7a', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 8px' },
  section:  { display: 'flex', flexDirection: 'column' },
  row:      { display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #0d1e27' },
  rowLabel: { fontSize: 12, color: '#546e7a' },
  rowValue: { fontSize: 12, color: '#b0bec5', textAlign: 'right' },
  typeList: { display: 'flex', flexDirection: 'column', gap: 3 },
  legendWrap: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 8,
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    background: '#0a1a23',
    border: '1px solid #123140',
    borderRadius: 999,
    padding: '2px 7px',
  },
  legendSwatch: {
    width: 10,
    height: 10,
    borderRadius: 999,
    border: '1px solid rgba(255,255,255,0.35)',
    boxShadow: '0 0 6px rgba(255,255,255,0.15) inset',
  },
  legendText: {
    fontSize: 10,
    color: '#cfd8dc',
    fontWeight: 600,
  },
  typeRow: {
    display: 'grid',
    gridTemplateColumns: '28px 1fr auto auto',
    gap: 6,
    alignItems: 'center',
    padding: '5px 8px',
    borderRadius: 6,
    cursor: 'default',
    background: 'transparent',
    transition: 'background 0.12s',
    userSelect: 'none',
  },
  typeRowHov:   { background: '#0f2230' },
  typeId:       { fontSize: 11, fontWeight: 700, color: '#4db6e6' },
  typeDims:     { fontSize: 10, color: '#78909c' },
  typeLoads:    { fontSize: 10, color: '#b0bec5' },
  typePrice:    { fontSize: 10, color: '#a5d6a7' },
  vertexList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    border: '1px solid #0d1e27',
    borderRadius: 6,
    padding: '6px 8px',
    background: '#081219',
  },
  vertexRow: {
    display: 'grid',
    gridTemplateColumns: '26px 1fr',
    gap: 8,
    alignItems: 'center',
  },
  vertexIdx: {
    fontSize: 11,
    color: '#81d4fa',
    fontWeight: 600,
  },
  vertexValue: {
    fontSize: 11,
    color: '#cfd8dc',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  },
  obstacleCard: {
    border: '1px solid #13303b',
    borderRadius: 8,
    padding: 8,
    background: '#08121b',
  },
  obstacleCardTitle: {
    fontSize: 11,
    color: '#90caf9',
    marginBottom: 6,
    fontWeight: 600,
  },
  viewsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  miniView: {
    display: 'flex',
    flexDirection: 'column',
    gap: 5,
  },
  miniViewTitle: {
    fontSize: 11,
    color: '#90a4ae',
    fontWeight: 600,
  },
  miniSvg: {
    width: '100%',
    height: 140,
    borderRadius: 6,
    border: '1px solid #1a2a33',
  },
  warning: {
    background: '#b71c1c22', border: '1px solid #c62828',
    color: '#ef9a9a', borderRadius: 6, padding: '8px 10px', fontSize: 12,
  },
}
