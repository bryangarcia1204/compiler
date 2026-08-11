import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

class JavaStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'java'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.java']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['javac', file_path]
        post_actions = []
        if output_path and output_path.endswith('.jar'):
            class_dir = os.path.dirname(file_path)
            post_actions.append(('jar', output_path, class_dir))
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, post_actions

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        jar_name = output_path or os.path.splitext(os.path.basename(file_path))[0] + '.jar'
        class_dir = os.path.dirname(file_path)
        cmd = ['jar', 'cf', jar_name, '-C', class_dir, '.']
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

STRATEGY_CLASS = JavaStrategy