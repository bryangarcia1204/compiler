import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

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
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        # Para pyinstaller, usamos build_package_command
        return self.build_package_command(file_path, output_path, extra_args)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
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

STRATEGY_CLASS = PyInstallerStrategy