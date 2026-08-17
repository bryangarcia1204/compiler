# src/compilers/builtin/emcc.py
import os
from typing import List, Tuple, Optional, Any
from src.compilers.base import CompilerStrategy


class EmscriptenStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'emscripten'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.c', '.cpp', '.cxx']

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
        if output_type != 'wasm':
            # Fallback a None si no es wasm
            return None, None, []
        out = output_path or os.path.splitext(file_path)[0] + '.wasm'
        cmd = ['emcc', file_path, '-o', out]
        if release_mode:
            cmd.append('-O2')
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        return self.build_command(file_path, output_path, extra_args, 'wasm', False, target)


STRATEGY_CLASS = EmscriptenStrategy