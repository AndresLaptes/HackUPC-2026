// Fetches obstacles from FastAPI via Tauri command (or direct fetch in browser dev mode)

import type { Obstacle } from '../domain/obstacle/obstacle.model'

const API_BASE = 'http://127.0.0.1:8000'
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

export async function getObstacles(): Promise<Obstacle[]> {
  if (isTauri) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke<Obstacle[]>('get_obstacles')
  }
  const res = await fetch(`${API_BASE}/obstacles`)
  return res.json() as Promise<Obstacle[]>
}
