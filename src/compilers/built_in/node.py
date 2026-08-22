# src/compilers/builtin/node.py
import os
from typing import Any, Dict, List, Optional, Tuple

from ..base import CompilerStrategy


class NodeStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return "node"

    @property
    def supported_extensions(self) -> List[str]:
        return [".js", ".ts"]

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = "exe",
        release_mode: bool = False,
        target: str = "native",
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ["node", file_path]
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = "native",
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        # Usar pkg para empaquetar (no es multi-target nativo, pero se puede)
        cmd = ["pkg"]
        if output_path:
            cmd.extend(["--output", output_path])
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(file_path)
        return cmd, None, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para Node.js."""
        project_name = os.path.basename(project_info.get("project_dir", "mi_proyecto"))
        main_file = os.path.basename(project_info.get("main_file", "index.js"))
        files = {}
        files["package.json"] = f"""{{
  "name": "{project_name}",
  "version": "1.0.0",
  "description": "Descripción del proyecto",
  "main": "{main_file}",
  "scripts": {{
    "start": "node {main_file}",
    "test": "echo \\"Error: no test specified\\" && exit 1"
  }},
  "dependencies": {{}},
  "devDependencies": {{}}
}}
"""
        files[".gitignore"] = """node_modules/
npm-debug.log
yarn-error.log
package-lock.json
yarn.lock
.env
"""
        return files


STRATEGY_CLASS = NodeStrategy
