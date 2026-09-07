# Fuente exacta e historia

`source-published-v17.zip` es un `git archive` del commit `f535ab92a3a291c8a902f0f4a14fa24c9c6ec67d`. Mantiene la estructura original con `app/` en la raíz y `next/font/google`.

`website-history.bundle` incluye todas las referencias del repositorio local en el momento de la entrega, con 18 commits. Puede restaurarse en una carpeta nueva:

```sh
git clone website-history.bundle flipflop-original
cd flipflop-original
git log --oneline
```

El remoto de ese clon será el archivo bundle; no contiene credenciales ni configura por sí solo un hosting. `commits.txt` sirve de índice. Versiones antiguas contienen logos, interfaces y conceptos descartados; la referencia aprobada para continuar es v17 y las decisiones de HANDOFF.md.
