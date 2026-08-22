# src/compilador_config.py
"""
Archivo de configuración central .compilador
TODO el comportamiento del compilador se basa en este archivo.
Si no existe, se crea automáticamente al analizar un proyecto.
"""

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..utils import logger

log = logger.Logger()


class CompiladorConfig:
    """
    Gestor del archivo de configuración .compilador.
    Es el CENTRO DE CONTROL de todo el compilador.
    """

    CONFIG_FILENAME = ".compilador"
    DEFAULT_CONFIG = {
        "version": 1.0,
        "project": {
            "name": "",
            "description": "",
            "type": "application",  # application | library | extension | web | cli
        },
        "languages": [],  # Lista de lenguajes detectados
        "dependencies": {},  # Dependencias por lenguaje
        "targets": [{"name": "default", "description": "Compilación por defecto", "steps": []}],
        "cross_compilation": {},  # Targets de compilación cruzada
        "env": {},  # Variables de entorno
        "ignore": ["__pycache__/", "*.pyc", "dist/", "build/", "target/", "node_modules/"],
        "analyzer": {
            "max_file_size": 1048576,  # 1MB
            "include_patterns": [],
            "exclude_patterns": [],
        },
        "ai": {"enabled": False, "provider": "plataformia", "model": "agent-xs", "api_key": ""},
        "build": {"default_target": "default", "output_dir": "dist", "clean_before_build": False},
        "main_files": [],  # Archivos principales detectados
        "evidence": [],  # Evidencia recopilada por el analizador
        "score_breakdown": {},  # Puntuación de intenciones
        "suggested_config_files": [],  # Archivos de configuración sugeridos
        "suggested_build_architecture": "",  # Arquitectura de build sugerida
        "build_plan": [],  # Plan de construcción generado
        "tools": {},  # Herramientas detectadas por CompilerDetector
    }

    def __init__(self, project_dir: str, auto_create: bool = True):
        """
        Inicializa el gestor de configuración.

        Args:
            project_dir: Directorio del proyecto
            auto_create: Si es True, crea el archivo si no existe
        """
        self.project_dir = Path(project_dir).resolve()
        self.config_path = self.project_dir / self.CONFIG_FILENAME
        self.config: Dict[str, Any] = {}
        self._hash: str = ""
        self._loaded = False
        self._observer = None
        self._callbacks = []

        # Cargar o crear configuración
        self._load_or_create(auto_create)

    def _load_or_create(self, auto_create: bool):
        """Carga la configuración o la crea si no existe."""
        if self.config_path.exists():
            self.load()
        elif auto_create:
            log.info(
                f"[CompiladorConfig] No existe {self.CONFIG_FILENAME}, creando archivo de configuración..."
            )
            self._create_default()
            self.save()
            log.info(f"[CompiladorConfig] ✅ {self.CONFIG_FILENAME} creado en {self.project_dir}")

    def load(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo .compilador"""
        if not self.config_path.exists():
            return self._create_default()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
                self._hash = hashlib.md5(content.encode()).hexdigest()
                self.config = yaml.safe_load(content) or {}
                self._loaded = True
                log.debug(f"[CompiladorConfig] Configuración cargada desde {self.config_path}")
                return self.config
        except yaml.YAMLError as e:
            log.error(f"[CompiladorConfig] Error parseando YAML: {e}")
            return self.config
        except Exception as e:
            log.error(f"[CompiladorConfig] Error cargando configuración: {e}")
            return self.config

    def _create_default(self) -> Dict[str, Any]:
        """Crea la configuración por defecto"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.config["project"]["name"] = self.project_dir.name
        self.config["project"]["description"] = f"Proyecto {self.project_dir.name}"
        return self.config

    def save(self) -> bool:
        """Guarda la configuración en el archivo .compilador"""
        try:
            content = yaml.dump(
                self.config, default_flow_style=False, indent=2, allow_unicode=True, sort_keys=False
            )
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._hash = hashlib.md5(content.encode()).hexdigest()
            log.debug(f"[CompiladorConfig] Configuración guardada en {self.config_path}")
            return True
        except Exception as e:
            log.error(f"[CompiladorConfig] Error guardando configuración: {e}")
            return False

    def reload(self) -> bool:
        """Recarga la configuración si ha cambiado"""
        if not self.config_path.exists():
            return False

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
                new_hash = hashlib.md5(content.encode()).hexdigest()

                if new_hash != self._hash:
                    self.config = yaml.safe_load(content) or {}
                    self._hash = new_hash
                    log.info("[CompiladorConfig] Configuración recargada (cambios detectados)")
                    self._notify_callbacks()
                    return True
        except Exception as e:
            log.error(f"[CompiladorConfig] Error recargando configuración: {e}")

        return False

    # ── GETTERS / SETTERS ──

    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor usando notación con puntos (ej: 'project.name')"""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> bool:
        """Establece un valor usando notación con puntos"""
        keys = key.split(".")
        target = self.config
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        return True

    def update_from_analyzer(self, analyzer_summary: Dict) -> Dict:
        """
        Actualiza la configuración con los datos del analizador.
        Los valores del .compilador tienen prioridad.
        """
        result = analyzer_summary.copy()

        # Lenguajes detectados
        if self.get("languages"):
            result["languages"] = self.get("languages")
        elif "languages" in analyzer_summary:
            result["languages"] = list(analyzer_summary["languages"].keys())

        # Dependencias
        deps = self.get("dependencies", {})
        if deps:
            result["dependencies"] = deps
        elif "dependencies" in analyzer_summary:
            result["dependencies"] = list(analyzer_summary["dependencies"])

        # Tipo de proyecto
        if self.get("project.type"):
            result["project_type"] = self.get("project.type")

        # Nombre del proyecto
        if self.get("project.name"):
            result["project_name"] = self.get("project.name")

        return result

    def get_build_targets(self) -> List[Dict]:
        """Obtiene los targets de compilación"""
        return self.get("targets", [])

    def get_default_target(self) -> str:
        """Obtiene el target por defecto"""
        return self.get("build.default_target", "default")

    def get_languages(self) -> List[Dict]:
        """Obtiene los lenguajes configurados"""
        return self.get("languages", [])

    def get_ignore_patterns(self) -> List[str]:
        """Obtiene los patrones de ignorar"""
        return self.get("ignore", [])

    def is_ai_enabled(self) -> bool:
        """Verifica si la IA está habilitada"""
        return self.get("ai.enabled", False)

    def get_ai_config(self) -> Dict:
        """Obtiene la configuración de IA"""
        return {
            "enabled": self.get("ai.enabled", False),
            "provider": self.get("ai.provider", "plataformia"),
            "model": self.get("ai.model", "agent-xs"),
            "api_key": self.get("ai.api_key", ""),
        }

    def get_output_dir(self) -> str:
        """Obtiene el directorio de salida"""
        return self.get("build.output_dir", "dist")

    def should_clean_before_build(self) -> bool:
        """Verifica si se debe limpiar antes de compilar"""
        return self.get("build.clean_before_build", False)

    # ── VIGILANCIA ──

    def watch(self, callback=None):
        """Vigila el archivo .compilador para cambios en tiempo real"""
        if self._observer:
            return

        class ConfigHandler(FileSystemEventHandler):
            def __init__(self, parent):
                self.parent = parent
                self._debounce = 0

            def on_modified(self, event):
                if event.src_path == str(self.parent.config_path):
                    now = time.time()
                    if now - self._debounce < 0.5:
                        return
                    self._debounce = now
                    log.info("[CompiladorConfig] Cambio detectado en .compilador")
                    if self.parent.reload():
                        if callback:
                            callback(self.parent.config)

        self._observer = Observer()
        self._observer.schedule(ConfigHandler(self), str(self.project_dir), recursive=False)
        self._observer.start()
        log.info(f"[CompiladorConfig] Vigilando {self.CONFIG_FILENAME} para cambios")

    def stop_watch(self):
        """Detiene la vigilancia del archivo"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            log.info("[CompiladorConfig] Vigilancia detenida")

    def register_callback(self, callback):
        """Registra un callback que se ejecuta cuando cambia la configuración"""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        """Notifica a los callbacks registrados"""
        for callback in self._callbacks:
            try:
                callback(self.config)
            except Exception as e:
                log.error(f"[CompiladorConfig] Error en callback: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Devuelve la configuración como diccionario"""
        return self.config.copy()

    def merge_with_analyzer(self, analyzer_summary: Dict) -> Dict:
        """
        Combina la configuración con el análisis del proyecto.
        LA CONFIGURACIÓN .compilador TIENE PRIORIDAD.
        """
        result = analyzer_summary.copy()

        # Proyecto
        if self.get("project.name"):
            result["project_name"] = self.get("project.name")
        if self.get("project.type"):
            result["project_type"] = self.get("project.type")
        if self.get("project.description"):
            result["project_description"] = self.get("project.description")

        # Lenguajes
        if self.get("languages"):
            result["languages"] = self.get("languages")
        elif "languages" in analyzer_summary and isinstance(analyzer_summary["languages"], dict):
            result["languages"] = list(analyzer_summary["languages"].keys())

        # Dependencias
        deps = self.get("dependencies", {})
        if deps:
            result["dependencies"] = deps
        elif "dependencies" in analyzer_summary:
            result["dependencies"] = list(analyzer_summary["dependencies"])

        # Targets
        if self.get("targets"):
            result["targets"] = self.get("targets")

        return result

    def get_build_command_for_language(self, language: str) -> Optional[str]:
        """
        Obtiene el comando de compilación para un lenguaje desde .compilador.
        """
        targets = self.get("targets", [])
        default_target = self.get("build.default_target", "default")

        for target in targets:
            if target.get("name") == default_target:
                for step in target.get("steps", []):
                    if step.get("language") == language:
                        return step.get("command")
        return None

    def get_env_vars(self) -> Dict[str, str]:
        """Obtiene las variables de entorno desde .compilador"""
        return self.get("env", {})

    def get_build_steps(self) -> List[Dict]:
        """Obtiene todos los pasos de build desde .compilador"""
        targets = self.get("targets", [])
        default_target = self.get("build.default_target", "default")

        for target in targets:
            if target.get("name") == default_target:
                return target.get("steps", [])
        return []

    def should_build_parallel(self) -> bool:
        return self.get("build.parallel", False)

    def get_cross_compilation_targets(self) -> Dict:
        return self.get("cross_compilation", {})

    # compilador_config.py - Añadir método

    def enhance_with_ai(self, ai_client) -> bool:
        """Mejora la configuración usando IA."""
        prompt = f"""
Eres un experto en configuración de proyectos. Revisa la siguiente configuración y sugiere mejoras para optimizar la compilación.

Configuración actual:
{yaml.dump(self.config, default_flow_style=False, indent=2)}

Basándote en el análisis (evidence, score_breakdown, suggested_config_files), sugiere:
1. Comandos de compilación más eficientes para cada lenguaje.
2. Dependencias adicionales que podrían ser necesarias.
3. Optimizaciones para el build multi-lenguaje.
4. Variables de entorno recomendadas.
5. Archivos de configuración que faltan (Makefile, CMakeLists.txt, etc.).

Responde en formato YAML con la configuración mejorada.
"""
        response = ai_client.chat(
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en desarrollo de software. Responde SOLO en formato YAML.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=5000,  # Aumentado para respuesta completa
        )
        if response:
            try:
                improved_config = yaml.safe_load(response)
                self.config = self._merge_configs(self.config, improved_config)
                self.save()
                return True
            except Exception as e:
                log.error(f"Error mejorando configuración con IA: {e}")
        return False

    def _merge_configs(self, current: Dict, improved: Dict) -> Dict:
        """Fusiona dos configuraciones, dando prioridad a la mejorada."""
        result = current.copy()
        for key, value in improved.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
