import type { CandlestickData, HistogramData, LineData, UTCTimestamp } from "lightweight-charts";

export type MarketBar = {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
  symbol?: string;
  timeframe?: string;
  synthetic?: boolean;
};

export type ChartBar = {
  candle: CandlestickData<UTCTimestamp>;
  volume: HistogramData<UTCTimestamp>;
};

export type ChartRange = "1H" | "4H" | "1D" | "ALL";

const NEW_YORK_CLOCK = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

export function newYorkSession(time: number): "OVERNIGHT" | "PRE" | "RTH" {
  const parts = NEW_YORK_CLOCK.formatToParts(new Date(time * 1000));
  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? 0);
  const clock = hour * 60 + minute;
  if (clock >= 570 && clock < 960) return "RTH";
  if (clock >= 240 && clock < 570) return "PRE";
  return "OVERNIGHT";
}

export function sessionShadeData(bars: readonly ChartBar[]): HistogramData<UTCTimestamp>[] {
  const colors = {
    OVERNIGHT: "rgba(137, 148, 158, 0.012)",
    PRE: "rgba(216, 174, 76, 0.018)",
    RTH: "rgba(226, 233, 238, 0.038)",
  } as const;
  return bars.map((bar) => ({
    time: bar.candle.time,
    value: 1,
    color: colors[newYorkSession(Number(bar.candle.time))],
  }));
}

export function rangeSeconds(range: ChartRange): number | null {
  if (range === "1H") return 60 * 60;
  if (range === "4H") return 4 * 60 * 60;
  if (range === "1D") return 24 * 60 * 60;
  return null;
}

function utcTimestamp(value: string | number): UTCTimestamp | null {
  const raw = typeof value === "number" ? value : Date.parse(value);
  if (!Number.isFinite(raw)) return null;
  const seconds = typeof value === "number" && Math.abs(value) < 100_000_000_000
    ? Math.trunc(value)
    : Math.trunc(raw / 1000);
  return seconds > 0 ? seconds as UTCTimestamp : null;
}

export function normalizeMarketBars(input: readonly MarketBar[]): ChartBar[] {
  const byTime = new Map<UTCTimestamp, ChartBar>();

  for (const bar of input) {
    if (!bar || bar.synthetic === true) continue;
    const time = utcTimestamp(bar.time);
    const values = [bar.open, bar.high, bar.low, bar.close].map(Number);
    if (time === null || values.some((value) => !Number.isFinite(value))) continue;
    const [open, high, low, close] = values as [number, number, number, number];
    if (high < Math.max(open, close) || low > Math.min(open, close) || low > high) continue;
    const volume = Number(bar.volume ?? 0);
    byTime.set(time, {
      candle: { time, open, high, low, close },
      volume: {
        time,
        value: Number.isFinite(volume) && volume >= 0 ? volume : 0,
        color: close >= open ? "rgba(31, 167, 95, 0.28)" : "rgba(185, 55, 58, 0.28)",
      },
    });
  }

  return [...byTime.values()].sort((a, b) => Number(a.candle.time) - Number(b.candle.time));
}

export function simpleMovingAverage(bars: readonly ChartBar[], period: number): LineData<UTCTimestamp>[] {
  if (!Number.isInteger(period) || period < 2) return [];
  const points: LineData<UTCTimestamp>[] = [];
  let sum = 0;
  for (let i = 0; i < bars.length; i += 1) {
    const current = bars[i];
    if (!current) continue;
    sum += current.candle.close;
    if (i >= period) {
      const expired = bars[i - period];
      if (expired) sum -= expired.candle.close;
    }
    if (i >= period - 1) points.push({ time: current.candle.time, value: sum / period });
  }
  return points;
}
