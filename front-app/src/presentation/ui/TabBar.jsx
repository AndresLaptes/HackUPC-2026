/**
 * @param {{ cases: {id: string, caseName: string}[],
 *           activeId: string | null,
 *           onSwitch: (id: string) => void,
 *           onClose: (id: string) => void,
 *           onAdd: () => void }} props
 */
export default function TabBar({ cases, activeId, onSwitch, onClose, onAdd }) {
  return (
    <div style={styles.bar}>
      {cases.map((c) => (
        <div
          key={c.id}
          style={{ ...styles.tab, ...(c.id === activeId ? styles.tabActive : {}) }}
          onClick={() => onSwitch(c.id)}
        >
          <span style={styles.label}>{c.caseName}</span>
          <button
            style={styles.closeBtn}
            onClick={(e) => { e.stopPropagation(); onClose(c.id) }}
            title="Close"
          >
            ×
          </button>
        </div>
      ))}
      <button style={styles.addBtn} onClick={onAdd} title="Load another case">
        + Load case
      </button>
    </div>
  )
}

const styles = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    height: 40,
    background: '#0a1014',
    borderBottom: '1px solid #1e2d35',
    padding: '0 8px',
    gap: 4,
    flexShrink: 0,
    overflowX: 'auto',
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '0 10px',
    height: 30,
    borderRadius: 6,
    background: '#132028',
    border: '1px solid #1e2d35',
    cursor: 'pointer',
    color: '#78909c',
    fontSize: 13,
    whiteSpace: 'nowrap',
    userSelect: 'none',
    transition: 'background 0.15s',
  },
  tabActive: {
    background: '#1b3040',
    border: '1px solid #2e6080',
    color: '#eceff1',
  },
  label: { pointerEvents: 'none' },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    color: 'inherit',
    cursor: 'pointer',
    fontSize: 16,
    lineHeight: 1,
    padding: 0,
    display: 'flex',
    alignItems: 'center',
    opacity: 0.6,
  },
  addBtn: {
    marginLeft: 4,
    padding: '0 12px',
    height: 30,
    borderRadius: 6,
    background: 'transparent',
    border: '1px solid #2e6080',
    color: '#4db6e6',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
}
