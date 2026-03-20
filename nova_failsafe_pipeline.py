"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  NOVA FAILSAFE RESPONSE PIPELINE  v1.0  —  Guaranteed Responses            ║
║                                                                              ║
║  Pensamiento Crítico en Producción:                                         ║
║    "Cuando el agente falla, NUNCA debe quedarse sin respuesta"             ║
║                                                                              ║
║  Arquitectura de 4 Layers:                                                  ║
║    Layer 1: Agent normal response (Melissa)                                ║
║    Layer 2: Governance fallback (Nova LLM)                                 ║
║    Layer 3: Smart template (sin LLM)                                       ║
║    Layer 4: Final fallback + escalación                                    ║
║                                                                              ║
║  Garantía: 100% de las preguntas reciben respuesta                         ║
║  Latencia máxima: 5s (Layer 1 timeout)                                     ║
║  Costo por fallback: <$0.01                                                ║
║                                                                              ║
║  Para contexto médico/clínica: NO puedes dejar a un paciente sin respuesta ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any
from enum import Enum

log = logging.getLogger("nova")


class ResponseLayer(str, Enum):
    """Qué layer generó la respuesta."""
    AGENT = "layer1_agent"
    GOVERNANCE = "layer2_governance"
    SMART_TEMPLATE = "layer3_smart_template"
    FINAL_FALLBACK = "layer4_final_fallback"


class ResponseResult:
    """Resultado de una request con metadata completa."""
    
    def __init__(
        self,
        response: str,
        layer: ResponseLayer,
        success: bool = True,
        ms: int = 0,
        error: Optional[str] = None,
        user_question: str = "",
        escalated: bool = False,
        ticket_id: Optional[str] = None,
    ):
        self.response = response
        self.layer = layer
        self.success = success
        self.ms = ms
        self.error = error
        self.user_question = user_question
        self.escalated = escalated
        self.ticket_id = ticket_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "response": self.response,
            "layer": self.layer,
            "success": self.success,
            "ms": self.ms,
            "error": self.error,
            "escalated": self.escalated,
            "ticket_id": self.ticket_id,
            "timestamp": self.timestamp,
        }


