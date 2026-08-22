# src/compilers/plugins/electron_builder.py
"""
Plugin para electron-builder: Empaquetador multi-target para Node.js/Electron.
Soporta compilación cruzada a Windows, Linux y macOS.
"""

import json
import os
import shutil
from typing import Any, List, Optional, Tuple

from src.compilers.base import CompilerStrategy


class ElectronBuilderStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return "electron-builder"

    @property
    def supported_extensions(self) -> List[str]:
        return [".js", ".ts", ".jsx", ".tsx", ".html", ".json"]

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = "exe",
        release_mode: bool = False,
        target: str = "native",
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        return self.build_package_command(file_path, output_path, extra_args, target, release_mode)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = "native",
        release_mode: bool = False,
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []

        # Verificar si npx está disponible
        if not shutil.which("npx"):
            return [], None, []

        # Detectar si es un proyecto Electron válido
        package_json_path = self._find_package_json(file_path)
        if not package_json_path:
            return [], None, []

        cmd = ["npx", "electron-builder"]

        # ── Modo release ──
        if release_mode:
            cmd.append("--publish")  # o '--config' según sea necesario

        # ── Flags de plataforma ──
        if target == "windows-x86_64":
            cmd.extend(["--win", "--x64"])
        elif target == "windows-x86":
            cmd.extend(["--win", "--ia32"])
        elif target == "windows-arm64":
            cmd.extend(["--win", "--arm64"])
        elif target == "macos-x86_64":
            cmd.extend(["--mac", "--x64"])
        elif target == "macos-arm64":
            cmd.extend(["--mac", "--arm64"])
        elif target == "macos-universal":
            cmd.extend(["--mac", "--universal"])
        elif target == "linux-x86_64":
            cmd.extend(["--linux", "--x64"])
        elif target == "linux-arm64":
            cmd.extend(["--linux", "--arm64"])
        else:
            # nativo: electron-builder detecta la plataforma actual
            cmd.append("--dir")

        if extra_args:
            cmd.extend(extra_args)

        cwd = os.path.dirname(package_json_path) or "."
        return cmd, cwd, []

    def _find_package_json(self, file_path: str) -> Optional[str]:
        search_dir = os.path.dirname(file_path) if os.path.isfile(file_path) else file_path
        for root, _, files in os.walk(search_dir):
            if "package.json" in files:
                return os.path.join(root, "package.json")
        return None

    def generate_config_files(self, project_info: dict, target: str = "native") -> dict:
        config = {
            "appId": "com.example.app",
            "productName": project_info.get("project_name", "MyApp"),
            "directories": {"output": "dist"},
            "files": ["**/*"],
            "win": (
                {"target": "nsis", "icon": "build/icon.ico"} if target.startswith("windows") else {}
            ),
            "mac": (
                {"target": "dmg", "icon": "build/icon.icns"} if target.startswith("macos") else {}
            ),
            "linux": (
                {"target": "AppImage", "icon": "build/icon.png"}
                if target.startswith("linux")
                else {}
            ),
        }
        config = {k: v for k, v in config.items() if v}
        return {"electron-builder.json": json.dumps(config, indent=2)}


STRATEGY_CLASS = ElectronBuilderStrategy
