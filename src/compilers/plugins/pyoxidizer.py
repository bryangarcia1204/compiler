# src/compilers/plugins/pyoxidizer.py
"""
Plugin para PyOxidizer: Empaquetador multi-target para Python.
Soporta compilación cruzada a Windows, Linux, macOS y más.
"""

import os
import shutil
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy
from ...target_manager import TargetManager


class PyOxidizerStrategy(CompilerStrategy):
    """
    Estrategia para PyOxidizer, empaquetador multi-target.
    Genera ejecutables nativos para múltiples plataformas.
    """

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
        """
        PyOxidizer genera ejecutables, no compila en sí.
        Usamos build_package_command.
        """
        return self.build_package_command(file_path, output_path, extra_args, target)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        """
        Construye el comando para PyOxidizer.
        """
        extra_args = extra_args or []
        post_actions = []

        # Verificar si PyOxidizer está instalado
        if not shutil.which('pyoxidizer'):
            return [], None, []

        # Comando base
        cmd = ['pyoxidizer', 'build']

        # ── Target ──
        if target != 'native':
            # Mapear target a formato PyOxidizer
            # https://pyoxidizer.readthedocs.io/en/stable/pyoxidizer_cross_compilation.html
            pyo_target = self._map_target_to_pyoxidizer(target)
            if pyo_target:
                cmd.extend(['--target', pyo_target])

        # ── Archivo de configuración ──
        # PyOxidizer necesita un archivo pyoxidizer.toml o pyoxidizer.bzl
        config_file = self._create_config_file(file_path, output_path, target)
        if config_file:
            cmd.extend(['--config', config_file])

        # ── Argumentos extra ──
        if extra_args:
            cmd.extend(extra_args)

        # ── Post-actions ──
        if output_path:
            post_actions.append(('move', self._get_output_path(file_path, output_path, target), output_path))

        # ── Directorio de trabajo ──
        cwd = os.path.dirname(file_path) or None

        return cmd, cwd, post_actions

    def _map_target_to_pyoxidizer(self, target: str) -> Optional[str]:
        """
        Mapea nombres de target a los que soporta PyOxidizer.
        """
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

    def _create_config_file(self, file_path: str, output_path: Optional[str], target: str) -> Optional[str]:
        """
        Crea un archivo de configuración pyoxidizer.toml si no existe.
        """
        # Buscar si ya existe un archivo de configuración
        cwd = os.path.dirname(file_path) or '.'
        config_paths = [
            os.path.join(cwd, 'pyoxidizer.toml'),
            os.path.join(cwd, 'pyoxidizer.bzl'),
        ]

        for path in config_paths:
            if os.path.exists(path):
                return path

        # Si no existe, creamos uno básico
        config_path = os.path.join(cwd, 'pyoxidizer.toml')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_config_content(file_path, output_path, target))
            return config_path
        except Exception as e:
            return None

    def _generate_config_content(self, file_path: str, output_path: Optional[str], target: str) -> str:
        """
        Genera el contenido de pyoxidizer.toml.
        """
        app_name = os.path.splitext(os.path.basename(file_path))[0]
        output_name = os.path.basename(output_path) if output_path else app_name

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
build_mode = "release"  # release o debug

[target.output]
name = "{output_name}"
path = "dist/"
'''

    def _get_output_path(self, file_path: str, output_path: Optional[str], target: str) -> str:
        """
        Determina la ruta del archivo de salida generado por PyOxidizer.
        """
        name = os.path.splitext(os.path.basename(file_path))[0]
        ext = '.exe' if target == 'windows-x86_64' or target == 'windows-x86' else ''
        output_name = os.path.basename(output_path) if output_path else f"{name}{ext}"

        # PyOxidizer guarda en dist/
        return os.path.join(os.path.dirname(file_path) or '.', 'dist', output_name)

    def generate_config_files(self, project_info: dict, target: str = 'native') -> dict:
        """
        Genera pyoxidizer.toml para el target especificado.
        """
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
# Registro del plugin
STRATEGY_CLASS = PyOxidizerStrategy