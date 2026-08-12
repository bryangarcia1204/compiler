# src/template_loader.py
"""
Carga y gestiona plantillas de archivos de configuración desde una base de datos JSON.
"""

import os
import json
import re
from typing import Dict, List, Optional, Any

from .ai_client import AIClient
from . import logger

log = logger.Logger()


class TemplateLoader:
    """Carga plantillas desde la base de datos JSON."""

    def __init__(
        self,
        templates_path: Optional[str] = None,
        use_ai: bool = False,
        provider: str = "plataformia",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.templates_path = templates_path or os.path.join(
            os.path.dirname(__file__), 'project_templates', 'templates_db.json'
        )
        self.use_ai = use_ai
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

        # Inicializar AIClient
        self.ai_client = None
        if self.use_ai and self.api_key:
            self.ai_client = AIClient(
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                api_base=self.api_base
            )

        self.db = self._load_templates()

    def _load_templates(self) -> Dict:
        """Carga la base de datos de plantillas."""
        try:
            with open(self.templates_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            log.warning(f"[TemplateLoader] No se encontró la base de datos: {self.templates_path}")
            return {'version': '1.0.0', 'languages': {}}

    def get_language_info(self, language: str) -> Optional[Dict]:
        """Obtiene la información de un lenguaje específico."""
        return self.db.get('languages', {}).get(language)

    def get_language_from_extension(self, extension: str) -> Optional[str]:
        """Obtiene el lenguaje a partir de una extensión."""
        for lang, info in self.db.get('languages', {}).items():
            if extension in info.get('extensions', []):
                return lang
        return None

    def get_template(self, language: str, filename: str) -> Optional[str]:
        """Obtiene el contenido de una plantilla específica."""
        lang_info = self.get_language_info(language)
        if lang_info:
            config_files = lang_info.get('config_files', {})
            if filename in config_files:
                return config_files[filename]['template']
        return None

    def get_all_templates_for_language(self, language: str) -> Dict[str, str]:
        """Obtiene todas las plantillas para un lenguaje."""
        lang_info = self.get_language_info(language)
        if not lang_info:
            return {}
        return {
            name: info['template']
            for name, info in lang_info.get('config_files', {}).items()
        }

    def get_build_commands(self, language: str) -> Dict[str, str]:
        """Obtiene los comandos de build para un lenguaje."""
        lang_info = self.get_language_info(language)
        if lang_info:
            return lang_info.get('build_commands', {})
        return {}

    def generate_with_ai(
        self,
        language: str,
        project_name: str,
        custom_prompt: str = "",
        context: str = ""
    ) -> Dict[str, str]:
        """Genera archivos de configuración usando AIClient."""
        if not self.ai_client or not self.ai_client.client:
            log.warning("[TemplateLoader] AIClient no disponible, usando plantillas")
            return self.generate_with_templates(language, project_name, custom_prompt)

        try:
            # Obtener plantillas existentes para referencia
            existing_templates = self.get_all_templates_for_language(language)
            template_examples = "\n".join(
                f"--- {name} ---\n{content[:300]}...\n--- FIN ---"
                for name, content in list(existing_templates.items())[:3]
            )

            prompt = f"""
Eres un experto en desarrollo de software. Genera los archivos de configuración necesarios para un proyecto de {language}.

**Nombre del proyecto:** {project_name}
**Instrucciones adicionales:** {custom_prompt if custom_prompt else 'Genera los archivos típicos para este proyecto.'}

**Contexto adicional:**
{context if context else 'No hay contexto adicional.'}

**Archivos relevantes para {language}:**
{', '.join(existing_templates.keys()) if existing_templates else 'No hay archivos predefinidos.'}

**Formato de respuesta:** Cada archivo debe estar delimitado por:
--- NOMBRE_ARCHIVO ---
contenido del archivo
--- FIN ---

**Ejemplo de formato:**
{template_examples if template_examples else '--- README.md ---\n# Proyecto\n\nDescripción\n--- FIN ---'}

Asegúrate de que los archivos generados sean funcionales y sigan las mejores prácticas para {language}.
"""

            response = self.ai_client.chat([
                {"role": "system", "content": "Eres un experto en desarrollo de software y generación de archivos de configuración."},
                {"role": "user", "content": prompt}
            ], temperature=0.7, max_tokens=500, extra_body={"thinking": {"type": "enabled"}} if self.provider == "deepseek" else {})

            if response:
                return self._parse_ai_response(response, language)

            log.warning("[TemplateLoader] No se recibió respuesta de IA")
            return self.generate_with_templates(language, project_name, custom_prompt)

        except Exception as e:
            log.error(f"[TemplateLoader] Error con IA: {e}")
            return self.generate_with_templates(language, project_name, custom_prompt)

    def _parse_ai_response(self, content: str, language: str) -> Dict[str, str]:
        """Parsea la respuesta de la IA en un diccionario de archivos."""
        result = {}
        pattern = r'---\s*([A-Za-z0-9_.-]+)\s*---\s*([\s\S]*?)\s*---\s*FIN\s*---'
        matches = re.findall(pattern, content)

        for filename, file_content in matches:
            result[filename] = file_content.strip()

        if not result:
            log.warning("[TemplateLoader] No se pudo parsear respuesta de IA, usando plantillas")
            return {}

        return result

    def generate_with_templates(
        self,
        language: str,
        project_name: str,
        custom_prompt: str = ""
    ) -> Dict[str, str]:
        """Genera archivos usando plantillas predefinidas."""
        templates = self.get_all_templates_for_language(language)
        if not templates:
            log.warning(f"[TemplateLoader] No hay plantillas para {language}")
            return {}

        result = {}
        for filename, template in templates.items():
            try:
                rendered = template
                # Reemplazar variables
                if '{project_name}' in rendered:
                    rendered = rendered.replace('{project_name}', project_name)
                if '{PROJECT_NAME}' in rendered:
                    rendered = rendered.replace('{PROJECT_NAME}', project_name.upper())
                if '{project_lower}' in rendered:
                    rendered = rendered.replace('{project_lower}', project_name.lower())
                result[filename] = rendered
            except Exception as e:
                log.error(f"[TemplateLoader] Error renderizando {filename}: {e}")
                result[filename] = template

        return result