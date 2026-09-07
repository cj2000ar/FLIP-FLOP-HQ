export const worldSections = [
  'inicio',
  'producto',
  'como-funciona',
  'requisitos',
  'reparto',
  'condiciones',
  'acceso',
] as const;
export type WorldFrame = {
  earth: number;
  tunnel: number;
  orbit: number;
  flow: number;
  digits: number;
  turn: number;
  x: number;
  y: number;
  travel: number;
};

const stops: Omit<WorldFrame, 'travel'>[] = [
  {
    earth: 1,
    tunnel: 0.09,
    orbit: 0,
    flow: 0,
    digits: 0.06,
    turn: -0.12,
    x: 0.73,
    y: 0.5,
  },
  {
    earth: 1,
    tunnel: 0,
    orbit: 0,
    flow: 0,
    digits: 0.1,
    turn: 0.14,
    x: 0.76,
    y: 0.52,
  },
  {
    earth: 0,
    tunnel: 0.12,
    orbit: 0.95,
    flow: 0,
    digits: 0.95,
    turn: -0.38,
    x: 0.68,
    y: 0.51,
  },
  {
    earth: 0,
    tunnel: 0.08,
    orbit: 0.08,
    flow: 1,
    digits: 0.48,
    turn: 0.32,
    x: 0.3,
    y: 0.46,
  },
  {
    earth: 0,
    tunnel: 0.1,
    orbit: 0.82,
    flow: 0.15,
    digits: 0.95,
    turn: -0.28,
    x: 0.39,
    y: 0.52,
  },
  {
    earth: 0,
    tunnel: 0.06,
    orbit: 0.08,
    flow: 1,
    digits: 0.55,
    turn: 0.3,
    x: 0.76,
    y: 0.48,
  },
  {
    earth: 1,
    tunnel: 0.08,
    orbit: 0.1,
    flow: 0,
    digits: 0.15,
    turn: -0.12,
    x: 0.73,
    y: 0.5,
  },
];

/** Reversible camera path driven by ordinary scrolling, without scroll interception. */
export function sampleWorldJourney(
  scroll: number,
  anchors: readonly number[],
  overviewEnd = anchors[1] ?? 0,
): WorldFrame {
  let index = 0;
  while (index < stops.length - 1 && scroll >= anchors[index + 1]) index++;
  const end = Math.min(index + 1, stops.length - 1);
  const start =
    index === 1
      ? Math.min((anchors[end] ?? 0) - 1, Math.max(anchors[index], overviewEnd))
      : (anchors[index] ?? 0);
  const distance = Math.max(1, (anchors[end] ?? 0) - start);
  const progress =
    end === index ? 0 : Math.max(0, Math.min(1, (scroll - start) / distance));
  const ease = progress * progress * (3 - 2 * progress);
  const from = stops[index],
    to = stops[end];
  const blend = (key: keyof typeof from) =>
    from[key] + (to[key] - from[key]) * ease;
  return {
    earth: blend('earth'),
    tunnel: blend('tunnel'),
    orbit: blend('orbit'),
    flow: blend('flow'),
    digits: blend('digits'),
    turn: blend('turn'),
    x: blend('x'),
    y: blend('y'),
    travel: index + progress,
  };
}
export const initialWorldFrame = sampleWorldJourney(0, [0, 1, 2, 3, 4, 5, 6]);
