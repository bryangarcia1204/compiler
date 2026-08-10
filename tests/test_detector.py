import unittest
from src.compiler_detector import CompilerDetector

class TestDetector(unittest.TestCase):
    def test_detection(self):
        tools = CompilerDetector.get_all_tools()
        self.assertIsInstance(tools, list)

if __name__ == '__main__':
    unittest.main()