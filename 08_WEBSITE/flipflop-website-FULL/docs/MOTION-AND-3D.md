# Movimiento, 3D y calidad

La Tierra y las velas son geometría procedural de Three.js. **No existe un archivo Blender, GLB, FBX u OBJ fuente**: el modelo reproducible está en `src/app/earth-scene.tsx`, sus shaders y las tres texturas. `public/assets/models/README.md` explica dónde modificarlo.

La cámara inicial usa FOV 39 y zoom 1.72 en close-up. La Tierra se sombrea combinando superficie diurna, mapa nocturno y nubes. Las imágenes son mapas archivados, no una transmisión de satélite en directo. La geometría de las velas orbitales y sus cambios se calcula en código.

`world-journey.ts` calcula la transición de siete zonas del recorrido. Mantiene el producto legible antes de introducir la secuencia espacial. `world-atmosphere.ts` dibuja la capa de partículas/números y `smoke-atmosphere.tsx` complementa el humo. La composición final está coordinada desde `page.tsx` y CSS.

`createMotionLoop` concentra requestAnimationFrame, límite de frecuencia, IntersectionObserver, visibilidad de pestaña y preferencia de movimiento reducido. Conserva las funciones de dispose al modificar escenas. Nunca dejes varios bucles activos al desmontar un componente.

El chart de la demo dibuja con Canvas y densidad de píxel limitada a 2. El bucle apunta a un máximo de 60 actualizaciones por segundo; el estado textual de React se actualiza a menor frecuencia. Esto no garantiza 60 fps en todos los equipos. En móvil se muestran menos velas históricas, conservando el mismo escenario y niveles.

Cada ciclo automático dura 26 segundos: 22 de recorrido, cierre visible y transición. Alterna Long/TP, Short/SL, Short/TP y Long/SL. La interfaz activa usa NQ; otros instrumentos definidos en el motor son presets ilustrativos conservados y probados, no conexiones aprobadas ni datos de mercado reales. Los colores de TP, SL y velas se coordinan con la marca.

Pruebas de regresión: `npm test`. Para rendimiento real, medir en los dispositivos objetivo, con WebGL activo/inactivo, cambio de pestaña, reducción de movimiento y redes lentas. La Tierra tiene carga diferida; preserve la entrada con logo y las salidas seguras si WebGL no está disponible.
