// WebSocket com reconexão exponencial. O servidor reenvia o "snapshot" ao conectar.
export function connect({ onOpen, onClose, onMessage }) {
  const base = import.meta.env.VITE_WS_URL || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
  let ws, tries = 0, closed = false
  const open = () => {
    ws = new WebSocket(base)
    ws.onopen = () => { tries = 0; onOpen?.() }
    ws.onmessage = (e) => onMessage(JSON.parse(e.data))
    ws.onclose = () => {
      onClose?.()
      if (!closed) setTimeout(open, Math.min(500 * 2 ** tries++, 8000))
    }
  }
  open()
  return {
    send: (o) => ws?.readyState === 1 && ws.send(JSON.stringify(o)),
    close: () => { closed = true; ws?.close() },
  }
}
