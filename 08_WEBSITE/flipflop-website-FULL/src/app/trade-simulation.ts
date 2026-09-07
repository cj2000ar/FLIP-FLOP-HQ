export const demoMarkets = [
  { symbol: 'NQ', group: 'Futuros', base: 20000, step: 0.25, digits: 2 },
  { symbol: 'MNQ', group: 'Futuros', base: 20000, step: 0.25, digits: 2 },
  { symbol: 'ES', group: 'Futuros', base: 5500, step: 0.25, digits: 2 },
  { symbol: 'CL', group: 'Futuros', base: 75, step: 0.01, digits: 2 },
  { symbol: 'GC', group: 'Oro · futuros', base: 2500, step: 0.1, digits: 1 },
  { symbol: 'EUR/USD', group: 'Forex', base: 1.085, step: 0.0001, digits: 5 },
  { symbol: 'GBP/USD', group: 'Forex', base: 1.275, step: 0.0001, digits: 5 },
  { symbol: 'USD/JPY', group: 'Forex', base: 145, step: 0.01, digits: 3 },
  { symbol: 'XAU/USD', group: 'Oro · spot', base: 2500, step: 0.1, digits: 2 },
] as const;
export type DemoMarket = (typeof demoMarkets)[number];
export type Direction = 'long' | 'short';
export type Outcome = 'tp' | 'sl';

/** A visual-only loop with a readable close, then a quiet fade into the next example. */
export function automaticTradeAt(seconds: number) {
  const time = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const cycle = Math.floor(time / 26);
  const phase = time % 26;
  const scenarios: { direction: Direction; outcome: Outcome }[] = [
    { direction: 'long', outcome: 'tp' },
    { direction: 'short', outcome: 'sl' },
    { direction: 'short', outcome: 'tp' },
    { direction: 'long', outcome: 'sl' },
  ];
  const fade = Math.min(1, phase / 1.2, (26 - phase) / 2);
  return {
    ...scenarios[cycle % scenarios.length],
    cycle,
    progress: Math.min(1, phase / 22),
    opacity: fade * fade * (3 - 2 * fade),
  };
}
export type Candle = {
  open: number;
  high: number;
  low: number;
  close: number;
  index: number;
};
const historyCount = 30;
const replayCount = 30;
const limit = (n: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, n));

/** Deliberately scripted, synthetic prices. No feed, broker, fills, fees or strategy engine. */
export function replayTrade(
  market: DemoMarket,
  direction: Direction,
  outcome: Outcome,
  progress: number,
) {
  const p = limit(Number.isFinite(progress) ? progress : 0, 0, 1);
  const sign = direction === 'long' ? 1 : -1;
  const entry = market.base,
    stop = entry - sign * market.step * 12,
    target = entry + sign * market.step * 24;
  const candles: Candle[] = [];
  const history = (i: number) =>
    market.base +
    market.step *
      (Math.sin(i * 0.61) * 5 + Math.sin(i * 1.83) * 2) *
      (1 - i / historyCount);
  for (let i = 0; i < historyCount; i++) {
    const open = history(i),
      close = history(i + 1);
    candles.push({
      open,
      close,
      high: Math.max(open, close) + market.step * (1 + Math.abs(Math.sin(i))),
      low: Math.min(open, close) - market.step * (1 + Math.abs(Math.cos(i))),
      index: i,
    });
  }
  const points =
    outcome === 'tp'
      ? [0, 4, 1, 9, 5, 15, 11, 21, 24]
      : [0, 5, 2, -3, 1, -7, -5, -10, -12];
  const at = (position: number) => {
    const v = limit(position, 0, 1) * (points.length - 1),
      i = Math.min(Math.floor(v), points.length - 2),
      f = v - i;
    return (
      entry + sign * market.step * (points[i] + (points[i + 1] - points[i]) * f)
    );
  };
  const completed = Math.floor(p * replayCount);
  const total = Math.min(replayCount, completed + (p < 1 ? 1 : 0));
  for (let i = 0; i < total; i++) {
    const start = i / replayCount,
      end = Math.min((i + 1) / replayCount, p);
    const open = at(start),
      close = at(end),
      span = limit((end - start) * replayCount, 0, 1);
    const padding = market.step * 0.6 * span;
    const ceiling = Math.max(stop, target) - market.step * 0.1;
    const floor = Math.min(stop, target) + market.step * 0.1;
    candles.push({
      open,
      close,
      high: Math.max(
        open,
        close,
        Math.min(ceiling, Math.max(open, close) + padding),
      ),
      low: Math.min(
        open,
        close,
        Math.max(floor, Math.min(open, close) - padding),
      ),
      index: historyCount + i,
    });
  }
  return {
    candles,
    entry,
    stop,
    target,
    current: at(p),
    progress: p,
    closed: p === 1,
    outcome,
    direction,
    delta: (at(p) - entry) * sign,
    riskUnits: ((at(p) - entry) * sign) / (market.step * 12),
    historyCount,
    replayCount,
  };
}
export type ReplayFrame = ReturnType<typeof replayTrade>;

