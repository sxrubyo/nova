"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  NOVA PROMPT REFINER  v1.0  —  Intelligent Rule Violation Recovery         ║
║                                                                              ║
║  Cuando un agente viola una regla:                                          ║
║    1. Nova genera PROMPT LAYERS (capas de instrucción)                      ║
║    2. Intenta que el agente se corrija automáticamente                      ║
║    3. Si falla, Nova responde directamente                                  ║
║                                                                              ║
║  Características:                                                           ║
║    - Bidireccional (agente → Nova → agente)                                ║
║    - Mantiene personalidad del agente                                       ║
║    - Fallback a respuesta directa de Nova                                   ║
║    - Auditoría completa de refinamientos                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
from typing import Optional, Dict, Any
import httpx
import aiosqlite
from datetime import datetime, timezone

log = logging.getLogger("nova")


class PromptRefiner:
    """
    Refina prompts violadores de reglas y genera respuestas alternativas.
    
    Flujo:
      1. Detect violation (rule_id, reason, original_message)
      2. Generate prompt layers (restricciones, intención, refinamiento)
      3. Enviar a agente con instrucción refinada
      4. Si agente falla → generar respuesta directa de Nova
    """

    def __init__(self, llm):
        self.llm = llm
        self.db_path = "./nova_refinements.db"

    async def initialize(self):
        """Crear tabla de auditoría de refinamientos."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS refinements (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    agent_name TEXT,
                    rule_id TEXT,
                    rule_name TEXT,
                    original_message TEXT,
                    violation_reason TEXT,
                    prompt_layers TEXT,
                    refinement_result TEXT,
                    agent_response TEXT,
                    nova_response TEXT,
                    fallback_used INTEGER,
                    score REAL
                )
            """)
            await db.commit()

    async def generate_prompt_layers(
        self,
        rule_id: str,
        rule_name: str,
        violation_reason: str,
        original_message: str,
        rule_details: Dict,
    ) -> Dict[str, str]:
        """
        Genera capas de prompt que refinan la respuesta original.
        
        Retorna:
        {
            "intention": "Analizar lo que el agente intentaba hacer",
            "violation": "Por qué viola la regla",
            "constraint": "Restricción que se debe cumplir",
            "refinement": "Cómo refinar la respuesta",
            "tone": "Mantener tono original del agente"
        }
        """

        prompt = f"""
Analiza esta violación de regla y genera capas de refinamiento:

REGLA VIOLADA: {rule_name} ({rule_id})
MOTIVO: {violation_reason}

MENSAJE ORIGINAL:
"{original_message}"

DETALLES DE LA REGLA:
{json.dumps(rule_details, indent=2, ensure_ascii=False)}

Genera un JSON con estas claves:
{{
  "intention": "¿Qué intentaba el agente?",
  "violation_type": "tipo de violación (promesa, PII, diagnóstico, etc)",
  "constraint": "Restricción técnica a cumplir",
  "refinement": "Cómo refinar la respuesta original",
  "tone": "Descripción del tono/estilo del agente original",
  "suggested_fix": "Sugerencia de cómo reparar el mensaje"
}}

Sé conciso pero completo. Responde SOLO con JSON.
"""

        response = await self.llm.complete(prompt, max_tokens=300)
        if not response:
            return self._default_layers(rule_name, violation_reason)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._default_layers(rule_name, violation_reason)

    def _default_layers(
        self, rule_name: str, violation_reason: str
    ) -> Dict[str, str]:
        """Capas por defecto si LLM no está disponible."""
        return {
            "intention": "Proporcionar información al usuario",
            "violation_type": "governance_rule",
            "constraint": f"Cumplir con: {rule_name}",
            "refinement": f"Evitar: {violation_reason}",
            "tone": "Profesional y amable",
            "suggested_fix": "Reformular manteniendo el propósito pero sin violar la regla",
        }

    async def generate_fallback_response(
        self,
        rule_id: str,
        rule_name: str,
        original_message: str,
        violation_reason: str,
        agent_name: str,
        context: str = "",
    ) -> str:
        """
        Genera una respuesta directa de Nova cuando el agente no se puede refinar.
        
        Nova mantiene el espíritu de la respuesta pero asegura cumplimiento.
        """

        prompt = f"""
Un agente ({agent_name}) violó una regla de gobernanza. 
Nova (yo) voy a responder en su lugar de manera profesional.

CONTEXTO:
- Regla: {rule_name} ({rule_id})
- Razón del bloqueo: {violation_reason}
- Intención original: {original_message}
{f"- Contexto adicional: {context}" if context else ""}

Genera una respuesta que:
1. Mantiene tono profesional y amable
2. Explica por qué no se puede responder la solicitud original
3. Ofrece una alternativa constructiva
4. Cumple estrictamente con la regla

Responde SOLO con el mensaje (sin comillas, sin explicación adicional).
"""

        response = await self.llm.complete(prompt, max_tokens=150)
        if response:
            return response.strip()

        # Fallback genérico
        return (
            f"No puedo procesar esa solicitud debido a restricciones de gobernanza. "
            f"Por favor, contacta con el administrador para más información."
        )

    async def build_agent_refinement_request(
        self,
        agent_url: str,
        original_prompt: str,
        prompt_layers: Dict[str, str],
        rule_name: str,
    ) -> Optional[str]:
        """
        Construye y envía una solicitud refinada al agente.
        
        Le indica al agente: "Tu respuesta anterior violó X, aquí hay capas 
        de contexto para que lo hagas de nuevo correctamente"
        """

        refined_instruction = f"""
INSTRUCCIÓN REFINADA DE GOBERNANZA:

Tu respuesta anterior violó la regla: "{rule_name}"

Para corregirla, considera esto:
- Intención detectada: {prompt_layers.get('intention', '')}
- Restricción a cumplir: {prompt_layers.get('constraint', '')}
- Cómo refinar: {prompt_layers.get('refinement', '')}
- Mantén el tono: {prompt_layers.get('tone', '')}

Por favor, responde nuevamente al usuario original, 
pero esta vez cumpliendo con las restricciones anteriores.

MENSAJE ORIGINAL DEL USUARIO:
{original_prompt}
"""

        # En una implementación real, esto iría a un endpoint del agente
        # Por ahora retornamos la instrucción refinada
        return refined_instruction

    async def log_refinement(
        self,
        refinement_id: str,
        agent_name: str,
        rule_id: str,
        rule_name: str,
        original_message: str,
        violation_reason: str,
        prompt_layers: Dict,
        agent_response: Optional[str] = None,
        nova_response: Optional[str] = None,
        fallback_used: bool = False,
        score: float = 0.0,
    ):
        """Registra el refinamiento en auditoría."""

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO refinements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    refinement_id,
                    datetime.now(timezone.utc).isoformat(),
                    agent_name,
                    rule_id,
                    rule_name,
                    original_message,
                    violation_reason,
                    json.dumps(prompt_layers, ensure_ascii=False),
                    "pending",
                    agent_response or "",
                    nova_response or "",
                    1 if fallback_used else 0,
                    score,
                ),
            )
            await db.commit()

    async def get_refinement_stats(self) -> Dict[str, Any]:
        """Estadísticas de refinamientos."""

        async with aiosqlite.connect(self.db_path) as db:
            total = await db.execute_scalar(
                "SELECT COUNT(*) FROM refinements"
            )
            fallbacks = await db.execute_scalar(
                "SELECT COUNT(*) FROM refinements WHERE fallback_used = 1"
            )
            avg_score = await db.execute_scalar(
                "SELECT AVG(score) FROM refinements"
            )

            return {
                "total_refinements": total or 0,
                "fallbacks_used": fallbacks or 0,
                "avg_rule_score": round(avg_score or 0, 2),
                "success_rate": round(
                    ((total - fallbacks) / total * 100) if total else 0, 1
                ),
            }


