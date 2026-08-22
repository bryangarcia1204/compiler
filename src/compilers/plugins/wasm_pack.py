# src/compilers/builtin/wasm_pack.py
import os
from typing import Any, Dict, List, Optional, Tuple

from src.compilers.base import CompilerStrategy


class WasmPackStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return "wasm-pack"

    @property
    def supported_extensions(self) -> List[str]:
        return [".rs", ".wasm", ".c", ".cpp"]

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = "exe",
        release_mode: bool = False,
        target: str = "native",
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        if output_type == "wasm":
            return self.build_package_command(file_path, output_path, extra_args, target)
        return self.build_package_command(file_path, output_path, extra_args, target)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = "native",
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ["wasm-pack", "build"]
        if output_path:
            out_dir = os.path.dirname(output_path)
            if out_dir:
                cmd.extend(["--out-dir", out_dir])
        if extra_args:
            cmd.extend(extra_args)
        cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
        return cmd, cwd, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para PyInstaller."""
        # PyInstaller no necesita archivos de configuración específicos
        return {}


STRATEGY_CLASS = WasmPackStrategy
