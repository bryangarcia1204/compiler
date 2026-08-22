# src/compilers/builtin/pyinstaller.py
import os
from typing import List, Tuple, Optional, Any, Dict
from src.compilers.base import CompilerStrategy
from src.utils import logger

log = logger.Logger()


class PyInstallerStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'pyinstaller'

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
        return self.build_package_command(file_path, output_path, extra_args, target)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        if target != 'native':
            # Advertir que PyInstaller no soporta cross-compilation
            log.warning(f"[PyInstaller] PyInstaller no soporta cross-compilation a {target}. Se usará el target nativo.")
        cmd = ['pyinstaller', '--onefile', '--noconsole']
        if output_path:
            base_dir = os.path.dirname(output_path)
            if base_dir:
                cmd.extend(['--distpath', base_dir])
            if os.path.splitext(output_path)[1]:
                output_name = os.path.splitext(os.path.basename(output_path))[0]
                cmd.extend(['--name', output_name])
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(file_path)
        return cmd, None, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para PyInstaller."""
        # PyInstaller no necesita archivos de configuración específicos
        return {}


STRATEGY_CLASS = PyInstallerStrategy
