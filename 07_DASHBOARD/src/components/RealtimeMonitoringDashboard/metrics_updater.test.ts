/**
 * Metrics Updater Unit Tests
 */

import { calculateTradeMetrics, TradeRecord } from './metrics_updater';

describe('Metrics Updater', () => {
  describe('calculateTradeMetrics', () => {
    it('should return default metrics for empty trades', () => {
      const result = calculateTradeMetrics([]);

      expect(result.winRate).toBe(0);
      expect(result.profitFactor).toBe(1);
      expect(result.maxDrawdown).toBe(0);
      expect(result.avgLatency).toBe(0);
    });

    it('should calculate win rate correctly', () => {
      const trades: TradeRecord[] = [
        {
          id: '1',
          strategyId: 's1',
          entryTime: 0,
          entryPrice: 100,
          quantity: 1,
          pnl: 100,
          latencyMs: 50,
          type: 'LONG',
        },
        {
          id: '2',
          strategyId: 's1',
          entryTime: 1000,
          entryPrice: 100,
          quantity: 1,
          pnl: -50,
          latencyMs: 50,
          type: 'LONG',
        },
      ];

      const result = calculateTradeMetrics(trades);
      expect(result.winRate).toBe(50);
    });

    it('should calculate profit factor correctly', () => {
      const trades: TradeRecord[] = [
        {
          id: '1',
          strategyId: 's1',
          entryTime: 0,
          entryPrice: 100,
          quantity: 1,
          pnl: 200,
          latencyMs: 50,
          type: 'LONG',
        },
        {
          id: '2',
          strategyId: 's1',
          entryTime: 1000,
          entryPrice: 100,
          quantity: 1,
          pnl: -100,
          latencyMs: 50,
          type: 'LONG',
        },
      ];

      const result = calculateTradeMetrics(trades);
      expect(result.profitFactor).toBe(2);
    });

    it('should calculate max drawdown correctly', () => {
      const trades: TradeRecord[] = [
        {
          id: '1',
          strategyId: 's1',
          entryTime: 0,
          entryPrice: 100,
          quantity: 1,
          pnl: 100,
          latencyMs: 50,
          type: 'LONG',
        },
        {
          id: '2',
          strategyId: 's1',
          entryTime: 1000,
          entryPrice: 100,
          quantity: 1,
          pnl: -150,
          latencyMs: 50,
          type: 'LONG',
        },
      ];

      const result = calculateTradeMetrics(trades);
      expect(result.maxDrawdown).toBe(150);
    });

    it('should calculate average latency correctly', () => {
      const trades: TradeRecord[] = [
        {
          id: '1',
          strategyId: 's1',
          entryTime: 0,
          entryPrice: 100,
          quantity: 1,
          pnl: 100,
          latencyMs: 100,
          type: 'LONG',
        },
        {
          id: '2',
          strategyId: 's1',
          entryTime: 1000,
          entryPrice: 100,
          quantity: 1,
          pnl: 50,
          latencyMs: 200,
          type: 'LONG',
        },
      ];

      const result = calculateTradeMetrics(trades);
      expect(result.avgLatency).toBe(150);
    });

    it('should handle all winning trades', () => {
      const trades: TradeRecord[] = [
        {
          id: '1',
          strategyId: 's1',
          entryTime: 0,
          entryPrice: 100,
          quantity: 1,
          pnl: 100,
          latencyMs: 50,
          type: 'LONG',
        },
        {
          id: '2',
          strategyId: 's1',
          entryTime: 1000,
          entryPrice: 100,
          quantity: 1,
          pnl: 50,
          latencyMs: 50,
          type: 'LONG',
        },
      ];

      const result = calculateTradeMetrics(trades);
      expect(result.winRate).toBe(100);
      expect(result.profitFactor).toBe(Infinity);
      expect(result.maxDrawdown).toBe(0);
    });

    it('should handle all losing trades', () => {
      const trades: TradeRecord[] = [
        {
          id: '1',
          strategyId: 's1',
          entryTime: 0,
          entryPrice: 100,
          quantity: 1,
          pnl: -100,
          latencyMs: 50,
          type: 'LONG',
        },
        {
          id: '2',
          strategyId: 's1',
          entryTime: 1000,
          entryPrice: 100,
          quantity: 1,
          pnl: -50,
          latencyMs: 50,
          type: 'LONG',
        },
      ];

      const result = calculateTradeMetrics(trades);
      expect(result.winRate).toBe(0);
      expect(result.profitFactor).toBe(1);
    });

    it('should handle single trade', () => {
      const trades: TradeRecord[] = [
        {
          id: '1',
          strategyId: 's1',
          entryTime: 0,
          entryPrice: 100,
          quantity: 1,
          pnl: 100,
          latencyMs: 50,
          type: 'LONG',
        },
      ];

      const result = calculateTradeMetrics(trades);
      expect(result.winRate).toBe(100);
      expect(result.profitFactor).toBe(Infinity);
      expect(result.maxDrawdown).toBe(0);
      expect(result.avgLatency).toBe(50);
    });
  });
});
