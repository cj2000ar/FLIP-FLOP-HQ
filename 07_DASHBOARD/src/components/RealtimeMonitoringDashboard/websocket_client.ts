/**
 * WebSocket Client for Real-time Metrics Updates
 * Auto-reconnect, bitemporal data, machine_id + fencing_token auth
 */

export interface MetricsUpdate {
  type: 'heartbeat' | 'gates' | 'batch' | 'trades' | 'health' | 'error';
  timestamp: number;
  data?: Record<string, unknown>;
  error?: string;
}

export interface WebSocketClientConfig {
  url: string;
  machineId: string;
  fencingToken: string;
  reconnectAttempts: number;
  reconnectDelayMs: number;
  onUpdate: (update: MetricsUpdate) => void;
  onError: (error: string) => void;
  onStatusChange: (status: 'connected' | 'disconnected' | 'reconnecting') => void;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: WebSocketClientConfig;
  private reconnectCount: number = 0;
  private messageQueue: string[] = [];
  private isIntentionallyClosed: boolean = false;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  constructor(config: WebSocketClientConfig) {
    this.config = config;
  }

  /**
   * Connect to WebSocket server with auth headers
   */
  public connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.url);

        this.ws.onopen = () => {
          // Send auth credentials
          this.send({
            type: 'auth',
            machine_id: this.config.machineId,
            fencing_token: this.config.fencingToken,
            timestamp: Date.now(),
          });

          this.reconnectCount = 0;
          this.config.onStatusChange('connected');
          this.flushQueue();
          this.startHeartbeat();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const update: MetricsUpdate = JSON.parse(event.data);
            this.config.onUpdate(update);
          } catch (error) {
            this.config.onError(`Failed to parse message: ${error}`);
          }
        };

        this.ws.onerror = (event) => {
          this.config.onError(`WebSocket error: ${event}`);
          reject(event);
        };

        this.ws.onclose = () => {
          this.stopHeartbeat();
          if (!this.isIntentionallyClosed) {
            this.config.onStatusChange('disconnected');
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Send message to server
   */
  public send(data: Record<string, unknown>): void {
    const message = JSON.stringify(data);

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      this.messageQueue.push(message);
    }
  }

  /**
   * Subscribe to metrics updates
   */
  public subscribe(channel: string): void {
    this.send({
      type: 'subscribe',
      channel,
      timestamp: Date.now(),
    });
  }

  /**
   * Unsubscribe from metrics updates
   */
  public unsubscribe(channel: string): void {
    this.send({
      type: 'unsubscribe',
      channel,
      timestamp: Date.now(),
    });
  }

  /**
   * Disconnect from server
   */
  public disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectCount >= this.config.reconnectAttempts) {
      this.config.onError(
        `Failed to reconnect after ${this.config.reconnectAttempts} attempts`
      );
      return;
    }

    this.reconnectCount++;
    const delayMs = this.config.reconnectDelayMs * Math.pow(2, this.reconnectCount - 1);

    this.config.onStatusChange('reconnecting');

    setTimeout(() => {
      this.connect().catch((error) => {
        this.config.onError(`Reconnection attempt ${this.reconnectCount} failed: ${error}`);
        this.attemptReconnect();
      });
    }, delayMs);
  }

  /**
   * Flush queued messages after connection
   */
  private flushQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift();
      if (message) {
        this.ws.send(message);
      }
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      this.send({
        type: 'ping',
        timestamp: Date.now(),
      });
    }, 30000); // Every 30 seconds
  }

  /**
   * Stop heartbeat interval
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

/**
 * Hook for WebSocket client management
 */
export function useWebSocketClient(config: WebSocketClientConfig) {
  const clientRef = React.useRef<WebSocketClient | null>(null);

  React.useEffect(() => {
    clientRef.current = new WebSocketClient(config);
    clientRef.current.connect().catch((error) => {
      config.onError(`Failed to connect: ${error}`);
    });

    return () => {
      clientRef.current?.disconnect();
    };
  }, [config]);

  return clientRef.current;
}

// Import React for the hook
import React from 'react';