# ─────────────────────────────────────────────────────────────────────────────
# Ejemplo de uso integrado con nova_core.py
# ─────────────────────────────────────────────────────────────────────────────

"""
En nova_core.py, después de detectar una violación:

    result = await gov.validate(...)
    
    if result.result == "BLOCKED":
        refiner = PromptRefiner(llm)
        
        # Paso 1: Generar capas de prompt
        layers = await refiner.generate_prompt_layers(
            rule_id=result.rule_id,
            rule_name=result.rule_name,
            violation_reason=result.reason,
            original_message=request.action,
            rule_details=rule.to_dict()
        )
        
        # Paso 2: Intentar refinar con el agente
        refined_instruction = await refiner.build_agent_refinement_request(
            agent_url=agent_url,
            original_prompt=request.action,
            prompt_layers=layers,
            rule_name=result.rule_name
        )
        
        agent_response = await send_to_agent(agent_url, refined_instruction)
        
        # Paso 3: Si agente falla → fallback directo de Nova
        if not agent_response_valid(agent_response, result.rule_id):
            nova_response = await refiner.generate_fallback_response(
                rule_id=result.rule_id,
                rule_name=result.rule_name,
                original_message=request.action,
                violation_reason=result.reason,
                agent_name=request.agent_name,
                context=request.context
            )
            return {
                "result": "BLOCKED",
                "fallback_response": nova_response,
                "refined_by": "nova",
                "layers": layers
            }
        
        # Paso 4: Auditoría
        await refiner.log_refinement(
            refinement_id=str(uuid.uuid4()),
            agent_name=request.agent_name,
            rule_id=result.rule_id,
            rule_name=result.rule_name,
            original_message=request.action,
            violation_reason=result.reason,
            prompt_layers=layers,
            agent_response=agent_response,
            fallback_used=False,
            score=result.score
        )
"""
