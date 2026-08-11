import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

class RustStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'rust'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.rs']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        post_actions = []

        # Exactamente igual que el original
        if os.path.basename(file_path).lower() == 'cargo.toml' or os.path.isdir(os.path.join(os.path.dirname(file_path), 'src')):
            cmd = ['cargo', 'build']
            if release_mode:
                cmd.append('--release')
            cwd = os.path.dirname(file_path) or None
            if output_path:
                post_actions.append(('cargo_move', output_path))
            if extra_args:
                cmd.extend(extra_args)
            return cmd, cwd, post_actions
        else:
            out = output_path or os.path.splitext(file_path)[0] + ('.exe' if os.name == 'nt' else '')
            cmd = ['rustc', file_path, '-o', out]
            if extra_args:
                cmd.extend(extra_args)
            return cmd, None, post_actions

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        # Empaquetado: cargo build --release (igual que original)
        extra_args = extra_args or []
        cmd = ['cargo', 'build', '--release']
        if output_path:
            # En el original no se maneja output_path en empaquetado,
            # pero podemos mantenerlo igual.
            pass
        if extra_args:
            cmd.extend(extra_args)
        cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
        return cmd, cwd, []

STRATEGY_CLASS = RustStrategy