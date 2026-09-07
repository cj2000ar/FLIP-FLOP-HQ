# Deployment notes

## Publicación existente

- URL: https://flipflop-hq-astral.cjar2000.chatgpt.site/
- Project ID: `appgprj_6a9eaadb02e8819187a9633c2a0dd075`
- Versión base publicada: 17.
- Commit original: `f535ab92a3a291c8a902f0f4a14fa24c9c6ec67d`.
- Acceso comprobado durante la entrega anterior: privado del propietario. El ZIP no cambia acceso ni vuelve a publicar.
- `deploy/published-v17.tar.gz` es un respaldo del archivo existente; la fuente original está en `history/source-published-v17.zip`.

## Compilar esta estructura

```sh
npm ci
npm run typecheck
npm test
npm run build
```

El build produce `dist/server/index.js`, la configuración generada del Worker y `dist/client/`. Esto **no es un export de HTML estático**. No publiques solo la carpeta `public/` ni arrastres el ZIP completo a un hosting estático.

## Sites

La configuración `.openai/hosting.json` identifica el Site original. Para continuar ese Site, usa la misma cuenta/proyecto y las herramientas nativas de Sites. Guarda los cambios en el repositorio configurado, publica el commit completo y construye el archivo desde ese mismo estado. Después guarda una versión y despliega con la audiencia autorizada. Una copia destinada a otro propietario necesita su propio registro de Site; no reutilices el ID original como si fuera suyo.

El flujo del agente propietario usa `sites_create_source_repository_write_credential`, `sites_save_site_version` y la operación de despliegue correspondiente al acceso. No hay tokens exportados. La credencial temporal se pasa por comando, no se escribe en el repositorio.

Para empaquetar con Sites, utiliza el `scripts/package-site.sh` de la instalación del plugin Sites con la raíz de este proyecto y la ruta de salida. Ese helper es una herramienta del entorno de publicación, no una dependencia del website.

## Otros proveedores

La salida actual está preparada para Cloudflare Workers mediante Vinext y `@cloudflare/vite-plugin`. Un desarrollador puede configurar su propia cuenta Worker, revisar la configuración generada y la integración `@openai/sites-vite-plugin`, y validar allí antes de publicar. No se ha certificado una migración directa a Vercel, Netlify, un servidor Node genérico o un hosting de archivos. El sistema comercial no requiere D1 ni R2 actualmente.

## Regla de caché que no se debe perder

`/` y `/demo` devuelven `Cache-Control: no-store, must-revalidate` desde `next.config.ts`. Evita que HTML antiguo solicite hashes de CSS/JS que ya no existen después de una publicación. Mantén los archivos estáticos versionados por contenido y publica el build completo de forma consistente. No fuerces caché persistente de HTML en una capa CDN que ignore esta regla.

## Validación después de publicar

```powershell
$env:HQ_ORIGIN='https://tu-sitio.example'
npm run test:delivery
```

En Sites privado, la prueba puede necesitar un token vigente en `HQ_CHECK_TOKEN`; la herramienta lo envía como `OAI-Sites-Authorization: Bearer ...`. No lo copies a `.env.example`, documentos, capturas ni Git. No hace falta este token para la prueba local.

Comprueba también imágenes/fuentes, la entrada con el logo, el paso a la Tierra, idiomas, modal y demo. La preparación de correo no prueba entrega SMTP: el sitio no tiene un servidor de correo. Revisa móvil/tablet y movimiento reducido en los navegadores objetivo.

## Restaurar

Para volver al estado publicado exacto, extrae `history/source-published-v17.zip` en una carpeta nueva, instala con su lockfile y compila. Para inspeccionar cualquier revisión anterior, clona el bundle en otra carpeta. No reemplaces un checkout con cambios sin guardarlos antes.