export function drawTradeChart(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  frame: ReplayFrame,
  market: DemoMarket,
  labels: { entry: string },
) {
  ctx.clearRect(0, 0, width, height);
  const left = 12,
    right = width < 500 ? 78 : 94,
    top = 28,
    bottom = 34;
  const w = Math.max(1, width - left - right),
    h = Math.max(1, height - top - bottom);
  const low = Math.min(frame.stop, frame.target) - market.step * 6,
    high = Math.max(frame.stop, frame.target) + market.step * 6;
  const y = (price: number) => top + ((high - price) / (high - low)) * h;
  // Keep fewer history bars on phones so candle bodies remain readable.
  const firstIndex = width < 500 ? Math.max(0, frame.historyCount - 12) : 0;
  const pitch = w / (frame.historyCount + frame.replayCount + 1 - firstIndex);
  const x = (index: number) => left + (index - firstIndex + 0.5) * pitch;
  const entryX = x(frame.historyCount);
  ctx.font = '10px ui-monospace, SFMono-Regular, Consolas, monospace';
  ctx.textBaseline = 'middle';
  for (let i = 0; i <= 6; i++) {
    const price = low + ((high - low) * i) / 6,
      py = y(price);
    ctx.strokeStyle = '#ffffff0d';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(left, py);
    ctx.lineTo(left + w, py);
    ctx.stroke();
    ctx.fillStyle = '#929292';
    ctx.fillText(price.toFixed(market.digits), left + w + 9, py);
  }
  const zone = (price: number, color: string) => {
    ctx.fillStyle = color;
    ctx.fillRect(
      entryX,
      Math.min(y(price), y(frame.entry)),
      left + w - entryX,
      Math.abs(y(price) - y(frame.entry)),
    );
  };
  zone(frame.target, '#2a7d3c0c');
  zone(frame.stop, '#dd281c09');
  const level = (price: number, text: string, color: string) => {
    ctx.setLineDash([4, 5]);
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(entryX, y(price));
    ctx.lineTo(left + w, y(price));
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#090909';
    ctx.fillRect(entryX + 4, y(price) - 17, Math.min(w * 0.42, 110), 14);
    ctx.fillStyle = color;
    ctx.fillText(text, entryX + 8, y(price) - 10);
  };
  level(frame.target, 'TP', '#62b676');
  level(frame.entry, labels.entry, '#c7c7c7');
  level(frame.stop, 'SL', '#f14234');
  for (const c of frame.candles) {
    if (c.index < firstIndex) continue;
    const color = c.close >= c.open ? '#62b676' : '#f14234';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x(c.index), y(c.high));
    ctx.lineTo(x(c.index), y(c.low));
    ctx.stroke();
    const cw = Math.max(2, pitch * 0.58);
    ctx.fillStyle = color;
    ctx.fillRect(
      x(c.index) - cw / 2,
      Math.min(y(c.open), y(c.close)),
      cw,
      Math.max(1.4, Math.abs(y(c.close) - y(c.open))),
    );
  }
  ctx.setLineDash([2, 5]);
  ctx.strokeStyle = '#ffffff44';
  ctx.beginPath();
  ctx.moveTo(left, y(frame.current));
  ctx.lineTo(left + w, y(frame.current));
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = '#e4e4e4';
  ctx.fillRect(left + w + 3, y(frame.current) - 9, right - 6, 18);
  ctx.fillStyle = '#101010';
  ctx.fillText(
    frame.current.toFixed(market.digits),
    left + w + 8,
    y(frame.current),
  );
  ctx.fillStyle = '#808080';
  const timeLabels = width < 500 ? 3 : 6;
  for (let i = 0; i < timeLabels; i++) {
    const index =
      firstIndex + Math.round((i * (55 - firstIndex)) / (timeLabels - 1));
    ctx.fillText(
      `${String(9 + Math.floor((30 + index) / 60)).padStart(2, '0')}:${String((30 + index) % 60).padStart(2, '0')}`,
      x(index),
      height - 13,
    );
  }
  ctx.fillStyle = '#ededed';
  ctx.beginPath();
  ctx.arc(entryX, y(frame.entry), 3, 0, Math.PI * 2);
  ctx.fill();
}
