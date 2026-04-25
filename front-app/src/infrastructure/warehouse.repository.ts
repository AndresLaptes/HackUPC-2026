// Fetches warehouse from FastAPI via Tauri command (or direct fetch in browser dev mode)

import type { Warehouse } from '../domain/warehouse/warehouse.model'

const API_BASE = 'http://127.0.0.1:8000'
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

export async function getWarehouse(): Promise<Warehouse> {
  if (isTauri) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke<Warehouse>('get_warehouse')
  }
  const res = await fetch(`${API_BASE}/warehouse`)
  return res.json() as Promise<Warehouse>
}
