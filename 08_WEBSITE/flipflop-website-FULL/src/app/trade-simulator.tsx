'use client';

import { useEffect, useRef, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import { useLanguage } from './site-language';
import { createMotionLoop } from './motion-loop';
import {
  automaticTradeAt,
  demoMarkets,
  drawTradeChart,
  replayTrade,
} from './trade-simulation';

const market = demoMarkets[0];
export default function TradeSimulator({
  paused = false,
}: {
  paused?: boolean;
}) {
  const { t } = useLanguage();
  const [running, setRunning] = useState(true);
  const [reduced, setReduced] = useState(false);
  const [sample, setSample] = useState(() => automaticTradeAt(0));
  const canvas = useRef<HTMLCanvasElement>(null);
  const elapsedTime = useRef(0);
  const playback = useRef({ paused, running });
  const refresh = useRef(() => {});
  const entryLabel = t('Entrada');
  const frame = replayTrade(
    market,
    sample.direction,
    sample.outcome,
    sample.progress,
  );
  useEffect(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(preference.matches);
    update();
    preference.addEventListener('change', update);
    return () => preference.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    playback.current = { paused, running };
    refresh.current();
  }, [paused, running]);
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const ctx = element.getContext('2d');
    if (!ctx) return;
    let width = 1,
      height = 1,
      bucket = -1,
      invalidate = () => {};
    const resize = () => {
      width = element.clientWidth;
      height = element.clientHeight;
      const ratio = Math.min(devicePixelRatio, 2);
      element.width = Math.round(width * ratio);
      element.height = Math.round(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      invalidate();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();
    const loop = createMotionLoop(
      element,
      (elapsed, moving) => {
        if (moving) elapsedTime.current += elapsed;
        const current = automaticTradeAt(elapsedTime.current);
        drawTradeChart(
          ctx,
          width,
          height,
          replayTrade(
            market,
            current.direction,
            current.outcome,
            current.progress,
          ),
          market,
          { entry: entryLabel },
        );
        // Fade only the drawing between examples; controls and page never jump.
        element.style.opacity = moving ? String(current.opacity) : '1';
        const next = Math.floor(elapsedTime.current * 8);
        if (next !== bucket) {
          bucket = next;
          setSample(current);
        }
      },
      {
        paused: () => playback.current.paused || !playback.current.running,
        maxFps: 60,
      },
    );
    invalidate = loop.invalidate;
    refresh.current = loop.invalidate;
    return () => {
      refresh.current = () => {};
      loop.dispose();
      observer.disconnect();
    };
  }, [entryLabel]);
  const stopped = paused || !running || reduced;
  const status = frame.closed
    ? t(sample.outcome === 'tp' ? 'TP alcanzado' : 'SL alcanzado')
    : t('Operación simulada abierta');
  return (
    <div className="trade-simulator trade-automatic">
      <div className="auto-trade-header">
        <div className="auto-instrument">
          <strong>NQ</strong>
          <span>
            {t('Futuros')} <i>·</i> SIM / 1m
          </span>
        </div>
        <div className="auto-trade-state">
          <span className="auto-label" data-running={!stopped}>
            <i aria-hidden="true" />
            {t(
              reduced
                ? 'Movimiento reducido'
                : stopped
                  ? 'En pausa'
                  : 'Automático',
            )}
          </span>
          <button
            type="button"
            className="auto-trade-pause"
            disabled={paused || reduced}
            aria-label={t(
              stopped ? 'Reanudar simulación' : 'Pausar reproducción',
            )}
            onClick={() => setRunning(!running)}
          >
            {stopped ? <Play size={15} /> : <Pause size={15} />}
          </button>
        </div>
      </div>
      <div className="trade-screen">
        <div className="trade-watermark" aria-hidden="true">
          FLIP FLOP <span>HQ</span>
        </div>
        <canvas
          ref={canvas}
          aria-label={t(
            'Chart ilustrativo con velas, entrada, take profit y stop loss.',
          )}
        />
      </div>
      <div className="auto-trade-footer">
        <div className="auto-trade-result">
          <span className="auto-direction">
            {sample.direction === 'long' ? 'Long' : 'Short'}
          </span>
          <output>{status}</output>
        </div>
        <span className="auto-price">
          {frame.current.toFixed(market.digits)}
        </span>
      </div>
      <dl className="sr-only">
        <dt>{t('Entrada')}</dt>
        <dd>{frame.entry.toFixed(market.digits)}</dd>
        <dt>TP</dt>
        <dd>{frame.target.toFixed(market.digits)}</dd>
        <dt>SL</dt>
        <dd>{frame.stop.toFixed(market.digits)}</dd>
      </dl>
      <p className="trade-caption auto-trade-caption">
        {t(
          'Simulación automática con precios sintéticos. Sin órdenes ni rendimiento real.',
        )}
      </p>
    </div>
  );
}
