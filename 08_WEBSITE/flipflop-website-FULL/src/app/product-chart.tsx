'use client';

import { useEffect, useId, useRef } from 'react';
import { useLanguage } from './site-language';
import { createMotionLoop } from './motion-loop';

const count = 48;
const spacing = 19;
const interval = 3.8;
const priceAt = (index: number) =>
  144 +
  Math.sin(index * 0.22) * 36 +
  Math.sin(index * 0.76) * 19 +
  Math.cos(index * 1.93) * 8;

export default function ProductChart({ paused }: { paused: boolean }) {
  const { t } = useLanguage();
  const svg = useRef<SVGSVGElement>(null);
  const stopped = useRef(paused);
  const refresh = useRef(() => {});
  const clipId = useId().replace(/:/g, '');
  useEffect(() => {
    stopped.current = paused;
    refresh.current();
  }, [paused]);
  useEffect(() => {
    const root = svg.current;
    if (!root) return;
    const track = root.querySelector('[data-track]');
    const candles = Array.from(root.querySelectorAll('[data-bar]'));
    const wicks = Array.from(root.querySelectorAll('[data-wick]'));
    const line = root.querySelector('[data-history]');
    const liveBody = root.querySelector('[data-live-body]');
    const liveWick = root.querySelector('[data-live-wick]');
    const liveDot = root.querySelector('[data-live-dot]');
    const guide = root.querySelector('[data-guide]');
    let time = 0,
      lastIndex = -1;
    const loop = createMotionLoop(
      root,
      (elapsed, moving) => {
        if (moving) time += elapsed;
        const index = Math.floor(time / interval);
        const progress = (time / interval) % 1;
        if (index !== lastIndex) {
          const points: string[] = [];
          candles.forEach((body, i) => {
            const n = index + i;
            const open = priceAt(n),
              close = priceAt(n + 1);
            const high = Math.min(open, close) - 5 - Math.abs(Math.sin(n)) * 8;
            const low =
              Math.max(open, close) + 4 + Math.abs(Math.cos(n * 0.7)) * 6;
            const color =
              close < open ? 'var(--brand-green-ink)' : 'var(--brand-red-ink)';
            body.setAttribute('y', String(Math.min(open, close)));
            body.setAttribute(
              'height',
              String(Math.max(2, Math.abs(open - close))),
            );
            body.setAttribute('fill', color);
            wicks[i].setAttribute('y1', String(high));
            wicks[i].setAttribute('y2', String(low));
            wicks[i].setAttribute('stroke', color);
            points.push(`${i ? 'L' : 'M'}${i * spacing + 11},${close}`);
          });
          line?.setAttribute('d', points.join(' '));
          lastIndex = index;
        }
        const open = priceAt(index + count);
        const target = priceAt(index + count + 1);
        const close =
          open +
          (target - open) * progress +
          Math.sin(progress * Math.PI * 6) * 3 * Math.sin(progress * Math.PI);
        const x = count * spacing + 11 - progress * spacing;
        const color =
          close < open ? 'var(--brand-green-ink)' : 'var(--brand-red-ink)';
        track?.setAttribute('transform', `translate(${-progress * spacing} 0)`);
        liveBody?.setAttribute('x', String(x - 3.5));
        liveBody?.setAttribute('y', String(Math.min(open, close)));
        liveBody?.setAttribute(
          'height',
          String(Math.max(2, Math.abs(open - close))),
        );
        liveBody?.setAttribute('fill', color);
        liveWick?.setAttribute('x1', String(x));
        liveWick?.setAttribute('x2', String(x));
        liveWick?.setAttribute(
          'y1',
          String(Math.min(open, close) - 4 * progress),
        );
        liveWick?.setAttribute(
          'y2',
          String(Math.max(open, close) + 4 * progress),
        );
        liveWick?.setAttribute('stroke', color);
        liveDot?.setAttribute('cx', String(x));
        liveDot?.setAttribute('cy', String(close));
        liveDot?.setAttribute('fill', color);
        guide?.setAttribute('y1', String(close));
        guide?.setAttribute('y2', String(close));
      },
      { paused: () => stopped.current },
    );
    refresh.current = loop.invalidate;
    return () => {
      refresh.current = () => {};
      loop.dispose();
    };
  }, []);
  return (
    <svg
      ref={svg}
      className="product-market-chart"
      viewBox="0 0 950 270"
      aria-label={t(
        'Simulación de velas de mercado que avanza en el tiempo. No muestra precios ni resultados reales.',
      )}
    >
      <defs>
        <clipPath id={clipId}>
          <rect x="0" y="0" width="938" height="258" rx="5" />
        </clipPath>
      </defs>
      {[50, 105, 160, 215].map((y) => (
        <line key={y} x1="0" x2="940" y1={y} y2={y} stroke="#ffffff0b" />
      ))}
      <g clipPath={`url(#${clipId})`}>
        <line
          data-guide=""
          x1="0"
          x2="938"
          y1="144"
          y2="144"
          stroke="#ffffff20"
          strokeDasharray="3 7"
        />
        <g data-track="">
          <path
            data-history=""
            fill="none"
            stroke="#b0b0b0"
            strokeWidth="1"
            opacity=".22"
            strokeLinejoin="round"
          />
          {Array.from({ length: count }, (_, i) => (
            <g key={i}>
              <line
                data-wick=""
                x1={i * spacing + 11}
                x2={i * spacing + 11}
                y1="139"
                y2="151"
                stroke="var(--brand-green-ink)"
                strokeWidth="1"
                opacity=".65"
              />
              <rect
                data-bar=""
                x={i * spacing + 7.5}
                y="142"
                width="7"
                height="4"
                rx="1"
                fill="var(--brand-green-ink)"
                opacity=".8"
              />
            </g>
          ))}
        </g>
        <line
          data-live-wick=""
          x1="923"
          x2="923"
          y1="140"
          y2="150"
          strokeWidth="1"
        />
        <rect data-live-body="" x="919.5" y="142" width="7" height="4" rx="1" />
        <circle data-live-dot="" cx="923" cy="144" r="2.5" />
      </g>
      <text
        x="0"
        y="267"
        fill="#737373"
        fontSize="9"
        fontFamily="ui-monospace, monospace"
        letterSpacing="1.5"
      >
        {t('SECUENCIA ILUSTRATIVA')}
      </text>
      <text
        x="938"
        y="267"
        textAnchor="end"
        fill="#737373"
        fontSize="9"
        fontFamily="ui-monospace, monospace"
      >
        SIM
      </text>
    </svg>
  );
}
