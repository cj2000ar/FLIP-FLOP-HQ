'use client';

import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowRight, Radar, ShieldCheck } from 'lucide-react';
import { createMotionLoop } from './motion-loop';
import { useLanguage } from './site-language';

const stages = [
  {
    label: 'Señal',
    icon: Radar,
    title: 'Lee el contexto.',
    body: 'Una señal es el punto de partida para evaluar una oportunidad. La estrategia concreta se revisa con HQ.',
  },
  {
    label: 'Reglas',
    icon: ShieldCheck,
    title: 'Primero, las condiciones.',
    body: 'La configuración y los permisos determinan cómo puede actuar el sistema. Se acuerdan antes de la activación.',
  },
  {
    label: 'Seguimiento',
    icon: Activity,
    title: 'Todo en contexto.',
    body: 'Consulta el estado, las operaciones y los próximos pasos desde tus dispositivos autorizados.',
  },
] as const;

export default function AutomationStory({ paused }: { paused: boolean }) {
  const { t } = useLanguage();
  const [selected, setSelected] = useState(0);
  const host = useRef<HTMLDivElement>(null);
  const stopped = useRef(paused);
  const refresh = useRef(() => {});
  useEffect(() => {
    stopped.current = paused;
    refresh.current();
  }, [paused]);
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let phase = 0;
    const loop = createMotionLoop(
      element,
      (elapsed, moving) => {
        if (moving) phase = (phase + elapsed * 16) % 100;
        element.style.setProperty('--signal-offset', String(-phase));
      },
      { paused: () => stopped.current, maxFps: 30 },
    );
    refresh.current = loop.invalidate;
    return () => {
      refresh.current = () => {};
      loop.dispose();
    };
  }, []);
  const stage = stages[selected];
  return (
    <section className="automation-story" aria-labelledby="automation-title">
      <div className="automation-heading">
        <span className="eyebrow">{t('DENTRO DE LA AUTOMATIZACIÓN')}</span>
        <h2 id="automation-title">
          {t('De una señal a una visión completa.')}
        </h2>
        <p>{t('Explora las tres etapas de este recorrido ilustrativo.')}</p>
      </div>
      <div className="automation-console" ref={host}>
        <fieldset className="automation-controls">
          <legend className="sr-only">
            {t('Seleccionar etapa de automatización')}
          </legend>
          {stages.map(({ label, icon: Icon }, index) => (
            <button
              key={label}
              type="button"
              aria-pressed={selected === index}
              aria-controls="automation-detail"
              onClick={() => setSelected(index)}
            >
              <span className="automation-index">0{index + 1}</span>
              <Icon size={19} aria-hidden="true" />
              <span>{t(label)}</span>
            </button>
          ))}
        </fieldset>
        <div className="automation-body">
          <div className="automation-network" aria-hidden="true">
            <svg viewBox="0 0 560 200" fill="none">
              <path className="automation-track" d="M90 100H470" />
              <path
                className="automation-signal"
                pathLength="100"
                d="M90 100H470"
              />
              {stages.map(({ icon: Icon, label }, index) => (
                <g
                  key={label}
                  className={
                    selected === index
                      ? 'automation-node is-current'
                      : 'automation-node'
                  }
                >
                  <rect
                    x={index * 190 + 57}
                    y="67"
                    width="66"
                    height="66"
                    rx="20"
                  />
                  <Icon
                    x={index * 190 + 78}
                    y="88"
                    width="24"
                    height="24"
                    strokeWidth="1.3"
                  />
                  <text x={index * 190 + 90} y="165" textAnchor="middle">
                    {t(label)}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <div
            className="automation-detail"
            id="automation-detail"
            aria-live="polite"
            aria-atomic="true"
          >
            <div key={selected} className="automation-copy">
              <span className="automation-step">0{selected + 1} / 03</span>
              <h3>{t(stage.title)}</h3>
              <p>{t(stage.body)}</p>
            </div>
          </div>
          <div className="automation-bottom">
            <p>
              {t(
                'Esquema ilustrativo. El funcionamiento depende de la configuración acordada.',
              )}
            </p>
            <button
              type="button"
              onClick={() =>
                setSelected((current) => (current + 1) % stages.length)
              }
            >
              {t('Siguiente etapa')} <ArrowRight size={17} aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
