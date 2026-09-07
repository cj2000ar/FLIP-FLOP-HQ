'use client';

import { useEffect, useRef, type RefObject } from 'react';
import { createMotionLoop } from './motion-loop';
import { drawWorldAtmosphere } from './world-atmosphere';
import type { WorldFrame } from './world-journey';

export default function NumberField({
  paused,
  journey,
  passage = false,
}: {
  paused: boolean;
  journey: RefObject<WorldFrame>;
  passage?: boolean;
}) {
  const host = useRef<HTMLCanvasElement>(null);
  const stopped = useRef(paused);
  const refresh = useRef(() => {});
  useEffect(() => {
    stopped.current = paused;
    refresh.current();
  }, [paused]);
  useEffect(() => {
    const canvas = host.current;
    if (!canvas) return;
    const context = canvas.getContext('2d', { alpha: true });
    if (!context) return;
    const palette = getComputedStyle(canvas);
    const colors = [
      '#b8bdc6',
      palette.getPropertyValue('--brand-green-ink').trim(),
      palette.getPropertyValue('--brand-red-ink').trim(),
    ];
    let width = 1,
      height = 1,
      time = 0,
      invalidate = () => {};
    const resize = () => {
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      const ratio = Math.min(devicePixelRatio, 1.25);
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      invalidate();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();
    const loop = createMotionLoop(
      canvas,
      (elapsed, moving) => {
        if (moving) time += elapsed;
        const frame = journey.current;
        drawWorldAtmosphere(
          context,
          width,
          height,
          time,
          passage
            ? {
                ...frame,
                tunnel: 1,
                orbit: 0,
                flow: 0,
                digits: 0.75,
                x: 0.5,
                y: 0.5,
              }
            : frame,
          colors,
        );
      },
      { paused: () => stopped.current, maxFps: 30 },
    );
    const parent = canvas.parentElement;
    parent?.addEventListener('world-frame', loop.invalidate);
    invalidate = loop.invalidate;
    refresh.current = loop.invalidate;
    return () => {
      refresh.current = () => {};
      parent?.removeEventListener('world-frame', loop.invalidate);
      loop.dispose();
      observer.disconnect();
    };
  }, [journey, passage]);
  return (
    <canvas
      className={passage ? 'world-passage-canvas' : 'number-field'}
      ref={host}
      aria-hidden="true"
    />
  );
}
