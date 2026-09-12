/**
 * TradingView Lightweight Charts surface over the FlipFlop bar pipeline.
 * Ported from UI_CHALLENGER_REACT_MOBILE_V1 (E:); data now comes from private_read_api
 * (/charts/bars + /charts/realtime SSE) through the authenticated labApiClient.
 *
 * Truth rules: bars flagged `synthetic` are dropped unless the viewer explicitly turns
 * on SIM view, and then the chart says so on every surface. Nothing here is evidence.
 */

import { useEffect, useRef, useState } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineStyle,
  LineSeries,
  createSeriesMarkers,
  createTextWatermark,
  createChart,
} from 'lightweight-charts';
import type { SeriesMarker, Time } from 'lightweight-charts';
import {
  normalizeMarketBars,
  rangeSeconds,
  sessionShadeData,
  simpleMovingAverage,
  type ChartRange,
  type MarketBar,
} from './chartData';
import { apiGet, apiStream } from '../labApiClient';

type ChartTelemetry = {
  bars: number;
  stream: 'CONNECTING' | 'LIVE' | 'OFFLINE';
  captureStart: number | null;
  latest: number | null;
  derived: boolean;
  synthetic: boolean;
  source: string;
};

type ChartQuote = {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
} | null;

interface BarsResponse {
  bars?: MarketBar[];
  derived?: boolean;
  source?: string;
  base_timeframe?: string;
  notice?: string;
}

function marketClock(value: number | null) {
  if (value == null) return '—';
  return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(
    new Date(value * 1000)
  );
}

function barAge(value: number | null) {
  if (value == null) return '—';
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - value));
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
}

export interface RealChartProps {
  symbol: string;
  timeframe: string;
  showSma20?: boolean;
  chartStyle?: 'candles' | 'line';
  showVolume?: boolean;
  showSessions?: boolean;
  range?: ChartRange;
  focus?: boolean;
  /** Include bars the pipeline flags synthetic (SIM view). Default false. */
  showSynthetic?: boolean;
}

