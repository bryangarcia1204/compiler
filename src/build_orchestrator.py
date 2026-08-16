# src/build_orchestrator.py
"""
Orquestador de compilaciones multi-lenguaje.
Ejecuta pasos en el orden correcto según dependencias usando reglas.
"""

import os
import subprocess
from typing import List, Dict, Optional, Any

from . import logger
from .build_rules import BuildRules

log = logger.Logger()


class BuildStep:
    """Representa un paso de compilación."""
    def __init__(self, name: str, description: str, command: List[str], cwd: str = None):
        self.name = name
        self.description = description
        self.command = command
        self.cwd = cwd or os.getcwd()
        self.dependencies = []  # Lista de nombres de pasos que deben ejecutarse antes

    def run(self) -> bool:
        """Ejecuta el paso."""
        log.info(f"[Build] {self.description}")
        log.debug(f"[Build] Comando: {' '.join(self.command)}")
        try:
            result = subprocess.run(
                self.command,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=600
            )
            if result.returncode != 0:
                log.error(f"[Build] Error: {result.stderr}")
                return False
            log.info(f"[Build] ✅ {self.name} completado")
            return True
        except Exception as e:
            log.error(f"[Build] Error ejecutando {self.name}: {e}")
            return False


class BuildOrchestrator:
    """
    Orquesta la compilación de proyectos multi-lenguaje usando reglas.
    """

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.steps: List[BuildStep] = []

    # src/build_orchestrator.py - Modificar create_pipeline

    def create_pipeline(self, project_info: Dict) -> List[BuildStep]:
        """
        Crea un pipeline usando .compilador o las reglas de build.
        """
        self.steps = []

        # ── 1. Intentar usar .compilador ──
        from .compilador_config import CompiladorConfig
        config = CompiladorConfig(self.project_dir, auto_create=False)

        if config and config.config_path.exists():
            steps = config.get_build_steps()
            if steps:
                log.info("[BuildOrchestrator] Usando pasos de build desde .compilador")
                for step_info in steps:
                    language = step_info.get('language')
                    command = step_info.get('command')
                    if command and command != 'auto':
                        step = BuildStep(
                            name=f"build_{language}",
                            description=f"Compilando {language}",
                            command=command.split(),
                            cwd=self.project_dir
                        )
                        self.steps.append(step)
                    elif command == 'auto':
                        # Usar detección automática
                        self._add_auto_step(language)
                return self.steps

        # ── 2. Si no hay .compilador o no tiene steps, usar reglas ──
        return self.create_pipeline_from_rules(project_info)

    def _add_auto_step(self, language: str):
        """Añade un paso automático para un lenguaje usando la estrategia correspondiente"""
        from .compilers.registry import CompilerRegistry
        strategy = CompilerRegistry.get(language)
        if strategy:
            step = BuildStep(
                name=f"build_{language}",
                description=f"Compilando {language} (auto)",
                command=["echo", f"Compilando {language}..."],
                cwd=self.project_dir
            )
            self.steps.append(step)

    def create_pipeline_from_rules(self, project_info: Dict) -> List[BuildStep]:
        """
        Crea un pipeline usando las reglas de build.
        """
        self.steps = []
        build_plan = project_info.get('build_plan', [])

        if not build_plan:
            log.warning("[BuildOrchestrator] No hay plan de build. Ejecuta ProjectAnalyzer._detect_build_needs() primero.")
            return []

        for plan in build_plan:
            cmd = plan.get('build_command', '')
            command_list = cmd.split() if cmd else []
            step = BuildStep(
                name=plan.get('name', 'unknown'),
                description=plan.get('description', ''),
                command=command_list,
                cwd=self.project_dir
            )
            # Dependencias: si el plan tiene 'requires', añadirlas (opcional)
            requires = plan.get('requires', [])
            if requires:
                step.dependencies = [r for r in requires]
            self.steps.append(step)

        return self.steps

    def run(self) -> bool:
        """Ejecuta todos los pasos en orden."""
        log.info("[BuildOrchestrator] Iniciando pipeline de compilación...")
        for step in self.steps:
            if not step.run():
                log.error(f"[BuildOrchestrator] Falló el paso: {step.name}")
                return False
        log.info("[BuildOrchestrator] ✅ Pipeline completado exitosamente")
        return True