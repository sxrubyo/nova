<div align="center">
  <h1>⬛ N O V A 🟦</h1>
  <h3>Control absoluto sobre tus automatizaciones.</h3>
  <p><i>El filtro de seguridad entre tus flujos y tus clientes.</i></p>
</div>

---

## 🛠️ ¿Qué es Nova?

Cuando escalas operaciones en herramientas como n8n o Make, los errores cuestan dinero. Un flujo mal configurado puede enviar el mismo correo dos veces al mismo cliente o aplicar un descuento que no autorizaste. 

**Nova no es una IA.** Es un motor de reglas rápido y determinístico (escrito en Python) que funciona como un "portero" para tu negocio. Ninguna automatización toca a un cliente sin que Nova lo apruebe primero.

### ⚙️ ¿Cómo funciona?

1. **La Petición:** Tu flujo en n8n prepara un envío (ej. *"Correo de ventas a ceo@empresa.com con 15% de descuento"*).
2. **La Consulta:** Antes de enviarlo, n8n le pasa el dato a la API de Nova.
3. **El Filtro:** Nova revisa su base de datos local. ¿Este correo ya se envió hoy? ¿Ese 15% supera el límite permitido?
4. **La Ejecución:** Si rompe las reglas, Nova devuelve un `BLOCKED` y detiene el proceso. Si todo está limpio, da luz verde (`APPROVED`).

---

## 🛡️ Características Principales

- **Filtro Anti-Duplicados:** Memoria a largo plazo. Nova registra cada acción en PostgreSQL. Si n8n intenta enviar algo repetido, Nova lo frena en seco.
- **Motor de Reglas (Gatekeeper):** Define límites estrictos (ej. "Cero descuentos mayores al 10%"). Si el texto contiene algo fuera de las reglas, se bloquea.
- **Registro Histórico Privado:** Todo lo que pasa por tu empresa queda guardado en tu propio servidor. Una auditoría perfecta de quién hizo qué y cuándo.
- **Cero Latencia:** Al ser código puro y correr en tu propia infraestructura, responde en milisegundos. Sin depender de APIs externas ni pagar por tokens.

---

## ⚡ Instalación

Instala el backend, la base de datos y la consola de comandos (CLI) en tu propio servidor AWS o máquina local con un solo comando.

### Linux & MacOS
```bash
curl -sSL [https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh](https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh) | bash
