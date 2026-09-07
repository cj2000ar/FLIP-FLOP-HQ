'use client';

import { useEffect, useRef, useState } from 'react';
import EarthScene from './earth-scene';
import Link from 'next/link';
import Brand from './brand';
import SmokeAtmosphere from './smoke-atmosphere';
import ProductShowcase from './product-showcase';
import ProductChart from './product-chart';
import NumberField from './number-field';
import AccessRequest from './access-request';
import ExperienceDemo from './experience-demo';
import OperatingPrinciples from './operating-principles';
import { InstallationDetails, AccessConditions } from './access-details';
import { createMotionLoop } from './motion-loop';
import {
  initialWorldFrame,
  sampleWorldJourney,
  worldSections,
} from './world-journey';
import {
  ArrowUpRight,
  ArrowDown,
  Pause,
  Play,
  Smartphone,
  CalendarDays,
  Layers,
  Check,
  Mail,
} from 'lucide-react';
import {
  LanguageProvider,
  LanguageSelector,
  useLanguage,
} from './site-language';

function MarketMotion({ paused }: { paused: boolean }) {
  const { t } = useLanguage();
  const chart = useRef<SVGSVGElement>(null);
  const stopped = useRef(paused);
  const refresh = useRef(() => {});
  useEffect(() => {
    stopped.current = paused;
    refresh.current();
  }, [paused]);
  useEffect(() => {
    const svg = chart.current;
    if (!svg) return;
    const line = svg.querySelector('[data-line]');
    const candles = svg.querySelectorAll('[data-candle]');
    let phase = 0;
    const loop = createMotionLoop(
      svg,
      (elapsed, moving) => {
        if (moving) phase += elapsed * 0.55;
        const values = Array.from(
          { length: 45 },
          (_, i) =>
            195 -
            i * 2.7 +
            Math.sin(i * 0.65 + phase) * 24 +
            Math.sin(i * 1.9 - phase * 0.6) * 13,
        );
        line?.setAttribute(
          'd',
          values
            .map((y, i) => (i ? 'L' : 'M') + (i * 20 + 10) + ',' + y)
            .join(' '),
        );
        candles.forEach((node, i) => {
          const y = values[i],
            previous = values[Math.max(0, i - 1)];
          node.setAttribute('y', String(Math.min(y, previous)));
          node.setAttribute(
            'height',
            String(Math.max(3, Math.abs(y - previous))),
          );
          node.setAttribute(
            'fill',
            y < previous ? 'var(--brand-green)' : 'var(--brand-red)',
          );
          node.setAttribute(
            'opacity',
            String(0.35 + Math.min(Math.abs(y - previous) / 12, 1) * 0.5),
          );
        });
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
      ref={chart}
      viewBox="0 0 900 270"
      className="market-motion"
      aria-label={t('Animación ilustrativa del mercado, sin datos reales')}
    >
      {[65, 130, 195, 260].map((y) => (
        <line key={y} x1="0" x2="900" y1={y} y2={y} stroke="#ffffff0c" />
      ))}
      {Array.from({ length: 45 }, (_, i) => (
        <rect
          data-candle=""
          key={i}
          x={i * 20 + 7}
          y="130"
          width="5"
          height="10"
          rx="1.4"
          fill="var(--brand-green)"
        />
      ))}
      <path
        data-line=""
        fill="none"
        stroke="#a5aaac"
        strokeWidth="1"
        opacity=".38"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Home() {
  const { t, locale } = useLanguage();
  const [paused, setPaused] = useState(false);
  const [split, setSplit] = useState<50 | 70>(50);
  const [requestOpen, setRequestOpen] = useState(false);
  const [earthActive, setEarthActive] = useState(true);
  const journey = useRef(initialWorldFrame);
  const scene = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const pointer = (event: PointerEvent) => {
      if (
        !scene.current ||
        paused ||
        media.matches ||
        event.pointerType !== 'mouse'
      )
        return;
      scene.current.style.setProperty(
        '--pointer-x',
        (event.clientX / innerWidth - 0.5) * 24 + 'px',
      );
      scene.current.style.setProperty(
        '--pointer-y',
        (event.clientY / innerHeight - 0.5) * 16 + 'px',
      );
    };
    const reset = () => {
      scene.current?.style.setProperty('--pointer-x', '0px');
      scene.current?.style.setProperty('--pointer-y', '0px');
    };
    reset();
    addEventListener('pointermove', pointer, { passive: true });
    media.addEventListener('change', reset);
    return () => {
      removeEventListener('pointermove', pointer);
      media.removeEventListener('change', reset);
    };
  }, [paused]);
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    let frame: number | null = null;
    let anchors: number[] = [],
      lastEarthActive: boolean | null = null,
      overviewEnd = 0;
    const measure = () => {
      anchors = [];
      worldSections.forEach((id, index) => {
        const top =
          document.getElementById(id)?.offsetTop ?? index * innerHeight;
        anchors.push(
          index === 0
            ? 0
            : Math.max(anchors[index - 1] + 1, top - innerHeight * 0.35),
        );
      });
      overviewEnd =
        (document.getElementById('world-passage')?.offsetTop ?? anchors[2]) -
        innerHeight * 0.25;
    };
    const paint = () => {
      frame = null;
      const element = scene.current;
      if (!element) return;
      element.style.setProperty(
        '--scroll',
        paused || media.matches ? '0px' : Math.min(scrollY * 0.16, 180) + 'px',
      );
      const current = media.matches
        ? initialWorldFrame
        : sampleWorldJourney(scrollY, anchors, overviewEnd);
      journey.current = current;
      element.style.setProperty('--earth-opacity', current.earth.toFixed(3));
      const active = current.earth > 0.008;
      if (lastEarthActive !== active) {
        lastEarthActive = active;
        setEarthActive(active);
      }
      if (paused) {
        element.dispatchEvent(new Event('world-frame'));
        document
          .getElementById('world-passage')
          ?.dispatchEvent(new Event('world-frame'));
      }
    };
    const update = () => {
      if (frame === null) frame = requestAnimationFrame(paint);
    };
    const resize = () => {
      measure();
      update();
    };
    const layoutObserver = new ResizeObserver(resize);
    const page = scene.current?.parentElement;
    if (page) layoutObserver.observe(page);
    resize();
    addEventListener('scroll', update, { passive: true });
    addEventListener('resize', resize, { passive: true });
    media.addEventListener('change', update);
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      removeEventListener('scroll', update);
      removeEventListener('resize', resize);
      layoutObserver.disconnect();
      media.removeEventListener('change', update);
    };
  }, [paused, locale]);

  return (
    <main
      id="inicio"
      className={'sales-site ' + (paused ? 'motion-paused' : '')}
    >
      <div
        className="space-scene sales-scene globe-scene"
        ref={scene}
        aria-hidden="true"
      >
        <SmokeAtmosphere />
        <NumberField paused={paused} journey={journey} />
        <EarthScene paused={paused} active={earthActive} closeUp />
        <div className="scene-shade" />
      </div>
      <header className="sales-header wrap">
        <a
          href="#inicio"
          className="hq-wordmark"
          aria-label={t('Flip Flop HQ inicio')}
        >
          <Brand />
        </a>
        <nav aria-label={t('Principal')}>
          <a href="#producto">{t('La app')}</a>
          <a href="#como-funciona">{t('Cómo funciona')}</a>
          <a href="#requisitos">{t('Requisitos')}</a>
          <a href="#reparto">{t('El modelo')}</a>
        </nav>
        <div className="header-actions">
          <LanguageSelector />
          <button
            type="button"
            aria-label={t('Solicitar acceso')}
            className="small-cta"
            onClick={() => setRequestOpen(true)}
          >
            <span>{t('Solicitar acceso')}</span>
            <ArrowUpRight size={16} />
          </button>
        </div>
      </header>
      <section className="sales-hero wrap">
        <div className="hero-copy">
          <span className="eyebrow">
            <i /> {t('TRADING AUTOMATIZADO. VISIÓN COMPLETA.')}
          </span>
          <h1>
            <span className="sr-only">{t('Tu trading. En otra órbita.')}</span>
            <span aria-hidden="true">
              {t('Tu trading.')}
              <br />
              {locale === 'es' ? (
                <>
                  En otra{' '}
                  <em>
                    <span className="accent-o">ó</span>
                    rbita.
                  </em>
                </>
              ) : (
                <em>
                  {t('En otra órbita')}
                  <span className="brand-punctuation">.</span>
                </em>
              )}
            </span>
          </h1>
          <p className="brand-promise">
            {t('Automatizado. Verificable. Bajo tu control.')}
          </p>
          <p>
            {t(
              'Automatización, seguimiento y agenda en un solo lugar. Instala HQ en tu PC y mantén tu operación a la vista desde tus dispositivos autorizados.',
            )}
          </p>
          <div className="cta-row">
            <button
              type="button"
              className="primary-cta"
              onClick={() => setRequestOpen(true)}
            >
              {t('Quiero conocer HQ')}
              <ArrowUpRight size={19} />
            </button>
            <a className="text-cta" href="#producto">
              <Play size={15} /> {t('Explorar la app')}
            </a>
          </div>
          <div className="hero-details">
            <span>
              <Check size={14} /> {t('Mac, Windows y móvil')}
            </span>
            <span>
              <Check size={14} /> {t('Instalación inicial en PC')}
            </span>
          </div>
        </div>
        <div className="orbit-caption">
          <span>{t('UNA VISIÓN GLOBAL')}</span>
          <span>{t('Tierra nocturna · NASA Black Marble')}</span>
        </div>
        <div className="hero-chart">
          <MarketMotion paused={paused} />
          <span>{t('VISUALIZACIÓN ILUSTRATIVA · NO ES RENDIMIENTO REAL')}</span>
        </div>
        <div className="hero-bottom">
          <a href="#producto">
            <ArrowDown size={16} /> {t('Descubre lo que hay dentro')}
          </a>
          <button
            className="motion-control"
            onClick={() => setPaused(!paused)}
            aria-pressed={paused}
          >
            {paused ? <Play size={14} /> : <Pause size={14} />}{' '}
            {t(paused ? 'Activar movimiento' : 'Pausar movimiento')}
          </button>
        </div>
      </section>

      <section className="product-section wrap" id="producto">
        <div className="section-heading">
          <span className="eyebrow">{t('01 / CONOCE LA APP')}</span>
          <h2>
            {t('Toda la operación.')}
            <br />
            <span>{t('Una sola vista.')}</span>
          </h2>
          <p>
            {t(
              'Operaciones, estado y próximos pasos. Una experiencia conectada para entender lo que ocurre y saber qué revisar después.',
            )}
          </p>
        </div>
        <ProductShowcase paused={paused}>
          <ProductChart paused={paused} />
        </ProductShowcase>
        <div className="product-link">
          <span>{t('Una misma perspectiva, en cada pantalla.')}</span>
          <Link href="/demo">
            {t('Abrir demo de la interfaz')}
            <ArrowUpRight size={16} />
          </Link>
        </div>
        <div className="benefit-grid">
          {[
            {
              icon: Layers,
              title: 'Automatización organizada',
              body: 'Configuración y seguimiento reunidos en un flujo claro.',
            },
            {
              icon: Smartphone,
              title: 'HQ en tus dispositivos',
              body: 'Consulta tu operación desde la PC, tu Mac o el teléfono.',
            },
            {
              icon: CalendarDays,
              title: 'Cada paso, a la vista',
              body: 'Agenda y puntos de revisión para mantener el contexto.',
            },
          ].map(({ icon: Icon, title, body }) => (
            <article key={title}>
              <Icon size={24} />
              <h3>{t(title)}</h3>
              <p>{t(body)}</p>
            </article>
          ))}
        </div>
      </section>

      <div className="world-passage" id="world-passage" aria-hidden="true">
        <NumberField paused={paused} journey={journey} passage />
      </div>

      <section className="steps-section wrap" id="como-funciona">
        <ExperienceDemo paused={paused} />
        <div className="section-heading">
          <span className="eyebrow">{t('02 / ASÍ EMPIEZA')}</span>
          <h2>
            {t('De conocer HQ')}
            <br />
            {t('a hacerlo tuyo.')}
          </h2>
        </div>
        <div className="steps">
          {[
            [
              '01',
              'Conoce la app',
              'Explora la experiencia, sus vistas y cómo encaja en tu forma de operar.',
            ],
            [
              '02',
              'Completa tu solicitud',
              'Cuéntanos tu experiencia, tu equipo y qué buscas. HQ revisa contigo los requisitos y las condiciones de acceso.',
            ],
            [
              '03',
              'Prepara tu PC',
              'Instala el sistema en Windows y revisa con HQ tu cuenta, permisos, documentos y modalidad.',
            ],
            [
              '04',
              'Valida en SIM',
              'Revisa la configuración en simulación y conecta tus dispositivos autorizados. La operativa real requiere una autorización posterior.',
            ],
          ].map(([n, title, body]) => (
            <article key={n}>
              <span>{n}</span>
              <div>
                <h3>{t(title)}</h3>
                <p>{t(body)}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <InstallationDetails />

      <section className="split-section wrap" id="reparto">
        <OperatingPrinciples />
        <div className="section-heading">
          <span className="eyebrow">{t('03 / UN MODELO COMPARTIDO')}</span>
          <h2>
            {t('Tu parte,')}
            <br />
            <span>{t('siempre clara.')}</span>
          </h2>
          <p>
            {t(
              'Dos modalidades de reparto: 70% para ti y 30% para HQ al añadir US$700 a tu cuenta; o 50% para cada parte sin añadir dinero para empezar.',
            )}
          </p>
        </div>
        <div className="split-card">
          <div className="split-top">
            <span>{t('REPARTO DE BENEFICIOS')}</span>
            <span>{t('SUJETO A ACUERDO')}</span>
          </div>
          <div className="split-values">
            <div>
              <strong>
                {split}
                <small>%</small>
              </strong>
              <span>{t('Para el cliente')}</span>
            </div>
            <div>
              <strong>
                {100 - split}
                <small>%</small>
              </strong>
              <span>{t('Para HQ')}</span>
            </div>
          </div>
          <div className="split-bar">
            <span style={{ width: split + '%' }} />
            <span style={{ width: 100 - split + '%' }} />
          </div>
          <div className="split-options">
            <button onClick={() => setSplit(70)} aria-pressed={split === 70}>
              {t('70 / 30 · Añadiendo $700')}
            </button>
            <button onClick={() => setSplit(50)} aria-pressed={split === 50}>
              {t('50 / 50 · Sin añadir dinero')}
            </button>
          </div>
          <div className="split-purchase">
            <div>
              <strong>{t('Da el primer paso hacia HQ.')}</strong>
              <span>
                {t('Solicita información sobre tu modalidad y la activación.')}
              </span>
            </div>
            <button type="button" onClick={() => setRequestOpen(true)}>
              {t('Solicitar acceso')}
              <ArrowUpRight size={17} />
            </button>
          </div>
          <p>
            {t(
              'Los US$700 se añaden a tu cuenta de trading; no son el precio de compra de la app. El reparto se aplica a beneficios, no representa rentabilidad. HQ confirmará contigo costes, cálculo y condiciones. El trading puede generar pérdidas y no garantiza beneficios.',
            )}
          </p>
        </div>
      </section>

      <AccessConditions />

      <section className="access-section wrap" id="acceso">
        <span className="eyebrow">{t('TU PRÓXIMO MOVIMIENTO')}</span>
        <h2>{t('Tu próximo paso empieza aquí.')}</h2>
        <p>
          {t('Empieza por la app. Revisa el modelo.')}
          <br />
          {t('Decide con toda la información.')}
        </p>
        <div className="cta-row">
          <Link className="primary-cta" href="/demo">
            {t('Explorar demo')}
            <ArrowUpRight size={18} />
          </Link>
          <button
            type="button"
            className="secondary-cta"
            onClick={() => setRequestOpen(true)}
          >
            {t('Solicitar acceso')}
            <Mail size={17} />
          </button>
        </div>
        <small>
          {t(
            'Escríbenos a cjar292@gmail.com. Completa tu solicitud y envíala a HQ desde tu correo.',
          )}
        </small>
      </section>
      <AccessRequest
        open={requestOpen}
        onClose={() => setRequestOpen(false)}
        split={split}
        onSplitChange={setSplit}
      />
      <footer className="sales-footer wrap">
        <a className="hq-wordmark" href="#inicio">
          <Brand />
        </a>
        <a href="/earth-imagery-credits.txt" target="_blank" rel="noreferrer">
          {t('Imágenes: NASA · Solar System Scope')}
        </a>
        <a href="#condiciones">
          {t('Condiciones de acceso')}
          <ArrowUpRight size={14} />
        </a>
      </footer>
    </main>
  );
}

export default function Website() {
  return (
    <LanguageProvider>
      <Home />
    </LanguageProvider>
  );
}
