import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

class PythonBuildStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'python-build'

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
        # python-build solo se usa para empaquetar, no para compilar
        return self.build_package_command(file_path, output_path, extra_args)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        """
        Construye el comando para generar una rueda (wheel) con python-build.
        """
        extra_args = extra_args or []
        cmd = ['python', '-m', 'build', '--wheel']
        if extra_args:
            cmd.extend(extra_args)
        cwd = os.path.dirname(file_path) or None
        post_actions = []
        if output_path:
            post_actions.append(('wheel_move', output_path))
        return cmd, cwd, post_actions

STRATEGY_CLASS = PythonBuildStrategy