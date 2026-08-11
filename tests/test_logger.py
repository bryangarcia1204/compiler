"""Pruebas para el sistema de logging."""
import unittest
import os
import sys
import tempfile
import logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logger import Logger


class TestLogger(unittest.TestCase):
    """Pruebas para Logger."""

    def setUp(self):
        # Limpiar instancia anterior y sus handlers del logger raíz
        if Logger._instance:
            logger = Logger._instance
            # Eliminar handlers del logger
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
            # También eliminar del logger raíz si existe (por si se añadieron)
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if handler.name == logger.logger.name or handler in logger.logger.handlers:
                    root_logger.removeHandler(handler)
        Logger._instance = None
        Logger._initialized = False

    def tearDown(self):
        if Logger._instance:
            logger = Logger._instance
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
            # Eliminar del logger raíz también
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if handler.name == logger.logger.name:
                    root_logger.removeHandler(handler)
            Logger._instance = None
            Logger._initialized = False

    def test_singleton(self):
        l1 = Logger()
        l2 = Logger()
        self.assertIs(l1, l2)

    def test_log_file_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('os.path.expanduser', return_value=tmpdir):
                logger = Logger()
                log_dir = os.path.join(tmpdir, '.compilador_app', 'logs')
                self.assertTrue(os.path.exists(log_dir))
                files = os.listdir(log_dir)
                self.assertGreater(len(files), 0)
                # Cerrar handlers para liberar archivo
                for handler in logger.logger.handlers:
                    handler.close()

    def test_log_methods(self):
        logger = Logger()
        with patch.object(logger.logger, 'debug') as mock_debug, \
             patch.object(logger.logger, 'info') as mock_info, \
             patch.object(logger.logger, 'warning') as mock_warning, \
             patch.object(logger.logger, 'error') as mock_error, \
             patch.object(logger.logger, 'critical') as mock_critical:

            logger.debug('debug msg')
            logger.info('info msg')
            logger.warning('warning msg')
            logger.error('error msg')
            logger.critical('critical msg')

            mock_debug.assert_called_once_with('debug msg')
            mock_info.assert_called_once_with('info msg')
            mock_warning.assert_called_once_with('warning msg')
            mock_error.assert_called_once_with('error msg')
            mock_critical.assert_called_once_with('critical msg')

    def test_log_levels(self):
        logger = Logger()
        # Buscar el file handler que pertenece a este logger (por nombre)
        file_handler = None
        for h in logger.logger.handlers:
            if isinstance(h, logging.FileHandler):
                # Asegurarnos de que es el handler recién creado (podemos comprobar que su nivel es DEBUG)
                if h.level == logging.DEBUG:
                    file_handler = h
                    break
        # Si no encontramos ninguno con DEBUG, buscar el primer FileHandler
        if file_handler is None:
            for h in logger.logger.handlers:
                if isinstance(h, logging.FileHandler):
                    file_handler = h
                    break

        self.assertIsNotNone(file_handler, "No se encontró FileHandler")
        # Ahora el nivel debería ser DEBUG (10)
        self.assertEqual(file_handler.level, logging.DEBUG)

        console_handler = None
        for h in logger.logger.handlers:
            if isinstance(h, logging.StreamHandler):
                console_handler = h
                break
        self.assertIsNotNone(console_handler, "No se encontró StreamHandler")

    def test_log_format(self):
        logger = Logger()
        handlers = logger.logger.handlers
        file_handler = next((h for h in handlers if isinstance(h, logging.FileHandler)), None)
        formatter = file_handler.formatter
        self.assertIsNotNone(formatter)
        fmt = formatter._fmt
        self.assertIn('%(asctime)s', fmt)
        self.assertIn('%(name)s', fmt)
        self.assertIn('%(levelname)s', fmt)
        self.assertIn('%(message)s', fmt)


if __name__ == '__main__':
    unittest.main()