# src/build_rules.py
"""
Sistema de reglas para orquestación de builds multi-lenguaje.
Cada regla define qué produce, qué necesita y cómo ejecutarse.
"""
import platform
from .compiler_detector import CompilerDetector
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class BuildArtifact(Enum):
    """Tipos de artefactos que puede producir un build."""
    # C/C++
    STATIC_LIB = "static_lib"
    SHARED_LIB = "shared_lib"
    EXECUTABLE = "executable"
    OBJECT_FILE = "object_file"
    PYD_MODULE = "pyd_module"
    SO_MODULE = "so_module"

    # Python
    PYTHON_PACKAGE = "python_package"
    WHEEL = "wheel"
    EGG = "egg"
    EXE_PYINSTALLER = "exe_pyinstaller"

    # Rust
    RUST_RLIB = "rust_rlib"
    RUST_CDYLIB = "rust_cdylib"
    RUST_EXE = "rust_exe"

    # Go
    GO_BIN = "go_bin"

    # Java
    JAR = "jar"
    CLASSES = "classes"

    # Node.js
    NODE_MODULES = "node_modules"
    NPM_PACKAGE = "npm_package"
    ELECTRON_APP = "electron_app"

    # Web
    WEB_BUNDLE = "web_bundle"
    WASM = "wasm"

    # Documentación
    DOCS = "docs"

    # General
    SOURCE = "source"
    CONFIG = "config"


@dataclass
class BuildRule:
    """Regla de build para un lenguaje/herramienta."""
    name: str
    language: str
    description: str

    # Qué produce
    produces: List[BuildArtifact] = field(default_factory=list)

    # Qué necesita (artefactos de otros lenguajes)
    requires: List[BuildArtifact] = field(default_factory=list)

    # Archivos de entrada típicos
    input_extensions: List[str] = field(default_factory=list)

    # Archivos de salida típicos
    output_extensions: List[str] = field(default_factory=list)

    # Comando de build
    build_command: Optional[str] = None

    # Si puede ejecutarse en paralelo con otros
    parallelizable: bool = True

    # Orden de prioridad (menor = más temprano)
    priority: int = 100


# ── REGISTRO DE REGLAS ──

class BuildRules:
    """Registro central de reglas de build."""

    _rules: Dict[str, BuildRule] = {}

    @classmethod
    def register(cls, rule: BuildRule):
        """Registra una regla."""
        cls._rules[rule.name] = rule

    @classmethod
    def get_rule(cls, name: str) -> Optional[BuildRule]:
        """Obtiene una regla por nombre."""
        return cls._rules.get(name)

    @classmethod
    def get_rules_for_language(cls, language: str) -> List[BuildRule]:
        """Obtiene todas las reglas para un lenguaje."""
        return [r for r in cls._rules.values() if r.language == language]

    @classmethod
    def get_rules_for_artifact(cls, artifact: BuildArtifact) -> List[BuildRule]:
        """Obtiene reglas que producen un artefacto específico."""
        return [r for r in cls._rules.values() if artifact in r.produces]

    @classmethod
    def get_rules_requiring(cls, artifact: BuildArtifact) -> List[BuildRule]:
        """Obtiene reglas que necesitan un artefacto específico."""
        return [r for r in cls._rules.values() if artifact in r.requires]

    @classmethod
    def build_order(cls, languages: List[str], summary: dict[str, Any] | None = None) -> List[str]:
        """
        Calcula el orden de ejecución basado en dependencias.
        Usa ordenamiento topológico.
        """
        # Filtrar reglas relevantes
        relevant = [r for r in cls._rules.values() if r.language in languages]

        if not relevant:
            return []

        # Construir grafo de dependencias
        graph = {r.name: [dep.name for dep in cls._rules.values() if dep.produces and any(
            a in r.requires for a in dep.produces
        )] for r in relevant} 

        if 'cpp_compile' in graph:
            if 'pybind11' in summary['imports']['c++']:
                graph.pop('cpp_compile')

        # Ordenamiento topológico simple
        result = []
        remaining = set(graph.keys())

        while remaining:
            # Encontrar nodos sin dependencias
            no_deps = [n for n in remaining if not graph.get(n, [])]
            if not no_deps:
                # Ciclo detectado, usar prioridad como fallback
                no_deps = sorted(remaining, key=lambda x: cls._rules[x].priority)
                # Tomar solo los primeros
                no_deps = no_deps[:1]

            for node in no_deps:
                result.append(node)
                remaining.remove(node)
                # Remover nodo de dependencias
                for deps in graph.values():
                    if node in deps:
                        deps.remove(node)
        return result


# ── REGISTRAR REGLAS POR DEFECTO ──

