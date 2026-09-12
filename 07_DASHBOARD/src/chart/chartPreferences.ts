import type { ChartRange } from './chartData';

// Symbols the bar pipeline actually stores (04_ENGINE market_downloader instruments).
export const CHART_INSTRUMENTS = [
  { symbol: 'NQ', verified: true },
  { symbol: 'MNQ', verified: true },
  { symbol: 'ES', verified: true },
  { symbol: 'MES', verified: true },
  { symbol: 'GC', verified: false },
  { symbol: 'MGC', verified: false },
] as const;

// Base bars are 30m; coarser frames are derived server-side, finer ones return nothing.
export const CHART_TIMEFRAMES = ['30m', '60m', '4h', '1D'] as const;
export const CHART_RANGES = ['1H', '4H', '1D', 'ALL'] as const satisfies readonly ChartRange[];

export type ChartSymbol = (typeof CHART_INSTRUMENTS)[number]['symbol'];
export type ChartTimeframe = (typeof CHART_TIMEFRAMES)[number];
export type ChartStyle = 'candles' | 'line';

export interface ChartPreferences {
  symbol: ChartSymbol;
  timeframe: ChartTimeframe;
  showSma20: boolean;
  chartStyle: ChartStyle;
  showVolume: boolean;
  showSessions: boolean;
  range: ChartRange;
  /** Show bars the pipeline flags synthetic (labelled loudly; never evidence). */
  showSynthetic: boolean;
}

export const DEFAULT_CHART_PREFERENCES: ChartPreferences = {
  symbol: 'NQ',
  timeframe: '30m',
  showSma20: false,
  chartStyle: 'candles',
  showVolume: true,
  showSessions: false,
  range: 'ALL',
  showSynthetic: false,
};

const STORAGE_KEY = 'flipflop.pro-chart-v3';
const VERIFIED_SYMBOLS = new Set<ChartSymbol>(
  CHART_INSTRUMENTS.filter((item) => item.verified).map((item) => item.symbol)
);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function normalizeChartPreferences(value: unknown): ChartPreferences {
  if (!isObject(value) || !VERIFIED_SYMBOLS.has(value.symbol as ChartSymbol)) return { ...DEFAULT_CHART_PREFERENCES };
  return {
    symbol: value.symbol as ChartSymbol,
    timeframe: CHART_TIMEFRAMES.includes(value.timeframe as ChartTimeframe)
      ? (value.timeframe as ChartTimeframe)
      : DEFAULT_CHART_PREFERENCES.timeframe,
    showSma20: value.showSma20 === true,
    chartStyle: value.chartStyle === 'line' ? 'line' : 'candles',
    showVolume: value.showVolume !== false,
    showSessions: value.showSessions === true,
    range: CHART_RANGES.includes(value.range as ChartRange) ? (value.range as ChartRange) : DEFAULT_CHART_PREFERENCES.range,
    showSynthetic: value.showSynthetic === true,
  };
}

export function loadChartPreferences(): ChartPreferences {
  try {
    return normalizeChartPreferences(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null'));
  } catch {
    return { ...DEFAULT_CHART_PREFERENCES };
  }
}

export function saveChartPreferences(preferences: ChartPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch {
    /* storage unavailable */
  }
}
