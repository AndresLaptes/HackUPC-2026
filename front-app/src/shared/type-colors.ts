export type TypeColorMap = Record<number, string>

function vanDerCorput(index: number): number {
  let n = index
  let denom = 1
  let out = 0
  while (n > 0) {
    denom *= 2
    out += (n % 2) / denom
    n = Math.floor(n / 2)
  }
  return out
}

function normalizedTypeId(typeId: unknown): number | null {
  const n = Number(typeId)
  if (!Number.isFinite(n)) return null
  return Math.trunc(n)
}

/** Parse type id from labels like "T13-2" */
export function parseTypeIdFromLabel(label?: string): number | null {
  if (!label) return null
  const m = /^T(\d+)-/.exec(label)
  return m ? Number(m[1]) : null
}

/**
 * Build a highly distinguishable color map for the current case type IDs.
 * Colors are spread with Van der Corput sequence (base 2) + sat/light cycles.
 */
export function buildTypeColorMap(typeIds: Array<number | null | undefined>): TypeColorMap {
  const ids = [...new Set(typeIds
    .map(normalizedTypeId)
    .filter((v): v is number => v != null))].sort((a, b) => a - b)

  const satCycle = [82, 70, 90, 76]
  const lightCycle = [52, 44, 60, 48]

  const map: TypeColorMap = {}
  ids.forEach((id, idx) => {
    const hue = Math.round(vanDerCorput(idx + 1) * 359)
    const sat = satCycle[idx % satCycle.length]
    const light = lightCycle[Math.floor(idx / satCycle.length) % lightCycle.length]
    map[id] = `hsl(${hue}, ${sat}%, ${light}%)`
  })

  return map
}

export function getTypeColor(typeId: number | null | undefined, map?: TypeColorMap, fallback = '#90a4ae'): string {
  if (typeId == null || Number.isNaN(typeId)) return fallback
  return map?.[typeId] ?? fallback
}
