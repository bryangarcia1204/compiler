# src/compilers/builtin/pkg.py
from typing import List, Tuple, Optional, Any, Dict
from src.compilers.base import CompilerStrategy


class PkgStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'pkg'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.js']

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
        cmd = ['pkg']
        # pkg no tiene soporte explícito para cross-compilation, pero se puede usar target
        if output_path:
            cmd.extend(['--output', output_path])
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(file_path)
        return cmd, None, []
    
    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para PyInstaller."""
        # PyInstaller no necesita archivos de configuración específicos
        return {}


STRATEGY_CLASS = PkgStrategy