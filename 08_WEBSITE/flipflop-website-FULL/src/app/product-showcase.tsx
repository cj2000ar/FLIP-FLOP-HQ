'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  BatteryFull,
  CalendarDays,
  ChevronRight,
  LayoutDashboard,
  LockKeyhole,
  Settings2,
  ShieldCheck,
  Signal,
  Users,
  Wifi,
} from 'lucide-react';
import { useLanguage } from './site-language';
import Brand from './brand';

const views = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'trades', label: 'Trades', icon: Activity },
  { id: 'performance', label: 'Performance', icon: BarChart3 },
  { id: 'calendar', label: 'Calendar', icon: CalendarDays },
  { id: 'agents', label: 'Agents', icon: Users },
] as const;
type View = (typeof views)[number]['id'] | 'settings';
const titles: Record<View, string> = {
  overview: 'Tu operación, conectada.',
  trades: 'Cada operación, en contexto.',
  performance: 'Una perspectiva completa.',
  calendar: 'Tu próximo paso, a la vista.',
  agents: 'Un equipo detrás de tu HQ.',
  settings: 'Tu espacio. Tus preferencias.',
};

export default function ProductShowcase({
  children,
  paused = false,
}: {
  children: ReactNode;
  paused?: boolean;
}) {
  const { t } = useLanguage();
  const [view, setView] = useState<View>('overview');
  const [notifications, setNotifications] = useState(true);
  const stage = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = stage.current;
    if (!element) return;
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    let frame: number | null = null,
      x = 0,
      y = 0;
    let rect = element.getBoundingClientRect();
    const paint = () => {
      frame = null;
      element.style.setProperty('--device-tilt-x', `${x}deg`);
      element.style.setProperty('--device-tilt-y', `${y}deg`);
    };
    const reset = () => {
      x = 0;
      y = 0;
      if (frame !== null) cancelAnimationFrame(frame);
      paint();
    };
    const enter = () => {
      rect = element.getBoundingClientRect();
    };
    const move = (event: PointerEvent) => {
      if (paused || media.matches || event.pointerType !== 'mouse') return;
      x = ((event.clientX - rect.left) / Math.max(1, rect.width) - 0.5) * 2.4;
      y = ((event.clientY - rect.top) / Math.max(1, rect.height) - 0.5) * -1.2;
      if (frame === null) frame = requestAnimationFrame(paint);
    };
    const observer = new IntersectionObserver(
      (entries) => {
        element.dataset.visible = String(
          entries.some((entry) => entry.isIntersecting),
        );
        if (element.dataset.visible === 'true')
          element.dataset.revealed = 'true';
      },
      { threshold: 0.08 },
    );
    observer.observe(element);
    reset();
    element.addEventListener('pointerenter', enter);
    element.addEventListener('pointermove', move, { passive: true });
    element.addEventListener('pointerleave', reset);
    media.addEventListener('change', reset);
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      observer.disconnect();
      element.removeEventListener('pointerenter', enter);
      element.removeEventListener('pointermove', move);
      element.removeEventListener('pointerleave', reset);
      media.removeEventListener('change', reset);
    };
  }, [paused]);
  return (
    <div className="device-showcase">
      <div className="showcase-hint">
        <span>{t('EXPLORA LA EXPERIENCIA')}</span>
        <span>
          {t('Prueba las vistas')}
          <ArrowUpRight size={14} />
        </span>
      </div>
      <div className="device-stage" ref={stage}>
        <div className="desktop-device">
          <div className="desktop-screen">
            <div className="device-toolbar">
              <div className="window-controls" aria-hidden="true">
                <i />
                <i />
                <i />
              </div>
              <Brand compact />
              <span className="preview-badge">{t('DEMO INTERACTIVA')}</span>
            </div>
            <div className="device-workspace">
              <aside className="device-sidebar">
                <span className="device-overline">{t('WORKSPACE')}</span>
                <nav aria-label={t('Vistas de la demostración')}>
                  {views.map(({ id, label, icon: Icon }) => (
                    <button
                      type="button"
                      key={id}
                      aria-label={t(label)}
                      aria-pressed={view === id}
                      onClick={() => setView(id)}
                    >
                      <Icon size={16} />
                      <span>{t(label)}</span>
                    </button>
                  ))}
                </nav>
                <button
                  className="device-settings"
                  type="button"
                  aria-label={t('Ajustes de la demostración')}
                  aria-pressed={view === 'settings'}
                  onClick={() => setView('settings')}
                >
                  <Settings2 size={16} /> {t('Ajustes')}
                </button>
              </aside>
              <div className="device-content">
                <div className="device-view-heading">
                  <div>
                    <span className="device-overline">FLIP FLOP / HQ</span>
                    <h3>{t(titles[view])}</h3>
                  </div>
                  <span className="device-mode">SIM</span>
                </div>
                <div className="device-panel" key={view}>
                  {(view === 'overview' || view === 'performance') && (
                    <>
                      <div className="device-metrics">
                        <div>
                          <span>{t('Automatización')}</span>
                          <strong>{t('Con contexto')}</strong>
                        </div>
                        <div>
                          <span>{t('Seguimiento')}</span>
                          <strong>{t('Una sola vista')}</strong>
                        </div>
                      </div>
                      <div className="device-chart">
                        {children}
                        <span>
                          {t(
                            'Visualización ilustrativa · Sin rendimiento real',
                          )}
                        </span>
                      </div>
                      <div className="device-detail">
                        <CalendarDays size={18} />
                        <div>
                          <strong>{t('Agenda de operación')}</strong>
                          <span>{t('Checkpoints y próximos pasos')}</span>
                        </div>
                        <button
                          type="button"
                          aria-label={t('Ver agenda de la demostración')}
                          onClick={() => setView('calendar')}
                        >
                          <ChevronRight size={17} />
                        </button>
                      </div>
                    </>
                  )}
                  {view === 'trades' && (
                    <div className="device-empty">
                      <Activity size={30} />
                      <h4>{t('Cada detalle cuenta.')}</h4>
                      <p>
                        {t(
                          'Entrada, salida, protección y seguimiento, reunidos por operación.',
                        )}
                      </p>
                      <span>
                        {t('Esta demostración no contiene operaciones reales.')}
                      </span>
                    </div>
                  )}
                  {view === 'calendar' && (
                    <div className="device-agenda">
                      <span className="device-overline">
                        {t('TU RUTA DE INICIO')}
                      </span>
                      {[
                        ['01', 'Preparar tu PC', 'Instalación del sistema'],
                        [
                          '02',
                          'Revisar tu acceso',
                          'Cuenta, documentos y permisos',
                        ],
                        [
                          '03',
                          'Conectar tus dispositivos',
                          'Mac, Windows y teléfono',
                        ],
                      ].map(([n, title, note]) => (
                        <div key={n}>
                          <span>{n}</span>
                          <div>
                            <strong>{t(title)}</strong>
                            <small>{t(note)}</small>
                          </div>
                          <ChevronRight size={16} />
                        </div>
                      ))}
                    </div>
                  )}
                  {view === 'agents' && (
                    <div className="device-agenda">
                      <span className="device-overline">
                        {t('DISEÑO DEL SISTEMA')}
                      </span>
                      {[
                        ['Guardian', 'Control de riesgo y permisos'],
                        ['Strategy Engine', 'Señales con contexto'],
                        ['Data & Sync', 'Seguimiento de la información'],
                      ].map(([title, note]) => (
                        <div key={title}>
                          <ShieldCheck size={20} />
                          <div>
                            <strong>{t(title)}</strong>
                            <small>{t(note)}</small>
                          </div>
                          <span className="device-tag">DEMO</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {view === 'settings' && (
                    <div className="device-preferences">
                      <div>
                        <div>
                          <strong>{t('Notificaciones')}</strong>
                          <small>
                            {t('Prueba visual en esta demostración')}
                          </small>
                        </div>
                        <button
                          className="device-switch"
                          type="button"
                          role="switch"
                          aria-checked={notifications}
                          aria-label={t('Notificaciones de ejemplo')}
                          onClick={() => setNotifications(!notifications)}
                        >
                          <span />
                        </button>
                      </div>
                      <div>
                        <div>
                          <strong>{t('Riesgo y ejecución')}</strong>
                          <small>{t('Permisos reservados al Owner')}</small>
                        </div>
                        <LockKeyhole size={18} />
                      </div>
                      <div>
                        <div>
                          <strong>{t('Estrategia CONTROL')}</strong>
                          <small>{t('Parámetros protegidos')}</small>
                        </div>
                        <span className="device-tag">{t('SOLO LECTURA')}</span>
                      </div>
                      <p>
                        {t(
                          'Los cambios de esta demo no modifican ninguna cuenta ni sistema.',
                        )}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="desktop-chin" aria-hidden="true">
            <span />
          </div>
          <div className="desktop-base" aria-hidden="true">
            <span />
          </div>
        </div>
        <div
          className="phone-device"
          aria-label={t('Vista móvil ilustrativa de HQ')}
        >
          <div className="phone-hardware" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
          <div className="phone-glass">
            <div className="phone-status" aria-hidden="true">
              <span>9:41</span>
              <span className="phone-island" />
              <div>
                <Signal size={11} />
                <Wifi size={11} />
                <BatteryFull size={15} />
              </div>
            </div>
            <div className="phone-content">
              <Brand compact />
              <span className="device-overline">
                {t('TU ESPACIO, CONTIGO')}
              </span>
              <h3>
                {t('Un solo HQ.')}
                <br />
                <span>{t('Donde estés.')}</span>
              </h3>
              <div className="phone-summary">
                <span>
                  {t(
                    view === 'calendar'
                      ? 'TU PRÓXIMO PASO'
                      : view === 'settings'
                        ? 'PREFERENCIAS'
                        : 'UNA VISIÓN CONECTADA',
                  )}
                </span>
                <strong>
                  {t(
                    view === 'calendar'
                      ? 'Preparar tu PC'
                      : view === 'settings'
                        ? notifications
                          ? 'Avisos activados'
                          : 'Avisos en pausa'
                        : 'Todo en contexto',
                  )}
                </strong>
                <small>{t('Vista ilustrativa')}</small>
              </div>
              <div className="phone-mini-list">
                <div>
                  <Activity size={15} />
                  <span>{t('Seguimiento')}</span>
                  <ChevronRight size={13} />
                </div>
                <div>
                  <CalendarDays size={15} />
                  <span>{t('Agenda')}</span>
                  <ChevronRight size={13} />
                </div>
                <div>
                  <ShieldCheck size={15} />
                  <span>{t('Control')}</span>
                  <ChevronRight size={13} />
                </div>
              </div>
            </div>
            <nav
              className="phone-dock"
              aria-label={t('Cambiar vista en la demostración móvil')}
            >
              {[
                {
                  id: 'overview' as const,
                  label: 'Inicio',
                  icon: LayoutDashboard,
                },
                {
                  id: 'calendar' as const,
                  label: 'Agenda',
                  icon: CalendarDays,
                },
                { id: 'settings' as const, label: 'Ajustes', icon: Settings2 },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  type="button"
                  key={id}
                  aria-pressed={view === id}
                  onClick={() => setView(id)}
                >
                  <Icon size={16} />
                  <span>{t(label)}</span>
                </button>
              ))}
            </nav>
            <div className="phone-home-bar" aria-hidden="true" />
          </div>
        </div>
      </div>
    </div>
  );
}
