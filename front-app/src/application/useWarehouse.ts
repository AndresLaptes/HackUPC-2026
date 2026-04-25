// Receives warehouse updates from the WebSocket (via Tauri event or browser WS)

import { useEffect, useState } from 'react'
import type { Warehouse } from '../domain/warehouse/warehouse.model'
import { validateWarehouse } from '../domain/warehouse/warehouse.service'
import { isTauri, subscribeBrowser } from '../infrastructure/socket'

interface WarehouseState {
  warehouse: Warehouse | null
  errors: string[]
  loading: boolean
}

export function useWarehouse(): WarehouseState {
  const [state, setState] = useState<WarehouseState>({ warehouse: null, errors: [], loading: true })

  useEffect(() => {
    function handle(payload: unknown) {
      const w = payload as Warehouse
      const errors = validateWarehouse(w)
      setState({ warehouse: errors.length ? null : w, errors, loading: false })
    }

    if (isTauri) {
      let unlisten: (() => void) | undefined
      import('@tauri-apps/api/event').then(({ listen }) => {
        listen<Warehouse>('warehouse', (e) => handle(e.payload)).then((fn) => { unlisten = fn })
      })
      return () => { unlisten?.() }
    }

    return subscribeBrowser('warehouse', handle)
  }, [])

  return state
}
