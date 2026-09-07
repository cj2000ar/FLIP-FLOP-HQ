# Sistema visual — Flip Flop HQ

Abrir `brand-board.html` para el tablero de marca. Fuente ejecutable de estilo: `src/app/globals.css`, `product-showcase.css`, `brand-palette.css` y `fonts.css`. Tokens de consulta en `tokens.json`; inventario completo en `assets.json`.

## Identidad

`brand/current/logo.png` y `FlipFlop-HQ-Logo-Trading.png` son el símbolo aprobado, idéntico al activo `flipflop-hq-mark-v4.png`. Es un PNG generado sobre fondo negro. No se creó un original vectorial editable; el nombre se renderiza como texto en React y permanece nítido a distintas escalas. El favicon SVG heredado se conserva solo como parte del archivo; el metadato activo usa el PNG v4.

Colores: fondo `#000000`; superficie `#090909`; verde base `#2a7d3c`; rojo base `#dd281c`; verde para texto/velas `#62b676`; rojo para texto/velas `#f14234`. FLIP y Q verdes; FLOP y H rojas. Los tonos de tinta levantan la legibilidad sobre negro sin introducir otra identidad.

Geist para el nombre y la interfaz; Manrope para titulares; Geist Mono para cifras. El nombre principal usa 24 px, peso 680 y tracking -0.035em en desktop, con ajustes compactos en CSS. No rasterizar el nombre junto al icono para usarlo como único archivo pequeño en todas las vistas.

## Composición

Hero de texto a la izquierda y Tierra nocturna amplia a la derecha. Fondo oscuro, humo contenido, blanco limpio en el texto. CTAs: conocer HQ en verde; explorar en rojo. Bordes finos y estados hover/focus moderados. Laptop y teléfono con volumen contenido, no una simulación de un sistema operativo completo.

El símbolo ya tiene margen negro. No añadir otro cuadrado brillante, bisel, reciclaje o resplandor. Las variantes de `brand/history/` documentan la evolución: no todas fueron aprobadas. En especial Clean/v3 fue rechazado; no seleccionarlo por su nombre de archivo.

## Assets

Los 12 archivos de `public/` se conservan también en `public/assets/`. Las rutas raíz evitan romper referencias del sitio publicado. Los assets históricos —Saturno, logos anteriores y fotografías antiguas— se incluyen para completar el handoff, pero no todos aparecen en la experiencia actual. Revisar el campo `active` de `assets.json`.

El material de `references/user/` es inspiración y feedback aportado por el propietario. No es una biblioteca nueva de imágenes aprobadas para publicación. Conserva las licencias de nubes/fuentes y los créditos NASA en cualquier distribución que use esos recursos.
