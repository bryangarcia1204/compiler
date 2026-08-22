# src/compilers/builtin/go.py
import os
from typing import List, Tuple, Optional, Any, Dict
from ..base import CompilerStrategy
from ...utils.target_manager import TargetManager


class GoStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'go'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.go']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        out = output_path or os.path.splitext(file_path)[0]

        # Go cross-compilation via environment variables
        
        if target != 'native':
            env = {}
            target_info = TargetManager.get_target(target)
            if target_info:
                goos_map = {
                    'windows': 'windows',
                    'linux': 'linux',
                    'macos': 'darwin',
                    'freebsd': 'freebsd',
                    'android': 'android',
                }
                goarch_map = {
                    'x86_64': 'amd64',
                    'x86': '386',
                    'arm64': 'arm64',
                    'arm': 'arm',
                    'riscv64': 'riscv64',
                    'wasm32': 'wasm',
                }
                os_name = target_info.os.value
                arch_name = target_info.arch.value
                if os_name in goos_map and arch_name in goarch_map:
                    env['GOOS'] = goos_map[os_name]
                    env['GOARCH'] = goarch_map[arch_name]

        cmd = ['go', 'build', '-o', out, file_path]
        if release_mode:
            cmd.extend(['-ldflags', '-s -w'])
        if extra_args:
            cmd.extend(extra_args)

        # Las variables de entorno se pasan en el proceso hijo (no en cmd)
        if target != 'native':
            return cmd, None, [], env
        else:
            return cmd, None, []

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        out = output_path or os.path.splitext(file_path)[0]
        cmd = ['go', 'build', '-o', out, file_path]
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para Go."""
        project_name = os.path.basename(project_info.get('project_dir', 'mi_proyecto'))
        files = {}
        files['go.mod'] = f'''module {project_name}

go 1.21

require (
    # Añade aquí tus dependencias
)
'''
        files['.gitignore'] = """*.exe
*.test
*.out
vendor/
"""
        return files


STRATEGY_CLASS = GoStrategy