def _register_default_rules(tools:list):
    """Registra las reglas por defecto para todos los lenguajes."""

    # ── C / C++ ──
    BuildRules.register(BuildRule(
        name="cpp_compile",
        language="c++",
        description="Compila C++ a objetos y librerías",
        produces=[BuildArtifact.OBJECT_FILE, BuildArtifact.STATIC_LIB, BuildArtifact.SHARED_LIB],
        requires=[],
        input_extensions=[".cpp", ".cc", ".cxx", ".h", ".hpp"],
        output_extensions=[".o", ".a", ".so", ".dylib", ".dll"],
        build_command="make"  # o cmake
    ))

    # ── C++ → Python (pybind11) ──
    BuildRules.register(BuildRule(
        name="cpp_to_pyd",
        language="c++",
        description="Compila C++ a módulo Python .pyd",
        produces=[BuildArtifact.PYD_MODULE],
        requires=[],
        input_extensions=[".cpp", ".h", ".hpp"],
        output_extensions=[".pyd", ".so"],
        build_command=f"python setup.py build_ext --inplace {'-c mingw32' if platform.system() == 'Windows' and 'cl' not in tools else ''}",
        priority=10  # Va primero
    ))

    # ── Python ──
    BuildRules.register(BuildRule(
        name="python_package",
        language="python",
        description="Empaqueta Python a wheel o ejecutable",
        produces=[BuildArtifact.WHEEL, BuildArtifact.EXE_PYINSTALLER],
        requires=[BuildArtifact.PYD_MODULE, BuildArtifact.SO_MODULE],  # Depende de C++ si existe
        input_extensions=[".py"],
        output_extensions=[".whl", ".exe"],
        build_command="python -m build",
        priority=20
    ))

    # ── JavaScript / Node.js ──
    BuildRules.register(BuildRule(
        name="node_install",
        language="javascript",
        description="Instala dependencias Node.js",
        produces=[BuildArtifact.NODE_MODULES],
        requires=[],
        input_extensions=[".js", ".ts", ".json"],
        output_extensions=["node_modules/"],
        build_command="npm install",
        priority=30,
        parallelizable=True
    ))

    # ── Electron ──
    BuildRules.register(BuildRule(
        name="electron_builder",
        language="javascript",
        description="Empaqueta Electron",
        produces=[BuildArtifact.ELECTRON_APP],
        requires=[BuildArtifact.NODE_MODULES, BuildArtifact.EXE_PYINSTALLER],
        input_extensions=[".js", ".ts", ".html", ".css"],
        output_extensions=[".exe", ".dmg", ".AppImage"],
        build_command="npx electron-builder",
        priority=40
    ))

    # ── Rust ──
    BuildRules.register(BuildRule(
        name="rust_build",
        language="rust",
        description="Compila Rust",
        produces=[BuildArtifact.RUST_EXE, BuildArtifact.RUST_RLIB, BuildArtifact.RUST_CDYLIB],
        requires=[],
        input_extensions=[".rs"],
        output_extensions=[".exe", ".rlib", ".so"],
        build_command="cargo build",
        priority=10
    ))

    # ── Go ──
    BuildRules.register(BuildRule(
        name="go_build",
        language="go",
        description="Compila Go",
        produces=[BuildArtifact.GO_BIN],
        requires=[],
        input_extensions=[".go"],
        output_extensions=[".exe", ".go-bin"],
        build_command="go build",
        priority=10
    ))

    # ── Java ──
    BuildRules.register(BuildRule(
        name="java_compile",
        language="java",
        description="Compila Java",
        produces=[BuildArtifact.CLASSES, BuildArtifact.JAR],
        requires=[],
        input_extensions=[".java"],
        output_extensions=[".class", ".jar"],
        build_command="mvn compile",
        priority=10
    ))

    # ── Web / Frontend ──
    BuildRules.register(BuildRule(
        name="web_bundle",
        language="javascript",
        description="Construye bundle web",
        produces=[BuildArtifact.WEB_BUNDLE],
        requires=[BuildArtifact.NODE_MODULES],
        input_extensions=[".js", ".ts", ".jsx", ".tsx", ".css", ".scss"],
        output_extensions=[".js", ".css", ".html"],
        build_command="npm run build",
        priority=35
    ))

    # ── WASM ──
    BuildRules.register(BuildRule(
        name="wasm_build",
        language="cpp",
        description="Compila a WebAssembly",
        produces=[BuildArtifact.WASM],
        requires=[],
        input_extensions=[".c", ".cpp"],
        output_extensions=[".wasm"],
        build_command="emcc -o output.wasm",
        priority=10
    ))


# Registrar reglas al importar
detector = CompilerDetector()
tools = detector.get_all_tools()
_register_default_rules(tools)