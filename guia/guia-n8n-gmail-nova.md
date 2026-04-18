# Guía práctica: Nova + n8n + Gmail sin duplicados

## Propósito

Esta guía explica cómo conectar Nova con n8n y operar el flujo real de Gmail anti-duplicados que ya quedó activo en producción dentro del workflow correcto, sin inventar capacidades que el producto todavía no tiene fuera de ese flujo.

La versión honesta hoy es esta:

- Nova ya puede gobernar un workflow de n8n.
- Nova ya puede registrar un workflow como agente gestionado.
- Nova ya puede bloquear por ledger dentro de su backend actual.
- El workflow real de outreach ya consulta `Sent` real de Gmail antes de enviar.
- La lectura histórica de Gmail todavía vive dentro del workflow de `n8n`, no como servicio transversal de toda Nova.

## Workflow exacto activo

El flujo que sí está vivo es este:

- archivo: `/home/ubuntu/Workflows-n8n/Xus Outreach Engine - V1.0 (1).json`
- workflow id: `S5U-InyurlAZCNkpoGJZT`
- nombre en `n8n`: `Xus Outreach Engine - V1.0`
- managed agent de Nova: `agent_6d3a8916ffa32c0d`
- credencial Nova usada por el nodo: `Nova Workflow QA`
- Gmail credential usada para la búsqueda real en `Sent`: `Gmail account`

Estado actual:

- el workflow quedó correcto, validado y activo
- el cron corre a las `9:00 AM`
- el timezone del runtime `n8n` es `America/Bogota`
- la definición viva coincide con el archivo endurecido del repo

## Qué resuelve hoy

Hoy puedes usar este flujo para:

- validar una acción antes de ejecutar un envío
- consultar `Gmail Sent` real antes de enviar
- bloquear duplicados históricos reales por destinatario
- registrar trazabilidad del flujo
- enviar solo si Nova aprueba la acción
- operar el envío diario sin depender de nodos `LangChain` en la ruta crítica

Hoy no debes prometer:

- que Nova lee por sí sola todo el historial de Gmail desde cualquier superficie del producto
- que cualquier workflow ya viene con mailbox-aware dedupe sin configuración
- que cualquier agente queda enlazado automáticamente a Gmail sin binding explícito

## Arquitectura real

La cadena actual endurecida es esta:

1. `n8n` dispara el workflow por cron o manualmente.
2. La rama `send` construye una query real de Gmail usando el destinatario.
3. `n8n` consulta `in:sent` con la credencial OAuth real de Gmail.
4. Si encuentra coincidencia real, bloquea el envío antes de `Gmail Send`.
5. Si no hay duplicado, Nova evalúa la acción mediante el nodo custom.
6. El nodo Nova intenta primero `/api/evaluate`.
7. Si ese endpoint no existe en el backend desplegado, hace fallback controlado a `/validate`.
8. Solo si Nova devuelve `ALLOW`, el workflow llega a `Gmail Send`.
9. El resultado vuelve al sistema con mensaje claro y logs operativos.

## Antes de empezar

Necesitas:

- Nova OS corriendo
- `n8n` corriendo
- una API key válida del workspace de Nova o un usuario web creado
- credenciales Gmail reales en `n8n`
- hojas con datos reales de empresas o leads

Si tu objetivo es operar en serio, también necesitas:

- una política clara de qué se considera duplicado
- una ventana de seguimiento definida
- un criterio de equivalencia bien entendido por destinatario o por destinatario+asunto

## Paso 1. Verifica Nova

En la web de Nova confirma:

- `Skills`
- `New Agent`
- `Discovery`
- `Settings`

En CLI también puedes verificar:

- `nova auth status`
- `nova auth whoami --api-key TU_API_KEY`
- `nova discover`

Lo que debes ver:

- el workspace activo
- el connector registry cargado
- el runtime `n8n` si ya fue detectado

## Paso 2. Decide el modo de deduplicación

### Opción A. `Ledger-only`

Es la opción genérica que hoy existe en Nova.

Sirve si:

- todos los correos sensibles pasan por Nova
- quieres impedir reenvíos dentro de una ventana con base en lo que Nova ya gobernó

Ventaja:

- funciona con lo que ya hay en el backend

Limitación:

- no ve el historial completo de `Gmail Sent`

### Opción B. `Mailbox-aware`

Ya quedó aplicada en el workflow correcto de `n8n`, no como capacidad genérica de toda la plataforma.

Para llegar aquí hace falta:

- OAuth real de Gmail
- lectura de `Sent`
- normalización del destinatario
- binding real entre workflow y conector Gmail

Ventaja:

- el flujo puede detectar duplicados históricos aunque ese correo previo no haya pasado por Nova

## Paso 3. Registra o conecta el agente de n8n

