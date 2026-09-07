# Flip Flop HQ — WEBSITE FULL

Entrega completa del website comercial y su demo ilustrativa. Diseño oscuro, identidad roja/verde, Tierra NASA en 3D, animaciones y seis idiomas. Basado en la versión publicada 17, commit `f535ab92a3a291c8a902f0f4a14fa24c9c6ec67d`.

**Empieza aquí:** [HANDOFF.md](HANDOFF.md) · [Diseño visual](design/brand-board.html) · [Arquitectura](docs/ARCHITECTURE.md) · [Despliegue](deploy-notes.md) · [Vídeo](video/FlipFlop-HQ-recorrido.mp4).

## Correr localmente

Requiere Node.js 22.13 o posterior, npm y una conexión a Internet para la primera instalación de dependencias. Usa una versión de Node compatible con el lockfile; no actualices paquetes para hacer la primera reproducción.

```powershell
cd flipflop-website-FULL
npm ci
npm run dev
```

Abre la URL local que imprima Vinext, normalmente `http://localhost:3000`. Si ese puerto está ocupado, usa el puerto indicado por el servidor. En Windows también puedes ejecutar `START-LOCAL.cmd`.

La web no requiere NinjaTrader, cuenta de broker, API keys ni credenciales de correo. Las fuentes, imágenes y texturas se incluyen localmente. `npm ci` instala las dependencias exactas del lockfile; `node_modules` no va dentro de la entrega.

## Comprobar y compilar

```powershell
npm run typecheck
npm test
npm run build
npm start -- --port 4177
```

En otra terminal, desde esta carpeta:

```powershell
npm run test:delivery
```

La última prueba usa `http://127.0.0.1:4177`, comprueba ambas rutas y sus archivos CSS/JS. `npm start` ejecuta el emulador local de Workers: no publica el sitio. Cierra ese proceso antes de volver a compilar en Windows para evitar archivos bloqueados.

Para comprobar que el paquete extraído está intacto, antes de editarlo:

```powershell
npm run verify:files
```

## Estructura

```text
flipflop-website-FULL/
├─ src/
│  ├─ app/                 Rutas, diseño, estado, 3D, animación, demo e idiomas
│  ├─ components/ui/       Biblioteca completa de componentes del proyecto
│  ├─ hooks/               Hooks compartidos
│  └─ lib/                 Utilidades
├─ public/
│  ├─ assets/              Imágenes, logos, texturas y fuentes locales
│  │  ├─ fonts/            Geist, Manrope y Geist Mono
│  │  └─ models/           Guía de geometría procedural y código 3D
│  └─ ...                  Copias de compatibilidad para las URLs publicadas
├─ brand/                  Logo aprobado, componentes y variantes históricas
├─ design/                 Guía visual, tokens e inventario de assets
├─ video/                  MP4, capítulos, 538 capturas y herramientas de edición
├─ docs/                   Arquitectura, funcionamiento, QA y continuación
├─ references/             Referencias que enviaste y documento de conexión
├─ tests/                  Pruebas de simulación, idiomas, movimiento y escenas
├─ scripts/                Ejecución de pruebas y verificación de entrega
├─ licenses/               Créditos, licencias e inventario de dependencias
├─ history/                Fuente exacta publicada y toda la historia Git disponible
├─ deploy/                 Archivo de la publicación v17, como respaldo
├─ provenance/             Correspondencia con la fuente original
├─ .openai/hosting.json    Identificador y configuración del Site existente
├─ package.json
├─ package-lock.json
├─ README.md
├─ HANDOFF.md
├─ deploy-notes.md
├─ MANIFEST.json           Tamaño y SHA-256 de cada archivo entregado
└─ TREE.txt                Esqueleto completo de archivos
```

## Qué entrega este sistema

El sistema completo construido **en esta conversación** es el website, sus visuales, sus maquetas y el chart de demostración. El formulario prepara un correo para `cjar292@gmail.com`; el visitante termina de enviarlo en su aplicación de correo. No existe un backend SMTP, base de datos de leads, checkout, alta de usuarios, firma contractual o ejecución de órdenes.

El software NinjaTrader/Guardian/Bridge instalado en otras carpetas no forma parte de este website ni fue construido aquí. Su estado documental y las fronteras de integración están en [SYSTEM-BOUNDARY.md](docs/SYSTEM-BOUNDARY.md). El material aportado por ti se conserva como referencia, no como prueba de ejecución actual.

## Conservación del original

La fuente principal se organizó bajo `src/`; las fuentes tipográficas se hicieron locales. Los imports y las rutas de configuración se ajustaron para esta estructura. Las dependencias y el lockfile se conservaron. Las copias de assets en la raíz de `public/` mantienen las URLs originales.

`history/source-published-v17.zip` contiene exactamente los archivos versionados del commit publicado, sin esas adaptaciones. `history/website-history.bundle` conserva las 18 revisiones disponibles. No incluye credenciales, sesiones, `.env` reales ni `node_modules`.
