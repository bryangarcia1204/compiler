"""Pruebas para el cliente de IA."""

import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.utils.ai_client import AIClient


class TestAIClient:
    """Pruebas para AIClient."""

    def test_init_openai_client(self):
        """Prueba la inicialización del cliente OpenAI."""
        with patch('src.utils.ai_client.OPENAI_AVAILABLE', True):
            client = AIClient(
                provider='openai',
                api_key='fake-key',
                model='gpt-4o-mini'
            )
            assert client.provider == 'openai'
            assert client.api_key == 'fake-key'
            assert client.model == 'gpt-4o-mini'

    def test_init_plataformia_client(self):
        """Prueba la inicialización del cliente PlataformIA."""
        with patch('src.utils.ai_client.OPENAI_AVAILABLE', True):
            client = AIClient(
                provider='plataformia',
                api_key='pk-fake',
                model='agent-xs'
            )
            assert client.provider == 'plataformia'
            assert client.api_key == 'pk-fake'
            assert client.model == 'agent-xs'

    # def test_init_tinyllama_client(self):
    #     """Prueba la inicialización de TinyLlama."""
    #     with patch('src.ai_client.LLAMA_CPP_AVAILABLE', True):
    #         with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
    #             f.write(b'fake model')
    #             f.close()

    #             client = AIClient(
    #                 provider='tinyllama',
    #                 model_path=f.name,
    #                 n_ctx=512
    #             )
    #             assert client.provider == 'tinyllama'
    #             assert client.model_path == f.name
    #             assert client.n_ctx == 512
    #             os.unlink(f.name)

    def test_chat_openai_mock(self):
        """Prueba el método chat con mock de OpenAI."""
        with patch('src.utils.ai_client.OPENAI_AVAILABLE', True):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello, World!"

            client = AIClient(provider='openai', api_key='fake')
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response

            response = client.chat(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.5
            )

            assert response == "Hello, World!"

    # def test_chat_tinyllama_mock(self):
    #     """Prueba el método chat con TinyLlama."""
    #     with patch('src.utils.ai_client.LLAMA_CPP_AVAILABLE', True):
    #         mock_llama = MagicMock()
    #         mock_llama.return_value = {
    #             'choices': [{'text': 'Hola, soy TinyLlama'}]
    #         }

    #         with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
    #             f.write(b'fake model')
    #             f.close()

    #             client = AIClient(
    #                 provider='tinyllama',
    #                 model_path=f.name
    #             )
    #             client.client = mock_llama

    #             response = client.chat(
    #                 messages=[{"role": "user", "content": "Hola"}],
    #                 temperature=0.1
    #             )

    #             assert response == 'Hola, soy TinyLlama'
    #             os.unlink(f.name)

    # def test_format_messages_for_llama(self):
    #     """Prueba el formateo de mensajes para TinyLlama."""
    #     client = AIClient(provider='tinyllama')
    #     messages = [
    #         {"role": "system", "content": "Eres un asistente."},
    #         {"role": "user", "content": "Hola"}
    #     ]
    #     formatted = client._format_messages_for_llama(messages)

    #     assert '<|system|>' in formatted
    #     assert 'Eres un asistente.' in formatted
    #     assert '<|user|>' in formatted
    #     assert 'Hola' in formatted
    #     assert '<|assistant|>' in formatted

    def test_generate_code(self):
        """Prueba la generación de código."""
        with patch('src.utils.ai_client.OPENAI_AVAILABLE', True):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "print('Hello')"

            client = AIClient(provider='openai', api_key='fake')
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response

            code = client.generate_code(
                prompt="Genera un print",
                context="Proyecto Python",
                language="python"
            )

            assert code == "print('Hello')"

    def test_analyze_project_json(self):
        """Prueba el análisis de proyecto con respuesta JSON."""
        with patch('src.utils.ai_client.OPENAI_AVAILABLE', True):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"project_type": "extension"}'

            client = AIClient(provider='openai', api_key='fake')
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response

            result = client.analyze_project("Resumen del proyecto")
            assert result is not None
            assert result['project_type'] == 'extension'

    def test_is_available(self):
        """Prueba la verificación de disponibilidad del cliente."""
        client = AIClient(provider='openai', api_key='fake')
        client.client = MagicMock()
        assert client.is_available() is True

        client.client = None
        assert client.is_available() is False