import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

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
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        out = output_path or os.path.splitext(file_path)[0]
        cmd = ['go', 'build', '-o', out, file_path]
        if release_mode:
            cmd.extend(['-ldflags', '-s -w'])
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        out = output_path or os.path.splitext(file_path)[0]
        cmd = ['go', 'build', '-o', out, file_path]
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

STRATEGY_CLASS = GoStrategy