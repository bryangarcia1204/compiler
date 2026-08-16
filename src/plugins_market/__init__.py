# src/plugins_market/__init__.py
"""
Marketplace de plugins para el Compilador Profesional.
Permite instalar, desinstalar y gestionar plugins de terceros.
"""

from .plugin_manager import PluginManager
from .plugin_registry import PluginRegistry, PluginMetadata, PluginStatus
from .market_client import MarketClient
from .market_dialog import MarketDialog
from .plugin_loader import PluginLoader

__all__ = [
    'PluginManager',
    'PluginRegistry',
    'PluginMetadata',
    'PluginStatus',
    'MarketClient',
    'MarketDialog',
    'PluginLoader',
]