import { useEffect, useMemo, useState } from 'react'
import { computeBayLayout } from '../domain/bay/bay.service'
import Scene3D from '../presentation/components/Scene/Scene3D'
import CaseSidebar from '../presentation/ui/CaseSidebar'

const API = 'http://127.0.0.1:8000'

/** Independent 3D view for a single loaded case. */
export default function CaseView({ caseName }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)
  const [hoveredBay, setHoveredBay] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetch(`${API}/cases/${caseName}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d) => { if (!cancelled) { setData(d); setLoading(false) } })
      .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false) } })
    return () => { cancelled = true }
  }, [caseName])

  const layout = useMemo(() => {
    if (!data?.warehouse || !data?.bays?.length) return []
    return computeBayLayout(data.bays, data.warehouse, data.obstacles ?? [])
  }, [data])

  if (loading) return <div style={centeredStyle}>Loading {caseName}…</div>
  if (error)   return <div style={{ ...centeredStyle, color: '#ef9a9a' }}>Error: {error}</div>

  const collisionCount = layout.filter((l) => l.hasCollision).length

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <Scene3D
        warehouse={data.warehouse}
        layout={layout}
        obstacles={data.obstacles ?? []}
        onBayHover={setHoveredBay}
      />
      <CaseSidebar
        caseName={caseName}
        warehouse={data.warehouse}
        bayTypes={data.bay_types ?? []}
        obstacles={data.obstacles ?? []}
        hoveredBay={hoveredBay}
        collisionCount={collisionCount}
      />
    </div>
  )
}

const centeredStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: '100%', height: '100%',
  color: '#78909c', fontSize: 16, background: '#060c10',
}
