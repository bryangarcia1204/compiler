import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

class GPPStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'g++'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.cpp', '.cc', '.cxx']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['g++']
        out = output_path or os.path.splitext(file_path)[0]

        if output_type in ('exe', 'bin', 'go-bin', 'rust-bin', 'cargo-release'):
            out = out + ('.exe' if os.name == 'nt' and not out.endswith('.exe') else '')
        elif output_type in ('dll', 'so', 'dylib'):
            ext = {'dll': '.dll', 'so': '.so', 'dylib': '.dylib'}[output_type]
            out = out + ext if not out.endswith(ext) else out
        elif output_type in ('obj', 'o'):
            out = out + ('.obj' if os.name == 'nt' else '.o')
        elif output_type == 'pyd':
            out = out + ('.pyd' if os.name == 'nt' else '.so')

        if output_type in ('dll', 'so', 'dylib', 'pyd'):
            cmd.append('-shared')
        if output_type in ('obj',):
            cmd.append('-c')

        if release_mode:
            cmd.append('-O2')
        else:
            cmd.append('-g')

        cmd.extend(['-o', out, file_path])
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

STRATEGY_CLASS = GPPStrategy