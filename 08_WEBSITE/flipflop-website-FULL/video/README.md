# Vídeo y material editable

`FlipFlop-HQ-recorrido.mp4` es el recorrido entregado: aproximadamente 1:52, H.264, 1440 × 984, sin audio. Incluye portada, vistas de laptop y maqueta de teléfono, requisitos, modalidades, solicitud, condiciones, idiomas y chart. Los 32 capítulos están en `FlipFlop-HQ-capitulos.json`.

`recording/` contiene las 538 capturas reales usadas. Son capturas sucesivas del navegador; el vídeo abrevia esperas entre acciones. La exportación es a 30 fps, pero la captura es de frecuencia variable. No es una prueba de rendimiento ni una grabación del sistema NinjaTrader.

Para volver a renderizarlo con Python:

```sh
python -m pip install -r video/tools/requirements.txt
python video/tools/render-video.py
```

El render escribe el MP4 y el índice de capítulos en esta carpeta, y usa `.video-build/` en la raíz para archivos temporales. Guarda una copia si editas los títulos, tiempos o imágenes y quieres conservar el vídeo original. El script `export-tour-original.py` conserva el método original y sus rutas históricas; usa `render-video.py` para esta estructura portable.
