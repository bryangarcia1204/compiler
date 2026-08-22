import logging
import os
from datetime import datetime


class Logger:
    """Gestor de logs de la aplicación."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            # Configurar logging
            self.logger = logging.getLogger('CompiladorApp')
            self.logger.setLevel(logging.DEBUG)

            # Crear directorio de logs si no existe
            log_dir = os.path.join(os.path.expanduser('~'), '.compilador_app', 'logs')
            os.makedirs(log_dir, exist_ok=True)

            # Handler para archivo
            log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            # Handler para consola
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Formato
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def critical(self, msg):
        self.logger.critical(msg)
