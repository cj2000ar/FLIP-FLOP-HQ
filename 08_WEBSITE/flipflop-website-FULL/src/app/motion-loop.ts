type MotionOptions = {
  paused: () => boolean;
  ready?: () => boolean;
  maxFps?: number;
};

/** Only schedule frames that can produce visible work. */
export function createMotionLoop(
  element: Element,
  draw: (elapsed: number, moving: boolean) => void,
  { paused, ready = () => true, maxFps = 60 }: MotionOptions,
) {
  const media = matchMedia('(prefers-reduced-motion: reduce)');
  let frame: number | null = null;
  let previous = 0,
    visible = false,
    dirty = true,
    disposed = false;
  const interval = 1000 / maxFps;
  function cancel() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
  }
  function schedule() {
    if (!disposed && visible && !document.hidden && ready() && frame === null) {
      frame = requestAnimationFrame(tick);
    }
  }
  function tick(now: number) {
    frame = null;
    if (disposed || !visible || document.hidden || !ready()) return;
    const moving = !paused() && !media.matches;
    if (!dirty && !moving) return;
    if (!dirty && now - previous < interval - 0.5) {
      schedule();
      return;
    }
    const elapsed = previous ? Math.min((now - previous) / 1000, 0.05) : 0;
    previous = now;
    draw(elapsed, moving);
    dirty = false;
    if (moving) schedule();
  }
  function invalidate() {
    dirty = true;
    previous = 0;
    cancel();
    schedule();
  }
  const observer = new IntersectionObserver((entries) => {
    visible = entries.some((entry) => entry.isIntersecting);
    invalidate();
  });
  observer.observe(element);
  media.addEventListener('change', invalidate);
  document.addEventListener('visibilitychange', invalidate);
  return {
    invalidate,
    dispose() {
      disposed = true;
      cancel();
      observer.disconnect();
      media.removeEventListener('change', invalidate);
      document.removeEventListener('visibilitychange', invalidate);
    },
  };
}
