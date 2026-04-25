// 2D sidebar panel — floating overlay on top of the 3D canvas

import { useState } from 'react'
import BayForm from './BayForm'
import InfoPanel from './InfoPanel'

/**
 * @param {{ bayDefaults: import('../../domain/bay/bay.model').Bay,
 *           onBayChange: (patch: Partial<import('../../domain/bay/bay.model').Bay>) => void,
 *           hoveredBay: import('../../domain/bay/bay.model').Bay | null,
 *           collisionCount: number }} props
 */
export default function Sidebar({ bayDefaults, onBayChange, hoveredBay, collisionCount }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside style={{ ...styles.aside, width: collapsed ? 40 : 272 }}>
      <button style={styles.collapseBtn} onClick={() => setCollapsed((c) => !c)} title={collapsed ? 'Expand' : 'Collapse'}>
        {collapsed ? '›' : '‹'}
      </button>

      {!collapsed && (
        <>
          <h1 style={styles.title}>Warehouse 3D</h1>

          <section style={styles.section}>
            <h2 style={styles.heading}>Bay Configuration</h2>
            <BayForm values={bayDefaults} onChange={onBayChange} />
          </section>

          <section style={styles.section}>
            <h2 style={styles.heading}>Selected Bay</h2>
            <InfoPanel bay={hoveredBay} />
          </section>

          {collisionCount > 0 && (
            <div style={styles.warning}>
              ⚠ {collisionCount} bay{collisionCount > 1 ? 's' : ''} with collision
            </div>
          )}
        </>
      )}
    </aside>
  )
}

const styles = {
  aside: {
    position: 'absolute', top: 12, left: 12, bottom: 12,
    zIndex: 10,
    background: 'rgba(10, 20, 24, 0.88)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 12,
    padding: '48px 16px 20px',
    display: 'flex', flexDirection: 'column', gap: 24,
    overflowY: 'auto',
    transition: 'width 0.2s ease',
    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
  },
  collapseBtn: {
    position: 'absolute', top: 10, right: 10,
    background: 'transparent', border: '1px solid #37474f',
    borderRadius: 6, color: '#90a4ae', fontSize: 18, lineHeight: 1,
    width: 24, height: 24, cursor: 'pointer', display: 'flex',
    alignItems: 'center', justifyContent: 'center', padding: 0,
  },
  title:   { fontSize: 16, fontWeight: 700, color: '#eceff1', margin: 0 },
  heading: { fontSize: 11, fontWeight: 600, color: '#546e7a', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 10px' },
  section: { display: 'flex', flexDirection: 'column' },
  warning: {
    background: '#b71c1c22', border: '1px solid #c62828',
    color: '#ef9a9a', borderRadius: 6, padding: '8px 10px', fontSize: 13,
  },
}
