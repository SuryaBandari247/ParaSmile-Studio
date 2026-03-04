import type { WebSocketMessage } from '@/types'

type MessageHandler = (msg: WebSocketMessage) => void

export class StudioWebSocket {
  private ws: WebSocket | null = null
  private projectId: string
  private handlers: Set<MessageHandler> = new Set()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private shouldReconnect = true

  constructor(projectId: string) {
    this.projectId = projectId
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/projects/${this.projectId}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.startPing()
    }

    this.ws.onmessage = (event) => {
      if (event.data === 'pong') return
      try {
        const msg = JSON.parse(event.data) as WebSocketMessage
        this.handlers.forEach(h => h(msg))
      } catch { /* ignore non-JSON */ }
    }

    this.ws.onclose = () => {
      this.stopPing()
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000)
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  disconnect(): void {
    this.shouldReconnect = false
    this.stopPing()
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  private startPing(): void {
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
      }
    }, 30000)
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }
}
