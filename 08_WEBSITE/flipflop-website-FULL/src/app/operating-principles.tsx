'use client';

import { ClipboardCheck, LockKeyhole, FlaskConical } from 'lucide-react';
import { useLanguage } from './site-language';

const principles = [
  {
    code: 'Authority = ZERO',
    icon: LockKeyhole,
    title: 'Permisos explícitos.',
    body: 'Ningún permiso operativo se da por supuesto. La activación y los cambios sensibles requieren autorización.',
  },
  {
    code: 'Live = OFF',
    icon: FlaskConical,
    title: 'Primero, validar.',
    body: 'La preparación empieza sin operativa real. Se revisan instalación, cuenta y pruebas en SIM antes de autorizar el siguiente paso.',
  },
  {
    code: 'Truth first',
    icon: ClipboardCheck,
    title: 'Hechos antes que promesas.',
    body: 'La información debe distinguir lo comprobado, lo pendiente y lo ilustrativo. Los resultados se evalúan con evidencia.',
  },
];

export default function OperatingPrinciples() {
  const { t } = useLanguage();
  return (
    <section
      className="operating-principles"
      aria-labelledby="principles-title"
    >
      <div className="principles-heading">
        <span className="eyebrow">{t('EL CRITERIO DETRÁS DE HQ')}</span>
        <h2 id="principles-title">{t('Automatizar con criterio.')}</h2>
        <p>
          {t(
            'Nuestra filosofía de preparación y acceso. Estos principios no muestran el estado de una cuenta en vivo.',
          )}
        </p>
      </div>
      <div className="principles-grid">
        {principles.map(({ code, icon: Icon, title, body }) => (
          <article key={code}>
            <div className="principle-label">
              <Icon size={20} aria-hidden="true" />
              <code>{code}</code>
            </div>
            <h3>{t(title)}</h3>
            <p>{t(body)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
