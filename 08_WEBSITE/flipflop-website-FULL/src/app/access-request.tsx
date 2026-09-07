'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Check, Copy, Mail, Monitor, X } from 'lucide-react';
import { useLanguage } from './site-language';
import Brand from './brand';

export default function AccessRequest({
  open,
  onClose,
  split,
  onSplitChange,
}: {
  open: boolean;
  onClose: () => void;
  split: 50 | 70;
  onSplitChange: (split: 50 | 70) => void;
}) {
  const { t } = useLanguage();
  const dialog = useRef<HTMLDialogElement>(null);
  const [prepared, setPrepared] = useState(false);
  const [copyState, setCopyState] = useState('Copiar solicitud');
  const [draft, setDraft] = useState('');
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (!open) {
      if (element.open) element.close();
      return;
    }
    if (!element.open) element.showModal();
    const before = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const dismiss = (event: MouseEvent) => {
      if (event.target !== element) return;
      const rect = element.getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      )
        element.close();
    };
    element.addEventListener('click', dismiss);
    return () => {
      document.body.style.overflow = before;
      element.removeEventListener('click', dismiss);
    };
  }, [open]);
  function submit(form: HTMLFormElement) {
    const data = new FormData(form);
    const text = (field: string) => {
      const value = data.get(field);
      return typeof value === 'string' ? value.trim() : '';
    };
    const plan = t(
      split === 70
        ? '70% cliente / 30% HQ · Añadiendo US$700 a mi cuenta'
        : '50% cliente / 50% HQ · Sin añadir dinero para empezar',
    );
    const message = [
      t('Hola Flip Flop HQ,'),
      '',
      t('Quiero solicitar información y acceso a la app.'),
      '',
      t('Nombre') + ': ' + text('name'),
      t('Correo de contacto') + ': ' + text('email'),
      t('Experiencia') + ': ' + text('experience'),
      t('PC con Windows') + ': ' + text('pc'),
      t('Modalidad de interés') + ': ' + plan,
      '',
      t('Mi motivo para solicitar acceso') + ':',
      text('reason'),
      '',
      t(
        'Entiendo que el sistema necesita una PC con Windows, que la activación requiere revisión y que el trading no garantiza beneficios. Quisiera conocer las condiciones finales y los próximos pasos.',
      ),
    ].join('\n');
    setDraft(message);
    const href =
      'mailto:cjar292@gmail.com?subject=' +
      encodeURIComponent(t('Solicitud de acceso · Flip Flop HQ')) +
      '&body=' +
      encodeURIComponent(message);
    setPrepared(true);
    setCopyState('Copiar solicitud');
    window.location.href = href;
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(draft);
      setCopyState('Solicitud copiada');
    } catch {
      setCopyState('Selecciona el texto de abajo');
    }
  }
  return (
    <dialog
      ref={dialog}
      className="access-dialog"
      aria-labelledby="request-title"
      onCancel={onClose}
      onClose={onClose}
    >
      <div className="request-shell">
        <div className="request-top">
          <Brand compact />
          <button
            type="button"
            className="request-close"
            aria-label={t('Cerrar solicitud')}
            onClick={onClose}
          >
            <X size={19} />
          </button>
        </div>
        <span className="eyebrow">{t('EL PRIMER PASO ES CONOCERNOS')}</span>
        <h2 id="request-title">
          {t('Tu acceso a HQ')}
          <br />
          {t('empieza aquí.')}
        </h2>
        <p className="request-intro">
          {t(
            'Cuéntanos un poco sobre ti. HQ revisará contigo la instalación, tu modalidad y las condiciones antes de activar el acceso.',
          )}
        </p>
        <div className="request-requirement">
          <Monitor size={20} />
          <p>
            <strong>{t('Necesitas una PC con Windows.')}</strong>
            <span>
              {t(
                'Después podrás consultar HQ desde Mac, Windows y móvil con tu acceso autorizado.',
              )}
            </span>
          </p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit(event.currentTarget);
          }}
          onChange={() => setPrepared(false)}
        >
          <div className="request-fields">
            <label>
              {t('Tu nombre')}
              <input
                autoComplete="name"
                name="name"
                required
                minLength={2}
                maxLength={80}
                placeholder={t('Cómo te llamas')}
              />
            </label>
            <label>
              {t('Tu correo')}
              <input
                type="email"
                autoComplete="email"
                name="email"
                required
                maxLength={140}
                placeholder={t('nombre@correo.com')}
              />
            </label>
          </div>
          <div className="request-fields">
            <label>
              {t('Experiencia en trading')}
              <select name="experience" required defaultValue="">
                <option value="" disabled>
                  {t('Selecciona una opción')}
                </option>
                <option>{t('Estoy empezando')}</option>
                <option>{t('Tengo conocimientos básicos')}</option>
                <option>{t('Ya opero y conozco los riesgos')}</option>
              </select>
            </label>
            <label>
              {t('¿Tienes una PC con Windows?')}
              <select name="pc" required defaultValue="">
                <option value="" disabled>
                  {t('Selecciona una opción')}
                </option>
                <option>{t('Sí, tengo una PC disponible')}</option>
                <option>{t('Tengo Mac y necesito orientación')}</option>
                <option>{t('Aún no, quiero conocer los requisitos')}</option>
              </select>
            </label>
          </div>
          <label>
            {t('Modalidad de interés')}
            <select
              name="plan"
              value={split}
              onChange={(event) =>
                onSplitChange(Number(event.target.value) as 50 | 70)
              }
            >
              <option value={50}>{t('50 / 50 · Sin añadir dinero')}</option>
              <option value={70}>
                {t('70 / 30 · Añadiendo $700 a tu cuenta')}
              </option>
            </select>
          </label>
          <label>
            {t('¿Por qué quieres acceder a Flip Flop HQ?')}
            <textarea
              name="reason"
              required
              minLength={15}
              maxLength={1200}
              rows={4}
              placeholder={t(
                'Cuéntanos qué conoces de trading, qué te interesa de HQ y qué te gustaría consultar.',
              )}
            />
          </label>
          <label className="request-acknowledgment">
            <input name="understood" type="checkbox" required />
            <span>
              {t(
                'Entiendo que esto es una solicitud de información. El acceso requiere revisión, una PC configurada y condiciones acordadas. El trading implica riesgo y no garantiza beneficios.',
              )}
            </span>
          </label>
          <button className="request-submit" type="submit">
            {t('Continuar por correo')}
            <ArrowUpRight size={18} />
          </button>
          <p className="request-delivery">
            <Mail size={14} />
            <span>
              {t('Se abrirá tu correo con el mensaje para')}{' '}
              <strong>cjar292@gmail.com</strong>
              {t(
                '. Revisa la solicitud y pulsa Enviar allí. No se realiza ningún cobro ni firma desde esta web.',
              )}
            </span>
          </p>
        </form>
        {prepared && (
          <output className="request-prepared">
            <Check size={18} />
            <div>
              <strong>{t('Solicitud preparada.')}</strong>
              <p>
                {t(
                  'Completa el envío en tu aplicación de correo. Si no se abrió, copia el mensaje y envíalo a cjar292@gmail.com.',
                )}
              </p>
              <button type="button" onClick={copy}>
                <Copy size={14} />
                {t(copyState)}
              </button>
              <details>
                <summary>{t('Ver el mensaje preparado')}</summary>
                <textarea
                  readOnly
                  aria-label={t('Texto de la solicitud')}
                  value={draft}
                  rows={7}
                />
              </details>
            </div>
          </output>
        )}
      </div>
    </dialog>
  );
}
