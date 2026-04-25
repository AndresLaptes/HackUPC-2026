// Browser-mode WebSocket singleton — shared across all hooks to avoid duplicate connections

const WS_URL = 'ws://127.0.0.1:8000/ws'

type Listener = (payload: unknown) => void
const _listeners = new Map<string, Set<Listener>>()
let _ws: WebSocket | null = null

function ensureConnected() {
  if (_ws && _ws.readyState !== WebSocket.CLOSED) return

  _ws = new WebSocket(WS_URL)

  _ws.onmessage = ({ data }) => {
    try {
      const { type, payload } = JSON.parse(data as string) as { type: string; payload: unknown }
      _listeners.get(type)?.forEach((fn) => fn(payload))
    } catch { /* ignore malformed frames */ }
  }

  _ws.onclose = () => {
    _ws = null
    setTimeout(ensureConnected, 2000)
  }
}

/** Subscribe to a named message type. Returns an unlisten function. */
export function subscribeBrowser(type: string, fn: Listener): () => void {
  if (!_listeners.has(type)) _listeners.set(type, new Set())
  _listeners.get(type)!.add(fn)
  ensureConnected()
  return () => _listeners.get(type)?.delete(fn)
}

export const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
