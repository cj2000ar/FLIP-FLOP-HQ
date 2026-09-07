'use client';

import {
  ArrowRight,
  ChevronDown,
  Laptop,
  Monitor,
  ShieldCheck,
  Smartphone,
} from 'lucide-react';
import { useLanguage } from './site-language';

export function InstallationDetails() {
  const { t } = useLanguage();
  return (
    <section className="installation-section wrap" id="requisitos">
      <div className="section-heading">
        <span className="eyebrow">{t('TU PC ES EL PUNTO DE PARTIDA')}</span>
        <h2>
          {t('Instálalo una vez.')}
          <br />
          <span>{t('Accede desde donde estés.')}</span>
        </h2>
        <p>
          {t(
            'El sistema necesita una instalación inicial en una PC con Windows. Después de configurar y autorizar tu acceso, podrás consultar HQ desde el navegador de tu Mac, otra PC o tu teléfono.',
          )}
        </p>
      </div>
      <div className="installation-flow">
        <article>
          <span className="installation-step">
            {t('01 · INSTALACIÓN OBLIGATORIA')}
          </span>
          <Monitor size={29} />
          <h3>{t('PC con Windows')}</h3>
          <p>
            {t(
              'Aquí se instala y funciona el sistema. La PC debe permanecer encendida y conectada mientras esté operando.',
            )}
          </p>
          <span className="installation-tag">{t('Sistema principal')}</span>
        </article>
        <ArrowRight
          className="installation-arrow"
          size={20}
          aria-hidden="true"
        />
        <article>
          <span className="installation-step">{t('02 · ACCESO A HQ')}</span>
          <Laptop size={29} />
          <h3>{t('Mac o Windows')}</h3>
          <p>
            {t(
              'Accede a la interfaz desde el navegador con tu usuario autorizado. El acceso desde Mac no sustituye la instalación en Windows.',
            )}
          </p>
          <span className="installation-tag">{t('Interfaz web')}</span>
        </article>
        <ArrowRight
          className="installation-arrow"
          size={20}
          aria-hidden="true"
        />
        <article>
          <span className="installation-step">{t('03 · CONTIGO')}</span>
          <Smartphone size={29} />
          <h3>{t('Tu teléfono')}</h3>
          <p>
            {t(
              'Consulta seguimiento, agenda y estado desde tu dispositivo vinculado. El teléfono se conecta al sistema instalado en tu PC.',
            )}
          </p>
          <span className="installation-tag">{t('Acceso móvil')}</span>
        </article>
      </div>
      <div className="installation-note">
        <ShieldCheck size={18} />
        <p>
          {t(
            'Antes de instalar, HQ revisará contigo la compatibilidad de la PC, la conexión y la configuración de tu cuenta. La demo de esta web permite conocer la experiencia sin instalar el sistema.',
          )}
        </p>
      </div>
      <HardwareGuide />
      <CompatibilityGuide />
    </section>
  );
}

function CompatibilityGuide() {
  const { t } = useLanguage();
  return (
    <div className="compatibility-guide">
      <div className="compatibility-heading">
        <span className="eyebrow">{t('PLATAFORMA Y CONEXIÓN')}</span>
        <h3>{t('Prepara una configuración compatible.')}</h3>
        <p>
          {t(
            'NinjaTrader Desktop 8 es la base de HQ. El build instalado exacto no está acreditado. Este resumen refleja el documento de validación del 7 de septiembre de 2026; no es un estado en vivo.',
          )}
        </p>
      </div>
      <div className="compatibility-panel">
        <span className="compatibility-label">
          {t('ESTADO DE VALIDACIÓN · 07/09/2026')}
        </span>
        <ul>
          {[
            [
              'NinjaTrader Desktop 8 + NinjaScript',
              'Base confirmada · build exacto pendiente',
            ],
            [
              'Market Replay · NQ / MNQ',
              'Probado para investigación · sin ejecución real',
            ],
            [
              'Sim101 / Paper',
              'Validación parcial · forward completo pendiente',
            ],
            [
              'Broker / feed LIVE',
              'Ninguno aprobado por HQ · órdenes: ninguna',
            ],
          ].map(([name, type]) => (
            <li key={name}>
              <strong>{name}</strong>
              <span>{t(type)}</span>
            </li>
          ))}
        </ul>
        <p>
          {t(
            'LIVE permanece bloqueado. La compatibilidad oficial de un proveedor con NinjaTrader no equivale a aprobación por HQ. Cada conexión debe completar las pruebas de órdenes, protección, reconciliación y reconexión.',
          )}
        </p>
        <a
          href="https://ninjatrader.com/support/helpguides/nt8/data_by_provider.htm?utm_source=chatgpt.com"
          target="_blank"
          rel="noreferrer"
        >
          {t('Consultar proveedores documentados')}{' '}
          <ArrowRight size={15} aria-hidden="true" />
        </a>
      </div>
      <p className="compatibility-scope">
        {t(
          'El acceso de escritorio, tablet y teléfono está diseñado mediante una API privada; el móvil no conecta directamente con el broker. Su disponibilidad operativa debe revalidarse. TradingView es solo visual e investigación; el asistente es de solo lectura.',
        )}
      </p>
    </div>
  );
}

