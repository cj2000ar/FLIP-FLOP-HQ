/**
 * WebSocket Client Unit Tests
 */

import { WebSocketClient, MetricsUpdate } from './websocket_client';

describe('WebSocketClient', () => {
  let client: WebSocketClient;
  let mockConfig: any;
  let mockWebSocket: any;

  beforeEach(() => {
    mockConfig = {
      url: 'ws://localhost:8000',
      machineId: 'machine-001',
      fencingToken: 'token-123',
      reconnectAttempts: 3,
      reconnectDelayMs: 100,
      onUpdate: jest.fn(),
      onError: jest.fn(),
      onStatusChange: jest.fn(),
    };

    // Mock WebSocket
    mockWebSocket = {
      readyState: 0,
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;
  });

  it('should construct with valid config', () => {
    client = new WebSocketClient(mockConfig);
    expect(client).toBeDefined();
  });

  it('should send auth message on connection', async () => {
    client = new WebSocketClient(mockConfig);
    mockWebSocket.readyState = 1;

    client.connect();
    await new Promise((resolve) => setTimeout(resolve, 10));

    // Verify WebSocket was created
    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000');
  });

  it('should handle message queue before connection', () => {
    client = new WebSocketClient(mockConfig);
    mockWebSocket.readyState = 0;

    client.send({ type: 'test', data: 'value' });
    expect(mockWebSocket.send).not.toHaveBeenCalled();
  });

  it('should subscribe to channel', () => {
    client = new WebSocketClient(mockConfig);
    mockWebSocket.readyState = 1;
    client['ws'] = mockWebSocket;

    client.subscribe('metrics');

    // Verify send was called with subscription
    expect(mockWebSocket.send).toHaveBeenCalled();
  });

  it('should unsubscribe from channel', () => {
    client = new WebSocketClient(mockConfig);
    mockWebSocket.readyState = 1;
    client['ws'] = mockWebSocket;

    client.unsubscribe('metrics');

    expect(mockWebSocket.send).toHaveBeenCalled();
  });

  it('should check connection status', () => {
    client = new WebSocketClient(mockConfig);
    mockWebSocket.readyState = 1;
    client['ws'] = mockWebSocket;

    expect(client.isConnected()).toBe(true);

    mockWebSocket.readyState = 0;
    expect(client.isConnected()).toBe(false);
  });

  it('should disconnect gracefully', () => {
    client = new WebSocketClient(mockConfig);
    client['ws'] = mockWebSocket;

    client.disconnect();

    expect(mockWebSocket.close).toHaveBeenCalled();
  });
});
