import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

class WasmPackStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'wasm-pack'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.rs', '.wasm', '.c', '.cpp']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        # wasm-pack se usa principalmente para empaquetar, pero también puede compilar
        # Si output_type == 'wasm', usamos build_package_command
        if output_type == 'wasm':
            return self.build_package_command(file_path, output_path, extra_args)
        # Si no, caemos en el fallback genérico (o podríamos usar build normalmente)
        # Pero para wasm-pack, lo más común es empaquetar.
        return self.build_package_command(file_path, output_path, extra_args)

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['wasm-pack', 'build']
        if output_path:
            # wasm-pack no tiene flag directo para output, pero podemos usar --out-dir
            out_dir = os.path.dirname(output_path)
            if out_dir:
                cmd.extend(['--out-dir', out_dir])
        if extra_args:
            cmd.extend(extra_args)
        cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
        return cmd, cwd, []

STRATEGY_CLASS = WasmPackStrategy