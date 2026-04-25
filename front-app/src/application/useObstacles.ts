// Receives obstacle updates from the WebSocket (via Tauri event or browser WS)

import { useEffect, useState } from 'react'
import type { Obstacle } from '../domain/obstacle/obstacle.model'
import { isTauri, subscribeBrowser } from '../infrastructure/socket'

interface ObstaclesState {
  obstacles: Obstacle[]
  loading: boolean
}

export function useObstacles(): ObstaclesState {
  const [state, setState] = useState<ObstaclesState>({ obstacles: [], loading: true })

  useEffect(() => {
    function handle(payload: unknown) {
      setState({ obstacles: payload as Obstacle[], loading: false })
    }

    if (isTauri) {
      let unlisten: (() => void) | undefined
      import('@tauri-apps/api/event').then(({ listen }) => {
        listen<Obstacle[]>('obstacles', (e) => handle(e.payload)).then((fn) => { unlisten = fn })
      })
      return () => { unlisten?.() }
    }

    return subscribeBrowser('obstacles', handle)
  }, [])

  return state
}
