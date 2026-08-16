# src/plugins_market/plugin_registry.py
"""
Registro central de plugins activos y disponibles.
"""

import os
import json
import importlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PluginStatus(Enum):
    """Estado de un plugin."""
    AVAILABLE = "available"
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    NEEDS_UPDATE = "needs_update"
    INCOMPATIBLE = "incompatible"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Metadatos de un plugin."""
    id: str
    name: str
    version: str
    description: str
    author: str
    email: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    supported_languages: List[str] = field(default_factory=list)
    supported_platforms: List[str] = field(default_factory=list)
    min_compiler_version: str = "1.0.0"
    max_compiler_version: Optional[str] = None
    installed_at: Optional[str] = None
    active: bool = True
    status: PluginStatus = PluginStatus.AVAILABLE
    strategy_class: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'email': self.email,
            'homepage': self.homepage,
            'repository': self.repository,
            'dependencies': self.dependencies,
            'supported_languages': self.supported_languages,
            'supported_platforms': self.supported_platforms,
            'min_compiler_version': self.min_compiler_version,
            'max_compiler_version': self.max_compiler_version,
            'installed_at': self.installed_at,
            'active': self.active,
            'status': self.status.value,
            'strategy_class': self.strategy_class,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PluginMetadata':
        status = data.get('status', 'available')
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            version=data.get('version', '0.0.1'),
            description=data.get('description', ''),
            author=data.get('author', 'Unknown'),
            email=data.get('email'),
            homepage=data.get('homepage'),
            repository=data.get('repository'),
            dependencies=data.get('dependencies', []),
            supported_languages=data.get('supported_languages', []),
            supported_platforms=data.get('supported_platforms', []),
            min_compiler_version=data.get('min_compiler_version', '1.0.0'),
            max_compiler_version=data.get('max_compiler_version'),
            installed_at=data.get('installed_at'),
            active=data.get('active', True),
            status=PluginStatus(status) if isinstance(status, str) else status,
            strategy_class=data.get('strategy_class'),
        )


class PluginRegistry:
    """Registro de plugins instalados y activos."""

    _instance = None
    _plugins: Dict[str, PluginMetadata] = {}
    _loaded = False
    REGISTRY_FILE = "plugins_registry.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self._load_registry()

    def _load_registry(self) -> None:
        """Carga el registro de plugins desde el archivo."""
        registry_path = self._get_registry_path()
        if registry_path.exists():
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for plugin_id, plugin_data in data.items():
                        self._plugins[plugin_id] = PluginMetadata.from_dict(plugin_data)
            except Exception as e:
                from .. import logger
                log = logger.Logger()
                log.error(f"[PluginRegistry] Error cargando registro: {e}")
        self._loaded = True

    def _save_registry(self) -> None:
        """Guarda el registro de plugins."""
        registry_path = self._get_registry_path()
        try:
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            data = {pid: p.to_dict() for pid, p in self._plugins.items()}
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            from .. import logger
            log = logger.Logger()
            log.error(f"[PluginRegistry] Error guardando registro: {e}")

    def _get_registry_path(self):
        from pathlib import Path
        from ..config_manager import CONFIG_DIR
        return CONFIG_DIR / self.REGISTRY_FILE

    def get_plugin(self, plugin_id: str) -> Optional[PluginMetadata]:
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> List[PluginMetadata]:
        return list(self._plugins.values())

    def get_active_plugins(self) -> List[PluginMetadata]:
        return [p for p in self._plugins.values() if p.active]

    def get_plugins_by_language(self, language: str) -> List[PluginMetadata]:
        return [p for p in self._plugins.values() if language in p.supported_languages]

    def get_plugins_by_status(self, status: PluginStatus) -> List[PluginMetadata]:
        return [p for p in self._plugins.values() if p.status == status]

    def add_plugin(self, metadata: PluginMetadata) -> bool:
        """Añade un plugin al registro."""
        if metadata.id in self._plugins:
            return False
        self._plugins[metadata.id] = metadata
        self._save_registry()
        return True

    def update_plugin(self, plugin_id: str, metadata: PluginMetadata) -> bool:
        if plugin_id not in self._plugins:
            return False
        self._plugins[plugin_id] = metadata
        self._save_registry()
        return True

    def set_active(self, plugin_id: str, active: bool) -> bool:
        if plugin_id not in self._plugins:
            return False
        self._plugins[plugin_id].active = active
        self._save_registry()
        return True

    def remove_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        del self._plugins[plugin_id]
        self._save_registry()
        return True

    def is_installed(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins

    def get_installed_plugins(self) -> List[PluginMetadata]:
        return [p for p in self._plugins.values() if p.status != PluginStatus.AVAILABLE]