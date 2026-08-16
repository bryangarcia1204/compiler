# src/compilers/builtin/python_build.py
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
        cmd = ['python', '-m', 'build', '--wheel']
        if extra_args:
            cmd.extend(extra_args)
        cwd = os.path.dirname(file_path) or None
        post_actions = []
        if output_path:
            post_actions.append(('wheel_move', output_path))
        return cmd, cwd, post_actions


STRATEGY_CLASS = PythonBuildStrategy