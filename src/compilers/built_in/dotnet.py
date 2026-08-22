# src/compilers/builtin/dotnet.py
import os
from typing import Any, Dict, List, Optional, Tuple

from ..base import CompilerStrategy


class DotnetStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return "dotnet"

    @property
    def supported_extensions(self) -> List[str]:
        return [".cs", ".csproj", ".sln"]

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = "exe",
        release_mode: bool = False,
        target: str = "native",
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []

        if file_path.endswith(".cs"):
            out = output_path or os.path.splitext(file_path)[0] + (
                ".exe" if os.name == "nt" else ""
            )
            cmd = ["csc", f"/out:{out}", file_path]
            if extra_args:
                cmd.extend(extra_args)
            return cmd, None, []

        cmd = ["dotnet", "build"]
        if release_mode:
            cmd.extend(["-c", "Release"])
        if output_path:
            outdir = os.path.dirname(output_path)
            if outdir:
                cmd.extend(["-o", outdir])
        if extra_args:
            cmd.extend(extra_args)
        if file_path.endswith((".csproj", ".sln")):
            cmd.append(file_path)
        cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
        return cmd, cwd, []

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = "native",
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ["dotnet", "publish"]
        if output_path:
            outdir = os.path.dirname(output_path)
            if outdir:
                cmd.extend(["-o", outdir])
        if extra_args:
            cmd.extend(extra_args)
        if file_path.endswith((".csproj", ".sln")):
            cmd.append(file_path)
        cwd = os.path.dirname(file_path) if os.path.isfile(file_path) else None
        return cmd, cwd, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para .NET."""
        project_name = os.path.basename(project_info.get("project_dir", "mi_proyecto"))
        files = {}
        files[f"{project_name}.csproj"] = f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <RootNamespace>{project_name}</RootNamespace>
  </PropertyGroup>
</Project>
"""
        files[".gitignore"] = """bin/
obj/
*.user
*.suo
"""
        return files


STRATEGY_CLASS = DotnetStrategy