function HardwareGuide() {
  const { t } = useLanguage();
  return (
    <div className="hardware-guide">
      <div className="hardware-heading">
        <span className="eyebrow">{t('ELEGIR TU EQUIPO')}</span>
        <h3>
          {t('Un equipo dedicado.')}
          <br />
          {t('Una base para tu HQ.')}
        </h3>
        <p>
          {t(
            'Recomendamos un equipo Windows dedicado, con buena refrigeración, SSD y conexión por Ethernet. Estas configuraciones son una orientación para preparar HQ; su capacidad se confirma con la instalación y pruebas de carga reales.',
          )}
        </p>
      </div>
      <div className="hardware-options">
        <article>
          <span className="hardware-tier">{t('PUNTO DE PARTIDA')}</span>
          <h4>{t('Uso ligero')}</h4>
          <p>{t('Una instalación y seguimiento básico.')}</p>
          <dl>
            <div>
              <dt>CPU</dt>
              <dd>{t('Intel / AMD x64 moderno, 4 núcleos o más')}</dd>
            </div>
            <div>
              <dt>{t('Memoria')}</dt>
              <dd>{t('16 GB RAM')}</dd>
            </div>
            <div>
              <dt>{t('Almacenamiento')}</dt>
              <dd>{t('SSD NVMe de 512 GB')}</dd>
            </div>
          </dl>
          <small>
            {t(
              'La cantidad de gráficos, datos y procesos determina la capacidad disponible.',
            )}
          </small>
        </article>
        <article className="hardware-recommended">
          <span className="hardware-tier">{t('RECOMENDACIÓN PARA HQ')}</span>
          <h4>{t('Más margen')}</h4>
          <p>{t('Mini PC o desktop dedicado al sistema.')}</p>
          <dl>
            <div>
              <dt>CPU</dt>
              <dd>
                {t(
                  'Core i5 / Core Ultra 5 o Ryzen 5/7 reciente, 6 núcleos o más',
                )}
              </dd>
            </div>
            <div>
              <dt>{t('Memoria')}</dt>
              <dd>{t('32 GB RAM, ampliable')}</dd>
            </div>
            <div>
              <dt>{t('Almacenamiento')}</dt>
              <dd>{t('SSD NVMe de 1 TB')}</dd>
            </div>
          </dl>
          <small>
            {t(
              'Ethernet por cable, buena ventilación y respaldo eléctrico UPS recomendados.',
            )}
          </small>
        </article>
        <article>
          <span className="hardware-tier">{t('REPLAY E INVESTIGACIÓN')}</span>
          <h4>{t('Pruebas intensivas')}</h4>
          <p>{t('Más recursos para históricos y optimización.')}</p>
          <dl>
            <div>
              <dt>CPU</dt>
              <dd>{t('Procesador x64 moderno, 8 núcleos o más')}</dd>
            </div>
            <div>
              <dt>{t('Memoria')}</dt>
              <dd>{t('64 GB RAM recomendados')}</dd>
            </div>
            <div>
              <dt>{t('Almacenamiento')}</dt>
              <dd>{t('SSD NVMe de 2 TB y copia de respaldo')}</dd>
            </div>
          </dl>
          <small>
            {t(
              'Preferimos separar las pruebas pesadas del equipo destinado a la operación autorizada.',
            )}
          </small>
        </article>
      </div>
      <div className="hardware-basics">
        <p>
          <strong>{t('Windows y gráficos.')}</strong>{' '}
          {t(
            'Windows 11 de 64 bits, .NET Framework 4.8 y gráficos compatibles con DirectX 10 o superior. La prioridad de esta recomendación es CPU, RAM y SSD.',
          )}
        </p>
        <p>
          <strong>{t('Pantalla.')}</strong>{' '}
          {t(
            'Recomendamos 1920 × 1080 o más para trabajar cómodamente en desktop. Esa resolución corresponde al monitor; el teléfono adapta la interfaz a su pantalla.',
          )}
        </p>
        <p>
          <strong>{t('Uso desde Mac.')}</strong>{' '}
          {t(
            'Acceso a la interfaz web del sistema instalado en la PC Windows. La mini PC permite mantener ese sistema separado de tu equipo personal.',
          )}
        </p>
      </div>
      <p className="hardware-source">
        {t(
          'Orientación de hardware basada en la arquitectura prevista de HQ y en los',
        )}{' '}
        <a
          href="https://ninjatrader.com/support/helpGuides/nt8/minimum_system_requirements.htm"
          target="_blank"
          rel="noreferrer"
        >
          {t('requisitos oficiales de NinjaTrader')}
        </a>
        {t(
          '. NinjaTrader recomienda cuatro núcleos, 8 GB RAM y SSD; las configuraciones superiores de esta guía son nuestra propuesta de margen, no una certificación de Flip Flop para todas las cargas.',
        )}
      </p>
    </div>
  );
}

