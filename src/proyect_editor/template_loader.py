# src/template_loader.py
"""
Carga y gestiona plantillas de archivos de configuración desde una base de datos JSON.
"""

import os
import json
import re
from typing import Dict, List, Optional, Any

from ..ai_client import AIClient
from .. import logger

log = logger.Logger()


class TemplateLoader:
    """Carga plantillas desde la base de datos JSON."""

    def __init__(
        self,
        templates_path: Optional[str] = None,
    ):
        self.templates_path = templates_path or os.path.join(
            os.path.dirname(__file__), 'project_templates', 'templates_db.json'
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