// Shows details about the currently hovered bay

/** @param {{ bay: import('../../domain/bay/bay.model').Bay | null }} props */
export default function InfoPanel({ bay }) {
  if (!bay) {
    return <p style={styles.empty}>Hover a bay to inspect it</p>
  }
  const rows = [
    ['Label', bay.label],
    ['Position', `(${bay.x}, ${bay.y}) mm`],
    ['Size', `${bay.width} × ${bay.depth} × ${bay.height} mm`],
    ['Loads', bay.nLoads],
    ['Gap', `${bay.gap} mm`],
  ]
  return (
    <table style={styles.table}>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}>
            <td style={styles.key}>{k}</td>
            <td style={styles.val}>{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const styles = {
  empty: { color: '#546e7a', fontSize: 13, fontStyle: 'italic' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  key:   { color: '#90a4ae', paddingRight: 8, paddingBottom: 4, whiteSpace: 'nowrap' },
  val:   { color: '#eceff1', paddingBottom: 4 },
}
