# Handoff — continuar sin perder el rumbo

## Resultado aprobado

Website para presentar y vender el acceso a Flip Flop HQ. El visitante conoce el producto, entiende la instalación en PC, revisa modalidades y prepara una solicitud. Las maquetas y el chart explican la experiencia; no son la app operativa ni indicadores de rentabilidad.

## Decisiones que se conservan

- Fondo negro puro, paneles negros discretos, relieve contenido, tipografía clara y espacio para respirar.
- Marca actual: símbolo de dos trayectorias de mercado. **No volver al reciclaje, a las letras FF dentro del icono ni al emblema plástico.**
- FLIP verde; FLOP rojo; H roja; Q verde. Colores exactos en `design/tokens.json` y `src/app/brand-palette.css`.
- Planeta nocturno con mapas NASA, grande y desplazado lateralmente. Zoom inicial de cámara 1.72; conservarlo al redimensionar. Rotación lenta y velas orbitales.
- Entrada con el logo sobre la atmósfera, seguida por la Tierra. El Saturno antiguo se conserva como archivo histórico, pero no debe volver como pantalla de carga.
- Transición de mundo 3D después de la presentación de la app. No cubrir la laptop, el teléfono o el texto con las capas de fondo.
- Simulación actual: solo chart automático, TP/SL y pausa. No recuperar las pestañas de preparación o acuerdo de ejemplo retiradas.
- Español, inglés, portugués, francés, italiano y alemán para el website.
- 50/50 sin añadir dinero; 70/30 al añadir US$700 a la cuenta de trading. Los US$700 no son el precio de la aplicación.
- PC Windows para instalar el sistema; acceso web desde dispositivos autorizados según validación. El Mac/teléfono no sustituye el nodo Windows.
- Contacto comercial: cjar292@gmail.com. El usuario revisa y envía el correo desde su cliente.

## Archivos de entrada para otro desarrollador

1. `src/app/page.tsx`: secuencia de secciones y conexiones entre componentes.
2. `src/app/globals.css` y `product-showcase.css`: composición y responsive.
3. `src/app/brand.tsx`, `brand-palette.css`, `fonts.css`: identidad.
4. `src/app/earth-scene.tsx`, `world-journey.ts`, `world-atmosphere.ts`: escena y progresión por scroll.
5. `src/app/trade-simulator.tsx`, `trade-simulation.ts`: reproducción ilustrativa.
6. `src/app/access-request.tsx` y `access-details.tsx`: solicitud y condiciones informativas.
7. `src/app/site-language.tsx` y `locales/`: internacionalización.

Lee `docs/QA-v17.md` para las pruebas anteriores y `docs/HANDOFF-VALIDATION.md` para la comprobación de esta entrega organizada. Las credenciales de publicación se obtienen por el mecanismo del hosting, nunca desde este ZIP.

## Pendientes reales

El website no implementa correo servidor, CRM, checkout, firma, sesiones de usuario ni conexión con NinjaTrader. Añadir cualquiera de esas funciones requiere especificación e implementación independiente. No reutilices las cifras simuladas como datos reales. Mantén la distinción entre compatibilidad de NinjaTrader, prueba HQ y aprobación HQ.
