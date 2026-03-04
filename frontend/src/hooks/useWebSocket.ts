import { useEffect, useRef, useCallback, useState } from 'react'
import { StudioWebSocket } from '@/api/websocket'
import type { WebSocketMessage } from '@/types'

export function useWebSocket(projectId: string | undefined) {
  const wsRef = useRef<StudioWebSocket | null>(null)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  useEffect(() => {
    if (!projectId) return
    const ws = new StudioWebSocket(projectId)
    wsRef.current = ws
    ws.connect()
    const unsub = ws.onMessage(setLastMessage)
    return () => {
      unsub()
      ws.disconnect()
      wsRef.current = null
    }
  }, [projectId])

  const onMessage = useCallback((handler: (msg: WebSocketMessage) => void) => {
    return wsRef.current?.onMessage(handler) ?? (() => {})
  }, [])

  return { lastMessage, onMessage }
}