export function RealChart({
  symbol,
  timeframe,
  showSma20 = false,
  chartStyle = 'candles',
  showVolume = true,
  showSessions = true,
  range = 'ALL',
  focus = false,
  showSynthetic = false,
}: RealChartProps) {
  const host = useRef<HTMLDivElement>(null);
  const goLive = useRef<() => void>(() => undefined);
  const [status, setStatus] = useState<string>('CONNECTING');
  const [notice, setNotice] = useState<string>('Loading market bars…');
  const [hasBars, setHasBars] = useState<boolean>(false);
  const [telemetry, setTelemetry] = useState<ChartTelemetry>({
    bars: 0,
    stream: 'CONNECTING',
    captureStart: null,
    latest: null,
    derived: false,
    synthetic: false,
    source: '',
  });
  const [quote, setQuote] = useState<ChartQuote>(null);

  useEffect(() => {
    const el = host.current;
    if (!el) return;

    setStatus('CONNECTING');
    setNotice('Loading market bars…');
    setHasBars(false);
    setQuote(null);
    setTelemetry({ bars: 0, stream: 'CONNECTING', captureStart: null, latest: null, derived: false, synthetic: false, source: '' });

    const chart = createChart(el, {
      width: Math.max(el.clientWidth, 280),
      height: focus ? Math.max(el.clientHeight, 520) : 330,
      layout: {
        background: { type: ColorType.Solid, color: '#020303' },
        textColor: '#aeb2ba',
        attributionLogo: true,
      },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(199,204,208,.38)', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#2c3035' },
        horzLine: { color: 'rgba(199,204,208,.38)', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#c7ccd0' },
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
      kineticScroll: { mouse: false, touch: true },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.12)', scaleMargins: { top: 0.08, bottom: 0.24 }, tickMarkDensity: 1.15 },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.12)',
        timeVisible: true,
        secondsVisible: timeframe.endsWith('s'),
        rightOffset: focus ? 5 : 3,
        maxBarSpacing: focus ? 28 : 22,
      },
    });

    const firstPane = chart.panes()[0];
    if (firstPane) {
      createTextWatermark(firstPane, {
        visible: true,
        horzAlign: 'center',
        vertAlign: 'center',
        lines: [
          {
            text: showSynthetic ? `${symbol} · ${timeframe} · SYNTHETIC` : `${symbol} · ${timeframe}`,
            color: showSynthetic ? 'rgba(216,174,76,.10)' : 'rgba(226,233,238,.032)',
            fontSize: focus ? 64 : 42,
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontStyle: '700',
          },
        ],
      });
    }

    const sessionBands = chart.addSeries(HistogramSeries, {
      visible: showSessions,
      priceScaleId: 'sessions',
      priceLineVisible: false,
      lastValueVisible: false,
      base: 0,
    });
    chart.priceScale('sessions').applyOptions({ visible: false, scaleMargins: { top: 0, bottom: 0 } });
    const candles = chart.addSeries(CandlestickSeries, {
      visible: chartStyle === 'candles',
      upColor: '#146c43',
      downColor: '#8f2f35',
      wickUpColor: '#278a5c',
      wickDownColor: '#b2464c',
      borderVisible: false,
      priceLineColor: '#aeb2ba',
      priceFormat: { type: 'price', precision: 2, minMove: 0.25 },
    });
    const volumes = chart.addSeries(HistogramSeries, {
      visible: showVolume,
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const closeLine = chart.addSeries(LineSeries, {
      visible: chartStyle === 'line',
      color: '#c7ccd0',
      lineWidth: 2,
      priceLineColor: '#c7ccd0',
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      lastValueVisible: true,
      priceFormat: { type: 'price', precision: 2, minMove: 0.25 },
    });
    const sma20 = showSma20
      ? chart.addSeries(LineSeries, {
          color: '#c7ccd0',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: 'SMA 20',
        })
      : null;
    goLive.current = () => chart.timeScale().scrollToRealTime();
    chart.subscribeCrosshairMove((param) => {
      const candle = param.seriesData.get(candles);
      if (!candle || !('open' in candle)) return;
      const volume = param.seriesData.get(volumes);
      setQuote({
        open: Number(candle.open),
        high: Number(candle.high),
        low: Number(candle.low),
        close: Number(candle.close),
        volume: volume && 'value' in volume ? Number(volume.value) : 0,
      });
    });

    const ctrl = new AbortController();
    const seenTimes = new Set<number>();
    const resize = () =>
      chart.applyOptions({
        width: Math.max(el.clientWidth, 280),
        ...(focus ? { height: Math.max(el.clientHeight, 420) } : {}),
      });
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
    if (observer) observer.observe(el);
    else window.addEventListener('resize', resize);

    // A synthetic bar is accepted only in SIM view; a real one always.
    const accept = (bar: MarketBar) => bar.synthetic !== true || showSynthetic;

    (async () => {
      try {
        const q = `symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=2400&include_synthetic=${showSynthetic ? 1 : 0}`;
        const d = await apiGet<BarsResponse>(`/charts/bars?${q}`, ctrl.signal);
        const raw = (d.bars ?? []).filter(accept);
        const anySynthetic = raw.some((bar) => bar.synthetic === true);
        // normalizeMarketBars drops synthetic bars by design; in SIM view we pass them through unflagged.
        const initial = normalizeMarketBars(showSynthetic ? raw.map((bar) => ({ ...bar, synthetic: false })) : raw);
        sessionBands.setData(sessionShadeData(initial));
        candles.setData(initial.map((bar) => bar.candle));
        closeLine.setData(initial.map((bar) => ({ time: bar.candle.time, value: Number(bar.candle.close) })));
        volumes.setData(initial.map((bar) => bar.volume));
        sma20?.setData(simpleMovingAverage(initial, 20));
        initial.forEach((bar) => seenTimes.add(Number(bar.candle.time)));
        const firstBar = initial[0];
        const latestBar = initial[initial.length - 1];
        if (latestBar) {
          setQuote({
            open: Number(latestBar.candle.open),
            high: Number(latestBar.candle.high),
            low: Number(latestBar.candle.low),
            close: Number(latestBar.candle.close),
            volume: Number(latestBar.volume.value),
          });
        }
        const captureMarker: SeriesMarker<Time>[] = firstBar
          ? [{ time: firstBar.candle.time, position: 'belowBar', color: '#c7ccd0', shape: 'circle', text: 'CAPTURE' }]
          : [];
        if (chartStyle === 'line') createSeriesMarkers(closeLine, captureMarker);
        else createSeriesMarkers(candles, captureMarker);
        const firstTime = firstBar ? Number(firstBar.candle.time) : null;
        const latestTime = latestBar ? Number(latestBar.candle.time) : null;
        const timeScale = chart.timeScale();
        const seconds = rangeSeconds(range);
        if (seconds != null && latestTime != null) {
          timeScale.setVisibleRange({ from: (latestTime - seconds) as Time, to: latestTime as Time });
        } else timeScale.fitContent();
        if (initial.length > 0 && initial.length < 24) {
          timeScale.applyOptions({ barSpacing: focus ? 18 : 14, rightOffset: focus ? 5 : 3 });
          timeScale.scrollToRealTime();
        }
        setHasBars(initial.length > 0);
        const source = d.source ?? 'UNKNOWN';
        if (initial.length === 0) {
          setNotice(
            d.notice ??
              (showSynthetic
                ? `No bars stored for ${symbol} · ${timeframe}.`
                : `No real bars for ${symbol} · ${timeframe}. Pipeline has synthetic bars only — turn on SIM DATA to view them (not evidence).`)
          );
        } else setNotice('');
        setStatus(
          `${initial.length} ${anySynthetic ? 'SYNTHETIC' : 'REAL'} BARS • ${source}${d.derived ? ` • DERIVED FROM ${d.base_timeframe ?? 'BASE'}` : ''}${anySynthetic ? ' • NOT EVIDENCE' : ' • SYNTHETIC OFF'}`
        );
        setTelemetry({
          bars: initial.length,
          stream: 'CONNECTING',
          captureStart: firstTime,
          latest: latestTime,
          derived: d.derived === true,
          synthetic: anySynthetic,
          source,
        });

        const s = await apiStream(`/charts/realtime?${q}`, ctrl.signal);
        if (!s.ok || !s.body) {
          setTelemetry((current) => ({ ...current, stream: 'OFFLINE' }));
          return;
        }
        setTelemetry((current) => ({ ...current, stream: 'LIVE' }));
        const reader = s.body.getReader();
        const dec = new TextDecoder();
        let buf = '';
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          for (let i = buf.indexOf('\n\n'); i >= 0; i = buf.indexOf('\n\n')) {
            const packet = buf.slice(0, i);
            buf = buf.slice(i + 2);
            const lines = packet.split('\n');
            if (!lines.some((l) => l.startsWith('event:') && l.includes('chart-bar'))) continue;
            const data = lines.find((l) => l.startsWith('data:'));
            if (!data) continue;
            let bar: MarketBar | null = null;
            try {
              bar = JSON.parse(data.slice(5).trim()) as MarketBar;
            } catch {
              bar = null;
            }
            if (bar && accept(bar) && bar.symbol === symbol && bar.timeframe === timeframe) {
              const normalized = normalizeMarketBars([{ ...bar, synthetic: false }])[0];
              if (!normalized) continue;
              candles.update(normalized.candle);
              closeLine.update({ time: normalized.candle.time, value: Number(normalized.candle.close) });
              volumes.update(normalized.volume);
              sessionBands.update(sessionShadeData([normalized])[0]!);
              seenTimes.add(Number(normalized.candle.time));
              setHasBars(true);
              setNotice('');
              setStatus(`${seenTimes.size} ${bar.synthetic ? 'synthetic' : 'real'} bars • live`);
              setQuote({
                open: Number(normalized.candle.open),
                high: Number(normalized.candle.high),
                low: Number(normalized.candle.low),
                close: Number(normalized.candle.close),
                volume: Number(normalized.volume.value),
              });
              setTelemetry((current) => ({
                ...current,
                bars: seenTimes.size,
                stream: 'LIVE',
                captureStart: current.captureStart ?? Number(normalized.candle.time),
                latest: Number(normalized.candle.time),
                synthetic: current.synthetic || bar!.synthetic === true,
              }));
            }
          }
        }
        setTelemetry((current) => ({ ...current, stream: 'OFFLINE' }));
      } catch (e) {
        if ((e as { name?: string }).name !== 'AbortError') {
          setStatus('CORE_UNREACHABLE');
          setNotice(`Chart unavailable. ${(e as Error).message ?? 'API could not be reached.'}`);
          setHasBars(false);
          setTelemetry((current) => ({ ...current, stream: 'OFFLINE' }));
        }
      }
    })();

    return () => {
      ctrl.abort();
      observer?.disconnect();
      if (!observer) window.removeEventListener('resize', resize);
      goLive.current = () => undefined;
      chart.remove();
    };
  }, [symbol, timeframe, showSma20, chartStyle, showVolume, showSessions, range, focus, showSynthetic]);

  return (
    <div className={`real-chart${hasBars ? '' : ' is-empty'}${focus ? ' real-chart-focus' : ''}`}>
      <div className="real-chart-truth" aria-label="Market feed status">
        <span className={`chart-stream chart-stream-${telemetry.stream.toLowerCase()}`}>
          <i />
          {telemetry.stream}
        </span>
        <span>
          <b>{telemetry.bars}</b> {telemetry.synthetic ? 'SYNTHETIC' : 'REAL'} BARS
        </span>
        {telemetry.synthetic && <span className="chart-synthetic">SIM VIEW · NOT EVIDENCE</span>}
        <span className="chart-capture">CAPTURE {marketClock(telemetry.captureStart)}</span>
        <span>LAST {marketClock(telemetry.latest)}</span>
        <span className="chart-age">
          BAR AGE <b>{barAge(telemetry.latest)}</b>
        </span>
        {telemetry.derived && <span>DERIVED</span>}
        <button type="button" className="chart-go-live" onClick={() => goLive.current()}>
          <i />
          GO LIVE
        </button>
      </div>
      {quote && (
        <div className="chart-ohlc" aria-label="Current chart values">
          <span>
            O <b>{quote.open.toFixed(2)}</b>
          </span>
          <span>
            H <b>{quote.high.toFixed(2)}</b>
          </span>
          <span>
            L <b>{quote.low.toFixed(2)}</b>
          </span>
          <span>
            C <b className={quote.close >= quote.open ? 'positive' : 'negative'}>{quote.close.toFixed(2)}</b>
          </span>
          <span>
            V <b>{Math.round(quote.volume).toLocaleString()}</b>
          </span>
        </div>
      )}
      <div ref={host} className="real-chart-host" aria-label={`${symbol} ${timeframe} TradingView Lightweight Chart`} />
      {notice && (
        <div className="real-chart-empty" role="status">
          {notice}
        </div>
      )}
      <div className="real-chart-footer">
        <small className="real-chart-status" role="status">
          {status}
        </small>
        <a className="real-chart-attribution" href="https://www.tradingview.com/" target="_blank" rel="noreferrer">
          Charts by TradingView
        </a>
      </div>
    </div>
  );
}