class FailsafeResponsePipeline:
    """
    Garantiza que SIEMPRE hay una respuesta, incluso si todo falla.
    
    Flujo:
      1. Intenta con agente normal (5s timeout)
      2. Si falla/bloqueada → Nova LLM (3s timeout)
      3. Si falla → Template inteligente (regex, <100ms)
      4. Si falla → Fallback final + escalación (garantizado)
    """
    
    def __init__(self, agent_url: str, llm, interceptor=None):
        self.agent_url = agent_url.rstrip("/")
        self.llm = llm
        self.interceptor = interceptor
        
        # Templates por categoría de pregunta
        self.templates = self._build_templates()

    def _build_templates(self) -> Dict[str, str]:
        """Construye templates inteligentes por categoría."""
        return {
            "precio": """Para información detallada sobre precios y opciones de pago, 
nuestro equipo administrativo puede asesorarte mejor. 
Contacta con nosotros:
📞 +1-800-ESTÉTICA
📧 precios@clinica.com
💬 Agendar consulta gratuita: [link]""",

            "cita": """Para agendar una cita con nuestros especialistas:
📅 [Calendario online]
📞 +1-800-ESTÉTICA
💬 WhatsApp: [link]

Tenemos disponibilidad de lunes a viernes, 8am-6pm.
Responder en menos de 24 horas.""",

            "procedimiento": """Para conocer detalles específicos sobre este procedimiento:
✓ Ver galería de resultados
✓ Leer testimonios de pacientes
✓ Agendar consulta con especialista

Nuestro equipo médico responderá tus preguntas específicas.
[Agendar consulta]""",

            "resultados": """Los resultados varían según cada persona.
Nuestro equipo especializado puede proporcionarte:
✓ Estimado personalizado
✓ Fotos antes/después
✓ Plan de tratamiento detallado

Agendar consulta gratuita: [link]""",

            "seguridad": """La seguridad es nuestra prioridad.
✓ Equipo médico certificado
✓ Tecnología de última generación
✓ Protocolos de esterilización garantizados

Consulta con nuestro médico sobre procedimientos específicos.
[Agendar consulta]""",

            "default": """Gracias por tu pregunta. 
Nuestro equipo especializado está aquí para ayudarte.

Agendar consulta: [link]
Llamar: +1-800-ESTÉTICA
Email: info@clinica.com

Un especialista se comunicará contigo en los próximos minutos.""",
        }

    def _categorize_question(self, question: str) -> str:
        """Detecta categoría de pregunta con regex."""
        question_lower = question.lower()

        # Mapeos de palabras clave a categoría
        categories = {
            "precio": [
                r"precio", r"costo", r"dinero", r"cuanto cuesta",
                r"tarifa", r"paquete", r"descuento"
            ],
            "cita": [
                r"cita", r"agendar", r"horario", r"disponible",
                r"cuando", r"turno", r"calendario"
            ],
            "procedimiento": [
                r"como es", r"procedimiento", r"proceso", r"que incluye",
                r"pasos", r"sesion", r"duracion"
            ],
            "resultados": [
                r"resultado", r"funciona", r"efectivo", r"sirve",
                r"garantia", r"seguro que", r"cuanto dura"
            ],
            "seguridad": [
                r"seguro", r"riesgo", r"peligro", r"complicacion",
                r"efectos secundarios", r"garantizado"
            ],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if re.search(keyword, question_lower):
                    return category

        return "default"

    async def layer1_agent_response(
        self,
        question: str,
        timeout: float = 5.0,
    ) -> Optional[ResponseResult]:
        """
        Layer 1: Intenta con agente normal (Melissa).
        
        Timeout: 5s (tiempo máximo que usuario espera)
        Success: Melissa responde bien
        Fail: Timeout, error, o respuesta vacía → siguiente layer
        """
        import time
        import httpx

        t0 = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.post(
                    f"{self.agent_url}/chat",
                    json={
                        "message": question,
                        "scope": "user:default"
                    },
                    timeout=timeout,
                )

                if r.status_code >= 400:
                    log.warning(f"[layer1] Agent returned {r.status_code}")
                    return None

                data = r.json()
                response = data.get("response") or data.get("message") or ""

                if not response or len(response.strip()) < 10:
                    log.warning("[layer1] Agent returned empty response")
                    return None

                ms = int((time.time() - t0) * 1000)

                log.info(f"[layer1] Agent responded in {ms}ms")
                return ResponseResult(
                    response=response,
                    layer=ResponseLayer.AGENT,
                    success=True,
                    ms=ms,
                    user_question=question,
                )

        except asyncio.TimeoutError:
            ms = int((time.time() - t0) * 1000)
            log.warning(f"[layer1] Agent timeout after {ms}ms")
            return None
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            log.warning(f"[layer1] Agent error: {e}")
            return None

    async def layer2_governance_fallback(
        self,
        question: str,
        timeout: float = 3.0,
    ) -> Optional[ResponseResult]:
        """
        Layer 2: Nova LLM genera respuesta cuando Melissa falla.
        
        Timeout: 3s (más rápido que layer 1)
        Genera respuesta:
        - Profesional y útil
        - Cumple governance
        - Mantiene contexto de pregunta
        """
        import time

        t0 = time.time()

        try:
            prompt = f"""Eres un especialista en clínica estética profesional y amable.
Un paciente preguntó: "{question}"

Responde:
1. Directamente y útilmente
2. Profesionalmente
3. Sin hacer promesas no verificadas
4. Ofreciendo alternativas (agendar cita, contactar equipo, etc)

Responde SOLO con la respuesta, sin explicaciones adicionales."""

            response = await asyncio.wait_for(
                self.llm.complete(prompt, max_tokens=200),
                timeout=timeout,
            )

            if not response or len(response.strip()) < 10:
                log.warning("[layer2] LLM returned empty response")
                return None

            ms = int((time.time() - t0) * 1000)
            log.info(f"[layer2] Nova LLM responded in {ms}ms")

            return ResponseResult(
                response=response,
                layer=ResponseLayer.GOVERNANCE,
                success=True,
                ms=ms,
                user_question=question,
            )

        except asyncio.TimeoutError:
            ms = int((time.time() - t0) * 1000)
            log.warning(f"[layer2] LLM timeout after {ms}ms")
            return None
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            log.warning(f"[layer2] LLM error: {e}")
            return None

    async def layer3_smart_template(
        self,
        question: str,
    ) -> ResponseResult:
        """
        Layer 3: Template inteligente (sin LLM).
        
        Timeout: <100ms (puro regex)
        Categoriza pregunta → selecciona template
        Garantizado que responde
        """
        import time

        t0 = time.time()

        category = self._categorize_question(question)
        template = self.templates.get(category, self.templates["default"])

        ms = int((time.time() - t0) * 1000)
        log.info(f"[layer3] Template matched: {category} in {ms}ms")

        return ResponseResult(
            response=template,
            layer=ResponseLayer.SMART_TEMPLATE,
            success=True,
            ms=ms,
            user_question=question,
        )

    async def layer4_final_fallback(
        self,
        question: str,
        escalate_fn=None,
    ) -> ResponseResult:
        """
        Layer 4: Fallback final + escalación.
        
        Timeout: <10ms
        GARANTIZADO que responde
        Automáticamente:
        - Crea ticket de soporte
        - Alerta al equipo
        - Promete respuesta manual
        """
        import time

        t0 = time.time()

        ticket_id = str(uuid.uuid4())[:8]

        fallback_response = f"""Gracias por tu pregunta.

Nuestro equipo especializado está trabajando en tu respuesta.
Un profesional se comunicará contigo en los próximos minutos.

**Ticket de soporte: #{ticket_id}**

Mientras tanto:
📞 +1-800-ESTÉTICA
📧 soporte@clinica.com
💬 WhatsApp: [link]"""

        # Escalación automática
        if escalate_fn:
            try:
                await escalate_fn(question, ticket_id)
                log.warning(
                    f"[layer4] Escalated to human: ticket={ticket_id}"
                )
            except Exception as e:
                log.error(f"[layer4] Escalation failed: {e}")

        ms = int((time.time() - t0) * 1000)
        log.error(
            f"[layer4] Final fallback triggered (all layers failed). "
            f"Ticket: {ticket_id}"
        )

        return ResponseResult(
            response=fallback_response,
            layer=ResponseLayer.FINAL_FALLBACK,
            success=True,  # Técnicamente "success" porque responde
            ms=ms,
            user_question=question,
            escalated=True,
            ticket_id=ticket_id,
        )

    async def handle_request(
        self,
        question: str,
        escalate_fn=None,
    ) -> ResponseResult:
        """
        Main method: Garantiza respuesta pasando por layers.
        
        Retorna: ResponseResult con response + metadata
        
        GARANTÍA: Siempre hay una respuesta, nunca falla
        """
        import time

        t0_total = time.time()

        # LAYER 1: Agent normal
        log.debug(f"[pipeline] Layer 1 attempt for: {question[:50]}...")
        layer1 = await self.layer1_agent_response(question, timeout=5.0)
        if layer1:
            return layer1

        # LAYER 2: Nova LLM governance fallback
        log.debug("[pipeline] Layer 1 failed, trying Layer 2...")
        layer2 = await self.layer2_governance_fallback(question, timeout=3.0)
        if layer2:
            return layer2

        # LAYER 3: Smart template
        log.debug("[pipeline] Layer 2 failed, using Layer 3 template...")
        layer3 = await self.layer3_smart_template(question)
        if layer3:
            return layer3

        # LAYER 4: Final fallback + escalation
        log.error("[pipeline] All layers failed, using Layer 4 final fallback...")
        layer4 = await self.layer4_final_fallback(question, escalate_fn)

        return layer4

    async def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del pipeline (placeholder)."""
        return {
            "layer1_success_rate": 95.0,
            "layer2_success_rate": 4.0,
            "layer3_success_rate": 0.8,
            "layer4_success_rate": 0.2,
            "guaranteed_response": "100%",
            "avg_latency_ms": 450,
            "message": "100% de preguntas reciben respuesta garantizada",
        }
