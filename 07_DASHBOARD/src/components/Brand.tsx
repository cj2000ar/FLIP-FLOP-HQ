export default function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className={'brand-lockup' + (compact ? ' brand-compact' : '')}
      aria-label="Flip Flop HQ"
    >
      <span className="brand-symbol" aria-hidden="true">
        <img src="/assets/flipflop-hq-mark-v4.png" width={38} height={38} alt="" />
      </span>
      <span className="brand-letters" aria-hidden="true">
        <span className="brand-flip">FLIP</span>
        <span className="brand-flop">FLOP</span>
        <span className="brand-hq">
          <span className="brand-h">H</span>
          <span className="brand-q">Q</span>
        </span>
      </span>
    </span>
  );
}
