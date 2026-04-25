// Receives bay updates from the WebSocket and re-computes layout reactively

import { useEffect, useMemo, useState } from 'react'
import type { Bay, BayLayout } from '../domain/bay/bay.model'
import type { Warehouse } from '../domain/warehouse/warehouse.model'
import type { Obstacle } from '../domain/obstacle/obstacle.model'
import { computeBayLayout } from '../domain/bay/bay.service'
import { isTauri, subscribeBrowser } from '../infrastructure/socket'

interface BaysState {
  layout: BayLayout[]
  loading: boolean
}

export function useBays(warehouse: Warehouse | null, obstacles: Obstacle[]): BaysState {
  const [rawBays, setRawBays] = useState<Bay[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    function handle(payload: unknown) {
      setRawBays(payload as Bay[])
      setLoading(false)
    }

    if (isTauri) {
      let unlisten: (() => void) | undefined
      import('@tauri-apps/api/event').then(({ listen }) => {
        listen<Bay[]>('bays', (e) => handle(e.payload)).then((fn) => { unlisten = fn })
      })
      return () => { unlisten?.() }
    }

    return subscribeBrowser('bays', handle)
  }, [])

  const layout = useMemo<BayLayout[]>(() => {
    if (!warehouse || rawBays.length === 0) return []
    return computeBayLayout(rawBays, warehouse, obstacles)
  }, [rawBays, warehouse, obstacles])

  return { layout, loading: loading || !warehouse }
}
