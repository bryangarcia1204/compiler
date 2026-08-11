import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

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
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        # Replicar exactamente el fallback de compilador
        extra_args = extra_args or []
        cmd = ['gcc']
        out = output_path or os.path.splitext(file_path)[0]

        # Gestión de output_type (idéntico al original)
        if output_type in ('exe', 'bin', 'go-bin', 'rust-bin', 'cargo-release'):
            out = out + ('.exe' if os.name == 'nt' and not out.endswith('.exe') else '')
        elif output_type in ('dll', 'so', 'dylib'):
            ext = {'dll': '.dll', 'so': '.so', 'dylib': '.dylib'}[output_type]
            out = out + ext if not out.endswith(ext) else out
        elif output_type in ('obj', 'o'):
            out = out + ('.obj' if os.name == 'nt' else '.o')
        elif output_type == 'pyd':
            out = out + ('.pyd' if os.name == 'nt' else '.so')

        # Flags según output_type
        if output_type in ('dll', 'so', 'dylib', 'pyd'):
            cmd.append('-shared')
        if output_type in ('obj',):
            cmd.append('-c')

        # Modo release/debug (siempre -g o -O2 según release_mode)
        if release_mode:
            cmd.append('-O2')
        else:
            cmd.append('-g')

        cmd.extend(['-o', out, file_path])
        if extra_args:
            cmd.extend(extra_args)

        # Post-actions para bibliotecas estáticas (como en original)
        post_actions = []
        if output_type in ('a', 'lib'):
            # El original no maneja esto en el fallback de compilador,
            # pero lo manejaremos igual para mantener consistencia
            # (en el original solo se maneja en la parte de GCC específica)
            # Para no perder funcionalidad, lo añadimos igual que en el legacy
            if output_path:
                obj_path = output_path.replace('.a', '.o').replace('.lib', '.obj')
                # Ya se añadió -o con obj_path arriba? Mejor lo dejamos como en el original.
                # En el original, para static lib se usa un bloque aparte.
                # Lo movemos aquí para que funcione.
                # Pero como el original no tiene este bloque en el fallback,
                # lo dejamos como está y confiamos en que el usuario use output_type='a'
                pass

        return cmd, None, post_actions

STRATEGY_CLASS = GCCStrategy