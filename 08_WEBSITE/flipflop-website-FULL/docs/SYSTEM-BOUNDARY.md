# Frontera del sistema y verdad de producto

Esta entrega incluye íntegramente lo construido aquí para el website. La interfaz comercial, las maquetas y la simulación son reales como software web. No acreditan implementación del motor operativo.

## Estado informado por el propietario — 7 de septiembre de 2026

| Elemento | Estado documental |
|---|---|
| NinjaTrader Desktop 8 + NinjaScript | Base principal confirmada; build instalado exacto NOT_PROVEN |
| Playback / Market Replay NQ y MNQ | Probado para investigación |
| Playback101 | Cuenta de replay |
| Sim101 / Paper | Pruebas parciales; forward E2E completo pendiente |
| Broker/feed LIVE aprobado por HQ | Ninguno |
| LIVE_AUTHORITY | BLOCKED |
| BROKER_ORDERS | NONE |
| Asistente | Solo lectura; AUTHORITY=ZERO |
| Acceso desktop/tablet/phone | Diseño mediante API privada; disponibilidad operativa por revalidar |
| TradingView | Solo visual/investigación |
| Family/multi-user | Futuro, diferido |

Fuente: documento DOCX aportado en `references/user/FLIPFLOP_HQ_NINJATRADER_CONNECTION_TRUTH_2026-09-07.docx` y el contexto del propietario. Es una referencia fechada, no telemetría vigente.

La ruta operativa descrita es Router → Guardian → Bridge → NinjaTrader. No se implementa en este website. El teléfono no debe convertirse en ruta directa al broker. Compatibilidad oficial de plataforma ≠ prueba HQ ≠ aprobación HQ.

## Qué haría falta para integrar después

Una especificación independiente de identidad, autorización, API privada de lectura, transporte, datos con fechas/evidencia, disponibilidad del nodo, permisos y criterios de validación. La fuente de datos debe distinguir real, replay, paper, stale y desconocido. Los estados ausentes nunca se convierten en aprobación.

No se exportaron ni modificaron binarios, cuentas, políticas, conexiones, claves o procesos del sistema NinjaTrader/Guardian. No se crearon adaptadores ficticios para aparentar una integración completa. El DOCX y este mapa permiten continuar la conversación de arquitectura sin atribuir capacidades que la web no tiene.
