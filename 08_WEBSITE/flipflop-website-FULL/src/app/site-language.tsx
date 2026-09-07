'use client';

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import { Check, ChevronDown, Globe2 } from 'lucide-react';
import spanish from './locales/es.json';

export const languages = {
  es: 'Español',
  en: 'English',
  pt: 'Português',
  fr: 'Français',
  it: 'Italiano',
  de: 'Deutsch',
} as const;
export type Locale = keyof typeof languages;
type Dictionary = Record<string, string>;
const loaders: Record<
  Exclude<Locale, 'es'>,
  () => Promise<{ default: Dictionary }>
> = {
  en: () => import('./locales/en.json'),
  pt: () => import('./locales/pt.json'),
  fr: () => import('./locales/fr.json'),
  it: () => import('./locales/it.json'),
  de: () => import('./locales/de.json'),
};
const isLocale = (value: string | null): value is Locale =>
  value !== null && Object.hasOwn(languages, value);
const LanguageContext = createContext({
  locale: 'es' as Locale,
  busy: false,
  error: false,
  setLocale: (_locale: Locale) => {},
  t: (source: string) => source,
});
const initial = {
  locale: 'es' as Locale,
  dictionary: spanish as Dictionary,
  busy: false,
  error: false,
};
let snapshot = initial,
  revision = 0,
  restored = false;
const listeners = new Set<() => void>();
const getSnapshot = () => snapshot;
const getServerSnapshot = () => initial;
function publish(next: typeof initial) {
  snapshot = next;
  listeners.forEach((listener) => listener());
}
async function selectLocale(locale: Locale, persist = true) {
  const id = ++revision;
  publish({ ...snapshot, busy: true, error: false });
  try {
    const dictionary =
      locale === 'es' ? spanish : (await loaders[locale]()).default;
    if (id !== revision) return;
    publish({ locale, dictionary, busy: false, error: false });
    if (persist) {
      try {
        localStorage.setItem('hq-website-language', locale);
      } catch {
        /* Selection works without storage. */
      }
    }
  } catch {
    if (id === revision) publish({ ...snapshot, busy: false, error: true });
  }
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  if (!restored) {
    restored = true;
    queueMicrotask(() => {
      try {
        const saved = localStorage.getItem('hq-website-language');
        if (isLocale(saved) && saved !== snapshot.locale)
          void selectLocale(saved, false);
      } catch {
        /* Use the default if storage is unavailable. */
      }
    });
  }
  return () => {
    listeners.delete(listener);
  };
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  useEffect(() => {
    const previous = document.documentElement.lang;
    const title = document.title;
    document.documentElement.lang = state.locale;
    document.title =
      'Flip Flop HQ — ' +
      (state.dictionary['Tu trading. En otra órbita.'] ??
        'Tu trading. En otra órbita.');
    return () => {
      document.documentElement.lang = previous;
      document.title = title;
    };
  }, [state]);
  const value = useMemo(
    () => ({
      locale: state.locale,
      busy: state.busy,
      error: state.error,
      setLocale: (locale: Locale) => {
        void selectLocale(locale);
      },
      t: (source: string) => state.dictionary[source] ?? source,
    }),
    [state],
  );
  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

export function LanguageSelector() {
  const { locale, busy, error, setLocale, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const element = root.current;
    if (!open || !element) return;
    const button = trigger.current;
    element.querySelector<HTMLButtonElement>('[aria-pressed="true"]')?.focus();
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !element.contains(event.target))
        setOpen(false);
    };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(false);
        button?.focus();
        return;
      }
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
      const options = Array.from(
        element.querySelectorAll<HTMLButtonElement>('[data-language]'),
      );
      const index = options.findIndex(
        (option) => option === document.activeElement,
      );
      const next =
        event.key === 'Home'
          ? 0
          : event.key === 'End'
            ? options.length - 1
            : (index + (event.key === 'ArrowDown' ? 1 : -1) + options.length) %
              options.length;
      event.preventDefault();
      options[next]?.focus();
    };
    const leave = (event: FocusEvent) => {
      if (
        event.relatedTarget instanceof Node &&
        !element.contains(event.relatedTarget)
      )
        setOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    element.addEventListener('keydown', keyboard);
    element.addEventListener('focusout', leave);
    return () => {
      document.removeEventListener('pointerdown', outside);
      element.removeEventListener('keydown', keyboard);
      element.removeEventListener('focusout', leave);
    };
  }, [open]);
  return (
    <div className="language-control" ref={root}>
      <button
        type="button"
        className="language-selector"
        ref={trigger}
        aria-label={t('Idioma del website') + ': ' + languages[locale]}
        aria-expanded={open}
        aria-controls="website-languages"
        aria-busy={busy}
        onClick={() => setOpen(!open)}
      >
        <Globe2 size={15} aria-hidden="true" />
        <span className="language-code">
          {busy ? '…' : locale.toUpperCase()}
        </span>
        <ChevronDown
          className="language-chevron"
          size={11}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="language-menu" id="website-languages">
          <span className="language-menu-title">{t('Idioma del website')}</span>
          <ul>
            {(Object.keys(languages) as Locale[]).map((code) => (
              <li key={code}>
                <button
                  data-language=""
                  type="button"
                  disabled={busy}
                  aria-pressed={locale === code}
                  lang={code}
                  onClick={() => {
                    setLocale(code);
                    setOpen(false);
                    trigger.current?.focus();
                  }}
                >
                  <span className="language-option-code">
                    {code.toUpperCase()}
                  </span>
                  <span>{languages[code]}</span>
                  {locale === code && <Check size={15} aria-hidden="true" />}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <output className={error ? 'language-error' : 'sr-only'}>
        {error
          ? t('No se pudo cargar el idioma. Inténtalo de nuevo.')
          : busy
            ? t('Cargando idioma')
            : languages[locale]}
      </output>
    </div>
  );
}
