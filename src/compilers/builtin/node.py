from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

class NodeStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'node'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.js']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['node', file_path]
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
        cmd = ['pkg']
        if output_path:
            cmd.extend(['--output', output_path])
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(file_path)
        return cmd, None, []

STRATEGY_CLASS = NodeStrategy