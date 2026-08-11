"""Pruebas para la interfaz gráfica con PyQt5."""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt5.QtWidgets import QApplication, QDialog
    from PyQt5.QtCore import Qt
    from src.main import MainWindow
    from src.argument_suggester import ArgumentSuggester
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False


@unittest.skipIf(not HAS_PYQT, "PyQt5 no está instalado")
class TestGUI(unittest.TestCase):
    """Pruebas para la interfaz gráfica."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.show()
        # Esperar a que la detección de herramientas termine (puede ser asíncrona)
        self.window.detecting_tools = False  # Forzar que no esté detectando para pruebas
        self.window.available_tools = [{'name': 'gcc', 'type': 'compiler', 'extensions': ['.c']}]
        self.window.current_tools = self.window.available_tools
        self.window.update_tools_list(self.window.current_tools)

    def tearDown(self):
        self.window.close()

    def test_window_title(self):
        self.assertIn("Compilador", self.window.windowTitle())

    def test_tool_combo_populated(self):
        # Debe haber al menos una herramienta (gcc)
        self.assertGreater(self.window.tools_combo.count(), 0)

    def test_tool_selection(self):
        # Seleccionar el primer elemento
        self.window.tools_combo.setCurrentIndex(0)
        self.assertIsNotNone(self.window.selected_tool)

    def test_output_types_update(self):
        # Seleccionar una herramienta debe actualizar los tipos de salida
        self.window.tools_combo.setCurrentIndex(0)
        # El combo de tipos debe estar habilitado (si no es intérprete)
        self.assertTrue(self.window.output_type_combo.isEnabled())

    @patch('src.main.ArgumentSuggester.get_arguments_for_tool')
    def test_show_argument_suggestions(self, mock_get_args):
        mock_get_args.return_value = [{'flag': '-O2', 'description': 'Optimize', 'category': 'Opt'}]
        # Seleccionar herramienta
        self.window.tools_combo.setCurrentIndex(0)
        # Abrir diálogo de sugerencias
        with patch('PyQt5.QtWidgets.QDialog.exec_') as mock_exec:
            # Simular que el diálogo se ejecuta y se cierra
            mock_exec.return_value = QDialog.Accepted
            self.window.show_argument_suggestions()
            # Verificar que se llamó a get_arguments_for_tool
            mock_get_args.assert_called_once()


if __name__ == '__main__':
    unittest.main()