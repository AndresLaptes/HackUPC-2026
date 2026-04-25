// Fetches bays from FastAPI via Tauri command (or direct fetch in browser dev mode)

import type { Bay } from '../domain/bay/bay.model'

const API_BASE = 'http://127.0.0.1:8000'
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

export async function getBays(): Promise<Bay[]> {
  if (isTauri) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke<Bay[]>('get_bays')
  }
  const res = await fetch(`${API_BASE}/bays`)
  return res.json() as Promise<Bay[]>
}
