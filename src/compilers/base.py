from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Any

class CompilerStrategy(ABC):
    """
    Clase base para todas las estrategias de compilación.
    """

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Nombre de la herramienta (ej: 'gcc')."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Extensiones de archivo que soporta (ej: ['.c'])."""
        pass

    # src/compilers/base.py
    @abstractmethod
    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = '',
        release_mode: bool = False,
        target: str = 'native'  # <-- NUEVO
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        """
        Construye el comando de compilación/ejecución.

        Returns:
            Tupla (cmd, cwd, post_actions)
        """
        pass

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native'  # <-- NUEVO
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        """
        (Opcional) Construye el comando para empaquetar.
        Por defecto, usa build_command con output_type='exe'.
        """
        return self.build_command(file_path, output_path, extra_args, 'exe', False, target)

    def generate_config_files(self, project_info: dict, target: str = 'native') -> dict:
        """
        Genera archivos de configuración adicionales para el target específico.
        Por defecto retorna dict vacío.
        Los plugins pueden sobrescribir este método.
        """
        return {}