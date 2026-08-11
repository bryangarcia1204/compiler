import os
from typing import List, Tuple, Optional, Any
from ..base import CompilerStrategy

class DotnetStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'dotnet'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.cs', '.csproj', '.sln']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []

        # Si es .cs suelto, usar csc
        if file_path.endswith('.cs'):
            out = output_path or os.path.splitext(file_path)[0] + ('.exe' if os.name == 'nt' else '')
            cmd = ['csc', f'/out:{out}', file_path]
            if extra_args:
                cmd.extend(extra_args)
            return cmd, None, []

        # Si es proyecto, usar dotnet build
        cmd = ['dotnet', 'build']
        if release_mode:
            cmd.extend(['-c', 'Release'])
        if output_path:
            outdir = os.path.dirname(output_path)
            if outdir:
                cmd.extend(['-o', outdir])
        if extra_args:
            cmd.extend(extra_args)
        if file_path.endswith(('.csproj', '.sln')):
            cmd.append(file_path)
        cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
        return cmd, cwd, []

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['dotnet', 'publish']
        if output_path:
            outdir = os.path.dirname(output_path)
            if outdir:
                cmd.extend(['-o', outdir])
        if extra_args:
            cmd.extend(extra_args)
        if file_path.endswith(('.csproj', '.sln')):
            cmd.append(file_path)
        cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
        return cmd, cwd, []

STRATEGY_CLASS = DotnetStrategy