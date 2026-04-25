// Controlled form for editing bay dimensions and load configuration

/** @param {{ values: import('../../domain/bay/bay.model').Bay, onChange: (patch: Partial<import('../../domain/bay/bay.model').Bay>) => void }} props */
export default function BayForm({ values, onChange }) {
  const field = (key, label, min = 1) => (
    <label style={styles.label}>
      <span style={styles.labelText}>{label}</span>
      <input
        type="number"
        min={min}
        value={values[key]}
        onChange={(e) => onChange({ [key]: Number(e.target.value) })}
        style={styles.input}
      />
    </label>
  )

  return (
    <div style={styles.form}>
      {field('width',  'Width (mm)')}
      {field('depth',  'Depth (mm)')}
      {field('height', 'Height (mm)')}
      {field('gap',    'Gap (mm)', 0)}
      {field('nLoads', 'Loads', 1)}
    </div>
  )
}

const styles = {
  form:      { display: 'flex', flexDirection: 'column', gap: 10 },
  label:     { display: 'flex', flexDirection: 'column', gap: 3 },
  labelText: { fontSize: 11, color: '#90a4ae', textTransform: 'uppercase', letterSpacing: '0.05em' },
  input: {
    background: '#1e2a2f', border: '1px solid #37474f', borderRadius: 4,
    color: '#eceff1', padding: '6px 8px', fontSize: 14, width: '100%',
  },
}
