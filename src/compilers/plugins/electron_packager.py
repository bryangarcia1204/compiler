# src/compilers/plugins/electron_packager.py
"""
Plugin para electron-packager: Empaquetador simple para Node.js/Electron.
Soporta multi-target vía flags.
"""

import os
import shutil
from typing import List, Tuple, Optional, Any, Dict
from src.compilers.base import CompilerStrategy


class ElectronPackagerStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'electron-packager'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.js', '.ts', '.jsx', '.tsx']

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
        Electron-Packager genera ejecutables, no compila en sí.
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
        extra_args = extra_args or []

        if not shutil.which('npx'):
            return [], None, []

        app_name = os.path.splitext(os.path.basename(file_path))[0]
        src_dir = os.path.dirname(file_path) or '.'

        # Mapeo de target a flags
        platform_map = {
            'windows-x86_64': ('win32', 'x64'),
            'windows-x86': ('win32', 'ia32'),
            'windows-arm64': ('win32', 'arm64'),
            'macos-x86_64': ('darwin', 'x64'),
            'macos-arm64': ('darwin', 'arm64'),
            'linux-x86_64': ('linux', 'x64'),
            'linux-arm64': ('linux', 'arm64'),
        }

        platform, arch = platform_map.get(target, (None, None))

        cmd = ['npx', '@electron/packager', src_dir, app_name]

        if platform and arch:
            cmd.extend(['--platform', platform, '--arch', arch])
        # si es nativo, no se pasan flags → electron-packager usa la plataforma actual

        if output_path:
            cmd.extend(['--out', output_path])

        if extra_args:
            cmd.extend(extra_args)

        return cmd, None, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para PyInstaller."""
        # PyInstaller no necesita archivos de configuración específicos
        return {}


STRATEGY_CLASS = ElectronPackagerStrategy
