# src/compilers/plugins/pyoxidizer.py
"""
Plugin para PyOxidizer: Empaquetador multi-target para Python.
Soporta compilación cruzada a Windows, Linux, macOS y más.
"""

import os
import shutil
from typing import List, Tuple, Optional, Any
from src.compilers.base import CompilerStrategy
from src.target_manager import TargetManager


class PyOxidizerStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'pyoxidizer'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.py']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        return self.build_package_command(file_path, output_path, extra_args, target, release_mode)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native',
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        post_actions = []

        if not shutil.which('pyoxidizer'):
            return [], None, []

        cmd = ['pyoxidizer', 'build']

        # ── Modo release ──
        if release_mode:
            cmd.append('--release')

        # ── Target ──
        if target != 'native':
            pyo_target = self._map_target_to_pyoxidizer(target)
            if pyo_target:
                cmd.extend(['--target', pyo_target])

        # ── Archivo de configuración ──
        config_file = self._create_config_file(file_path, output_path, target, release_mode)
        if config_file:
            cmd.extend(['--config', config_file])

        if extra_args:
            cmd.extend(extra_args)

        if output_path:
            post_actions.append(('move', self._get_output_path(file_path, output_path, target), output_path))

        cwd = os.path.dirname(file_path) or None
        return cmd, cwd, post_actions

    def _map_target_to_pyoxidizer(self, target: str) -> Optional[str]:
        target_map = {
            'windows-x86_64': 'x86_64-pc-windows-msvc',
            'windows-x86': 'i686-pc-windows-msvc',
            'linux-x86_64': 'x86_64-unknown-linux-gnu',
            'linux-arm64': 'aarch64-unknown-linux-gnu',
            'linux-arm': 'arm-unknown-linux-gnueabihf',
            'macos-x86_64': 'x86_64-apple-darwin',
            'macos-arm64': 'aarch64-apple-darwin',
        }
        return target_map.get(target)

    def _create_config_file(self, file_path: str, output_path: Optional[str], target: str, release_mode: bool) -> Optional[str]:
        cwd = os.path.dirname(file_path) or '.'
        config_paths = [
            os.path.join(cwd, 'pyoxidizer.toml'),
            os.path.join(cwd, 'pyoxidizer.bzl'),
        ]
        for path in config_paths:
            if os.path.exists(path):
                return path

        config_path = os.path.join(cwd, 'pyoxidizer.toml')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_config_content(file_path, output_path, target, release_mode))
            return config_path
        except Exception:
            return None

    def _generate_config_content(self, file_path: str, output_path: Optional[str], target: str, release_mode: bool) -> str:
        app_name = os.path.splitext(os.path.basename(file_path))[0]
        output_name = os.path.basename(output_path) if output_path else app_name
        build_mode = "release" if release_mode else "debug"

        return f'''# Archivo de configuración para PyOxidizer
# Generado automáticamente por Compilador Profesional

[env]
PYTHONPATH = "."

[python]
distribution_flavor = "standalone"
python_version = "3.12"

[python.pip]
enabled = true
packages = []

[application]
name = "{app_name}"
main_script = "{os.path.basename(file_path)}"
resources = ["."]

[target]
# Target: {target if target != 'native' else 'nativo'}
build_mode = "{build_mode}"

[target.output]
name = "{output_name}"
path = "dist/"
'''

    def _get_output_path(self, file_path: str, output_path: Optional[str], target: str) -> str:
        name = os.path.splitext(os.path.basename(file_path))[0]
        ext = '.exe' if target == 'windows-x86_64' or target == 'windows-x86' else ''
        output_name = os.path.basename(output_path) if output_path else f"{name}{ext}"
        return os.path.join(os.path.dirname(file_path) or '.', 'dist', output_name)

    def generate_config_files(self, project_info: dict, target: str = 'native') -> dict:
        app_name = project_info.get('project_name', 'myapp')
        main_script = os.path.basename(project_info.get('main_file', 'main.py'))
        target_triple = TargetManager.get_target_triple(target) or 'native'

        config = f'''# Archivo de configuración para PyOxidizer
# Generado automáticamente por Compilador Profesional

[env]
PYTHONPATH = "."

[python]
distribution_flavor = "standalone"
python_version = "3.12"

[python.pip]
enabled = true
packages = []

[application]
name = "{app_name}"
main_script = "{main_script}"
resources = ["."]

[target]
# Target: {target}
build_mode = "release"

[target.output]
name = "{app_name}"
path = "dist/"
'''
        return {'pyoxidizer.toml': config}


STRATEGY_CLASS = PyOxidizerStrategy