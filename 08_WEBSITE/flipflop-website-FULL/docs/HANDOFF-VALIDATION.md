# Validación de la entrega FULL

Fecha: 7 de septiembre de 2026. Fuente original: f535ab92a3a291c8a902f0f4a14fa24c9c6ec67d.

- Fuente versionada original: 114 archivos presentes y copia exacta en source-published-v17.zip.
- Bundle Git: completo, 18 commits; verificación de Git pasó.
- Estructura src/: TypeScript y build de producción pasaron.
- Dependencias: lockfile idéntico al original. Para la validación se reutilizó la instalación existente mediante una unión local temporal; node_modules no está en la entrega. No se afirmó una instalación limpia en otro equipo.
- Seis suites de pruebas pasaron: chart automático, 3.636 estados de simulación, 576 dibujos, seis idiomas, estado de idioma, pausas/limpieza y continuidad de escenas.
- Worker local de la copia: / y /demo devolvieron 200, no-store y 18 referencias CSS/JS funcionales por ruta.
- 41 recursos de medios, fuentes y créditos servidos con bytes idénticos a los archivos fuente.
- Los documentos de handoff, el mapa de archivos y los enlaces locales se comprobaron.
- No se incluyeron node_modules, archivos .env reales, credenciales, sesiones ni cachés locales. Se revisaron patrones de credenciales en el texto exportado y la fuente original.
- El archivo original de despliegue contiene Worker y metadatos de hosting.
- La entrega conserva todos los recursos públicos, 32 referencias aportadas y 538 capturas del vídeo.

El ZIP se verificó con CRC y cada archivo se compara con el MANIFEST.json. El hash del ZIP está en el archivo SHA256 adyacente. Al editar archivos, su hash cambiará de forma esperada.

Límites: esta revisión no vuelve a certificar Safari/iOS ni una instalación nueva de dependencias. La guía visual y las adaptaciones de fuente se entregan como código editable; el website publicado no se alteró durante el empaquetado. El bot operativo de NinjaTrader no forma parte del repositorio web.
