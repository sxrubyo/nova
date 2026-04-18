# Guía del producto: estado real de Nova OS

## Qué es Nova hoy

Nova OS ya es un producto usable para operar runtimes, gobernar acciones y mantener trazabilidad.

Lo que ya hace bien:

- discovery de runtimes reales
- gobierno de agentes y acciones
- ledger auditable
- integración con n8n mediante nodo custom
- inventario de skills y conectores
- login, sesión y perfil de workspace
- alta de cuenta web desde CLI
- interfaz web operativa
- CLI funcional para tareas principales

Lo que todavía no está cerrado:

- paridad total entre CLI, backend y UI
- binding formal de conectores por agente
- deduplicación Gmail mailbox-aware
- compilación completa de prompts largos en planes ejecutables
- experiencia de configuración inicial más unificada

## Estado por bloque

### Frontend

Estado: usable, serio y presentable, pero incompleto.

Ya tiene:

- dashboard
- discovery
- help de discovery
- agents
- new agent
- ledger
- skills
- settings
- login
- onboarding post-login
- personalización real persistida en backend

Le falta:

- más paridad con la CLI
- configuración de perfil más visible
- estado de conectores por agente
- pantallas operativas para `gateway`, `stream`, `ledger verify/export`

### Backend

Estado: fuerte, pero conviviente.

Ya tiene:

- auth
- session handling
- workspace profile
- setup/bootstrap
- discovery
- ledger
- Gmail duplicate check
- agents
- analytics
- assistant

Punto delicado:

- conviven backend monolítico y runtime modular
- algunas capacidades existen en más de un sitio
- hay superficie legacy que todavía debe convivir con la moderna

### CLI

Estado: operativa para el núcleo.

Ya soporta:

- `start`
- `status`
- `version`
- `seed`
- `watch`
- `discover`
- `connect`
- `evaluate`
- `chat`
- `validate`
- `agents`
- `agent`
- `ledger`
- `gateway`
- `stream`
- `shield`
- `auth status`
- `auth signup`
- `auth login`
- `auth whoami`
- `auth profile`
- `auth logout`

Le falta:

- comandos de skills más completos
- mejor ayuda contextual para operadores no técnicos

### Discovery

Estado: fuerte.

Ya hace:

- fingerprints reales
- checks múltiples por runtime
- confidence por evidencia
- logos por runtime
- conexión de runtimes descubiertos

Soporta ya de forma visible:

- Codex CLI
- n8n
- OpenClaw
- Open Interpreter
- LangChain
- CrewAI

### Agents

Estado: usable.

Ya permite:

- crear agentes gestionados
- enlazar a runtimes detectados
- configurar permisos
- revisar logs y métricas

Le falta:

- binding formal `agent -> connectors`
- estado más rico de cada lane
- más claridad para runtimes existentes

### Ledger

Estado: real y útil.

Ya hace:

- registrar acciones
- listar entradas
- verificar integridad
- servir de base para dedupe y trazabilidad

Le falta:

- una experiencia visual más profunda
- más comandos y vistas operativas

### Gateway y modelos

Estado: usable.

Ya hace:

- mostrar proveedores configurados
- exponer catálogo de modelos
- servir assistant/gateway providers

Le falta:

- una pantalla más operativa
- estado de salud por proveedor más claro

### Assistant

Estado: útil, pero todavía no es el compilador final del producto.

Ya hace:

- recibe lenguaje natural
- usa modelos configurados
- responde con contexto del workspace
- sugiere comandos y acciones

Le falta:

- compilar prompts largos de forma determinista
- transformar intención en plan ejecutable completo
- operar con más profundidad sobre n8n y skills

### n8n node

Estado: real y útil.

Ya hace:

- `evaluate`
- duplicate check
- register workflow agent
- ledger list
- ledger verify
- fallback a `/validate` para stacks donde `/api/evaluate` aún no está expuesto

Le falta:

- binding profundo con conectores
- dedupe mailbox-aware como capacidad genérica del producto
- documentación de operación más clara para equipos

Hoy sí existe un caso mailbox-aware real, pero quedó resuelto dentro del workflow endurecido `Xus Outreach Engine - V1.0` en n8n y no como servicio genérico de Nova.

### Connector Registry

Estado: ya existe de forma inicial.

Hoy Nova puede:

- leer el store local de skills
- detectar conectores presentes
- reflejar conectores conectados en la UI

Le falta:

- persistencia rica por workspace
- binding de conectores a agentes concretos
- alta y baja desde la CLI y UI con un modelo unificado

## Qué está listo para demo

Puedes mostrar con confianza:

- login y sesión
- onboarding post-login
- edición del perfil desde Settings
- creación de cuenta web desde CLI
- discovery de runtimes reales
- creación de agente nuevo o existente
- skills y conectores visibles
- ledger y trazabilidad
- nodo Nova para n8n
- duplicate check basado en ledger

## Qué está listo solo de forma parcial

- Gmail anti-duplicados contra todo el buzón
- paridad total CLI/UI
- configuración avanzada de conectores
- catálogo completo de runtimes detectables
- panel de operación por agente más profundo

## Qué falta para decir “production ready” con rigor

Falta cerrar estos puntos:

1. Unificar modelo de conectores.
2. Añadir binding `agent -> connectors`.
3. Completar Gmail mailbox-aware.
4. Exponer más operaciones CLI en web.
5. Añadir pruebas E2E de los flujos críticos.
6. Reducir la fractura entre superficies legacy y modernas.

## Cómo usar Nova hoy

### 1. Entrar

Puedes entrar de dos formas:

- web con email y contraseña
- API key del workspace

También puedes crear o preparar la cuenta desde CLI:

- `nova auth signup --name "Tu Nombre" --email "tu@correo.com" --password "TuClaveSegura" --company "Tu Workspace"`
- `nova auth login --email "tu@correo.com" --password "TuClaveSegura"`
- `nova auth whoami`

### 2. Completar el perfil

Define:

- nombre preferido
- rol
- fecha de nacimiento si aplica
- lane por defecto entre Nova, Melissa o ambas

Hoy esto se puede hacer en dos sitios:

- modal post-login
- `Settings`

Y también desde CLI:

- `nova auth profile --preferred-name "Santiago" --role-title "AI System Architect" --default-assistant both --complete-onboarding`

### 3. Detectar lo que existe

Usa `Discovery` para ver runtimes reales del host.

### 4. Crear o conectar agentes

Usa `New Agent` para:

- crear uno nuevo
- conectar uno existente

### 5. Revisar skills

Usa `Skills` para entender:

- conectores instalados
- runtimes detectados
- estado básico de conexión

### 6. Gobernar acciones

Usa el assistant, el ledger y el nodo de n8n para ejecutar flujos con trazabilidad.

## Lectura honesta para inversores

Nova ya no es una idea vacía.

Es un control plane funcional con:

- identidad
- discovery
- gobernanza
- auditoría
- n8n
- skills

Pero todavía no conviene presentarlo como una plataforma completamente unificada hasta cerrar:

- el registry de conectores
- el mailbox-aware Gmail
- la paridad CLI/UI
- los flujos E2E críticos

## Resumen ejecutivo

Nova está en una fase fuerte de producto real.

Está por encima de un prototipo, pero todavía debajo de una plataforma totalmente cerrada.

La base existe. Lo que falta es unificar, endurecer y exponer mejor lo que ya funciona.
