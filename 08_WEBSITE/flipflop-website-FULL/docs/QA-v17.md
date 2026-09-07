# Flip Flop HQ · entrega y revisión

7 de septiembre de 2026 · versión 17

[Website actualizado](https://flipflop-hq-astral.cjar2000.chatgpt.site/) · [Demo automática](https://flipflop-hq-astral.cjar2000.chatgpt.site/demo)

## Cambios

- Demo con un único chart automático de precios sintéticos. Repite ejemplos Long/Short con TP y SL, cierre visible, transición suave y una pausa accesible. Se retiraron las pestañas de preparación y acuerdo de ejemplo.
- Nombre en Geist, con tamaño, peso y espaciado refinados. FLIP verde, FLOP rojo, H roja y Q verde. Los textos y las velas comparten verde `#62b676` y rojo `#f14234`; los botones conservan las bases de marca `#2a7d3c` y `#dd281c`.
- Acento rojo de «órbita» unido correctamente al carácter. Pausa táctil de 44 × 44 px. Menos velas históricas en pantallas pequeñas para mejorar la lectura.
- Tierra NASA, fondo negro, humo y composición existentes conservados.

## Verificación realizada

| Área | Resultado |
|---|---|
| Seis vistas de desktop y tres vistas de la maqueta de teléfono | Cambian correctamente |
| Navegación, enlaces a demo, accesos al formulario y seis desplegables de condiciones | Verificados en navegador |
| Español, inglés, portugués, francés, italiano y alemán | Cambio y contenido verificados; sin desbordamiento horizontal en las comprobaciones de desktop y móvil |
| Selector de idioma por teclado y persistencia al recargar | Verificados |
| Modalidades 50/50 y 70/30 | Cambian y se incorporan al borrador de solicitud |
| Formulario | Campos requeridos, datos de ejemplo, motivo, reconocimiento, borrador, copia y cierre por Escape verificados |
| Pausa del chart y pausa global | Precio estable en pausa y continuación al reanudar |
| Pantallas de 320, 390, 768, 1024 y 1440 px | Comprobaciones de adaptación realizadas; sin desbordamiento de página en los casos registrados |
| Consola del navegador durante el recorrido | Sin errores registrados |
| Motor de la simulación | 3.636 estados y 576 dibujos en cuatro tamaños comprobados |
| Movimiento | Ciclos TP/SL, pausa al salir de pantalla, pestaña oculta, movimiento reducido y limpieza comprobados por pruebas del componente |
| Traducciones y correo preparado | 374 mensajes por idioma; composición verificada para ambas modalidades en seis idiomas |
| TypeScript, lint y compilación | Pasaron |
| Entrega publicada | `/` y `/demo` responden correctamente; sus 18 referencias CSS/JS por página cargan; HTML con `no-store` para evitar referencias antiguas tras publicar |

## Vídeo

`FlipFlop-HQ-recorrido.mp4`: aproximadamente 1:52, 1440 × 984, H.264, 32 capítulos visibles. Recorrido del website y su demo mediante capturas reales sucesivas del navegador, con esperas entre acciones abreviadas. La exportación es a 30 fps; la captura tiene frecuencia variable y no constituye una medición del rendimiento de la web. No lleva audio. Los capítulos también están en `FlipFlop-HQ-capitulos.json`.

El vídeo muestra portada, vistas de desktop y de la maqueta de teléfono, requisitos, modalidades, solicitud, condiciones, idiomas y chart automático. Las pruebas de tamaños móviles se realizaron aparte de este recorrido de escritorio.

## Alcance

Se revisó el website y su demo ilustrativa, no la aplicación de trading instalada. No se enviaron correos, no se firmaron acuerdos ni se cursaron órdenes. Safari/iOS y Firefox reales no se ejecutaron; las comprobaciones de tamaños se hicieron en el navegador Chromium disponible. Las pruebas registradas no garantizan ausencia de fallos en cualquier dispositivo o situación.

Publicación con el acceso privado existente. Commit: `f535ab92a3a291c8a902f0f4a14fa24c9c6ec67d`.
