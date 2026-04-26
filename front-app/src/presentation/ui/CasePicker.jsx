import { useEffect, useState } from 'react'

const API = 'http://127.0.0.1:8000'

/**
 * @param {{ onSelect: (caseName: string) => void,
 *           canClose: boolean,
 *           onClose: () => void }} props
 */
export default function CasePicker({ onSelect, canClose, onClose }) {
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let cancelled = false
    let timer

    function tryFetch() {
      fetch(`${API}/cases`)
        .then((r) => r.json())
        .then((data) => {
          if (cancelled) return
          setCases(data)
          setLoading(false)
          setErr(null)
        })
        .catch((e) => {
          if (cancelled) return
          setErr(e.message)
          setLoading(false)
          timer = setTimeout(tryFetch, 4000)
        })
    }

    tryFetch()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [])

  return (
    <div style={styles.overlay}>
      {canClose && (
        <button style={styles.closeBtn} onClick={onClose} title="Back to view">×</button>
      )}

      <div style={styles.card}>
        <div style={styles.icon}>🏭</div>
        <h1 style={styles.title}>Warehouse Viewer</h1>
        <p style={styles.subtitle}>Select a test case to visualise in 3D</p>

        {loading && <p style={styles.hint}>Connecting to backend…</p>}
        {err    && <p style={styles.hint}>Starting backend, please wait…</p>}

        {!loading && !err && (
          <div style={styles.grid}>
            {cases.map((name) => (
              <button key={name} style={styles.caseBtn} onClick={() => onSelect(name)}>
                <span style={styles.caseName}>{name}</span>
                <span style={styles.caseArrow}>→</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const styles = {
  overlay: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'radial-gradient(ellipse at 50% 40%, #0d1e2a 0%, #060c10 100%)',
  },
  closeBtn: {
    position: 'absolute',
    top: 16,
    right: 16,
    background: 'transparent',
    border: '1px solid #37474f',
    borderRadius: 6,
    color: '#78909c',
    fontSize: 20,
    width: 32,
    height: 32,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 20,
    padding: '48px 56px',
    background: 'rgba(13, 30, 42, 0.9)',
    border: '1px solid #1e3a4a',
    borderRadius: 16,
    backdropFilter: 'blur(20px)',
    boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
    minWidth: 360,
  },
  icon:     { fontSize: 48, lineHeight: 1 },
  title:    { margin: 0, fontSize: 22, fontWeight: 700, color: '#eceff1' },
  subtitle: { margin: 0, fontSize: 14, color: '#546e7a' },
  hint:     { margin: 0, fontSize: 13, color: '#78909c' },
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    width: '100%',
    marginTop: 8,
  },
  caseBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 18px',
    background: '#0f2230',
    border: '1px solid #1e3a4a',
    borderRadius: 10,
    color: '#b0bec5',
    fontSize: 15,
    cursor: 'pointer',
    transition: 'background 0.15s, border-color 0.15s',
  },
  caseName: { fontWeight: 600, color: '#eceff1' },
  caseArrow: { color: '#4db6e6', fontSize: 18 },
}
