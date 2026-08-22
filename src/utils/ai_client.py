# src/ai_client.py
"""
Cliente unificado para servicios de IA.
Soporta: PlataformIA, DeepSeek, OpenAI, Groq, y TinyLlama (local)
"""

import os
import json
import re
from typing import Optional, Dict, Any, List

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

from . import logger

log = logger.Logger()


class AIClient:
    """Cliente unificado para servicios de IA."""

    # Configuración por proveedor
    PROVIDERS = {
        "plataformia": {
            "base_url": "https://apigateway.avangenio.net",
            "default_model": "agent-xs",
            "api_key_env": "PLATAFORMIA_API_KEY",
            "local": False,
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-coder",
            "api_key_env": "DEEPSEEK_API_KEY",
            "local": False,
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
            "local": False,
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama3-70b-8192",
            "api_key_env": "GROQ_API_KEY",
            "local": False,
        },
        "huggingface": {
            "base_url": "https://router.huggingface.co/v1",
            "default_model": "deepseek-ai/DeepSeek-V4-Pro-0813:fireworks-ai",
            "api_key_env": "HIGGING_API_KEY",
            "local": False,
        },
        "tinyllama": {
            "base_url": None,
            "default_model": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
            "api_key_env": None,
            "local": True,
        },
    }

    def __init__(
        self,
        provider: str = "plataformia",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_threads: int = 4,
        verbose: bool = False
    ):
        """
        Inicializa el cliente de IA.

        Args:
            provider: Proveedor a usar (plataformia, deepseek, openai, groq, tinyllama)
            api_key: API Key (no necesaria para TinyLlama)
            base_url: URL base de la API (opcional)
            model: Nombre del modelo (opcional)
            model_path: Ruta al archivo .gguf para TinyLlama
            n_ctx: Contexto para TinyLlama
            n_threads: Hilos para TinyLlama
            verbose: Verbosidad para TinyLlama
        """
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(self.PROVIDERS[self.provider]["api_key_env"])
        self.base_url = base_url or self.PROVIDERS[self.provider]["base_url"]
        self.model = model or self.PROVIDERS[self.provider]["default_model"]
        self.is_local = self.PROVIDERS[self.provider].get("local", False)

        # Configuración específica para TinyLlama
        self.model_path = model_path or os.getenv(
            "TINYLLAMA_PATH",
            os.path.join(os.path.dirname(__file__), 'module', 'qwen2.5-coder-1.5b-instruct-q3_k_m.gguf')
        )
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.verbose = verbose

        # Clientes
        self.client = None
        self._init_client()

    def _init_client(self):
        """Inicializa el cliente según el proveedor."""
        if self.provider == "tinyllama":
            self._init_tinyllama()
        else:
            self._init_openai_client()

    def _init_openai_client(self):
        """Inicializa cliente OpenAI (para PlataformIA, DeepSeek, OpenAI, Groq)."""
        if not OPENAI_AVAILABLE:
            log.error("[AIClient] OpenAI no está instalado. Instala con: pip install openai")
            return

        if not self.api_key:
            log.error(f"[AIClient] No se encontró API key para {self.provider}")
            return

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            log.info(f"[AIClient] Cliente inicializado para {self.provider} - Modelo: {self.model}")
        except Exception as e:
            log.error(f"[AIClient] Error inicializando cliente {self.provider}: {e}")

    def _init_tinyllama(self):
        """Inicializa cliente local con TinyLlama."""
        if not LLAMA_CPP_AVAILABLE:
            log.error("[AIClient] llama-cpp-python no está instalado. Instala con: pip install llama-cpp-python")
            return

        if not os.path.exists(self.model_path):
            log.error(f"[AIClient] Modelo Qwen no encontrado en: {self.model_path}")
            log.info("[AIClient] Descarga el modelo desde: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF")
            return

        try:
            self.client = Llama(
                model_path=self.model_path,
                n_ctx=8192,              # Contexto máximo para archivos grandes
                n_threads=4,
                verbose=False,
                seed=42,                 # Resultados deterministas
                repeat_penalty=1.1,      # Evita repeticiones
                temperature=0.1,         # Baja para código preciso
                top_p=0.9,
                top_k=40,
                stop=["</s>", "User:", "Assistant:"]
            )
            log.info(f"[AIClient] Qwen cargado correctamente desde: {self.model_path}")
        except Exception as e:
            log.error(f"[AIClient] Error cargando Qwen: {e}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2000,
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
            if self.provider == "tinyllama":
                return self._chat_tinyllama(messages, temperature, max_tokens)
            else:
                return self._chat_openai(messages, model, temperature, max_tokens, **kwargs)

        except Exception as e:
            log.error(f"[AIClient] Error en la solicitud: {e}")
            return None

    def _chat_openai(self, messages, model, temperature, max_tokens, **kwargs):
        """Método para clientes OpenAI (PlataformIA, DeepSeek, OpenAI, Groq)."""
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content

    def _chat_tinyllama(self, messages, temperature, max_tokens):
        """Método específico para TinyLlama."""
        prompt = self._format_messages_for_llama(messages)

        log.debug(f"[TinyLlama] Prompt (primeros 300 chars): {prompt}")

        response = self.client(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["</s>", "User:", "Assistant:", "\n\n", "###"],
            echo=False
        )

        result = response['choices'][0]['text'].strip()
        log.debug(f"[TinyLlama] Respuesta (primeros 300 chars): {result}")
        return result

    def _format_messages_for_llama(self, messages: List[Dict[str, str]]) -> str:
        """
        Convierte mensajes al formato que espera TinyLlama.

        TinyLlama usa el formato:
        <|system|> contenido
        <|user|> contenido
        <|assistant|>
        """
        formatted = ""
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'system':
                formatted += f"<|system|>\n{content}\n"
            elif role == 'user':
                formatted += f"<|user|>\n{content}\n"
            elif role == 'assistant':
                formatted += f"<|assistant|>\n{content}\n"

        # Añadir el final para que la IA empiece a generar
        formatted += "<|assistant|>\n"

        return formatted

    def generate_code(
        self,
        prompt: str,
        context: str = "",
        language: str = "python"
    ) -> Optional[str]:
        """
        Especializado para generar código.

        Args:
            prompt: Descripción de lo que se quiere generar
            context: Contexto adicional (archivos, dependencias, etc.)
            language: Lenguaje de programación

        Returns:
            str: Código generado
        """
        system_prompt = f"""Eres un experto en desarrollo de software especializado en {language}.
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
        Analiza un proyecto y devuelve sugerencias estructuradas en JSON.

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
            # Intentar extraer JSON de la respuesta (en caso de que TinyLlama no devuelva JSON puro)
            response = self._extract_json(response)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                log.error(f"[AIClient] Error parseando JSON de la IA. Respuesta: {response[:200]}")
                return None
        return None

    def _extract_json(self, text: str) -> str:
        """
        Intenta extraer un objeto JSON de un texto que puede contener markdown o texto adicional.
        """
        # Buscar JSON entre ```json ... ``` o directamente el objeto JSON
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # Bloque JSON con markdown
            r'```\s*([\s\S]*?)\s*```',       # Bloque sin especificar
            r'\{[\s\S]*\}',                  # Cualquier objeto JSON
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                extracted = match.group(1) if len(match.groups()) > 0 else match.group(0)
                # Verificar que es un JSON válido
                try:
                    json.loads(extracted)
                    return extracted
                except json.JSONDecodeError:
                    continue

        # Si no se encuentra JSON, devolver el texto original
        return text

    def is_available(self) -> bool:
        """Verifica si el cliente está disponible y funcional."""
        if not self.client:
            return False

        # Para TinyLlama, verificar que el modelo está cargado
        if self.provider == "tinyllama":
            return LLAMA_CPP_AVAILABLE and os.path.exists(self.model_path)

        # Para APIs, verificar que hay API key
        return bool(self.api_key)