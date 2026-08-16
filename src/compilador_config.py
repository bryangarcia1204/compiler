# src/compilador_config.py
"""
Módulo para manejar el archivo de configuración .compilador (YAML)
"""

import os
import yaml
import time
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import logger

log = logger.Logger()


class CompiladorConfig:
    """Gestor del archivo de configuración .compilador"""

    CONFIG_FILENAME = ".compilador"
    DEFAULT_CONFIG = {
        "version": 1.0,
        "project": {
            "name": "",
            "description": "",
            "type": "application"
        },
        "languages": [],
        "dependencies": {},
        "targets": [
            {
                "name": "default",
                "description": "Compilación por defecto",
                "steps": []
            }
        ],
        "cross_compilation": {},
        "env": {},
        "ignore": [
            "__pycache__/",
            "*.pyc",
            "dist/",
            "build/",
            "target/",
            "node_modules/"
        ],
        "analyzer": {
            "max_file_size": 1048576,
            "include_patterns": [],
            "exclude_patterns": []
        },
        "ai": {
            "enabled": False,
            "provider": "plataformia",
            "model": "radiance",
            "api_key": ""
        }
    }

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self.config_path = self.project_dir / self.CONFIG_FILENAME
        self.config: Dict[str, Any] = {}
        self._hash: str = ""
        self._loaded = False
        self._observer = None

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            log.warning(f"[CompiladorConfig] No existe {self.CONFIG_FILENAME}, creando uno por defecto")
            self._create_default()
            return self.config

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._hash = hashlib.md5(content.encode()).hexdigest()
                self.config = yaml.safe_load(content) or {}
                self._loaded = True
                log.info(f"[CompiladorConfig] Configuración cargada desde {self.config_path}")
                return self.config
        except yaml.YAMLError as e:
            log.error(f"[CompiladorConfig] Error parseando YAML: {e}")
            return self.config
        except Exception as e:
            log.error(f"[CompiladorConfig] Error cargando configuración: {e}")
            return self.config

    def _create_default(self):
        self.config = self.DEFAULT_CONFIG.copy()
        self.config["project"]["name"] = self.project_dir.name
        self.save()

    def save(self) -> bool:
        try:
            content = yaml.dump(
                self.config,
                default_flow_style=False,
                indent=2,
                allow_unicode=True,
                sort_keys=False
            )
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self._hash = hashlib.md5(content.encode()).hexdigest()
            log.info(f"[CompiladorConfig] Configuración guardada en {self.config_path}")
            return True
        except Exception as e:
            log.error(f"[CompiladorConfig] Error guardando configuración: {e}")
            return False

    def reload(self) -> bool:
        if not self.config_path.exists():
            return False

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                new_hash = hashlib.md5(content.encode()).hexdigest()
                if new_hash != self._hash:
                    self.config = yaml.safe_load(content) or {}
                    self._hash = new_hash
                    log.info("[CompiladorConfig] Configuración recargada (cambios detectados)")
                    return True
        except Exception as e:
            log.error(f"[CompiladorConfig] Error recargando configuración: {e}")

        return False

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
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
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        return True

    def get_build_targets(self) -> List[Dict]:
        return self.get('targets', [])

    def get_languages(self) -> List[Dict]:
        return self.get('languages', [])

    def get_ignore_patterns(self) -> List[str]:
        return self.get('ignore', [])

    def watch(self, callback=None):
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
        self._observer.schedule(
            ConfigHandler(self),
            str(self.project_dir),
            recursive=False
        )
        self._observer.start()
        log.info("[CompiladorConfig] Vigilando .compilador para cambios")

    def stop_watch(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            log.info("[CompiladorConfig] Vigilancia detenida")

    def to_dict(self) -> Dict[str, Any]:
        return self.config.copy()

    def merge_with_analyzer(self, analyzer_summary: Dict) -> Dict:
        result = analyzer_summary.copy()

        if self.get('project.name'):
            result['project_name'] = self.get('project.name')
        if self.get('project.type'):
            result['project_type'] = self.get('project.type')

        deps = self.get('dependencies', {})
        if deps:
            result['dependencies'] = set(deps)

        langs = self.get('languages', [])
        if langs:
            result['languages'] = langs

        return result