const conditions = [
  {
    title: 'Un acceso acorde a tu perfil',
    body: 'El acceso y los dispositivos se revisan con el propietario. Las funciones de familia y multiusuario están previstas para una fase posterior; no están disponibles como parte del acceso actual.',
  },
  {
    title: 'Ajustes personales y controles protegidos',
    body: 'Puedes personalizar la interfaz y los avisos. Activar operativa real, cambiar cuentas o rutas e incrementar límites requiere autorización del propietario. Los parámetros de la estrategia CONTROL permanecen protegidos.',
  },
  {
    title: 'Documentos antes de la activación',
    body: 'Antes de activar el sistema se revisan la cuenta, los documentos, los riesgos, el dispositivo y las condiciones comerciales. Un pago no habilita el trading automáticamente. El acuerdo está en revisión; recibirás su versión aprobada antes de firmar o activar.',
  },
  {
    title: 'Capital, reparto y cálculo de beneficios',
    body: 'El capital permanece en tu cuenta con el broker; HQ no tiene autorización para retirarlo. Las modalidades propuestas son 70/30 añadiendo US$700 a esa cuenta, o 50/50 sin añadir dinero. El acuerdo definirá la base de cálculo, los costes, los periodos y el tratamiento de pérdidas. El reparto no es una promesa de rentabilidad.',
  },
  {
    title: 'Facturación, avisos y suspensión',
    body: 'La facturación comercial corresponde a usuarios de pago, según las condiciones acordadas. La suspensión prevista bloquea nuevas operaciones sin retirar la protección de posiciones abiertas. El acuerdo fijará avisos, plazos y reactivación.',
  },
  {
    title: 'Qué puedes hacer hoy',
    body: 'Explora la demo y solicita información sobre acceso e instalación. Esta web no conecta con brokers, envía órdenes, cobra ni recoge firmas. HQ tiene LIVE bloqueado y ningún broker o feed aprobado; solicitar acceso no habilita operativa real.',
  },
];

export function AccessConditions() {
  const { t } = useLanguage();
  return (
    <section className="conditions-section wrap" id="condiciones">
      <div className="section-heading">
        <span className="eyebrow">{t('ANTES DE EMPEZAR')}</span>
        <h2>
          {t('Todo claro.')}
          <br />
          <span>{t('Desde el principio.')}</span>
        </h2>
        <p>
          {t(
            'Instalación, permisos y condiciones del modelo de acceso. Conoce qué necesitas y qué se revisa contigo antes de activar el sistema.',
          )}
        </p>
        <span className="conditions-status">
          {t('Acuerdo de cliente en revisión')}
        </span>
      </div>
      <div className="conditions-list">
        {conditions.map(({ title, body }) => (
          <details key={title}>
            <summary>
              {t(title)}
              <ChevronDown size={18} />
            </summary>
            <p>{t(body)}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
