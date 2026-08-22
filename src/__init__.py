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

from src.detector.compiler_detector import CompilerDetector
from src.detector.language_detector import LanguageDetector
from src.engine.compilation_engine import CompilationEngine

# Importar componentes principales para facilitar el uso.
from src.main import main
from src.module import cpp_module
from src.proyect_editor.project_analyzer import ProjectAnalyzer
from src.proyect_editor.project_generator import ProjectGenerator
from src.proyect_editor.project_generator_dialog import ProjectGeneratorDialog
from src.proyect_editor.template_loader import TemplateLoader
from src.utils.ai_client import AIClient
from src.utils.argument_suggester import ArgumentSuggester
from src.utils.error_parser import ErrorParser
from src.utils.logger import Logger
from src.utils.output_types import OUTPUT_TYPE_MAP

# Definir qué se exporta cuando alguien hace "from src import *"
__all__ = [
    "main",
    "CompilerDetector",
    "LanguageDetector",
    "CompilationEngine",
    "ErrorParser",
    "ArgumentSuggester",
    "OUTPUT_TYPE_MAP",
    "Logger",
    "ProjectAnalyzer",
    "ProjectGenerator",
    "ProjectGeneratorDialog",
    "AIClient",
    "TemplateLoader",
    "cpp_module",
]

# Información del paquete
__all__ += ["__version__", "__author__", "__email__", "__license__"]
