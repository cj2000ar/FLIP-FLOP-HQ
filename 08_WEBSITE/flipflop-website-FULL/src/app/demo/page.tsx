'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Pause, Play } from 'lucide-react';
import Brand from '../brand';
import ExperienceDemo from '../experience-demo';
import {
  LanguageProvider,
  LanguageSelector,
  useLanguage,
} from '../site-language';

function DemoPage() {
  const { t } = useLanguage();
  const [paused, setPaused] = useState(false);
  return (
    <main className={'sales-site demo-page ' + (paused ? 'motion-paused' : '')}>
      <header className="demo-header wrap">
        <Link
          className="hq-wordmark"
          href="/"
          aria-label={t('Flip Flop HQ inicio')}
        >
          <Brand />
        </Link>
        <div className="header-actions">
          <LanguageSelector />
          <Link className="demo-return" href="/">
            <ArrowLeft size={16} />
            {t('Volver al website')}
          </Link>
        </div>
      </header>
      <div className="demo-page-content wrap">
        <div className="demo-page-tools">
          <span>{t('DEMOSTRACIÓN INTERACTIVA · SIN CONEXIÓN REAL')}</span>
          <button
            type="button"
            className="motion-control"
            aria-pressed={paused}
            onClick={() => setPaused(!paused)}
          >
            {paused ? <Play size={14} /> : <Pause size={14} />}{' '}
            {t(paused ? 'Activar movimiento' : 'Pausar movimiento')}
          </button>
        </div>
        <ExperienceDemo paused={paused} />
      </div>
      <footer className="demo-page-footer wrap">
        <Brand compact />
        <span>
          {t(
            'Simulación automática con precios sintéticos. Sin órdenes ni rendimiento real.',
          )}
        </span>
      </footer>
    </main>
  );
}
export default function Demo() {
  return (
    <LanguageProvider>
      <DemoPage />
    </LanguageProvider>
  );
}
