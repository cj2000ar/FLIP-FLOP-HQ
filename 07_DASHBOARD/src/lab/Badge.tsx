import { Tone, toneFor } from './labData';

export default function Badge({ status, tone }: { status: string; tone?: Tone }) {
  const t = tone ?? toneFor(status);
  return <span className={`lab-badge lab-badge--${t}`}>{status}</span>;
}
