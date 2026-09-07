import type { WorldFrame } from './world-journey';
const glyphs = [
  '0',
  '1',
  '2',
  '3',
  '5',
  '7',
  '8',
  '9',
  'Σ',
  'Δ',
  '+',
  '−',
  '×',
  '%',
];
const tau = Math.PI * 2;

/** Perspective geometry only; these numbers and frames are decorative, never market data. */
export function drawWorldAtmosphere(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  time: number,
  frame: WorldFrame,
  colors: readonly string[],
) {
  ctx.clearRect(0, 0, width, height);
  const mobile = width < 640;
  const scale = Math.min(width * 0.66, height * 0.76);
  const centerX = width * (mobile ? 0.5 + (frame.x - 0.5) * 0.5 : frame.x);
  const centerY = height * frame.y;
  const travel = time * 0.075 + frame.travel * 0.82;
  const heading = frame.turn + Math.sin(time * 0.023) * 0.055;

  // The tunnel bends into each chapter and leaves its vanishing point open.
  const rings = mobile ? 11 : 15,
    panels = mobile ? 10 : 12;
  const focal = Math.min(width, height) * 0.91;
  for (let ring = rings - 1; ring >= 0; ring--) {
    const z = 0.85 + ((ring * 0.64 + travel) % (rings * 0.64));
    const fade = Math.min(
      1,
      (z - 0.85) * 2.3,
      (rings * 0.64 + 0.85 - z) * 0.65,
    );
    for (let panel = 0; panel < panels; panel++) {
      const angle = (panel / panels) * tau + heading + z * 0.065;
      ctx.beginPath();
      for (let corner = 0; corner < 4; corner++) {
        const a = angle + (corner === 0 || corner === 3 ? -0.12 : 0.12);
        const depth = z + (corner > 1 ? 0.4 : 0);
        const bend = Math.sin(depth * 0.24 + heading * 2) * 0.5;
        const x = ((Math.cos(a) * 1.67 + bend) * focal) / depth;
        const y =
          ((Math.sin(a) * 1.67 + Math.cos(depth * 0.3 + heading) * 0.18) *
            focal) /
          depth;
        if (corner === 0) ctx.moveTo(centerX + x, centerY + y);
        else ctx.lineTo(centerX + x, centerY + y);
      }
      ctx.closePath();
      const color = (panel + ring) % 4;
      ctx.strokeStyle = colors[color === 0 ? 2 : color === 2 ? 1 : 0];
      const opacity = frame.tunnel * fade * (0.17 + 0.37 / (1 + z * 0.25));
      ctx.globalAlpha = opacity * 0.12;
      ctx.lineWidth = 4;
      ctx.stroke();
      ctx.globalAlpha = opacity;
      ctx.lineWidth = Math.max(0.55, 1.75 - z * 0.1);
      ctx.stroke();
    }
  }
  if (frame.orbit > 0.005) {
    ctx.lineWidth = 1;
    const angle = -0.45 + heading + Math.sin(time * 0.035) * 0.18;
    for (let ring = 0; ring < 24; ring++) {
      const u = (ring / 24) * tau + time * 0.035 + frame.travel * 0.22;
      ctx.beginPath();
      for (let j = 0; j <= 64; j++) {
        const v = (j / 64) * tau,
          r = 0.54 + 0.23 * Math.cos(v);
        const x = r * Math.cos(u),
          y = r * Math.sin(u),
          z = 0.23 * Math.sin(v);
        const rx = x * Math.cos(angle) + z * Math.sin(angle),
          rz = -x * Math.sin(angle) + z * Math.cos(angle);
        const ry = y * 0.61 - rz * 0.79,
          depth = y * 0.79 + rz * 0.61;
        const perspective = 2.6 / (2.6 + depth);
        const px = centerX + rx * scale * perspective,
          py = centerY + ry * scale * perspective;
        if (j === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.strokeStyle =
        ring % 12 === 0 ? colors[2] : ring % 8 === 0 ? colors[1] : '#d3d6dc';
      ctx.globalAlpha = frame.orbit * (0.24 + 0.34 * (Math.sin(u) * 0.5 + 0.5));
      ctx.stroke();
    }
  }
  if (frame.flow > 0.005) {
    const rows = mobile ? 46 : 72,
      columns = mobile ? 23 : 42;
    ctx.fillStyle = '#e0e3e8';
    for (let row = 0; row < rows; row++) {
      const v = row / (rows - 1),
        wave = v * Math.PI * 3 + time * 0.15 + frame.travel * 0.24;
      for (let col = 0; col < columns; col++) {
        const u = col / (columns - 1);
        const x = (u - 0.5) * 1.55 + Math.sin(wave) * 0.24,
          y = (v - 0.5) * 2.6;
        const z =
          Math.sin(u * 5.5 + wave) * 0.32 +
          Math.cos(v * 13 - time * 0.12) * 0.12;
        const perspective = 2.6 / (2.6 + z);
        const px = centerX + (x + z * heading) * scale * perspective,
          py = centerY + y * scale * 0.67 * perspective;
        const edge = Math.sin(u * Math.PI) * Math.sin(v * Math.PI),
          grain = 0.7 + 0.3 * Math.sin(row * 8.13 + col * 4.31);
        ctx.globalAlpha = frame.flow * edge * grain * (0.4 + (z + 0.45) * 0.48);
        const size = Math.max(0.9, 1.55 * perspective);
        ctx.fillRect(px, py, size, size);
      }
    }
  }
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const count = mobile ? 25 : 46;
  for (let i = 0; i < count; i++) {
    const seed = i * 2.39996323 + heading * 0.6;
    const z = 0.5 + ((i * 0.137 + time * 0.007 + frame.travel * 0.03) % 1.8),
      distance = 0.72 + 1 / z;
    const x = width * 0.5 + Math.sin(seed) * width * 0.31 * distance;
    const y =
      height * 0.52 +
      Math.cos(seed * 1.7 + time * 0.025) * height * 0.29 * distance;
    const edgeFade = Math.min(1, (z - 0.5) * 5, (2.3 - z) * 5);
    const centerFade =
      0.3 + 0.7 * Math.min(1, Math.abs(x - width * 0.5) / (width * 0.3));
    ctx.globalAlpha = Math.max(
      0,
      frame.digits * edgeFade * centerFade * (0.25 + 0.25 / z),
    );
    ctx.fillStyle = colors[i % 5 === 0 ? 2 : i % 3 === 0 ? 1 : 0];
    ctx.font = `${Math.round(Math.min(58, 15 + 23 / z))}px ui-monospace, SFMono-Regular, Consolas, monospace`;
    ctx.fillText(glyphs[i % glyphs.length], x, y);
  }
  ctx.globalAlpha = 1;
}
