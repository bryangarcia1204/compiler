# src/ai_client.py
"""
Cliente unificado para servicios de IA (PlataformIA, OpenAI, Groq, etc.)
"""

import os
from typing import Optional, Dict, Any

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from . import logger

log = logger.Logger()


class AIClient:
    """Cliente unificado para servicios de IA."""

    # Configuración por proveedor
    PROVIDERS = {
        "plataformia": {
            "base_url": "https://apigateway.avangenio.net",
            "default_model": "radiance",
            "api_key_env": "PLATAFORMIA_API_KEY",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama3-70b-8192",
            "api_key_env": "GROQ_API_KEY",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "default_model": "deepseek-v4-pro",
            "api_key_env": "DEEPSEEK_API_KEY",
        }
    }

    def __init__(
        self,
        provider: str = "deepseek",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(self.PROVIDERS[self.provider]["api_key_env"])
        self.base_url = base_url or self.PROVIDERS[self.provider]["base_url"]
        self.model = model or self.PROVIDERS[self.provider]["default_model"]

        self.client = None
        self._init_client()

    def _init_client(self):
        """Inicializa el cliente de OpenAI con la configuración actual."""
        if not OPENAI_AVAILABLE:
            log.error("[AIClient] OpenAI no está instalado. Instala con: pip install openai")
            return

        if not self.api_key:
            log.error(f"[AIClient] No se encontró API key para {self.provider}")
            return

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        log.info(f"[AIClient] Cliente inicializado para {self.provider} - Modelo: {self.model}")

    def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 0,
        **kwargs
    ) -> Optional[str]:
        """
        Realiza una petición de chat al modelo.

        Args:
            messages: Lista de mensajes en formato OpenAI
            model: Modelo a usar (si no, usa el predeterminado)
            temperature: Temperatura (0-1)
            max_tokens: Tokens máximos de respuesta
            **kwargs: Argumentos adicionales para la API

        Returns:
            str: Contenido de la respuesta, o None si falla
        """
        if not self.client:
            log.error("[AIClient] Cliente no inicializado")
            return None

        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content

        except Exception as e:
            log.error(f"[AIClient] Error en la solicitud: {e}")
            return None

    def generate_code(self, prompt: str, context: str = "") -> Optional[str]:
        """
        Especializado para generar código.

        Args:
            prompt: Descripción de lo que se quiere generar
            context: Contexto adicional (archivos, dependencias, etc.)

        Returns:
            str: Código generado
        """
        system_prompt = """Eres un experto en desarrollo de software especializado en generación de código.
        Genera código limpio, bien estructurado y siguiendo las mejores prácticas.
        Responde solo con el código, sin explicaciones adicionales, a menos que se solicite explícitamente.
        Incluye comentarios relevantes en el código."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Contexto del proyecto:\n{context}\n\nTarea: {prompt}"}
        ]

        return self.chat(messages, temperature=0.3, max_tokens=4000)

    def analyze_project(self, project_summary: str) -> Optional[Dict[str, Any]]:
        """
        Analiza un proyecto y devuelve sugerencias estructuradas.

        Args:
            project_summary: Resumen del proyecto (archivos, dependencias, etc.)

        Returns:
            Dict con sugerencias
        """
        system_prompt = """Eres un experto en análisis de proyectos de software.
        Analiza la información proporcionada y devuelve sugerencias en formato JSON.
        Incluye: tipo de proyecto, archivos de configuración necesarios, recomendaciones."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analiza este proyecto:\n\n{project_summary}\n\nResponde en formato JSON con las siguientes claves: project_type, suggested_configs, recommendations, binary_config."}
        ]

        response = self.chat(messages, temperature=0.4, max_tokens=2000)
        if response:
            try:
                import json
                return json.loads(response)
            except json.JSONDecodeError:
                log.error("[AIClient] Error parseando JSON de la IA")
                return None
        return None