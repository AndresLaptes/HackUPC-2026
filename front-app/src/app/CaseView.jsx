import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { computeBayLayout } from '../domain/bay/bay.service'
import { buildTypeColorMap, parseTypeIdFromLabel } from '../shared/type-colors'
import Scene3D from '../presentation/components/Scene/Scene3D'
import CaseSidebar from '../presentation/ui/CaseSidebar'
import AxisGizmoOverlay from '../presentation/components/Scene/AxisGizmo'

const API = 'http://127.0.0.1:8000'

export default function CaseView({ caseId, caseName, solveToken = 0, solveForCaseId = null, onSolveDone }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [solveMsg, setSolveMsg] = useState(null)
  const [solveErr, setSolveErr] = useState(null)
  const [solveElapsedSeconds, setSolveElapsedSeconds] = useState(null)
  const [dropDurationMs, setDropDurationMs] = useState(0)
  const [dropStartAt, setDropStartAt] = useState(0)
  const [dropProgress, setDropProgress] = useState(1)
  const [hoveredBay, setHoveredBay] = useState(null)
  const [hoveredObstacle, setHoveredObstacle] = useState(null)

  const bridgeRef     = useRef(null)
  const gizmoDomRef   = useRef(null)
  const gizmoStateRef = useRef([])

  const loadCaseData = useCallback(async (includeOutput = false) => {
    setLoading(true)
    setError(null)
    setHoveredBay(null)
    setHoveredObstacle(null)
    try {
      const res = await fetch(`${API}/cases/${caseName}?include_output=${includeOutput ? '1' : '0'}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const d = await res.json()
      setData(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [caseName])

  useEffect(() => {
    setSolveMsg(null)
    setSolveErr(null)
    setSolveElapsedSeconds(null)
    setDropDurationMs(0)
    setDropStartAt(0)
    setDropProgress(1)
    loadCaseData(false)
  }, [loadCaseData])

  useEffect(() => {
    if (dropDurationMs <= 0 || dropStartAt <= 0) return

    let raf = 0
    const tick = () => {
      const elapsed = performance.now() - dropStartAt
      const p = Math.max(0, Math.min(1, elapsed / dropDurationMs))
      setDropProgress(p)
      if (p < 1) raf = requestAnimationFrame(tick)
    }

    setDropProgress(0)
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [dropDurationMs, dropStartAt])

  async function runSolver() {
    setSolveErr(null)
    setSolveMsg(null)

    try {
      const res = await fetch(`${API}/cases/${caseName}/solve`, { method: 'POST' })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(body?.detail || `HTTP ${res.status}`)
      }

      const resFetch = await fetch(`${API}/cases/${caseName}?include_output=1`)
      if (!resFetch.ok) throw new Error(`HTTP ${resFetch.status}`)
      const newData = await resFetch.json()
      
      setData((prevData) => ({
        ...prevData,
        bays: newData.bays,
      }))
      const baysCount = body?.result?.baysCount
      const seconds = body?.result?.elapsedSeconds
      if (typeof seconds === 'number' && Number.isFinite(seconds)) {
        const clampedMs = Math.max(700, Math.min(16000, seconds * 700))
        setSolveElapsedSeconds(seconds)
        setDropDurationMs(clampedMs)
        setDropStartAt(performance.now())
      } else {
        setSolveElapsedSeconds(null)
        setDropDurationMs(0)
        setDropStartAt(0)
        setDropProgress(1)
      }
      setSolveMsg(
        `Hecho: ${baysCount ?? 0} bays en ${typeof seconds === 'number' ? seconds.toFixed(2) : '-'}s`,
      )
    } catch (e) {
      setSolveErr(e.message || 'Error ejecutando el algoritmo')
    } finally {
      onSolveDone?.(caseId)
    }
  }

  useEffect(() => {
    if (solveToken <= 0) return
    if (!caseId || solveForCaseId !== caseId) return
    runSolver()
  }, [solveToken, solveForCaseId, caseId])

  const layout = useMemo(() => {
    if (!data?.warehouse || !data?.bays?.length) return []
    return computeBayLayout(data.bays, data.warehouse, data.obstacles ?? [])
  }, [data])

  const typeColorMap = useMemo(() => {
    const fromBayTypes = (data?.bay_types ?? []).map((t) => t.id)
    const fromLayout = layout.map(({ bay }) => bay.bayTypeId ?? parseTypeIdFromLabel(bay.label))
    return buildTypeColorMap([...fromBayTypes, ...fromLayout])
  }, [data, layout])

  if (loading) return <div style={centeredStyle}>Loading {caseName}…</div>
  if (error)   return <div style={{ ...centeredStyle, color: '#ef9a9a' }}>Error: {error}</div>

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div style={styles.solveStatusWrap}>
        {solveMsg && <div style={styles.solveOk}>{solveMsg}</div>}
        {solveErr && <div style={styles.solveFail}>{solveErr}</div>}
      </div>

      <Scene3D
        warehouse={data.warehouse}
        layout={layout}
        obstacles={data.obstacles ?? []}
        typeColorMap={typeColorMap}
        dropProgress={dropProgress}
        onBayHover={setHoveredBay}
        onObstacleHover={setHoveredObstacle}
        bridgeRef={bridgeRef}
        gizmoDomRef={gizmoDomRef}
        gizmoStateRef={gizmoStateRef}
      />
      <AxisGizmoOverlay
        domRef={gizmoDomRef}
        stateRef={gizmoStateRef}
        bridgeRef={bridgeRef}
      />
      <CaseSidebar
        caseName={caseName}
        warehouse={data.warehouse}
        bayTypes={data.bay_types ?? []}
        obstacles={data.obstacles ?? []}
        layout={layout}
        typeColorMap={typeColorMap}
        solveElapsedSeconds={solveElapsedSeconds}
        dropProgress={dropProgress}
        hoveredBay={hoveredBay}
        hoveredObstacle={hoveredObstacle}
      />
    </div>
  )
}

const centeredStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: '100%', height: '100%',
  color: '#78909c', fontSize: 16, background: '#060c10',
}

const styles = {
  solveStatusWrap: {
    position: 'absolute',
    top: 10,
    left: 50,
    zIndex: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    pointerEvents: 'none',
  },
  solveOk: {
    color: '#9be7a7',
    fontSize: 12,
    textShadow: '0 0 6px rgba(0,0,0,0.6)',
  },
  solveFail: {
    color: '#ef9a9a',
    fontSize: 12,
    maxWidth: 320,
    textShadow: '0 0 6px rgba(0,0,0,0.6)',
  },
}
