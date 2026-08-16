# src/compilers/builtin/gcc.py
import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy
from ...target_manager import TargetManager


class GCCStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'gcc'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.c']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False,
        target: str = 'native'   # <-- NUEVO: target por defecto
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['gcc']
        out = output_path or os.path.splitext(file_path)[0]

        # ── CROSS-COMPILATION ──
        if target != 'native':
            target_info = TargetManager.get_target(target)
            if target_info:
                # Verificar si hay herramientas
                available = TargetManager.get_available_tools()
                tools = available.get(target, [])

                if 'zig' in tools:
                    # Usar Zig como compilador cruzado
                    cmd = ['zig', 'cc']
                    zig_target = TargetManager.get_zig_target(target)
                    if zig_target:
                        cmd.extend(['-target', zig_target])
                else:
                    # Usar MinGW o cross-gcc
                    prefix = TargetManager.get_compiler_prefix(target)
                    if prefix:
                        cmd = [f'{prefix}gcc']

        # ── RESTANTE COMANDO (sin cambios) ──
        if release_mode:
            cmd.append('-O2')
        else:
            cmd.append('-g')

        if output_type == 'obj':
            cmd.append('-c')
        elif output_type in ('dll', 'so', 'dylib'):
            cmd.append('-shared')
        elif output_type in ('a', 'lib'):
            cmd.append('-c')
            if output_path:
                obj_path = output_path.replace('.a', '.o').replace('.lib', '.obj')
                cmd.extend(['-o', obj_path])
                post_actions = [('archive', (obj_path, output_path))]
            else:
                post_actions = []
        else:
            post_actions = []

        if output_path and output_type not in ('a', 'lib'):
            cmd.extend(['-o', output_path])

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(file_path)
        return cmd, None, post_actions


STRATEGY_CLASS = GCCStrategy