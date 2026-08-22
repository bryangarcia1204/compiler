# src/target_manager.py
"""
Gestión de targets de compilación cruzada.
Detecta herramientas disponibles y genera los comandos adecuados.
"""


import platform
import shutil

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from . import logger

log = logger.Logger()


class OSTarget(Enum):
    """Sistemas operativos destino."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    DARWIN = "darwin"
    FREEBSD = "freebsd"
    ANDROID = "android"
    IOS = "ios"
    WASM = "wasm"


class ArchTarget(Enum):
    """Arquitecturas destino."""
    X86_64 = "x86_64"
    X86 = "x86"
    ARM64 = "arm64"
    AMD64 = "amd64"
    ARM = "arm"
    RISCV64 = "riscv64"
    RISCV32 = "riscv32"
    WASM32 = "wasm32"


@dataclass
class CompilerTarget:
    """Representa un target de compilación."""
    os: OSTarget
    arch: ArchTarget
    triple: str  # Ej: x86_64-pc-windows-gnu
    description: str

    def __str__(self) -> str:
        return f"{self.os.value}-{self.arch.value}"


class TargetManager:
    """Gestor de targets de compilación cruzada."""

    # ── TARGETS PREDEFINIDOS ──
    TARGETS = {
        "native": CompilerTarget(
            os=OSTarget(platform.system().lower()),
            arch=ArchTarget(platform.machine().lower()),
            triple="native",
            description="Sistema nativo (auto-detectado)"
        ),
        "windows-x86_64": CompilerTarget(
            os=OSTarget.WINDOWS,
            arch=ArchTarget.X86_64,
            triple="x86_64-pc-windows-gnu",
            description="Windows 64-bit (MinGW)"
        ),
        "windows-x86": CompilerTarget(
            os=OSTarget.WINDOWS,
            arch=ArchTarget.X86,
            triple="i686-pc-windows-gnu",
            description="Windows 32-bit (MinGW)"
        ),
        "linux-x86_64": CompilerTarget(
            os=OSTarget.LINUX,
            arch=ArchTarget.X86_64,
            triple="x86_64-unknown-linux-gnu",
            description="Linux 64-bit"
        ),
        "linux-arm64": CompilerTarget(
            os=OSTarget.LINUX,
            arch=ArchTarget.ARM64,
            triple="aarch64-unknown-linux-gnu",
            description="Linux ARM64"
        ),
        "linux-arm": CompilerTarget(
            os=OSTarget.LINUX,
            arch=ArchTarget.ARM,
            triple="arm-unknown-linux-gnueabihf",
            description="Linux ARM 32-bit"
        ),
        "macos-x86_64": CompilerTarget(
            os=OSTarget.MACOS,
            arch=ArchTarget.X86_64,
            triple="x86_64-apple-darwin",
            description="macOS 64-bit"
        ),
        "macos-arm64": CompilerTarget(
            os=OSTarget.MACOS,
            arch=ArchTarget.ARM64,
            triple="aarch64-apple-darwin",
            description="macOS ARM64 (Apple Silicon)"
        ),
        "wasm32": CompilerTarget(
            os=OSTarget.WASM,
            arch=ArchTarget.WASM32,
            triple="wasm32-unknown-unknown",
            description="WebAssembly 32-bit"
        ),
        "nodejs": CompilerTarget(
            os=OSTarget(platform.system().lower()),
            arch=ArchTarget(platform.machine().lower()),
            triple="nodejs",
            description="Node.js nativo (auto-detectado)"
        ),
        "electron": CompilerTarget(
            os=OSTarget(platform.system().lower()),
            arch=ArchTarget(platform.machine().lower()),
            triple="electron",
            description="Electron nativo (auto-detectado)"
        ),
    }

    # ── DETECCIÓN DE HERRAMIENTAS ──
    @staticmethod
    def get_available_tools() -> Dict[str, List[str]]:
        """
        Detecta las herramientas de cross-compilation disponibles.
        Retorna {target_name: [comandos_disponibles]}
        """
        tools = {}
        system = platform.system()

        # 1. MinGW (Windows → Windows/Linux)
        if shutil.which('x86_64-w64-mingw32-gcc'):
            tools.setdefault('windows-x86_64', []).append('mingw')
            tools.setdefault('windows-x86', []).append('mingw')
        if shutil.which('i686-w64-mingw32-gcc'):
            tools.setdefault('windows-x86', []).append('mingw')

        # 2. Zig (multi-target)
        if shutil.which('zig'):
            # Zig soporta muchos targets
            for target in TargetManager.TARGETS:
                if target != 'native':
                    tools.setdefault(target, []).append('zig')

        # 3. Cross-compiler Linux (para ARM)
        if shutil.which('aarch64-linux-gnu-gcc'):
            tools.setdefault('linux-arm64', []).append('gcc-cross')
        if shutil.which('arm-linux-gnueabihf-gcc'):
            tools.setdefault('linux-arm', []).append('gcc-cross')

        # 4. OSXCross (macOS en Linux)
        if shutil.which('osxcross'):
            tools.setdefault('macos-x86_64', []).append('osxcross')
            tools.setdefault('macos-arm64', []).append('osxcross')

        # 5. Emscripten (WASM)
        if shutil.which('emcc'):
            tools.setdefault('wasm32', []).append('emscripten')

        return tools

    @staticmethod
    def get_target(target_name: str) -> Optional[CompilerTarget]:
        """Obtiene un target por su nombre."""
        return TargetManager.TARGETS.get(target_name)

    @staticmethod
    def get_all_targets() -> List[str]:
        """Lista de todos los nombres de targets disponibles."""
        return list(TargetManager.TARGETS.keys())

    @staticmethod
    def get_available_targets() -> List[str]:
        """
        Retorna los targets para los que hay herramientas instaladas.
        """
        available = []
        tools = TargetManager.get_available_tools()
        for target_name in TargetManager.get_all_targets():
            if target_name in tools and tools[target_name]:
                available.append(target_name)
        if not available:
            # Al menos el nativo siempre está disponible
            available.append('native')
        return available

    @staticmethod
    def get_target_triple(target_name: str) -> Optional[str]:
        """Obtiene el triple del target."""
        target = TargetManager.get_target(target_name)
        if target:
            return target.triple
        return None

    @staticmethod
    def get_compiler_prefix(target_name: str) -> Optional[str]:
        """
        Devuelve el prefijo del compilador para el target.
        Ej: 'x86_64-w64-mingw32-' para MinGW.
        """
        target = TargetManager.get_target(target_name)
        if not target:
            return None

        triple = target.triple

        # MinGW
        if target.os == OSTarget.WINDOWS:
            if target.arch == ArchTarget.X86_64:
                return 'x86_64-w64-mingw32-'
            elif target.arch == ArchTarget.X86:
                return 'i686-w64-mingw32-'

        # Linux cross
        if target.os == OSTarget.LINUX:
            if target.arch == ArchTarget.ARM64:
                return 'aarch64-linux-gnu-'
            elif target.arch == ArchTarget.ARM:
                return 'arm-linux-gnueabihf-'

        # Si no hay prefijo, usar el compilador nativo
        return None

    @staticmethod
    def get_zig_target(target_name: str) -> Optional[str]:
        """Obtiene el target para Zig (ej: 'x86_64-windows-gnu')."""
        target = TargetManager.get_target(target_name)
        if not target:
            return None

        # Mapeo de triples a formato Zig
        zig_map = {
            'x86_64-pc-windows-gnu': 'x86_64-windows-gnu',
            'i686-pc-windows-gnu': 'i686-windows-gnu',
            'x86_64-unknown-linux-gnu': 'x86_64-linux-gnu',
            'aarch64-unknown-linux-gnu': 'aarch64-linux-gnu',
            'arm-unknown-linux-gnueabihf': 'arm-linux-gnueabihf',
            'x86_64-apple-darwin': 'x86_64-macos',
            'aarch64-apple-darwin': 'aarch64-macos',
            'wasm32-unknown-unknown': 'wasm32-wasi',
        }
        return zig_map.get(target.triple)

    @staticmethod
    def get_rust_target(target_name: str) -> Optional[str]:
        """Obtiene el target para Rust (ej: 'x86_64-pc-windows-gnu')."""
        target = TargetManager.get_target(target_name)
        if target:
            return target.triple
        return None