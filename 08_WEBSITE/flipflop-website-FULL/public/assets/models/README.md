# Modelos 3D procedurales

No hay modelos GLB, FBX, OBJ o proyectos Blender en esta entrega porque no se crearon ni se usaron. El 3D se reconstruye con:

- `src/app/earth-scene.tsx`: SphereGeometry, geometría de velas redondeadas, grupos, cámara, materiales y shaders.
- `public/assets/earth-blue-marble.jpg`: superficie NASA.
- `public/assets/earth-night-2016.jpg`: luces nocturnas NASA.
- `public/assets/earth-clouds.jpg`: nubes de Solar System Scope.
- `src/app/world-atmosphere.ts` y `world-journey.ts`: campos y movimiento por scroll.

Esos archivos son el modelo y la escena editables. Para exportar un GLB se necesitaría un trabajo adicional; un GLB estático tampoco sustituiría el shader y la lógica de animación.