Desde la UI:

1. Ve a `New Agent`.
2. Si `n8n` ya aparece como runtime detectado, usa `Add existing`.
3. Selecciona el runtime `n8n`.
4. Completa el nombre del agente, la URL y la configuración del workflow.

Desde `n8n`:

1. Usa el nodo Nova.
2. Elige la operación `Register Workflow Agent`.
3. Guarda el `managed agent id` que devuelve Nova.

Regla práctica:

- el agente de `n8n` debe quedar registrado una sola vez
- no crees duplicados del mismo workflow si no hay un motivo operativo

## Paso 4. Configura el nodo Nova en n8n

El nodo custom de Nova necesita:

- `Nova API URL`
- `Workspace API Key`

Usa la URL que pueda ver `n8n` desde su propia red. No asumas que `localhost` sirve si `n8n` corre en otro contenedor o máquina.

En el flujo activo quedó así:

- `Nova API URL`: `http://172.18.0.1:8000`
- workspace/api key: la de la credencial `Nova Workflow QA`
- `Managed Agent ID`: `agent_6d3a8916ffa32c0d`
- `Legacy Token ID`: `3`

Eso importa porque el backend desplegado hoy resuelve este caso por fallback `/validate`.

Si todavía no tienes el workspace preparado, puedes crearlo desde CLI:

- `nova auth signup --name "Santiago" --email "tu@correo.com" --password "TuClaveSegura" --company "Nova Workspace"`

Y si quieres dejar el perfil listo antes de entrar a la web:

- `nova auth profile --api-key TU_API_KEY --preferred-name "Santiago" --role-title "AI System Architect" --default-assistant both --complete-onboarding`

## Paso 5. Revisa el workflow real

Orden real ya montado:

1. Trigger
2. Construir `recipient`, `subject` y `body`
3. Query exacta contra `Gmail Sent`
4. `Search Sent Gmail`
5. `IF duplicate`
6. `Prepare Gmail Duplicate Skip`
7. `Nova Evaluate Send`
8. `Nova Approved?`
9. `Gmail Send`
10. Log final o skip

Ese orden importa porque:

- primero verificas el buzón real
- luego decides si hay duplicado
- luego pasas por Nova
- solo después envías

## Paso 6. Qué validar en la práctica

Prueba este caso:

1. Envía un correo de prueba a un destinatario concreto.
2. Repite un intento hacia ese mismo `recipient`.
3. Verifica que la query `in:sent to:<recipient>` encuentra el correo ya enviado.
4. Verifica que el workflow bloquea antes de `Gmail Send`.
5. Verifica que Nova conserva la evidencia del bloqueo o de la evaluación.

Si el segundo envío pasa, entonces uno de estos puntos falló:

- la query a `Sent` no coincide con el destinatario real
- el workflow no está consultando Gmail antes de `Gmail Send`
- la rama `Already Sent In Gmail?` no está gobernando la salida correcta
- el nodo Nova no está usando una credencial alcanzable desde la red de `n8n`

## Paso 7. Estado de producción real

Lo que sí quedó ya en producción dentro del workflow activo:

- cron vivo a las `9:00 AM`
- timezone `America/Bogota`
- búsqueda real en `Gmail Sent`
- bloqueo real de duplicados antes del envío
- evaluación por Nova antes de `Gmail Send`
- ruta crítica sin nodos `LangChain`
- branding de Nova servido desde la ruta pública canónica `/brand/nova/...`

Esto significa que si entran 100 leads a la rama de envío, el workflow hará 100 verificaciones reales contra Gmail, una por destinatario, antes de permitir cualquier envío.

## Paso 8. Qué falta para que el producto completo sea realmente completo

Para cerrar esta parte de forma seria faltan estas piezas:

- convertir esta lógica en capacidad oficial del backend de Nova, no solo del workflow activo
- binding visible en UI `agente -> conector Gmail`
- estado visible en la UI de si el correo se valida por ledger o por mailbox
- pruebas E2E para doble envío

## Recomendación operativa

Si vas a enseñarlo mañana:

- di que el workflow `Xus Outreach Engine - V1.0` ya consulta `Gmail Sent` real antes de enviar
- di que Nova gobierna la decisión antes del envío efectivo
- di que esta capacidad hoy vive de forma fuerte dentro del workflow activo de `n8n`
- di que el criterio actual de bloqueo histórico en este flujo es por destinatario

No digas que toda Nova ya ve todo Gmail desde cualquier superficie si todavía no hay una integración genérica centralizada.

## Resumen corto

Hoy puedes operar un flujo útil, gobernado y activo en producción.

Lo que todavía no debes vender como resuelto es que toda Nova ya tenga deduplicación mailbox-aware transversal en cualquier superficie del producto.
