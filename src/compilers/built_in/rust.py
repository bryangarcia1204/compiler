# src/compilers/builtin/rust.py
import os
from typing import List, Tuple, Optional, Any, Dict
from ..base import CompilerStrategy
from ...target_manager import TargetManager


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
        release_mode: bool = False,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        post_actions = []

        is_cargo_project = (
            os.path.basename(file_path).lower() == 'cargo.toml' or
            os.path.isdir(os.path.join(os.path.dirname(file_path), 'src'))
        )

        if is_cargo_project:
            cmd = ['cargo', 'build']
            if release_mode:
                cmd.append('--release')
            if output_path:
                post_actions.append(('cargo_move', output_path))
            # ── TARGET ──
            if target != 'native':
                rust_target = TargetManager.get_rust_target(target)
                if rust_target:
                    # Primero, instalar el target si no está instalado
                    cmd.extend(['--target', rust_target])
            if extra_args:
                cmd.extend(extra_args)
            cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
            return cmd, cwd, post_actions
        else:
            out = output_path or os.path.splitext(file_path)[0] + ('.exe' if os.name == 'nt' else '')
            cmd = ['rustc', '-o', file_path, out]
            if target != 'native':
                rust_target = TargetManager.get_rust_target(target)
                if rust_target:
                    cmd.extend(['--target', rust_target])
            if release_mode:
                cmd.append('-C')
                cmd.append('opt-level=3')
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

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """
        Genera archivos de configuración para Rust.
        """
        project_name = os.path.basename(project_info.get('project_dir', 'mi_proyecto'))
        deps = list(project_info.get('dependencies', set()))[:5]
        dep_lines = '\n'.join(f'    "{dep}" = "latest"' for dep in deps if dep not in ['std'])

        files = {}

        # ── Cargo.toml ──
        files['Cargo.toml'] = f'''[package]
name = "{project_name}"
version = "0.1.0"
edition = "2021"

[dependencies]
{dep_lines if dep_lines else '# Añade aquí tus dependencias'}

[[bin]]
name = "{project_name}"
path = "src/main.rs"
'''

        # ── .gitignore ──
        files['.gitignore'] = """target/
Cargo.lock
*.rs.bk
"""

        return files


STRATEGY_CLASS = RustStrategy