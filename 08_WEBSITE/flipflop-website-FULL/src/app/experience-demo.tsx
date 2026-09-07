'use client';

import { useLanguage } from './site-language';
import TradeSimulator from './trade-simulator';

export default function ExperienceDemo({
  paused = false,
}: {
  paused?: boolean;
}) {
  const { t } = useLanguage();
  return (
    <section
      className="experience-demo"
      aria-label={t('Simulación automática de trading')}
    >
      <div className="experience-console automatic-console">
        <TradeSimulator paused={paused} />
      </div>
    </section>
  );
}
