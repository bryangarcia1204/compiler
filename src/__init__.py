# src/__init__.py
"""
Compilador/Empaquetador Profesional
===================================
Aplicación de escritorio que detecta automáticamente herramientas 
de compilación y empaquetado instaladas en el sistema.

Permite compilar o empaquetar archivos fuente en múltiples formatos
de salida, con soporte para Windows, Linux y macOS.
"""

__version__ = "1.0.0"
__author__ = "Brayan M."
__email__ = "bgarciaguibert@gmail.com"
__license__ = "MIT"

# Importar componentes principales para facilitar el uso.
from src.main import main
from src.compiler_detector import CompilerDetector
from src.language_detector import LanguageDetector
from src.compilation_engine import CompilationEngine
from src.error_parser import ErrorParser
from src.argument_suggester import ArgumentSuggester
from src.output_types import OUTPUT_TYPE_MAP
from src.logger import Logger
from src.module import cpp_module

# Definir qué se exporta cuando alguien hace "from src import *"
__all__ = [
    'main',
    'CompilerDetector',
    'LanguageDetector',
    'CompilationEngine',
    'ErrorParser',
    'ArgumentSuggester',
    'OUTPUT_TYPE_MAP',
    'Logger',
    'cpp_module',
]

# Información del paquete
__all__ += ['__version__', '__author__', '__email__', '__license__']