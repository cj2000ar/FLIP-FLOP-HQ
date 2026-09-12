/**
 * Chart tab — TradingView Lightweight Charts over the FlipFlop/NinjaTrader bar pipeline.
 * SIM VIEW · READ ONLY. No order controls exist here and none may be added.
 */

import { useEffect, useState } from 'react';
import { RealChart } from './RealChart';
import {
  CHART_INSTRUMENTS,
  CHART_RANGES,
  CHART_TIMEFRAMES,
  loadChartPreferences,
  saveChartPreferences,
  type ChartPreferences,
} from './chartPreferences';
import './chart.css';

export default function ChartView() {
  const [preferences, setPreferences] = useState<ChartPreferences>(loadChartPreferences);
  const { symbol, timeframe, showSma20, chartStyle, showVolume, showSessions, range, showSynthetic } = preferences;
  const update = (next: Partial<ChartPreferences>) => setPreferences((current) => ({ ...current, ...next }));

  useEffect(() => {
    saveChartPreferences(preferences);
  }, [preferences]);

  return (
    <section className="chart-view" role="region" aria-label="Market chart">
      <div className="chart-view-title">
        <div>
          <span>FUTURES · MARKET FOCUS</span>
          <strong>
            {symbol} · {timeframe}
          </strong>
        </div>
        <small>TradingView Lightweight Charts · bars supplied by the FlipFlop/NinjaTrader pipeline · Authority ZERO</small>
      </div>

      <div className="chart-toolbar">
        <div className="chart-tool-section">
          <span>MARKET</span>
          <div className="toolbar-group" role="group" aria-label="Symbol">
            {CHART_INSTRUMENTS.map((item) => (
              <button
                type="button"
                key={item.symbol}
                className={symbol === item.symbol ? 'active' : ''}
                disabled={!item.verified}
                title={item.verified ? item.symbol : `${item.symbol} producer not verified`}
                onClick={() => update({ symbol: item.symbol })}
              >
                {item.symbol}
              </button>
            ))}
          </div>
        </div>
        <div className="chart-tool-section">
          <span>TIMEFRAME</span>
          <div className="toolbar-group" role="group" aria-label="Timeframe">
            {CHART_TIMEFRAMES.map((item) => (
              <button type="button" key={item} className={timeframe === item ? 'active' : ''} onClick={() => update({ timeframe: item })}>
                {item}
              </button>
            ))}
          </div>
        </div>
        <div className="chart-tool-actions">
          <div className="toolbar-group chart-style-group" role="group" aria-label="Chart style">
            <button type="button" className={chartStyle === 'candles' ? 'active' : ''} onClick={() => update({ chartStyle: 'candles' })}>
              Candles
            </button>
            <button type="button" className={chartStyle === 'line' ? 'active' : ''} onClick={() => update({ chartStyle: 'line' })}>
              Line
            </button>
          </div>
          <button type="button" className={`indicator-toggle${showVolume ? ' active' : ''}`} aria-pressed={showVolume} onClick={() => update({ showVolume: !showVolume })}>
            Volume
          </button>
          <button type="button" className={`indicator-toggle${showSma20 ? ' active' : ''}`} aria-pressed={showSma20} onClick={() => update({ showSma20: !showSma20 })}>
            SMA 20
          </button>
          <button type="button" className={`indicator-toggle${showSessions ? ' active' : ''}`} aria-pressed={showSessions} onClick={() => update({ showSessions: !showSessions })}>
            Sessions
          </button>
          <div className="toolbar-group chart-range-group" role="group" aria-label="Visible range">
            {CHART_RANGES.map((item) => (
              <button type="button" key={item} className={range === item ? 'active' : ''} onClick={() => update({ range: item })}>
                {item === 'ALL' ? 'All' : item}
              </button>
            ))}
          </div>
          <button
            type="button"
            className={`indicator-toggle synthetic${showSynthetic ? ' active' : ''}`}
            aria-pressed={showSynthetic}
            title="Show bars the pipeline flags synthetic. Never evidence."
            onClick={() => update({ showSynthetic: !showSynthetic })}
          >
            SIM DATA
          </button>
          <span className="sim-badge">SIM VIEW · READ ONLY</span>
        </div>
      </div>

      <div className="chart-canvas">
        <RealChart
          symbol={symbol}
          timeframe={timeframe}
          showSma20={showSma20}
          chartStyle={chartStyle}
          showVolume={showVolume}
          showSessions={showSessions}
          range={range}
          showSynthetic={showSynthetic}
          focus
        />
      </div>
    </section>
  );
}
